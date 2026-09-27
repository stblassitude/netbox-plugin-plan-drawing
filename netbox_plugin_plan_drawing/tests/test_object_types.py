from django.test import SimpleTestCase

from netbox_plugin_plan_drawing.object_types import get_linkable_model, get_linkable_model_keys


class LinkableObjectTypesTestCase(SimpleTestCase):

    def test_physical_objects_are_linkable(self):
        keys = get_linkable_model_keys()
        for key in (
            'dcim.site', 'dcim.location', 'dcim.rack', 'dcim.device', 'dcim.module', 'dcim.interface',
            'dcim.frontport', 'dcim.rearport', 'dcim.poweroutlet', 'dcim.cable', 'dcim.powerpanel',
            'dcim.powerfeed', 'circuits.circuit', 'circuits.circuittermination', 'wireless.wirelesslink',
        ):
            self.assertIn(key, keys)

    def test_kinds_and_organization_are_not_linkable(self):
        keys = get_linkable_model_keys()
        for key in (
            'dcim.devicetype', 'dcim.interfacetemplate', 'dcim.devicerole', 'dcim.region', 'dcim.manufacturer',
            'dcim.cablepath', 'dcim.cabletermination', 'circuits.provider', 'wireless.wirelesslan',
            'extras.script', 'ipam.prefix',
        ):
            self.assertNotIn(key, keys)

    def test_get_linkable_model(self):
        self.assertEqual(get_linkable_model('DCIM.Rack')._meta.model_name, 'rack')
        self.assertIsNone(get_linkable_model('dcim.devicetype'))
        self.assertIsNone(get_linkable_model('nonsense'))
