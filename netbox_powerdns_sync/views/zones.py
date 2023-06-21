from netbox.views import generic
from utilities.utils import count_related
from utilities.views import register_model_view

from .. import filtersets, forms, tables
from ..models import ApiServer, Zone

__all__ = (
    "ZoneListView",
    "ZoneView",
    "ZoneEditView",
    "ZoneDeleteView",
    #"ZoneBulkImportView",
    #"ZoneBulkEditView",
    "ZoneBulkDeleteView",
)

class ZoneListView(generic.ObjectListView):
    queryset = Zone.objects.annotate(
        api_server_count=count_related(ApiServer, 'zones'),
    )
    filterset = filtersets.ZoneFilterSet
    filterset_form = forms.ZoneFilterForm
    table = tables.ZoneTable


@register_model_view(Zone)
class ZoneView(generic.ObjectView):
    queryset = Zone.objects.all()


@register_model_view(Zone, 'edit')
class ZoneEditView(generic.ObjectEditView):
    queryset = Zone.objects.all()
    form = forms.ZoneForm


@register_model_view(Zone, 'delete')
class ZoneDeleteView(generic.ObjectDeleteView):
    queryset = Zone.objects.all()


# class ZoneBulkImportView(generic.BulkImportView):
    # queryset = Zone.objects.all()
    # model_form = forms.ZoneImportForm


# class ZoneBulkEditView(generic.BulkEditView):
    # queryset = Zone.objects.annotate(
        # zone_count=count_related(Zone, 'api_servers'),
    # )
    # filterset = filtersets.ZoneFilterSet
    # table = tables.ZoneTable
    # form = forms.ZoneBulkEditForm


class ZoneBulkDeleteView(generic.BulkDeleteView):
    queryset = Zone.objects.all()
    filterset = filtersets.ZoneFilterSet
    table = tables.ZoneTable
