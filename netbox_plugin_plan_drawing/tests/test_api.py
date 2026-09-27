from django.test import TestCase
from django.urls import reverse

from users.models import User

from netbox_plugin_plan_drawing.models import PlanDrawing

from .utils import create_test_objects, drawing_file, graph_model, linked_cell


class PlanDrawingAPITestCase(TestCase):

    def setUp(self):
        self.site, self.location, self.rack, self.device = create_test_objects()
        self.user = User.objects.create_superuser(username='admin', password='admin')
        self.client.force_login(self.user)

    def test_create_drawing_indexes_elements(self):
        content = drawing_file(('p1', 'Floor', graph_model(linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk))))
        response = self.client.post(
            reverse('plugins-api:netbox_plugin_plan_drawing-api:plandrawing-list'),
            {'name': 'Plan', 'site': self.site.pk, 'content': content},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        drawing = PlanDrawing.objects.get(pk=response.json()['id'])
        self.assertEqual(drawing.elements.get().assigned_object, self.rack)

    def test_create_drawing_rejects_invalid_content(self):
        response = self.client.post(
            reverse('plugins-api:netbox_plugin_plan_drawing-api:plandrawing-list'),
            {'name': 'Plan', 'content': '<nope'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_filter_drawings_by_object(self):
        content = drawing_file(('p1', 'Floor', graph_model(linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk))))
        drawing = PlanDrawing.objects.create(name='Plan', content=content)
        PlanDrawing.objects.create(name='Other')
        url = reverse('plugins-api:netbox_plugin_plan_drawing-api:plandrawing-list')

        response = self.client.get(url, {'object_type': 'dcim.rack', 'object_id': self.rack.pk})

        self.assertEqual([d['id'] for d in response.json()['results']], [drawing.pk])

    def test_elements(self):
        content = drawing_file(('p1', 'Floor', graph_model(linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk))))
        drawing = PlanDrawing.objects.create(name='Plan', content=content)
        url = reverse('plugins-api:netbox_plugin_plan_drawing-api:plandrawingelement-list')

        response = self.client.get(url, {'assigned_object_type': 'dcim.rack', 'assigned_object_id': self.rack.pk})

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['drawing']['id'], drawing.pk)
        self.assertEqual(results[0]['assigned_object']['id'], self.rack.pk)

    def test_elements_hidden_without_drawing_permission(self):
        content = drawing_file(('p1', 'Floor', graph_model(linked_cell('a', 'Rack', 'dcim.rack', self.rack.pk))))
        PlanDrawing.objects.create(name='Plan', content=content)
        self.client.force_login(User.objects.create_user(username='nobody', password='nobody'))

        response = self.client.get(reverse('plugins-api:netbox_plugin_plan_drawing-api:plandrawingelement-list'))

        self.assertEqual(response.status_code, 403)
