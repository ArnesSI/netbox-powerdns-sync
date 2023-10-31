import importlib

from dcim.models import Interface, Device
from ipam.models import FHRPGroup, IPAddress
from virtualization.models import VMInterface

from .models import Zone
from .utils import make_canonical, make_dns_label


def _load_class(path: str) -> object:
    try:
        module_path, class_name = path.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_path)
        klass = getattr(module, class_name)
        return klass
    except:
        return None


def generate_fqdn(ip: IPAddress, zone: Zone) -> str | None:
    """
    Generate a fully qualified domain name (FQDN) based on the given IP address and DNS zone.

    Args:
        ip (IPAddress): The IP address for which to generate the FQDN.
        zone (Zone): The DNS zone to which the FQDN belongs.

    Returns:
        str|None: The generated FQDN, or None if the zone is not provided or no naming method is available.

    Examples:
        >>> generate_fqdn(ip, zone)
        'example.com'
    """

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
    """
    Base class for generating fully qualified domain names (FQDNs) based on IP addresses and zones.

    Args:
        ip: The IP address associated with the FQDN.
        zone: The DNS zone where the FQDN belongs.

    Attributes:
        ip (IPAddress): The IP address associated with the FQDN.
        zone (Zone): The DNS zone where the FQDN belongs.
        interface (Interface|VMInterface|None): The interface associated with the IP address.
        host (Device|VirtualMachine|None): The host device or virtual machine associated with the IP address.

    Methods:
        make_fqdn: Generate a fully qualified domain name (FQDN) based on the IP address and zone.
        make_name: Generate a DNS name based on the host and interface attributes.
        _populate_host_interface: Populate the host and interface attributes based on the assigned object of the IP address.

    Raises:
        NotImplementedError: If the derived class does not implement the `make_name` method.

    Examples:
        >>> obj = NamingBase(ip, zone)
        >>> obj.make_fqdn()
        'example.com'
    """

    def __init__(self, ip: IPAddress, zone: Zone):
        self.ip = ip
        self.zone = zone
        self.interface = None
        self.host = None
        self.tld = None

    def make_fqdn(self) -> str | None:
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

    def make_name(self) -> str | None:
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
    Generate a DNS name based on the host and interface attributes.

    Returns:
        str|None: The generated DNS name, or None if the host attribute is None.

    Raises:
        None

    Examples:
        >>> obj = NamingDeviceByInterfacePrimary()
        >>> obj.make_name()
        'example.com'
    """

    def make_name(self) -> str | None:
        """
        Generate a DNS name based on the host and interface attributes.

        Returns:
            str|None: The generated DNS name, or None if the host attribute is None.

        Raises:
            None

        Examples:
            >>> obj = ClassName()
            >>> obj.make_name()
            'example.com'
        """

        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            # this doesnt make much sense
            # if self.ip != self.host.primary_ip4 and self.ip != self.host.primary_ip6:
            if self.interface and self.interface.name:
                name = (
                    make_dns_label(self.interface.name)
                    + "."
                    + name
                    + "."
                    + "productsup.int."
                )
            return name


class NamingDeviceByInterface(NamingBase):
    """Generate name in formatted as: interface.device.zone"""

    def make_name(self) -> str | None:
        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            name = make_dns_label(self.interface.name) + "." + name
            return name


class NamingDeviceName(NamingBase):
    """Generate name as: device.zone"""

    def make_name(self) -> str | None:
        self._populate_host_interface()
        if self.host:
            name = self.host.name
            name = ".".join(map(make_dns_label, name.split(".")))
            return name


class NamingIpDnsName(NamingBase):
    """Use IPAddress.dns_name"""

    def make_name(self) -> str | None:
        if self.ip.dns_name:
            return self.ip.dns_name


class NamingIpReverse(NamingBase):
    """
    Generate a DNS name based on the reverse DNS of the IP address.

    Returns:
        str|None: The generated DNS name, or None if the IP address does not have a reverse DNS.

    Examples:
        >>> obj = NamingIpReverse(ip, zone)
        >>> obj.make_name()
        'example.com'
    """

    def make_name(self) -> str | None:
        """
        Generate a DNS name based on the reverse DNS of the IP address.

        Returns:
            str|None: The generated DNS name, or None if the IP address does not have a reverse DNS.
        """

        return ".".join(self.ip.address.ip.reverse_dns.split(".")[:-3])


class NamingFGRPGroupName(NamingBase):
    """Use FGRPGroup name: fgrp-group.zone"""

    def make_name(self) -> str | None:
        if isinstance(self.ip.assigned_object, FHRPGroup):
            name = self.ip.assigned_object.name
            name = ".".join(map(make_dns_label, name.split(".")))
