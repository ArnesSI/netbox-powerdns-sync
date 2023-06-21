import logging
import powerdns
import traceback
from datetime import timedelta
from django.db.models import Q

from core.choices import JobStatusChoices
from core.models import Job
from dcim.models import Device, Interface
from extras.choices import LogLevelChoices
from ipam.models import IPAddress, FHRPGroup
from netbox_powerdns_sync.constants import FAMILY_TYPES, PTR_TYPE
from virtualization.models import VirtualMachine, VMInterface

from .exceptions import *
from .models import ApiServer, Zone
from .naming import generate_fqdn
from .record import DnsRecord
from .utils import get_ip_ttl, make_dns_label, make_canonical


logger = logging.getLogger("netbox.netbox_powerdns_sync.jobs")


class JobLoggingMixin:
    def log(self, level: str, msg: str) -> None:
        data = self.job.data or {}
        logs = data.get("log", [])
        logs.append({
            "message": msg,
            "status": level,
        })
        data["log"] = logs
        self.job.data = data
    
    def log_debug(self, msg: str) -> None:
        logger.debug(msg)
        self.log(LogLevelChoices.LOG_DEFAULT, msg)

    def log_success(self, msg: str) -> None:
        logger.info(msg)
        self.log(LogLevelChoices.LOG_SUCCESS, msg)

    def log_info(self, msg: str) -> None:
        logger.info(msg)
        self.log(LogLevelChoices.LOG_INFO, msg)

    def log_warning(self, msg: str) -> None:
        logger.warning(msg)
        self.log(LogLevelChoices.LOG_WARNING, msg)

    def log_failure(self, msg: str) -> None:
        logger.error(msg)
        self.log(LogLevelChoices.LOG_FAILURE, msg)


class PowerdnsTask(JobLoggingMixin):
    def __init__(self, job: Job) -> None:
        self.job = job
        self.init_attrs()
    
    def init_attrs(self):
        self.fqdn : str = ""
        self.forward_zone : Zone = None
        self.reverse_zone : Zone = None
        self.make_fqdn_ran : bool = False

    def get_pdns_servers_for_zone(self, zone_name) -> list[tuple[ApiServer, powerdns.interface.PDNSServer]]:
        if not zone_name:
            return []
        zone = Zone.objects.get(name=zone_name)
        servers = []
        for api_server in zone.api_servers.enabled().all():
            api_client = powerdns.PDNSApiClient(
                api_endpoint=api_server.api_url,
                api_key=api_server.api_token,
            )
            api = powerdns.PDNSEndpoint(api_client)
            servers.append((api_server, api.servers[0]))
        return servers

    def add_to_output(self, row):
        if not self.job.data:
            self.job.data = dict()
        if "output" not in self.job.data:
            self.job.data["output"] = []
        self.job.data["output"].append(row)

    def make_name_from_interface(self, interface: Interface|VMInterface, host: Device|VirtualMachine) -> str:
        name = host.name
        name = ".".join(map(make_dns_label, name.split(".")))
        if self.ip != host.primary_ip4 and self.ip != host.primary_ip6:
            name = make_dns_label(interface.name) + "." + name
        return name

    def make_fqdn(self) -> str:
        """ Determines FQDN and sets forward zone """
        if self.make_fqdn_ran:
            return self.fqdn
        self.make_fqdn_ran = True
        if self.determine_forward_zone():
            self.fqdn = generate_fqdn(self.ip, self.forward_zone)
        return self.fqdn

    def determine_forward_zone(self):
        # determine zone from any FQDN names
        name = None
        if self.ip.dns_name:
            name = self.ip.dns_name
        elif isinstance(self.ip.assigned_object, Interface):
            name = self.ip.assigned_object.device.name
        elif isinstance(self.ip.assigned_object, VMInterface):
            name = self.ip.assigned_object.virtual_machine.name
        elif isinstance(self.ip.assigned_object, FHRPGroup):
            name = self.ip.assigned_object.name
        if name:
            self.forward_zone = Zone.get_best_zone(name)
        # determine zone by matching tags or roles
        if not self.forward_zone:
            self.forward_zone = Zone.match_ip(self.ip).first()
        return self.forward_zone

    def make_reverse_domain(self) -> str|None:
        """ Returns reverse domain name """
        return make_canonical(self.ip.address.ip.reverse_dns)

    def create_record(self, dns_record: DnsRecord) -> None:
        for api_server, pdns_server in self.get_pdns_servers_for_zone(dns_record.zone_name):
            zone = pdns_server.get_zone(dns_record.zone_name)
            if not zone:
                raise PowerdnsSyncServerZoneMissing(
                    f"Zone {dns_record.zone_name} not found on server {api_server}"
                )
            self.add_to_output({"action": "CREATE", "rr": str(dns_record), "zone": str(zone), "server": str(api_server)})
            zone.create_records([dns_record.as_rrset()])

    def delete_record(self, dns_record: DnsRecord) -> None:
        for api_server, pdns_server in self.get_pdns_servers_for_zone(dns_record.zone_name):
            zone = pdns_server.get_zone(dns_record.zone_name)
            if not zone:
                raise PowerdnsSyncServerZoneMissing(
                    f"Zone {dns_record.zone_name} not found on server {api_server}"
                )
            self.add_to_output({"action": "DELETE", "rr": str(dns_record), "zone": str(zone), "server": str(api_server)})
            zone.delete_records([dns_record.as_rrset()])


