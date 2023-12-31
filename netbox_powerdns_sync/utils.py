import re
import unicodedata

from dcim.models import Device, Interface
from django.contrib.contenttypes.models import ContentType
from extras.choices import ObjectChangeActionChoices
from extras.models import ObjectChange
from extras.plugins.utils import get_plugin_config
from ipam.models import IPAddress
from powerdns import Comment, RRSet
from virtualization.models import VirtualMachine, VMInterface

from .constants import FAMILY_TYPES, PLUGIN_NAME, PTR_TYPE, PTR_ZONE_SUFFIXES


def get_ip_host(ip: IPAddress) -> Device | VirtualMachine | None:
    """
    If IPAddress is assigned to Interface or VMInterface return Device
    or VirtualMachine
    """
    if isinstance(ip.assigned_object, Interface):
        return ip.assigned_object.device
    if isinstance(ip.assigned_object, VMInterface):
        return ip.assigned_object.virtual_machine
    return None


def get_custom_domain(ip: IPAddress) -> str | None:
    """
    Get custom domain from plugin configuration
    """
    custom_domain = get_plugin_config(PLUGIN_NAME, "custom_domain_field")

    if isinstance(ip.assigned_object, Interface):
        device = Device.objects.get(id=ip.assigned_object.device.id)
        return device.cf.get(custom_domain, None)

    if isinstance(ip.assigned_object, VMInterface):
        vm = VirtualMachine.objects.get(id=ip.assigned_object.virtual_machine.id)
        return vm.cf.get(custom_domain, None)

    return ""


def get_ip_ttl(ip: IPAddress) -> int | None:
    """
    Get TTL from IPAddress custom field if set. Else None.
    """
    ttl = None
    ttl_cf = get_plugin_config(PLUGIN_NAME, "ttl_custom_field")
    if ttl_cf and ttl_cf in ip.cf:
        ttl = ip.cf.get(ttl_cf)
        if ttl and not isinstance(ttl, int):
            raise ValueError(f"Custom field {ttl_cf} must be a positive integer")
        if ttl and ttl < 1:
            raise ValueError(f"Custom field {ttl_cf} must be a positive integer")
    return ttl


def can_manage_record(record: dict | RRSet) -> bool:
    """
    Check if record from powerdns is of supported type and if using comments,
    check if it's correct
    """
    comment = get_plugin_config(PLUGIN_NAME, "powerdns_managed_record_comment")
    managed_types = [PTR_TYPE] + list(FAMILY_TYPES.values())
    if record["type"] not in managed_types:
        return False
    if comment:
        for record_comment in record["comments"]:
            if record_comment["content"] == comment:
                return True
        return False
    return True


def get_managed_comment() -> list:
    """
    Return powerdns RRset comment if set in confiuration
    """
    comment = get_plugin_config(PLUGIN_NAME, "powerdns_managed_record_comment")
    if comment:
        return [Comment(comment)]
    else:
        return []


def make_canonical(name: str) -> str:
    """Ensure string ends with a dot"""
    if name[-1] != ".":
        name = name + "."
    return name


def make_dns_label(name: str) -> str:
    """
    Convert to ASCII. Convert spaces, dosts or slashes or repeated dashes to
    single dashes. Remove characters that aren't alphanumerics, underscores,
    hyphens or slashes. Convert to lowercase. Also strip leading and trailing
    whitespace, dashes, and underscores.
    (adapted from django's slugify function)
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s\-\/\._]", "", name.lower())
    return re.sub(r"[_\.\/\-\s]+", "-", name).strip("-_")


def is_reverse(name: str) -> bool:
    return any(map(lambda s: name.endswith(s), PTR_ZONE_SUFFIXES))


def find_objectchange_ip(ip, request_id):
    return ObjectChange.objects.filter(
        action=ObjectChangeActionChoices.ACTION_CREATE,
        request_id=request_id,
        changed_object_type=ContentType.objects.get_for_model(ip),
        changed_object_id=ip.pk,
    )

def set_dns_name(ip_address_str: str, dns_name_str: str) -> bool:
    """
    Set the DNS name for a given IPAddress in NetBox.
    
    Parameters:
    - ip_address_str (str): The IP address for which the DNS name needs to be set.
    - dns_name_str (str): The DNS name to set for the given IP address.
    
    Returns:
    - bool: True if the operation succeeded, False otherwise.
    """
    
    try:
        print(f"Setting DNS name {dns_name_str} for IP address {ip_address_str}")
        ip_address = IPAddress.objects.get(address=str(ip_address_str))
        ip_address.dns_name = dns_name_str
        ip_address.save()
        return True
    except IPAddress.DoesNotExist:
        print(f"IP Address {ip_address_str} not found in the database.")
        return False
    except Exception as e:
        print(f"Error setting DNS name: {e}")
        return False
