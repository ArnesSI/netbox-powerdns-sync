from netbox.views import generic
from utilities.utils import count_related
from utilities.views import register_model_view

from .. import filtersets, forms, tables
from ..models import ApiServer, Zone

__all__ = (
    "ApiServerListView",
    "ApiServerView",
    "ApiServerEditView",
    "ApiServerDeleteView",
    #"ApiServerBulkImportView",
    #"ApiServerBulkEditView",
    "ApiServerBulkDeleteView",
)

class ApiServerListView(generic.ObjectListView):
    queryset = ApiServer.objects.annotate(
        zone_count=count_related(Zone, 'api_servers'),
    )
    filterset = filtersets.ApiServerFilterSet
    filterset_form = forms.ApiServerFilterForm
    table = tables.ApiServerTable


@register_model_view(ApiServer)
class ApiServerView(generic.ObjectView):
    queryset = ApiServer.objects.all()

    def get_extra_context(self, request, instance):
        zones = Zone.objects.restrict(request.user, 'view').filter(api_servers=instance)
        zone_table = tables.ZoneTable(zones, user=request.user)
        zone_table.columns.hide('api_server_count')
        zone_table.configure(request)

        return {
            'zones': zones,
            'zone_table': zone_table,
        }


@register_model_view(ApiServer, 'edit')
class ApiServerEditView(generic.ObjectEditView):
    queryset = ApiServer.objects.all()
    form = forms.ApiServerForm


@register_model_view(ApiServer, 'delete')
class ApiServerDeleteView(generic.ObjectDeleteView):
    queryset = ApiServer.objects.all()


# class ApiServerBulkImportView(generic.BulkImportView):
    # queryset = ApiServer.objects.all()
    # model_form = forms.ApiServerImportForm


# class ApiServerBulkEditView(generic.BulkEditView):
    # queryset = ApiServer.objects.annotate(
        # zone_count=count_related(Zone, 'api_servers'),
    # )
    # filterset = filtersets.ApiServerFilterSet
    # table = tables.ApiServerTable
    # form = forms.ApiServerBulkEditForm


class ApiServerBulkDeleteView(generic.BulkDeleteView):
    queryset = ApiServer.objects.annotate(
        zone_count=count_related(Zone, 'api_servers'),
    )
    filterset = filtersets.ApiServerFilterSet
    table = tables.ApiServerTable
