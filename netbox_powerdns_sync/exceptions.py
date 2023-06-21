class PowerdnsSyncNoNameFound(Exception):
    pass


class PowerdnsSyncNoZoneFound(Exception):
    pass


class PowerdnsSyncServerError(Exception):
    pass


class PowerdnsSyncServerZoneMissing(PowerdnsSyncServerError):
    pass


class PowerdnsSyncNoServers(PowerdnsSyncServerError):
    pass
