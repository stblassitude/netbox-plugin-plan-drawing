import json
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.utils.text import capfirst
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, reverse
from django.views import View

from dcim.models import Device, Location, PowerPanel, Rack
from netbox.views import generic
from utilities.permissions import get_permission_for_model
from utilities.query import count_related
from utilities.views import ObjectPermissionRequiredMixin, get_viewname, register_model_view

from .assets import static_digest, versioned_static
from .drawio import DrawingParseError, iter_pages
from .filtersets import PlanDrawingFilterSet
from .forms import PlanDrawingBulkEditForm, PlanDrawingFilterForm, PlanDrawingForm
from .models import PlanDrawing, PlanDrawingElement
from .object_types import get_linkable_models, object_type_key, object_type_label
from .tables import PlanDrawingTable

DRAWIO_INDEX = 'netbox_plugin_plan_drawing/drawio/index.html'


def location_and_rack_contents(objects, user):
    """
    Return the trees of objects in the given locations and racks, keyed by (model, pk) of the
    location or rack. A location contains its child locations, racks, devices not mounted in a
    rack, and power panels; a rack contains its devices, top to bottom; and a device contains the
    devices installed in its device bays. Objects in the given list are marked as linked. Objects
    the user may not view are left out.
    """
    linked = {(type(obj), obj.pk) for obj in objects}
    location_ids = set()
    for obj in objects:
        if isinstance(obj, Location):
            location_ids.update(obj.get_descendants(include_self=True).values_list('pk', flat=True))
    linked_rack_ids = [obj.pk for obj in objects if isinstance(obj, Rack)]
    if not location_ids and not linked_rack_ids:
        return {}

    locations = Location.objects.restrict(user, 'view').filter(pk__in=location_ids)
    racks = list(Rack.objects.restrict(user, 'view').filter(Q(location__in=location_ids) | Q(pk__in=linked_rack_ids)))
    devices = Device.objects.restrict(user, 'view').filter(
        Q(rack__in=[rack.pk for rack in racks]) | Q(location__in=location_ids, rack__isnull=True),
    ).select_related('parent_bay').order_by(F('position').desc(nulls_last=True), 'name')
    panels = PowerPanel.objects.restrict(user, 'view').filter(location__in=location_ids)

    nodes = {}

    def add(obj, *parents, position=None):
        """
        Add the object below the first of the parents, given as (model, pk), that is in the tree.
        """
        node = nodes[(type(obj), obj.pk)] = {
            'display': str(obj),
            'url': obj.get_absolute_url(),
            'object_type': f'{obj._meta.app_label}.{obj._meta.model_name}',
            'object_id': obj.pk,
            'object_type_label': capfirst(obj._meta.verbose_name),
            'position': position,
            'linked': (type(obj), obj.pk) in linked,
            'children': [],
        }
        for parent in parents:
            if parent in nodes:
                nodes[parent]['children'].append(node)
                break

    # Locations are ordered by their path, so that parents are added before their children.
    for location in locations:
        add(location, (Location, location.parent_id))
    for rack in racks:
        add(rack, (Location, rack.location_id))
    # Devices in device bays go below their parent device, once it has been added; devices whose
    # parent is not in the tree go below their rack or location.
    pending = list(devices)
    while pending:
        remaining = []
        pending_ids = {device.pk for device in pending}
        for device in pending:
            parent_bay = getattr(device, 'parent_bay', None)
            parent = (Device, parent_bay.device_id) if parent_bay else None
            if parent and parent not in nodes and parent_bay.device_id in pending_ids:
                remaining.append(device)
                continue
            add(device, parent, (Rack, device.rack_id), (Location, device.location_id), position=device.position)
        if len(remaining) == len(pending):
            break
        pending = remaining
    for panel in panels:
        add(panel, (Location, panel.location_id))
    return nodes


def linked_elements(drawing, user):
    """
    Return the drawing's linked elements, with the NetBox objects they are linked to, for the
    drawing viewer, in the order of the drawing's pages. Objects the user may not view are shown
    without their name. Locations and racks come with the objects in them.
    """
    elements = list(drawing.elements.select_related('assigned_object_type'))

    ids_by_type = defaultdict(set)
    for element in elements:
        ids_by_type[element.assigned_object_type].add(element.assigned_object_id)
    objects = {}
    for content_type, ids in ids_by_type.items():
        model = content_type.model_class()
        if model is None:
            continue
        for obj in model.objects.restrict(user, 'view').filter(pk__in=ids):
            objects[(content_type.pk, obj.pk)] = obj
    contents = location_and_rack_contents(list(objects.values()), user)

    result = []
    for element in elements:
        content_type = element.assigned_object_type
        model = content_type.model_class()
        obj = objects.get((content_type.pk, element.assigned_object_id))
        result.append({
            'page_id': element.page_id,
            'page_name': element.page_name,
            'cell_id': element.cell_id,
            'label': element.label,
            'object_type': f'{content_type.app_label}.{content_type.model}',
            'object_type_label': object_type_label(model) if model else content_type.model,
            'object_id': element.assigned_object_id,
            'display': str(obj) if obj else None,
            'url': obj.get_absolute_url() if obj else None,
            'contents': contents[(model, obj.pk)]['children'] if isinstance(obj, (Location, Rack)) else None,
        })

    try:
        page_order = {page_id: index for index, (page_id, _, _) in enumerate(iter_pages(drawing.content))}
    except DrawingParseError:
        page_order = {}
    result.sort(key=lambda e: (page_order.get(e['page_id'], len(page_order)), e['label'].lower(), e['cell_id']))
    return result


