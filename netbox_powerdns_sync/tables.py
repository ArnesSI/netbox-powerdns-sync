import django_tables2 as tables
from core.tables import JobTable
from netbox.tables import NetBoxTable, columns

from . import models


__all__ = (
    "ApiServerTable",
    "SyncJobTable",
    "ZoneTable",
)

SYNC_URL_ID = """<a href="{% url 'plugins:netbox_powerdns_sync:sync_result' job_pk=value %}">{{ value }}</a>"""
SYNC_URL_NAME = """<a href="{% url 'plugins:netbox_powerdns_sync:sync_result' job_pk=record.id %}">{{ value }}</a>"""
DEVICE_ROLE_COLUMN = """
{% for role in value.all %}
    <span class="badge" style="color: {{ role.color|fgcolor }}; background-color: #{{ role.color }}">
        <a href="{{ role.get_absolute_url }}">{{ role }}</a>
    </span>
{% endfor %}
"""
ZONE_EXTRA_BUTTONS = """
{% if record.enabled %}
    <a href="{% url 'plugins:netbox_powerdns_sync:sync_schedule' %}?zones={{ record.pk }}" class="btn btn-sm btn-primary" title="Schedule full sync for zone">
        <span class="mdi mdi-sync" aria-hidden="true"></span>
    </a>
{% else %}
    <a href="#" class="btn btn-sm btn-primary disabled" title="Schedule full sync for zone">
        <span class="mdi mdi-sync" aria-hidden="true"></span>
    </a>
{% endif %}
"""


class ApiServerTable(NetBoxTable):
    name = tables.Column(
        linkify=True
    )
    zone_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_powerdns_sync:zone_list",
        url_params={"api_server_id": "pk"},
        verbose_name="Zones"
    )
    enabled = columns.BooleanColumn()
    tags = columns.TagColumn(
        url_name="plugins:netbox_powerdns_sync:apiserver_list"
    )

    class Meta(NetBoxTable.Meta):
        model = models.ApiServer
        fields = (
            "pk", "id", "name", "zone_count", "description", "enabled", "api_url",
            "tags", "actions", "created", "last_updated",
        )
        default_columns = ("pk", "name", "zone_count", "description", "enabled")


class SyncJobTable(JobTable):
    id = tables.TemplateColumn(
        template_code=SYNC_URL_ID,
    )
    name = tables.TemplateColumn(
        template_code=SYNC_URL_NAME,
    )

    class Meta(JobTable.Meta):
        pass


class ZoneTable(NetBoxTable):
    name = tables.Column(
        linkify=True
    )
    api_server_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_powerdns_sync:apiserver_list",
        url_params={"zone_id": "pk"},
        verbose_name="API Servers"
    )
    enabled = columns.BooleanColumn()
    is_default = columns.BooleanColumn()
    is_reverse = columns.BooleanColumn(
        verbose_name="Reverse zone",
        orderable=False,
    )
    match_ipaddress_tags = columns.TagColumn(
        url_name="ipam:ipaddress_list"
    )
    match_interface_tags = columns.TagColumn(
        url_name="dcim:interface_list"
    )
    match_device_tags = columns.TagColumn(
        url_name="dcim:device_list"
    )
    match_fhrpgroup_tags = columns.TagColumn(
        url_name="ipam:fhrpgroup_list"
    )
    match_device_roles = columns.TemplateColumn(
        template_code=DEVICE_ROLE_COLUMN
    )
    match_interface_mgmt_only = columns.BooleanColumn()
    tags = columns.TagColumn(
        url_name="plugins:netbox_powerdns_sync:zone_list",
    )
    actions = columns.ActionsColumn(
        extra_buttons=ZONE_EXTRA_BUTTONS,
    )

    class Meta(NetBoxTable.Meta):
        model = models.Zone
        fields = (
            "pk", "id", "name", "api_server_count", "description",  "enabled",
            "is_default", "is_reverse", "default_ttl", "match_ipaddress_tags",
            "match_interface_tags", "match_device_tags", "match_fhrpgroup_tags",
            "match_device_roles", "match_interface_mgmt_only", "naming_ip_method",
            "naming_device_method", "naming_fgrpgroup_method", "tags", "actions",
            "created", "last_updated",
        )
        default_columns = ("pk", "name", "enabled", "is_default", "default_ttl")