class PowerdnsTaskIP(PowerdnsTask):
    def __init__(self, job: Job) -> None:
        super().__init__(job)
        self.ip : IPAddress = job.object

    @classmethod
    def run_update_ip(cls, job: Job, *args, **kwargs) -> None:
        task = cls(job)
        if job.object_id and not job.object:
            task.job.start()
            task.log_warning("No IP Address object given. IP was probably removed or DB transaction aborted, nothing to do.")
            task.job.terminate(status=JobStatusChoices.STATUS_COMPLETED)
            return
        try:
            task.log_debug("Starting task")
            task.job.start()
            task.log_debug("Creating forward record")
            task.create_forward()
            task.log_debug("Creating reverse record")
            task.create_reverse()
            task.log_success("Finished")
            task.job.terminate()
        except Exception as e:
            task.log_failure(f"error {e}")
            task.job.data = task.job.data or dict()
            task.job.data["exception"] = str(e)
            task.job.terminate(status=JobStatusChoices.STATUS_ERRORED)
            raise e

    def create_forward(self) -> None:
        self.make_fqdn()
        if not self.forward_zone:
            raise PowerdnsSyncNoZoneFound(f"No forward zone found for IP:{self.ip}")
        if not self.fqdn:
            raise PowerdnsSyncNoNameFound(f"No forward name for IP:{self.ip} (zone:{self.forward_zone})")
        name = self.fqdn.replace(self.forward_zone.name, "").rstrip(".")
        dns_record = DnsRecord(
            name=name,
            dns_type=FAMILY_TYPES[self.ip.family],
            data=str(self.ip.address.ip),
            ttl=get_ip_ttl(self.ip) or self.forward_zone.default_ttl,
            zone_name=self.forward_zone.name,
        )
        self.log_info(f"Forward record: {dns_record}")
        self.create_record(dns_record)
        self.log_info(f"Forward record created")

    def create_reverse(self) -> None:
        self.make_fqdn()
        if not self.fqdn:
            raise PowerdnsSyncNoNameFound(f"No forward name for IP:{self.ip}")
        reverse_fqdn = self.make_reverse_domain()
        self.reverse_zone = Zone.get_best_zone(reverse_fqdn)
        if not self.reverse_zone:
            self.log_warning(f"No reverse zone for IP:{self.ip} fqdn:{self.fqdn} Skipping")
            return
        name = reverse_fqdn.replace(self.reverse_zone.name, "").rstrip(".")
        dns_record = DnsRecord(
            name=name,
            dns_type=PTR_TYPE,
            data=self.fqdn,
            ttl=get_ip_ttl(self.ip) or self.reverse_zone.default_ttl,
            zone_name=self.reverse_zone.name,
        )
        self.log_info(f"Reverse record {dns_record}")
        self.create_record(dns_record)
        self.log_info(f"Reverse record created")


