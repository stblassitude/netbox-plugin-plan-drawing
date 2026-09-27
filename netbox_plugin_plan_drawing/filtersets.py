import django_filters
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from dcim.models import Location, Site
from netbox.filtersets import BaseFilterSet, PrimaryModelFilterSet
from utilities.filters import ContentTypeFilter

from .models import PlanDrawing, PlanDrawingElement


class PlanDrawingFilterSet(PrimaryModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label='Site (ID)',
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name='site__slug',
        queryset=Site.objects.all(),
        to_field_name='slug',
        label='Site (slug)',
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label='Location (ID)',
    )
    object_type = django_filters.CharFilter(
        method='filter_object',
        label='Contains an element linked to an object of this type (<app_label>.<model>)',
    )
    object_id = django_filters.NumberFilter(
        method='filter_object',
        label='Contains an element linked to the object with this ID (together with object_type)',
    )

    class Meta:
        model = PlanDrawing
        fields = ('id', 'name', 'description')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(elements__label__icontains=value)
        ).distinct()

    def filter_object(self, queryset, name, value):
        # Both parameters are applied together, from whichever is processed first.
        object_type = self.data.get('object_type')
        object_id = self.data.get('object_id')
        if not object_type:
            return queryset
        try:
            app_label, model = object_type.lower().split('.')
            content_type = ContentType.objects.get_by_natural_key(app_label, model)
        except (ValueError, ContentType.DoesNotExist):
            return queryset.none()
        elements = Q(elements__assigned_object_type=content_type)
        if object_id:
            elements &= Q(elements__assigned_object_id=object_id)
        return queryset.filter(elements).distinct()


class PlanDrawingElementFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )
    drawing_id = django_filters.ModelMultipleChoiceFilter(
        queryset=PlanDrawing.objects.all(),
        label='Drawing (ID)',
    )
    assigned_object_type = ContentTypeFilter()

    class Meta:
        model = PlanDrawingElement
        fields = ('id', 'page_id', 'cell_id', 'label', 'assigned_object_type_id', 'assigned_object_id')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(label__icontains=value) |
            Q(drawing__name__icontains=value)
        )
