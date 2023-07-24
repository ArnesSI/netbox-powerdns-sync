from netbox.api.routers import NetBoxRouter
from . import views


app_name = 'netbox_powerdns_sync'

router = NetBoxRouter()
router.register('api-servers', views.ApiServerViewSet)
router.register('zones', views.ZoneViewSet)

urlpatterns = router.urls
