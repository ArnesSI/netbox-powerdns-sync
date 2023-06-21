from rest_framework import serializers

from netbox.api.serializers import WritableNestedSerializer
from ..models import ApiServer, Zone

__all__ = (
    "NestedApiServerSerializer",
    "NestedZoneSerializer",
)


class NestedApiServerSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_powerdns_sync-api:apiserver-detail"
    )

    class Meta:
        model = ApiServer
        fields = ("id", "url", "display", "name", "api_url", "api_token", "enabled")


class NestedZoneSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_powerdns_sync-api:zone-detail"
    )

    class Meta:
        model = Zone
        fields = ("id", "url", "display", "name", "enabled")
