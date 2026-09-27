from django import forms

from dcim.models import Location, Site
from netbox.forms import PrimaryModelBulkEditForm, PrimaryModelFilterSetForm, PrimaryModelForm
from utilities.forms.fields import CommentField, DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.rendering import FieldSet

from .models import PlanDrawing


class PlanDrawingForm(PrimaryModelForm):
    """
    Edits a drawing's metadata; the drawing itself is edited with draw.io.
    """
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site'},
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('name', 'site', 'location', 'description', 'tags', name='Plan Drawing'),
    )

    class Meta:
        model = PlanDrawing
        fields = ('name', 'site', 'location', 'description', 'owner', 'comments', 'tags')


class PlanDrawingBulkEditForm(PrimaryModelBulkEditForm):
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site'},
    )
    description = forms.CharField(max_length=200, required=False)
    comments = CommentField()

    model = PlanDrawing
    fieldsets = (
        FieldSet('site', 'location', 'description', name='Plan Drawing'),
    )
    nullable_fields = ('site', 'location', 'description', 'comments')


class PlanDrawingFilterForm(PrimaryModelFilterSetForm):
    model = PlanDrawing
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='Site',
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site_id'},
        label='Location',
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag', 'owner_id'),
        FieldSet('site_id', 'location_id', name='Location'),
    )
