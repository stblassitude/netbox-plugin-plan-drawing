from django.contrib.contenttypes.models import ContentType

from netbox.plugins import PluginTemplateExtension

from .models import PlanDrawing
from .object_types import get_linkable_model_keys


class ObjectPlanDrawingsPanel(PluginTemplateExtension):
    """
    Lists the drawings an object appears in on the object's page, each linking to the drawing
    viewer with the object's elements highlighted. For sites and locations, drawings assigned
    to them are listed as well.
    """
    models = get_linkable_model_keys()

    def right_page(self):
        obj = self.context['object']
        user = self.context['request'].user
        drawings = PlanDrawing.objects.restrict(user, 'view')

        linked = drawings.filter(
            elements__assigned_object_type=ContentType.objects.get_for_model(obj),
            elements__assigned_object_id=obj.pk,
        ).distinct()
        entries = [(drawing, drawing.get_highlight_url(obj)) for drawing in linked]

        linked_pks = {drawing.pk for drawing, url in entries}
        assigned = drawings.none()
        if obj._meta.label_lower == 'dcim.site':
            assigned = drawings.filter(site=obj)
        elif obj._meta.label_lower == 'dcim.location':
            assigned = drawings.filter(location=obj)
        entries.extend(
            (drawing, drawing.get_absolute_url()) for drawing in assigned if drawing.pk not in linked_pks
        )

        if not entries:
            return ''
        return self.render('netbox_plugin_plan_drawing/inc/object_drawings_panel.html', extra_context={
            'drawing_entries': entries,
        })


template_extensions = (ObjectPlanDrawingsPanel,)