def linkable_object_types():
    """
    Return the linkable object types, with their REST API list endpoint, for the object picker.
    """
    types = []
    for model in get_linkable_models():
        try:
            api_url = reverse(get_viewname(model, action='list', rest_api=True))
        except NoReverseMatch:
            continue
        types.append({
            'value': object_type_key(model),
            'label': object_type_label(model),
            'api_url': api_url,
        })
    return types


@register_model_view(PlanDrawing, 'list', path='', detail=False)
class PlanDrawingListView(generic.ObjectListView):
    queryset = PlanDrawing.objects.annotate(
        element_count=count_related(PlanDrawingElement, 'drawing'),
    )
    table = PlanDrawingTable
    filterset = PlanDrawingFilterSet
    filterset_form = PlanDrawingFilterForm


@register_model_view(PlanDrawing)
class PlanDrawingView(generic.ObjectView):
    """
    Shows a drawing in the draw.io viewer, with the list of elements linked to NetBox objects.
    """
    queryset = PlanDrawing.objects.all()

    def get_extra_context(self, request, instance):
        return {
            'elements': linked_elements(instance, request.user),
            'drawio_viewer_url': versioned_static('netbox_plugin_plan_drawing/drawio/js/viewer-static.min.js'),
            'highlight': request.GET.get('highlight', ''),
        }


@register_model_view(PlanDrawing, 'add', detail=False)
@register_model_view(PlanDrawing, 'edit')
class PlanDrawingEditView(generic.ObjectEditView):
    queryset = PlanDrawing.objects.all()
    form = PlanDrawingForm


@register_model_view(PlanDrawing, 'delete')
class PlanDrawingDeleteView(generic.ObjectDeleteView):
    queryset = PlanDrawing.objects.all()


@register_model_view(PlanDrawing, 'bulk_edit', path='edit', detail=False)
class PlanDrawingBulkEditView(generic.BulkEditView):
    queryset = PlanDrawing.objects.all()
    filterset = PlanDrawingFilterSet
    table = PlanDrawingTable
    form = PlanDrawingBulkEditForm


@register_model_view(PlanDrawing, 'bulk_delete', path='delete', detail=False)
class PlanDrawingBulkDeleteView(generic.BulkDeleteView):
    queryset = PlanDrawing.objects.all()
    filterset = PlanDrawingFilterSet
    table = PlanDrawingTable


@register_model_view(PlanDrawing, 'draw')
class PlanDrawingDrawView(generic.ObjectView):
    """
    Edits the drawing with the bundled draw.io, embedded in the page.
    """
    queryset = PlanDrawing.objects.all()
    template_name = 'netbox_plugin_plan_drawing/plandrawing_draw.html'

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, 'change')

    def get_extra_context(self, request, instance):
        return {
            'drawio_url': static(DRAWIO_INDEX),
            # Passed on to PostConfig.js, which adds it to the URL of the draw.io plugin.
            'drawio_plugin_version': static_digest('netbox_plugin_plan_drawing/drawio-netbox.js') or '',
            'editor_config': {
                'content': instance.content,
                'title': instance.name,
                'last_updated': instance.last_updated.isoformat() if instance.last_updated else None,
                'save_url': reverse('plugins:netbox_plugin_plan_drawing:plandrawing_content', args=[instance.pk]),
                'csrf_token': get_token(request),
                'exit_url': instance.get_absolute_url(),
                'object_types': linkable_object_types(),
            },
        }


@register_model_view(PlanDrawing, 'content')
class PlanDrawingContentView(ObjectPermissionRequiredMixin, View):
    """
    Saves the drawing content from the editor. The request carries the last_updated time of
    the drawing as loaded into the editor; if the drawing has been changed since, the save is
    rejected with 409 Conflict, so that concurrent edits are not silently overwritten.
    """
    queryset = PlanDrawing.objects.all()

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, 'change')

    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            content = data['content']
            last_updated = data.get('last_updated')
        except (ValueError, KeyError, TypeError):
            return JsonResponse({'error': 'Invalid request'}, status=400)
        if not isinstance(content, str):
            return JsonResponse({'error': 'Invalid request'}, status=400)

        with transaction.atomic():
            drawing = get_object_or_404(self.queryset.select_for_update(), pk=pk)
            current = drawing.last_updated.isoformat() if drawing.last_updated else None
            if last_updated != current:
                return JsonResponse({
                    'error': 'The drawing has been changed by someone else since you opened it.',
                    'last_updated': current,
                }, status=409)

            drawing.snapshot()
            drawing.content = content
            try:
                drawing.full_clean()
            except ValidationError as e:
                return JsonResponse({'error': ' '.join(e.messages)}, status=400)
            drawing.save()

            # Object-level permissions may be constrained on attributes of the drawing.
            if not self.queryset.filter(pk=drawing.pk).exists():
                transaction.set_rollback(True)
                return JsonResponse({'error': 'Permission denied'}, status=403)

        return JsonResponse({
            'last_updated': drawing.last_updated.isoformat(),
            'element_count': drawing.elements.count(),
        })
