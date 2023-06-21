from django import forms
from extras.forms import ScriptForm
from utilities.forms.fields import DynamicModelMultipleChoiceField

from ..models import Zone


class ZoneScheduleForm(ScriptForm):
    zones = DynamicModelMultipleChoiceField(
        queryset=Zone.objects.enabled(),
        query_params={"enabled": True},
        help_text="Only enabled zones can be scheduled",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("_commit")
        self.fields["_schedule_at"].help_text = self.fields["_schedule_at"].help_text.replace("script", "sync")
        self.fields["_interval"].help_text = self.fields["_interval"].help_text.replace("script", "sync")
