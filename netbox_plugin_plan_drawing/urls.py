from django.urls import include, path

from utilities.urls import get_model_urls

from . import views  # noqa: F401 -- registers the model views

app_name = 'netbox_plugin_plan_drawing'

urlpatterns = (
    path('drawings/', include(get_model_urls('netbox_plugin_plan_drawing', 'plandrawing', detail=False))),
    path('drawings/<int:pk>/', include(get_model_urls('netbox_plugin_plan_drawing', 'plandrawing'))),
)
