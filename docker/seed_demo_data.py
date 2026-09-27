import uuid
from xml.sax.saxutils import quoteattr

from django.test import RequestFactory

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Location, Manufacturer, PowerPanel, Rack, Site
from netbox.context_managers import event_tracking
from users.models import User

from netbox_plugin_plan_drawing.models import PlanDrawing

site, _ = Site.objects.get_or_create(slug='demo-site', defaults={'name': 'Demo Site'})
location, _ = Location.objects.get_or_create(
    site=site, slug='server-room', defaults={'name': 'Server Room'},
)
closet, _ = Location.objects.get_or_create(
    site=site, slug='network-closet', defaults={'name': 'Network Closet'},
)
manufacturer, _ = Manufacturer.objects.get_or_create(slug='generic', defaults={'name': 'Generic'})
switch_type, _ = DeviceType.objects.get_or_create(
    manufacturer=manufacturer, slug='switch-48', defaults={'model': 'Switch 48', 'u_height': 1},
)
server_type, _ = DeviceType.objects.get_or_create(
    manufacturer=manufacturer, slug='server-2u', defaults={'model': 'Server 2U', 'u_height': 2},
)
ap_type, _ = DeviceType.objects.get_or_create(
    manufacturer=manufacturer, slug='access-point', defaults={'model': 'Access Point', 'u_height': 0},
)
network_role, _ = DeviceRole.objects.get_or_create(slug='network', defaults={'name': 'Network'})
server_role, _ = DeviceRole.objects.get_or_create(slug='server', defaults={'name': 'Server'})

racks = {}
for name, rack_location, u_height in (
    ('R1', location, 42),
    ('R2', location, 42),
    ('R3', closet, 12),
):
    racks[name], _ = Rack.objects.get_or_create(
        site=site, name=name, defaults={'location': rack_location, 'u_height': u_height},
    )

devices = {}
for name, device_type, role, rack, position in (
    ('sw1', switch_type, network_role, racks['R1'], 42),
    ('srv1', server_type, server_role, racks['R1'], 20),
    ('srv2', server_type, server_role, racks['R2'], 20),
    ('ap1', ap_type, network_role, None, None),
    ('sw2', switch_type, network_role, racks['R3'], 12),
):
    devices[name], _ = Device.objects.get_or_create(
        name=name,
        site=site,
        defaults={
            'device_type': device_type,
            'role': role,
            'location': rack.location if rack else location,
            'rack': rack,
            'position': position,
            'face': 'front' if rack else '',
            'status': DeviceStatusChoices.STATUS_ACTIVE,
        },
    )

power_panel, _ = PowerPanel.objects.get_or_create(site=site, name='PP1', defaults={'location': location})


def cell(cell_id, label, style, x, y, width, height, obj=None):
    geometry = f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/>'
    mxcell = f'<mxCell style={quoteattr(style)} vertex="1" parent="1">{geometry}</mxCell>'
    if obj is None:
        return f'<mxCell id="{cell_id}" value={quoteattr(label)} style={quoteattr(style)} vertex="1" parent="1">' \
               f'{geometry}</mxCell>'
    return (
        f'<object id="{cell_id}" label={quoteattr(label)} netbox_type="{obj._meta.label_lower}" '
        f'netbox_id="{obj.pk}" netbox_display={quoteattr(str(obj))}>{mxcell}</object>'
    )


def page(page_id, name, cells):
    return (
        f'<diagram id="{page_id}" name="{name}"><mxGraphModel grid="1" gridSize="10" page="1" '
        f'pageWidth="827" pageHeight="583"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        f'{"".join(cells)}</root></mxGraphModel></diagram>'
    )


ROOM = ('rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeWidth=8;verticalAlign=top;align=left;'
        'spacingLeft=10;spacingTop=6;fontSize=16;')
DOOR = ('verticalLabelPosition=bottom;html=1;verticalAlign=top;align=center;shape=mxgraph.floorplan.doorLeft;'
        'aspect=fixed;rotation=-90;flipV=1;')
RACK = 'rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;'
PANEL = 'rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
DEVICE = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;'
AP = 'ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#e1d5e7;strokeColor=#9673a6;'

content = (
    '<mxfile>'
    + page('floor', 'Server Room', [
        cell('room', 'Server Room', ROOM, 40, 40, 720, 460, location),
        cell('door', '', DOOR, 642.5, 417.5, 80, 85),
        cell('rack-r1', 'R1', RACK, 160, 200, 60, 100, racks['R1']),
        cell('rack-r2', 'R2', RACK, 240, 200, 60, 100, racks['R2']),
        cell('pp1', 'PP1', PANEL, 60, 380, 40, 80, power_panel),
        cell('ap1', 'ap1', AP, 480, 140, 50, 50, devices['ap1']),
        cell('desk', 'Desk', 'rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;',
             480, 300, 160, 70),
    ])
    + page('closet', 'Network Closet', [
        cell('closet', 'Network Closet', ROOM, 40, 40, 300, 220, closet),
        cell('closet-door', '', DOOR, 240, 175, 80, 85),
        # A small wall-mounted 12U rack, with the switch mounted in it.
        cell('rack-r3', 'R3', RACK + 'verticalAlign=top;', 60, 110, 60, 50, racks['R3']),
        cell('sw2', 'sw2', DEVICE + 'fontSize=10;', 66, 134, 48, 18, devices['sw2']),
    ])
    + '</mxfile>'
)

drawing, created = PlanDrawing.objects.get_or_create(
    name='Demo Site Floor Plan',
    defaults={
        'site': site,
        'description': 'Demo drawing of two rooms, with racks, devices and a power panel linked to NetBox objects',
    },
)

if created:
    # Save through a simulated request, so that the saves are recorded in the change log, as
    # they are when edited in the UI. The first save adds the content; the others change it
    # slightly, to give plan_drawing_changelog_stats something to report.
    request = RequestFactory().get('/')
    request.id = uuid.uuid4()
    request.user = User.objects.filter(is_superuser=True).first()
    with event_tracking(request):
        for revision in range(3):
            drawing.snapshot()
            drawing.content = content.replace('value="Desk"', f'value="Desk {revision}"') if revision else content
            drawing.full_clean()
            drawing.save()

print(f'Demo drawing: {drawing} (id={drawing.pk}), {drawing.elements.count()} linked elements')
