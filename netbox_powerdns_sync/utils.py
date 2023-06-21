import re
import unicodedata
from powerdns import Comment, RRSet
from django.contrib.contenttypes.models import ContentType
from dcim.models import Device, Interface
from extras.choices import ObjectChangeActionChoices
from extras.plugins import get_plugin_config
from extras.models import ObjectChange
from ipam.models import IPAddress
from virtualization.models import VirtualMachine, VMInterface

from .constants import PLUGIN_NAME, FAMILY_TYPES, PTR_TYPE, PTR_ZONE_SUFFIXES


def get_ip_host(ip:IPAddress) -> Device|VirtualMachine|None:
    """
    If IPAddress is assigned to Interface or VMInterface return Device
    or VirtualMachine
    """
    if isinstance(ip.assigned_object, Interface):
        return ip.assigned_object.device
    if isinstance(ip.assigned_object, VMInterface):
        return ip.assigned_object.virtual_machine
    return None


def get_ip_ttl(ip: IPAddress) -> int|None:
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


def can_manage_record(record: dict|RRSet) -> bool:
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
    """ Ensure string ends with a dot """
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


def is_reverse(name:str) -> bool:
    return any(map(lambda s: name.endswith(s), PTR_ZONE_SUFFIXES))


def find_objectchange_ip(ip, request_id):
    return ObjectChange.objects.filter(
        action=ObjectChangeActionChoices.ACTION_CREATE,
        request_id=request_id,
        changed_object_type=ContentType.objects.get_for_model(ip),
        changed_object_id=ip.pk,
    )
