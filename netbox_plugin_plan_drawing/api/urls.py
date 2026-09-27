from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_plugin_plan_drawing'

router = NetBoxRouter()
router.register('drawings', views.PlanDrawingViewSet)
router.register('elements', views.PlanDrawingElementViewSet)

urlpatterns = router.urls
