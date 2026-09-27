from dcim.api.serializers import LocationSerializer, SiteSerializer
from netbox.api.fields import ContentTypeField, RelatedObjectCountField
from netbox.api.gfk_fields import GFKSerializerField
from netbox.api.serializers import BaseModelSerializer, PrimaryModelSerializer

from ..models import PlanDrawing, PlanDrawingElement


class PlanDrawingSerializer(PrimaryModelSerializer):
    site = SiteSerializer(nested=True, required=False, allow_null=True)
    location = LocationSerializer(nested=True, required=False, allow_null=True)
    element_count = RelatedObjectCountField('elements')

    class Meta:
        model = PlanDrawing
        fields = (
            'id', 'url', 'display_url', 'display', 'name', 'site', 'location', 'description', 'content',
            'element_count', 'owner', 'comments', 'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name', 'description')


class PlanDrawingElementSerializer(BaseModelSerializer):
    drawing = PlanDrawingSerializer(nested=True, read_only=True)
    assigned_object_type = ContentTypeField(read_only=True)
    assigned_object = GFKSerializerField(read_only=True)

    class Meta:
        model = PlanDrawingElement
        fields = (
            'id', 'url', 'display', 'drawing', 'page_id', 'page_name', 'cell_id', 'label',
            'assigned_object_type', 'assigned_object_id', 'assigned_object',
        )
        brief_fields = ('id', 'url', 'display', 'cell_id', 'label')

