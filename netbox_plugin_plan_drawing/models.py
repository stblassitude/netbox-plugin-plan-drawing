from urllib.parse import urlencode

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse

from netbox.models import PrimaryModel

from .drawio import DrawingParseError, parse_links
from .object_types import get_linkable_model, get_linkable_model_keys, object_type_key


class PlanDrawing(PrimaryModel):
    """
    A draw.io drawing, like a floor plan, whose elements can be linked to NetBox objects.
    """
    name = models.CharField(
        verbose_name='name',
        max_length=100,
        unique=True,
    )
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        related_name='plan_drawings',
        blank=True,
        null=True,
    )
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.SET_NULL,
        related_name='plan_drawings',
        blank=True,
        null=True,
    )
    content = models.TextField(
        verbose_name='content',
        blank=True,
        help_text='The drawing in draw.io XML format',
    )

    clone_fields = ('site', 'location')

    class Meta:
        ordering = ('name',)
        verbose_name = 'plan drawing'
        verbose_name_plural = 'plan drawings'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_plugin_plan_drawing:plandrawing', args=[self.pk])

    def get_highlight_url(self, obj):
        """
        Return the URL of the drawing viewer, highlighting the elements linked to obj.
        """
        query = urlencode({'highlight': f'{object_type_key(obj)}:{obj.pk}'})
        return f'{self.get_absolute_url()}?{query}'

    def clean(self):
        super().clean()

        if self.location and self.site and self.location.site != self.site:
            raise ValidationError({
                'location': f'Location {self.location} does not belong to site {self.site}.',
            })
        if self.location and not self.site:
            self.site = self.location.site

        try:
            links = parse_links(self.content)
        except DrawingParseError as e:
            raise ValidationError({'content': str(e)})

        linkable = set(get_linkable_model_keys())
        invalid = sorted({link.object_type for link in links if link.object_type not in linkable})
        if invalid:
            raise ValidationError({
                'content': f'Drawing elements are linked to unsupported object types: {", ".join(invalid)}',
            })

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.sync_elements()

    def sync_elements(self):
        """
        Rebuild the index of drawing elements linked to NetBox objects from the drawing content.
        Links to object types that are not (or no longer) linkable are skipped.
        """
        try:
            links = parse_links(self.content)
        except DrawingParseError:
            links = []

        content_types = {}
        elements = []
        for link in links:
            if link.object_type not in content_types:
                model = get_linkable_model(link.object_type)
                content_types[link.object_type] = ContentType.objects.get_for_model(model) if model else None
            content_type = content_types[link.object_type]
            if content_type is None:
                continue
            elements.append(PlanDrawingElement(
                drawing=self,
                page_id=link.page_id,
                page_name=link.page_name,
                cell_id=link.cell_id,
                label=link.label,
                assigned_object_type=content_type,
                assigned_object_id=link.object_id,
            ))

        self.elements.all().delete()
        PlanDrawingElement.objects.bulk_create(elements, ignore_conflicts=True)


class PlanDrawingElementQuerySet(models.QuerySet):

    def restrict(self, user, action='view'):
        """
        Elements have no permissions of their own: they can be viewed by users who may view the
        drawing they belong to, and are changed only by saving the drawing.
        """
        if action != 'view':
            return self.none()
        return self.filter(drawing__in=PlanDrawing.objects.restrict(user, 'view'))


class PlanDrawingElement(models.Model):
    """
    A drawing element (draw.io cell) linked to a NetBox object. Derived from the drawing
    content whenever the drawing is saved; not edited directly.
    """
    drawing = models.ForeignKey(
        to=PlanDrawing,
        on_delete=models.CASCADE,
        related_name='elements',
    )
    page_id = models.CharField(
        verbose_name='page ID',
        max_length=100,
        blank=True,
    )
    page_name = models.CharField(
        verbose_name='page',
        max_length=200,
        blank=True,
    )
    cell_id = models.CharField(
        verbose_name='cell ID',
        max_length=100,
    )
    label = models.CharField(
        verbose_name='label',
        max_length=200,
        blank=True,
    )
    assigned_object_type = models.ForeignKey(
        to='contenttypes.ContentType',
        on_delete=models.CASCADE,
        related_name='+',
    )
    assigned_object_id = models.PositiveBigIntegerField()
    assigned_object = GenericForeignKey(
        ct_field='assigned_object_type',
        fk_field='assigned_object_id',
    )

    objects = PlanDrawingElementQuerySet.as_manager()

    class Meta:
        ordering = ('drawing', 'page_name', 'label', 'cell_id')
        verbose_name = 'plan drawing element'
        verbose_name_plural = 'plan drawing elements'
        constraints = (
            models.UniqueConstraint(
                fields=('drawing', 'page_id', 'cell_id'),
                name='plandrawingelement_unique_drawing_page_cell',
            ),
        )
        indexes = (
            models.Index(fields=('assigned_object_type', 'assigned_object_id')),
        )

    def __str__(self):
        return f'{self.label or self.cell_id} ({self.drawing})'

    def get_absolute_url(self):
        query = urlencode({'highlight': f'{self.assigned_object_type.app_label}.'
                                        f'{self.assigned_object_type.model}:{self.assigned_object_id}'})
        return f'{self.drawing.get_absolute_url()}?{query}'
