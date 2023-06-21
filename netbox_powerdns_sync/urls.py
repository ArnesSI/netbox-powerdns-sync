from django.urls import include, path

from utilities.urls import get_model_urls
from . import models, views


urlpatterns = (

    # API Servers
    path('api-servers/', views.ApiServerListView.as_view(), name='apiserver_list'),
    path('api-servers/add/', views.ApiServerEditView.as_view(), name='apiserver_add'),
    #path('api-servers/import/', views.ApiServerBulkImportView.as_view(), name='apiserver_import'),
    #path('api-servers/edit/', views.ApiServerBulkEditView.as_view(), name='apiserver_bulk_edit'),
    path('api-servers/delete/', views.ApiServerBulkDeleteView.as_view(), name='apiserver_bulk_delete'),
    path('api-servers/<int:pk>/', include(get_model_urls('netbox_powerdns_sync', 'apiserver'))),

    # Zones
    path('zones/', views.ZoneListView.as_view(), name='zone_list'),
    path('zones/add/', views.ZoneEditView.as_view(), name='zone_add'),
    #path('zones/import/', views.ZoneBulkImportView.as_view(), name='zone_import'),
    #path('zones/edit/', views.ZoneBulkEditView.as_view(), name='zone_bulk_edit'),
    path('zones/delete/', views.ZoneBulkDeleteView.as_view(), name='zone_bulk_delete'),
    path('zones/<int:pk>/', include(get_model_urls('netbox_powerdns_sync', 'zone'))),

    path('sync/', views.SyncJobsView.as_view(), name='sync_jobs'),
    path('sync/schedule/', views.SyncScheduleView.as_view(), name='sync_schedule'),
    path('sync/<int:job_pk>/', views.SyncResultView.as_view(), name='sync_result'),

)
