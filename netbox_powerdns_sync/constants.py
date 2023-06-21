PLUGIN_NAME = "netbox_powerdns_sync"
FAMILY_TYPES = {
    4: "A",
    6: "AAAA",
}
PTR_TYPE = "PTR"
PTR_ZONE_SUFFIXES = (
    "in-addr.arpa.",
    "ip6.arpa."
)

JOB_NAME_IP = "PowerDNS IP Address update"
JOB_NAME_INTERFACE = "PowerDNS Interface update"
JOB_NAME_DEVICE = "PowerDNS Device update"
JOB_NAME_SYNC = "PowerDNS zone sync"
