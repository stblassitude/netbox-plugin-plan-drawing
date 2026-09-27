from django.test import SimpleTestCase

from netbox_plugin_plan_drawing.drawio import DrawingParseError, label_text, parse_links

from .utils import compress_diagram, drawing_file, graph_model, linked_cell


class ParseLinksTestCase(SimpleTestCase):

    def test_empty_content(self):
        self.assertEqual(parse_links(''), [])
        self.assertEqual(parse_links('   '), [])

    def test_plain_multi_page(self):
        content = drawing_file(
            ('p1', 'Floor', graph_model(linked_cell('a', 'Rack A', 'dcim.rack', 1), '<mxCell id="x" parent="1"/>')),
            ('p2', 'Rack', graph_model(linked_cell('b', 'Dev', 'DCIM.Device', 2))),
        )
        links = parse_links(content)

        self.assertEqual(len(links), 2)
        self.assertEqual((links[0].page_id, links[0].page_name, links[0].cell_id), ('p1', 'Floor', 'a'))
        self.assertEqual((links[0].object_type, links[0].object_id, links[0].label), ('dcim.rack', 1, 'Rack A'))
        self.assertEqual((links[1].page_id, links[1].object_type, links[1].object_id), ('p2', 'dcim.device', 2))

    def test_compressed_page(self):
        model = graph_model(linked_cell('a', 'Rack A', 'dcim.rack', 7))
        content = f'<mxfile><diagram id="p1" name="Page-1">{compress_diagram(model)}</diagram></mxfile>'

        links = parse_links(content)

        self.assertEqual(len(links), 1)
        self.assertEqual((links[0].cell_id, links[0].object_id), ('a', 7))

    def test_bare_graph_model(self):
        links = parse_links(graph_model(linked_cell('a', 'A', 'dcim.site', 3)))

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].page_id, '')

    def test_user_object_element(self):
        content = graph_model(
            '<UserObject id="u" label="U" netbox_type="dcim.rack" netbox_id="4">'
            '<mxCell vertex="1" parent="1"/></UserObject>'
        )

        self.assertEqual(parse_links(content)[0].cell_id, 'u')

    def test_incomplete_link(self):
        content = graph_model('<object id="a" netbox_type="dcim.rack"><mxCell vertex="1" parent="1"/></object>')

        with self.assertRaises(DrawingParseError):
            parse_links(content)

    def test_invalid_id(self):
        with self.assertRaises(DrawingParseError):
            parse_links(graph_model(linked_cell('a', 'A', 'dcim.rack', 'abc')))

    def test_invalid_xml(self):
        with self.assertRaises(DrawingParseError):
            parse_links('<mxfile><diagram>')

    def test_unexpected_root(self):
        with self.assertRaises(DrawingParseError):
            parse_links('<html></html>')

    def test_invalid_compressed_page(self):
        with self.assertRaises(DrawingParseError):
            parse_links('<mxfile><diagram id="p">not compressed data!</diagram></mxfile>')

    def test_entity_expansion_rejected(self):
        content = (
            '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>'
            '<mxGraphModel><root><mxCell id="0" value="&lol;"/></root></mxGraphModel>'
        )

        with self.assertRaises(DrawingParseError):
            parse_links(content)


class LabelTextTestCase(SimpleTestCase):

    def test_html_label(self):
        self.assertEqual(label_text('<b>Rack</b><br>A &amp; B'), 'Rack A & B')

    def test_empty(self):
        self.assertEqual(label_text(None), '')
