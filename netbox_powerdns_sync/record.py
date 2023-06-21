import powerdns

from .utils import can_manage_record, get_managed_comment


class DnsRecord:
    def __init__(self, name:str, data:str, dns_type:str, zone_name:str, ttl:int):
        self.name = name.replace(zone_name, "")
        self.name = self.name.rstrip(".")
        self.data = data
        self.dns_type = dns_type
        self.ttl = ttl
        self.zone_name = zone_name

    @classmethod
    def from_pdns_record(cls, record:dict, zone:powerdns.interface.PDNSZone) -> tuple['DnsRecord']:
        dns_records = set()
        if not can_manage_record(record):
            return set()
        for content in record["records"]:
            dns_record = cls(
                name=record["name"],
                dns_type=record["type"],
                ttl=record["ttl"],
                data=content["content"],
                zone_name=zone.name,
            )
            dns_records.add(dns_record)
        return dns_records

    def as_rrset(self) -> powerdns.RRSet:
        return powerdns.RRSet(self.name, self.dns_type, [self.data], ttl=self.ttl, comments=get_managed_comment())

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.dns_type, self.ttl, self.data, self.zone_name]))

    def __eq__(self, other: "DnsRecord") -> bool:
        return self.name == other.name and self.data == other.data and \
            self.dns_type == other.dns_type and self.ttl == other.ttl and \
            self.zone_name == other.zone_name

    def __repr__(self) -> str:
        return f"<DNSRecord: {self}>"

    def __str__(self) -> str:
        return f"{self.name}.{self.zone_name} {self.dns_type} {self.ttl} {self.data}"
