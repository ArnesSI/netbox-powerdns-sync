import importlib
from dcim.models import Interface
from ipam.models import IPAddress, FHRPGroup
from virtualization.models import VMInterface

from .models import Zone
from .utils import make_dns_label, make_canonical


def _load_class(path:str) -> object:
    try:
        module_path, class_name = path.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_path)
        klass = getattr(module, class_name)
        return klass
    except:
        return None


def generate_fqdn(ip: IPAddress, zone:Zone) -> str|None:
    fqdn = None
    if not zone:
        return None
    if zone.naming_ip_method:
        klass = _load_class(zone.naming_ip_method)
        naming_method = klass(ip, zone)
        fqdn = naming_method.make_fqdn()
    if not fqdn and zone.naming_device_method:
        klass = _load_class(zone.naming_device_method)
        naming_method = klass(ip, zone)
        fqdn = naming_method.make_fqdn()
    if not fqdn and zone.naming_fgrpgroup_method:
        klass = _load_class(zone.naming_fgrpgroup_method)
        naming_method = klass(ip, zone)
        fqdn = naming_method.make_fqdn()
    return fqdn


class NamingBase:
    def __init__(self, ip:IPAddress, zone:Zone):
        self.ip = ip
        self.zone = zone
        self.interface = None
        self.host = None
    
    def make_fqdn(self) -> str|None:
        fqdn = None
        name = self.make_name()
        if not name:
            return None
        name = make_canonical(name)
        # check if name already includes zone name
        if name.endswith(self.zone.name):
            fqdn = name
        else:
            fqdn = name + self.zone.name
        return fqdn

    def make_name(self) -> str|None:
        raise NotImplementedError()

    def _populate_host_interface(self):
        if isinstance(self.ip.assigned_object, Interface):
            self.interface = self.ip.assigned_object
            self.host = self.ip.assigned_object.device
        elif isinstance(self.ip.assigned_object, VMInterface):
            self.interface = self.ip.assigned_object
            self.host = self.ip.assigned_object.virtual_machine


class NamingDeviceByInterfacePrimary(NamingBase):
    """
    Generate name in formatted as: interface.device.zone
    If IP is primary, don't prepend interface name
    """
    def make_name(self) -> str|None:
        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            if self.ip != self.host.primary_ip4 and self.ip != self.host.primary_ip6:
                name = make_dns_label(self.interface.name) + "." + name
            return name


class NamingDeviceByInterface(NamingBase):
    """ Generate name in formatted as: interface.device.zone """
    def make_name(self) -> str|None:
        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            name = make_dns_label(self.interface.name) + "." + name
            return name


class NamingDeviceName(NamingBase):
    """ Generate name as: device.zone """
    def make_name(self) -> str|None:
        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            return name


class NamingIpDnsName(NamingBase):
    """ Use IPAddress.dns_name """
    def make_name(self) -> str|None:
        if self.ip.dns_name:
            return self.ip.dns_name


class NamingIpReverse(NamingBase):
    """ Use IPAddress in reverse foramt """
    def make_name(self) -> str|None:
        return ".".join(self.ip.address.ip.reverse_dns.split(".")[:-3])


class NamingFGRPGroupName(NamingBase):
    """ Use FGRPGroup name: fgrp-group.zone """
    def make_name(self) -> str|None:
        if isinstance(self.ip.assigned_object, FHRPGroup):
            name = self.ip.assigned_object.name
            name = ".".join(map(make_dns_label, name.split(".")))
