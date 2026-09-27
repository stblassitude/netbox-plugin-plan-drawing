from netbox.api.authentication import TokenPermissions
from netbox.api.viewsets import NetBoxModelViewSet, NetBoxReadOnlyModelViewSet
from utilities.query import count_related

from ..filtersets import PlanDrawingElementFilterSet, PlanDrawingFilterSet
from ..models import PlanDrawing, PlanDrawingElement
from .serializers import PlanDrawingElementSerializer, PlanDrawingSerializer


class PlanDrawingViewSet(NetBoxModelViewSet):
    queryset = PlanDrawing.objects.annotate(
        element_count=count_related(PlanDrawingElement, 'drawing'),
    )
    serializer_class = PlanDrawingSerializer
    filterset_class = PlanDrawingFilterSet


class PlanDrawingElementPermissions(TokenPermissions):
    """
    Drawing elements can be viewed by users who may view drawings; the queryset is restricted
    to the drawings they may view (see PlanDrawingElementQuerySet).
    """
    perms_map = {
        **TokenPermissions.perms_map,
        'GET': ['netbox_plugin_plan_drawing.view_plandrawing'],
        'HEAD': ['netbox_plugin_plan_drawing.view_plandrawing'],
    }

    def has_object_permission(self, request, view, obj):
        return True


class PlanDrawingElementViewSet(NetBoxReadOnlyModelViewSet):
    queryset = PlanDrawingElement.objects.select_related('drawing', 'assigned_object_type')
    permission_classes = (PlanDrawingElementPermissions,)
    serializer_class = PlanDrawingElementSerializer
    filterset_class = PlanDrawingElementFilterSet
