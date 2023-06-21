from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer, NestedTagSerializer
from dcim.api.serializers import NestedDeviceRoleSerializer

from .nested_serializers import *
from ..models import ApiServer, Zone


class ApiServerSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_powerdns_sync-api:apiserver-detail"
    )
    zones = NestedZoneSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = ApiServer
        fields = (
            "id", "url", "display", "name", "api_url", "api_token", "enabled",
            "description", "zones", "tags", "custom_fields", "created", "last_updated"
        )


class ZoneSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_powerdns_sync-api:zone-detail"
    )
    is_reverse = serializers.BooleanField(read_only=True)
    api_servers = NestedApiServerSerializer(many=True, required=True)
    match_ipaddress_tags = NestedTagSerializer(many=True, required=False)
    match_interface_tags = NestedTagSerializer(many=True, required=False)
    match_device_tags = NestedTagSerializer(many=True, required=False)
    match_fhrpgroup_tags = NestedTagSerializer(many=True, required=False)
    match_device_roles = NestedDeviceRoleSerializer(many=True, required=False)

    class Meta:
        model = Zone
        fields = (
            "id", "url", "display", "name", "description", "api_servers", "enabled",
            "is_reverse", "is_default", "default_ttl", "match_ipaddress_tags",
            "match_interface_tags", "match_device_tags", "match_fhrpgroup_tags",
            "match_device_roles", "match_interface_mgmt_only", "naming_ip_method",
            "naming_device_method", "naming_fgrpgroup_method", "tags",
            "custom_fields", "created", "last_updated"
        )
