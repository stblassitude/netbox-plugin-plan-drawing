from django.core.exceptions import ValidationError
from django.test import TestCase

from dcim.models import Location, Site

from netbox_plugin_plan_drawing.models import PlanDrawing, PlanDrawingElement

from .utils import create_test_objects, drawing_file, graph_model, linked_cell


class PlanDrawingTestCase(TestCase):

    def setUp(self):
        self.site, self.location, self.rack, self.device = create_test_objects()

    def content(self, *cells):
        return drawing_file(('p1', 'Floor', graph_model(*cells)))

    def test_save_indexes_linked_elements(self):
        drawing = PlanDrawing.objects.create(name='Plan', content=self.content(
            linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk),
            linked_cell('b', 'Device', 'dcim.device', self.device.pk),
        ))

        elements = {element.cell_id: element for element in drawing.elements.all()}
        self.assertEqual(set(elements), {'a', 'b'})
        self.assertEqual(elements['a'].assigned_object, self.rack)
        self.assertEqual(elements['b'].assigned_object, self.device)
        self.assertEqual(elements['a'].page_name, 'Floor')
        self.assertEqual(elements['a'].label, 'Rack')

    def test_save_replaces_elements(self):
        drawing = PlanDrawing.objects.create(name='Plan', content=self.content(
            linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk),
        ))
        drawing.content = self.content(linked_cell('b', 'Device', 'dcim.device', self.device.pk))
        drawing.save()

        self.assertEqual(list(drawing.elements.values_list('cell_id', flat=True)), ['b'])

    def test_links_to_deleted_objects_are_kept(self):
        drawing = PlanDrawing.objects.create(name='Plan', content=self.content(
            linked_cell('a', 'Gone', 'dcim.rack', 999999),
        ))

        element = drawing.elements.get()
        self.assertIsNone(element.assigned_object)

    def test_clean_rejects_unsupported_object_types(self):
        drawing = PlanDrawing(name='Plan', content=self.content(linked_cell('a', 'Type', 'dcim.devicetype', 1)))

        with self.assertRaises(ValidationError) as cm:
            drawing.full_clean()
        self.assertIn('content', cm.exception.message_dict)

    def test_clean_rejects_invalid_content(self):
        drawing = PlanDrawing(name='Plan', content='<mxfile><diagram>')

        with self.assertRaises(ValidationError) as cm:
            drawing.full_clean()
        self.assertIn('content', cm.exception.message_dict)

    def test_clean_rejects_location_of_other_site(self):
        other_site = Site.objects.create(name='Site 2', slug='site-2')
        other_location = Location.objects.create(site=other_site, name='Room 2', slug='room-2')
        drawing = PlanDrawing(name='Plan', site=self.site, location=other_location)

        with self.assertRaises(ValidationError) as cm:
            drawing.full_clean()
        self.assertIn('location', cm.exception.message_dict)

    def test_clean_sets_site_from_location(self):
        drawing = PlanDrawing(name='Plan', location=self.location)
        drawing.full_clean()

        self.assertEqual(drawing.site, self.site)

    def test_highlight_url(self):
        drawing = PlanDrawing.objects.create(name='Plan')

        self.assertEqual(
            drawing.get_highlight_url(self.rack),
            f'{drawing.get_absolute_url()}?highlight=dcim.rack%3A{self.rack.pk}',
        )

    def test_elements_deleted_with_drawing(self):
        drawing = PlanDrawing.objects.create(name='Plan', content=self.content(
            linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk),
        ))
        drawing.delete()

        self.assertFalse(PlanDrawingElement.objects.exists())
