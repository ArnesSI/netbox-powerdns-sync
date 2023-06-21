from django import forms
from django.core.exceptions import ValidationError
from netbox.forms import NetBoxModelForm
from utilities.forms import add_blank_choice

from ..choices import NamingDeviceChoices, NamingFgrpGroupChoices, NamingIpChoices
from ..models import ApiServer, Zone
from ..utils import is_reverse

__all__ = (
    "ApiServerForm",
    "ZoneForm",
)


class ApiServerForm(NetBoxModelForm):
    fieldsets = (
        ("API Server", (
            "name", "api_url", "api_token", "description", "enabled", "tags",
        )),
    )

    class Meta:
        model = ApiServer
        fields = [
            "name", "api_url", "api_token", "description", "enabled", "tags",
        ]


class ZoneForm(NetBoxModelForm):
    naming_ip_method = forms.ChoiceField(
        choices=add_blank_choice(NamingIpChoices),
        required=False,
        label='From IP',
        help_text="How to construct DNS name from IP address. Leave blank to ignore.",
    )
    naming_device_method = forms.ChoiceField(
        choices=add_blank_choice(NamingDeviceChoices),
        required=False,
        label='From device',
        help_text="How to construct DNS name from device IP is assigned to. Leave blank to ignore.",
    )
    naming_fgrpgroup_method = forms.ChoiceField(
        choices=add_blank_choice(NamingFgrpGroupChoices),
        required=False,
        label='From FHRP Group',
        help_text="How to construct DNS name from FHRP Group IP is assigned to. Leave blank to ignore.",
    )

    fieldsets = (
        ("DNS Zone", (
            "name", "description", "enabled", "api_servers", "is_default",
            "default_ttl",
        )),
        ("Matchers", (
            "match_ipaddress_tags", "match_interface_tags",
            "match_device_tags", "match_fhrpgroup_tags", "match_device_roles",
            "match_interface_mgmt_only", 
        )),
        ("Naming methods", (
            "naming_ip_method", "naming_device_method", "naming_fgrpgroup_method",
        )),
        ("General", ("tags",)),
    )

    class Meta:
        model = Zone
        fields = [
            "name", "description", "enabled", "api_servers", "is_default",
            "default_ttl", "match_ipaddress_tags", "match_interface_tags",
            "match_device_tags", "match_fhrpgroup_tags", "match_device_roles",
            "match_interface_mgmt_only", "naming_ip_method", "naming_device_method",
            "naming_fgrpgroup_method", "tags",
        ]

    def clean(self):
        data = super().clean()
        self.clean_match_tags(data)
        self.clean_match_roles(data)
        self.clean_naming_methods(data)
        return data

    def clean_match_tags(self, data):
        if not is_reverse(data["name"]):
            return
        fields = (
            "match_ipaddress_tags",
            "match_interface_tags",
            "match_device_tags",
            "match_fhrpgroup_tags",
        )
        for f in fields:
            if data.get(f):
                self.add_error(f, "Cannot set match tags for reverse zone")

    def clean_match_roles(self, data):
        if not is_reverse(data["name"]):
            return
        if data.get("match_device_roles"):
            self.add_error("match_device_roles", "Cannot set match roles for reverse zone")

    def clean_naming_methods(self, data):
        if not is_reverse(data["name"]):
            return
        fields = (
            "naming_ip_method",
            "naming_device_method",
            "naming_fgrpgroup_method",
        )
        for f in fields:
            if data.get(f):
                self.add_error(f, "Cannot set naming methods for reverse zone")
