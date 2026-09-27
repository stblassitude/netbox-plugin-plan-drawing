import base64
import urllib.parse
import zlib

from dcim.models import Device, DeviceRole, DeviceType, Location, Manufacturer, Rack, Site


def compress_diagram(xml):
    """
    Compress an mxGraphModel the way draw.io does: URL-encode, raw deflate, base64.
    """
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    data = compressor.compress(urllib.parse.quote(xml).encode()) + compressor.flush()
    return base64.b64encode(data).decode()


def linked_cell(cell_id, label, obj_type, obj_id):
    return (
        f'<object id="{cell_id}" label="{label}" netbox_type="{obj_type}" netbox_id="{obj_id}">'
        f'<mxCell style="rounded=0;" vertex="1" parent="1">'
        f'<mxGeometry x="0" y="0" width="10" height="10" as="geometry"/></mxCell></object>'
    )


def graph_model(*cells):
    return (
        '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        + ''.join(cells)
        + '</root></mxGraphModel>'
    )


def drawing_file(*pages):
    """
    pages: (page_id, page_name, graph model XML) tuples.
    """
    diagrams = ''.join(f'<diagram id="{pid}" name="{name}">{model}</diagram>' for pid, name, model in pages)
    return f'<mxfile>{diagrams}</mxfile>'


def create_test_objects():
    site = Site.objects.create(name='Site 1', slug='site-1')
    location = Location.objects.create(site=site, name='Room 1', slug='room-1')
    manufacturer = Manufacturer.objects.create(name='Generic', slug='generic')
    device_type = DeviceType.objects.create(manufacturer=manufacturer, model='Box', slug='box')
    role = DeviceRole.objects.create(name='Role', slug='role')
    rack = Rack.objects.create(site=site, location=location, name='R1')
    device = Device.objects.create(
        name='dev1', site=site, location=location, rack=rack, device_type=device_type, role=role,
    )
    return site, location, rack, device
