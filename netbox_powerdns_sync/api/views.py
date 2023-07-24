from netbox.api.viewsets import NetBoxModelViewSet
from .. import filtersets, models
from .serializers import ApiServerSerializer, ZoneSerializer


class ApiServerViewSet(NetBoxModelViewSet):
    queryset = models.ApiServer.objects.prefetch_related("tags", "zones")
    serializer_class = ApiServerSerializer
    filterset_class = filtersets.ApiServerFilterSet


class ZoneViewSet(NetBoxModelViewSet):
    queryset = models.Zone.objects.prefetch_related(
        "api_servers",
        "match_ipaddress_tags",
        "match_interface_tags",
        "match_device_tags",
        "match_fhrpgroup_tags",
        "match_device_roles",
        "tags"
    )
    serializer_class = ZoneSerializer
    filterset_class = filtersets.ZoneFilterSet
