import django_filters
from django.db.models import Q
from dcim.models import DeviceRole
from netbox.filtersets import NetBoxModelFilterSet
from utilities import filters

from .choices import NamingDeviceChoices, NamingIpChoices, NamingFgrpGroupChoices
from .models import *

__all__ = (
    "ApiServerFilterSet",
    "ZoneFilterSet",
)


class ApiServerFilterSet(NetBoxModelFilterSet):
    zone_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        field_name="zones",
        label="Zone (ID)",
    )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(api_url__icontains=value)
        )

    class Meta:
        model = ApiServer
        fields = ["id", "name", "description", "api_url", "enabled"]


class ZoneFilterSet(NetBoxModelFilterSet):
    api_server_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ApiServer.objects.all(),
        field_name="api_servers",
        label="API Server (ID)",
    )
    reverse = django_filters.BooleanFilter(
        method="filter_reverse",
        label="Reverse zones"
    )
    match_tags = filters.MultiValueCharFilter(
        method="filter_match_tags",
        label="Match Tags",
    )
    match_device_roles = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceRole.objects.all(),
        label="Match Device Roles (ID)",
    )
    naming_ip_method = django_filters.MultipleChoiceFilter(
        choices=NamingIpChoices,
    )
    naming_device_method = django_filters.MultipleChoiceFilter(
        choices=NamingDeviceChoices,
    )
    naming_fgrpgroup_method = django_filters.MultipleChoiceFilter(
        choices=NamingFgrpGroupChoices,
    )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)|
            Q(description__icontains=value)
        )

    def filter_match_tags(self, queryset, name, value):        
        query = Q(match_ipaddress_tags__slug__in=value)|\
            Q(match_interface_tags__slug__in=value)|\
            Q(match_device_tags__slug__in=value)|\
            Q(match_fhrpgroup_tags__slug__in=value)
        return queryset.filter(query).distinct()

    def filter_reverse(self, queryset, name, value):
        if value:
            return queryset.reverse()
        else:
            return queryset.forward()

    class Meta:
        model = Zone
        fields = ["id", "name", "description", "enabled"]
