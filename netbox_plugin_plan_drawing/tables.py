import django_tables2 as tables

from netbox.tables import PrimaryModelTable
from netbox.tables.columns import TagColumn

from .models import PlanDrawing


class PlanDrawingTable(PrimaryModelTable):
    name = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    element_count = tables.Column(verbose_name='Linked Elements')
    tags = TagColumn(url_name='plugins:netbox_plugin_plan_drawing:plandrawing_list')

    class Meta(PrimaryModelTable.Meta):
        model = PlanDrawing
        fields = (
            'pk', 'id', 'name', 'site', 'location', 'description', 'element_count', 'owner', 'comments', 'tags',
            'created', 'last_updated',
        )
        default_columns = ('pk', 'name', 'site', 'location', 'description', 'element_count')
