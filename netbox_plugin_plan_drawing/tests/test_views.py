import json

from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ObjectChange
from users.models import User

from netbox_plugin_plan_drawing.models import PlanDrawing

from .utils import create_test_objects, drawing_file, graph_model, linked_cell


@override_settings(EXEMPT_VIEW_PERMISSIONS=[])
class PlanDrawingViewsTestCase(TestCase):

    def setUp(self):
        self.site, self.location, self.rack, self.device = create_test_objects()
        self.user = User.objects.create_superuser(username='admin', password='admin')
        self.client.force_login(self.user)
        self.drawing = PlanDrawing.objects.create(name='Plan', site=self.site, content=self.content(
            linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk),
        ))

    def content(self, *cells):
        return drawing_file(('p1', 'Floor', graph_model(*cells)))

    def save_content(self, content, last_updated):
        url = reverse('plugins:netbox_plugin_plan_drawing:plandrawing_content', args=[self.drawing.pk])
        return self.client.post(
            url, json.dumps({'content': content, 'last_updated': last_updated}), content_type='application/json',
        )

    def test_list(self):
        response = self.client.get(reverse('plugins:netbox_plugin_plan_drawing:plandrawing_list'))

        self.assertContains(response, 'Plan')

    def test_detail_shows_linked_elements(self):
        response = self.client.get(self.drawing.get_absolute_url() + '?highlight=dcim.rack:1')

        self.assertContains(response, 'plan-drawing-elements-data')
        self.assertEqual(response.context['elements'][0]['display'], str(self.rack))
        self.assertEqual(response.context['elements'][0]['url'], self.rack.get_absolute_url())

    def test_detail_lists_elements_in_page_order(self):
        self.drawing.content = drawing_file(
            ('z', 'Zeta', graph_model(linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk))),
            ('a', 'Alpha', graph_model(linked_cell('b', 'Device', 'dcim.device', self.device.pk))),
        )
        self.drawing.save()

        response = self.client.get(self.drawing.get_absolute_url())

        self.assertEqual([e['page_name'] for e in response.context['elements']], ['Zeta', 'Alpha'])

    def test_editor(self):
        url = reverse('plugins:netbox_plugin_plan_drawing:plandrawing_draw', args=[self.drawing.pk])
        response = self.client.get(url)

        self.assertContains(response, 'netbox_plugin_plan_drawing/drawio/index.html')
        config = response.context['editor_config']
        self.assertEqual(config['content'], self.drawing.content)
        self.assertIn('dcim.rack', [t['value'] for t in config['object_types']])

    def test_save_content(self):
        content = self.content(
            linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk),
            linked_cell('b', 'Device', 'dcim.device', self.device.pk),
        )
        response = self.save_content(content, self.drawing.last_updated.isoformat())

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['element_count'], 2)
        self.drawing.refresh_from_db()
        self.assertEqual(self.drawing.content, content)
        self.assertEqual(response.json()['last_updated'], self.drawing.last_updated.isoformat())

    def test_save_content_records_change(self):
        content = self.content()
        self.save_content(content, self.drawing.last_updated.isoformat())

        change = ObjectChange.objects.get(changed_object_id=self.drawing.pk)
        self.assertEqual(change.postchange_data['content'], content)
        self.assertIn('dcim.rack', change.prechange_data['content'])

    def test_save_content_conflict(self):
        response = self.save_content(self.content(), '2000-01-01T00:00:00+00:00')

        self.assertEqual(response.status_code, 409)
        self.drawing.refresh_from_db()
        self.assertEqual(self.drawing.elements.count(), 1)

    def test_save_content_invalid(self):
        response = self.save_content('<mxfile><diagram>', self.drawing.last_updated.isoformat())

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_save_content_requires_change_permission(self):
        viewer = User.objects.create_user(username='viewer', password='viewer')
        self.client.force_login(viewer)

        response = self.save_content(self.content(), self.drawing.last_updated.isoformat())

        self.assertEqual(response.status_code, 403)

    def test_object_page_lists_drawing(self):
        response = self.client.get(self.rack.get_absolute_url())

        self.assertContains(response, self.drawing.get_highlight_url(self.rack).replace('&', '&amp;'))

    def test_site_page_lists_assigned_drawing(self):
        response = self.client.get(self.site.get_absolute_url())

        self.assertContains(response, 'Plan Drawings')
        self.assertContains(response, f'href="{self.drawing.get_absolute_url()}"')