class PowerdnsTaskFullSync(PowerdnsTask):
    def __init__(self, job: Job) -> None:
        super().__init__(job)
        self.zone : Zone = job.object

    @classmethod
    def run_full_sync(cls, job: Job, *args, **kwargs) -> None:
        task = cls(job)

        try:
            task.log_debug(f"Starting sync for zone {task.zone}")
            task.job.start()
            if not task.zone.enabled:
                task.log_warning(f"Zone {task.zone} is disabled for updates, not syncing")
                task.job.terminate()
                return
            netbox_records = task.load_netbox_records()
            pdns_records = task.load_pdns_records()
            task.log_info(f"Found record count: netbox:{len(netbox_records)} pdns:{len(pdns_records)}")
            to_delete = pdns_records - netbox_records
            to_create = netbox_records - pdns_records
            task.log_info(f"Record change count: to_delete:{len(to_delete)} to_create:{len(to_create)}")
            for record in to_delete:
                task.delete_record(record)
            for record in to_create:
                task.create_record(record)
            task.log_success("Finished")
            task.job.terminate()
        except PowerdnsSyncNoServers as e:
            task.log_failure(str(e))
            task.job.data = task.job.data or dict()
            task.job.terminate(status=JobStatusChoices.STATUS_ERRORED)
        except Exception as e:
            stacktrace = traceback.format_exc()
            task.log_failure(f"An exception occurred: `{type(e).__name__}: {e}`\n```\n{stacktrace}\n```")
            task.job.data = task.job.data or dict()
            task.job.terminate(status=JobStatusChoices.STATUS_ERRORED)

        # Schedule the next job if an interval has been set
        if job.interval:
            new_scheduled_time = job.scheduled + timedelta(minutes=job.interval)
            Job.enqueue(
                cls.run_full_sync,
                instance=job.object,
                name=job.name,
                user=job.user,
                schedule_at=new_scheduled_time,
                interval=job.interval,
            )

    def get_addresses(self):
        """ Get IPAddress objects that could have DNS records """
        zone_canonical = self.zone.name
        zone_domain = self.zone.name.rstrip(".")
        # filter for FQDN names (ip.dns_name, Device, VM, FHRPGroup)
        query_zone = Q(dns_name__endswith=zone_canonical)|Q(dns_name__endswith=zone_domain)
        query_zone |= Q(interface__device__name__endswith=zone_canonical)|Q(interface__device__name__endswith=zone_domain)
        query_zone |= Q(vminterface__virtual_machine__name__endswith=zone_canonical)|Q(vminterface__virtual_machine__name__endswith=zone_domain)
        query_zone |= Q(fhrpgroup__name__endswith=zone_canonical)|Q(fhrpgroup__name__endswith=zone_domain)
        # filter for matchers (tags & roles)
        query_zone |= Q(tags__in=self.zone.match_ipaddress_tags.all())
        query_zone |= Q(interface__tags__in=self.zone.match_interface_tags.all())
        query_zone |= Q(vminterface__tags__in=self.zone.match_interface_tags.all())
        query_zone |= Q(interface__device__tags__in=self.zone.match_device_tags.all())
        query_zone |= Q(vminterface__virtual_machine__tags__in=self.zone.match_device_tags.all())
        query_zone |= Q(fhrpgroup__tags__in=self.zone.match_fhrpgroup_tags.all())
        query_zone |= Q(interface__device__device_role__in=self.zone.match_device_roles.all())
        query_zone |= Q(vminterface__virtual_machine__role__in=self.zone.match_device_roles.all())
        results = IPAddress.objects.filter(query_zone)
        if self.zone.match_interface_mgmt_only:
            results = results.filter(interface__mgmt_only=True)
        return results

    def load_netbox_records(self) -> set[DnsRecord]:
        records = set()
        ip: IPAddress
        ip_addresses = self.get_addresses()
        self.log_info(f"Found {ip_addresses.count()} matching addresses to check")
        for ip in ip_addresses:
            self.init_attrs()
            self.ip = ip
            self.make_fqdn()
            if not self.forward_zone:
                self.log_info(f"No matching forward zone found for IP:{ip}. Skipping")
                continue
            if not self.fqdn:
                self.log_info(f"No FQDN could be determined for IP:{ip} (zone:{self.forward_zone}). Skipping")
                continue
            if self.forward_zone == self.zone:
                name = self.fqdn.replace(self.forward_zone.name, "").rstrip(".")
                records.add(DnsRecord(
                    name=name,
                    data=str(ip.address.ip),
                    dns_type=FAMILY_TYPES.get(ip.family),
                    zone_name=self.forward_zone.name,
                    ttl=get_ip_ttl(ip) or self.forward_zone.default_ttl,
                ))
            if self.zone.is_reverse:
                reverse_fqdn = self.make_reverse_domain()
                self.reverse_zone = Zone.get_best_zone(reverse_fqdn)
                if not self.reverse_zone:
                    self.log_info(f"No matching reverse zone for {ip} ({self.fqdn}). Skipping")
                    continue
                if self.reverse_zone == self.zone:
                    name = reverse_fqdn.replace(self.reverse_zone.name, "").rstrip(".")
                    records.add(DnsRecord(
                        name=name,
                        data=self.fqdn,
                        dns_type=PTR_TYPE,
                        zone_name=self.reverse_zone.name,
                        ttl=get_ip_ttl(ip) or self.reverse_zone.default_ttl,
                    ))
        return records

    def load_pdns_records(self) -> set[DnsRecord]:
        flat_records = set()
        checked_types = [PTR_TYPE] + list(FAMILY_TYPES.values())
        servers = self.get_pdns_servers_for_zone(self.zone.name)
        if not servers:
            raise PowerdnsSyncNoServers(f"No valid servers found for zone {self.zone}")
        for api_server, pdns_server in servers:
            pdns_zone = pdns_server.get_zone(self.zone.name)
            if not pdns_zone:
                raise PowerdnsSyncServerZoneMissing(
                    f"Zone {self.zone.name} not found on server {api_server}"
                )
            for record in pdns_zone.records:
                if record["type"] not in checked_types:
                    continue
                flat_records.update(DnsRecord.from_pdns_record(record, pdns_zone))
        return flat_records
