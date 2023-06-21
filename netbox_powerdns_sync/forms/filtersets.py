from django import forms
from dcim.models import DeviceRole
from netbox.forms import NetBoxModelFilterSetForm
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import DynamicModelMultipleChoiceField, TagFilterField

from ..choices import NamingDeviceChoices, NamingFgrpGroupChoices, NamingIpChoices
from ..fields import MatchTagFilterField
from ..models import ApiServer, Zone


__all__ = (
    "ApiServerFilterForm",
    "ZoneFilterForm",
)


class ApiServerFilterForm(NetBoxModelFilterSetForm):
    model = ApiServer

    zone_id = DynamicModelMultipleChoiceField(
        queryset=Zone.objects.all(),
        required=False,
        null_option="None",
        label="Zone",
    )
    enabled = forms.NullBooleanField(
        required=False,
        label="Is Enabled",
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    tag = TagFilterField(model)


class ZoneFilterForm(NetBoxModelFilterSetForm):
    model = Zone

    api_server_id = DynamicModelMultipleChoiceField(
        queryset=ApiServer.objects.all(),
        required=False,
        null_option="None",
        label="API Server",
    )
    enabled = forms.NullBooleanField(
        required=False,
        label="Is Enabled",
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    reverse = forms.NullBooleanField(
        required=False,
        label="Reverse zones",
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES
        )
    )
    match_tags = MatchTagFilterField()
    match_device_roles = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        null_option="None",
        label="Match Device Roles",
    )
    naming_ip_method = forms.MultipleChoiceField(
        required=False,
        label="IP naming method",
        choices=NamingIpChoices,
    )
    naming_device_method = forms.MultipleChoiceField(
        required=False,
        label="Device naming method",
        choices=NamingDeviceChoices,
    )
    naming_fgrpgroup_method = forms.MultipleChoiceField(
        required=False,
        label="FHRP Group naming method",
        choices=NamingFgrpGroupChoices,
    )
    tag = TagFilterField(model)
