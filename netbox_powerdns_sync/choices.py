from utilities.choices import ChoiceSet


class NamingIpChoices(ChoiceSet):
    key = "Zone.naming_ip_method"
    CHOICES = [
        ("netbox_powerdns_sync.naming.NamingIpDnsName", "Use IP DNS name field"),
        ("netbox_powerdns_sync.naming.NamingIpReverse", "Use PTR format for IP (without arpa domain)"),
    ]


class NamingDeviceChoices(ChoiceSet):
    key = "Zone.naming_device_method"
    CHOICES = [
        ("netbox_powerdns_sync.naming.NamingDeviceName", "Use device name only"),
        ("netbox_powerdns_sync.naming.NamingDeviceByInterface", "Use interface.device format"),
        ("netbox_powerdns_sync.naming.NamingDeviceByInterfacePrimary", "Use interface.device format and device only for primary IP"),
    ]


class NamingFgrpGroupChoices(ChoiceSet):
    key = "Zone.naming_fhrpgroup_method"
    CHOICES = [
        ("netbox_powerdns_sync.naming.NamingFGRPGroupName", "Use FHRP Group name only"),
    ]
