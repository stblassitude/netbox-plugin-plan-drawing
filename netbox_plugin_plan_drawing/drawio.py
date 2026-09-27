"""
Reading draw.io files.

A draw.io file is an <mxfile> with one <diagram> per page; each page holds an <mxGraphModel>,
either as XML or compressed (raw deflate, base64 encoded, of the URL-encoded XML). Cells with
custom properties are wrapped in an <object> (or <UserObject>) element carrying those
properties as attributes. A cell linked to a NetBox object carries two of them:

    <object id="7" label="Rack 1" netbox_type="dcim.rack" netbox_id="12">
      <mxCell style="..." vertex="1" parent="1">...</mxCell>
    </object>
"""
import base64
import html
import re
import urllib.parse
import zlib
from dataclasses import dataclass
from xml.etree.ElementTree import ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring
from django.utils.html import strip_tags

TYPE_ATTRIBUTE = 'netbox_type'
ID_ATTRIBUTE = 'netbox_id'
LABEL_MAX_LENGTH = 200


class DrawingParseError(ValueError):
    pass


@dataclass(frozen=True)
class DrawingLink:
    page_id: str
    page_name: str
    cell_id: str
    label: str
    object_type: str
    object_id: int


def _parse_xml(text):
    try:
        return fromstring(text)
    except (ParseError, DefusedXmlException) as e:
        raise DrawingParseError(f'Invalid drawing XML: {e}')


def decompress_diagram(text):
    try:
        data = zlib.decompress(base64.b64decode(text), -zlib.MAX_WBITS)
    except (ValueError, zlib.error) as e:
        raise DrawingParseError(f'Invalid compressed diagram: {e}')
    return urllib.parse.unquote(data.decode('utf-8'))


def iter_pages(content):
    """
    Yield (page_id, page_name, mxGraphModel element) for each page of a drawing.
    """
    root = _parse_xml(content)
    if root.tag == 'mxGraphModel':
        yield '', '', root
        return
    if root.tag != 'mxfile':
        raise DrawingParseError(f'Not a draw.io file: unexpected root element <{root.tag}>')

    for index, diagram in enumerate(root.findall('diagram')):
        page_id = diagram.get('id') or str(index)
        page_name = diagram.get('name') or f'Page-{index + 1}'
        model = diagram.find('mxGraphModel')
        if model is None:
            text = (diagram.text or '').strip()
            if not text:
                continue
            model = _parse_xml(decompress_diagram(text))
        yield page_id, page_name, model


def label_text(label):
    """
    Return the plain text of a cell label, which may contain HTML.
    """
    text = re.sub(r'<br\s*/?>|</div>|</p>', ' ', label or '', flags=re.IGNORECASE)
    text = ' '.join(html.unescape(strip_tags(text)).split())
    return text[:LABEL_MAX_LENGTH]


def parse_links(content):
    """
    Return a DrawingLink for every cell in the drawing that is linked to a NetBox object.
    """
    if not content or not content.strip():
        return []

    links = []
    for page_id, page_name, model in iter_pages(content):
        for element in model.iter():
            object_type = element.get(TYPE_ATTRIBUTE)
            object_id = element.get(ID_ATTRIBUTE)
            if not object_type and not object_id:
                continue
            cell_id = element.get('id', '')
            if not object_type or not object_id:
                raise DrawingParseError(f'Cell {cell_id} has an incomplete NetBox object link')
            try:
                object_id = int(object_id)
            except ValueError:
                raise DrawingParseError(f'Cell {cell_id} links to an invalid NetBox object ID: {object_id}')
            links.append(DrawingLink(
                page_id=page_id,
                page_name=page_name,
                cell_id=cell_id,
                label=label_text(element.get('label')),
                object_type=object_type.lower(),
                object_id=object_id,
            ))
    return links
