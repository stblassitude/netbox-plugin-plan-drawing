# REST API

The plugin adds these endpoints to NetBox's REST API:

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/plugins/plan-drawing/drawings/` | GET, POST | List / create drawings |
| `/api/plugins/plan-drawing/drawings/<id>/` | GET, PUT, PATCH, DELETE | Retrieve / update / delete a drawing |
| `/api/plugins/plan-drawing/elements/` | GET | List linked drawing elements |
| `/api/plugins/plan-drawing/elements/<id>/` | GET | Retrieve a linked drawing element |

They follow NetBox's REST API conventions: authenticate with a token (or an authenticated browser session), page with `?limit=` and `?offset=`, request compact representations with `?brief=1`, and search with `?q=`. The complete schema is available from any NetBox instance at `/api/docs/`.

## Drawings

A drawing's `content` is the drawing in draw.io's XML format. Writing `content` validates it, and updates the drawing's linked elements, just like saving in the editor.

Drawings can be filtered by `site_id`, `location_id`, and by the objects they contain, with `object_type` (`<app_label>.<model>`) and `object_id`:

```
GET /api/plugins/plan-drawing/drawings/?object_type=dcim.device&object_id=4&brief=1
Authorization: Token <your-api-token>
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "url": "https://netbox.example.com/api/plugins/plan-drawing/drawings/1/",
      "display": "Demo Site Floor Plan",
      "name": "Demo Site Floor Plan",
      "description": "Demo drawing of two rooms, with racks, devices and a power panel linked to NetBox objects"
    }
  ]
}
```

## Linked elements

Linked elements are read-only: they are derived from the drawing's content whenever the drawing is saved, and their IDs change with every save. They can be filtered by `drawing_id`, `assigned_object_type` (e.g. `dcim.rack`), and `assigned_object_id`, e.g. to find where an object appears:

```
GET /api/plugins/plan-drawing/elements/?assigned_object_type=dcim.rack&assigned_object_id=1
Authorization: Token <your-api-token>
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 18,
      "url": "https://netbox.example.com/api/plugins/plan-drawing/elements/18/",
      "display": "R1 (Demo Site Floor Plan)",
      "drawing": {
        "id": 1,
        "url": "https://netbox.example.com/api/plugins/plan-drawing/drawings/1/",
        "display": "Demo Site Floor Plan",
        "name": "Demo Site Floor Plan",
        "description": "Demo drawing of two rooms, with racks, devices and a power panel linked to NetBox objects"
      },
      "page_id": "floor",
      "page_name": "Server Room",
      "cell_id": "rack-r1",
      "label": "R1",
      "assigned_object_type": "dcim.rack",
      "assigned_object_id": 1,
      "assigned_object": {
        "id": 1,
        "url": "https://netbox.example.com/api/dcim/racks/1/",
        "display": "R1",
        "name": "R1",
        "description": ""
      }
    }
  ]
}
```

`page_id` and `cell_id` identify the element in the drawing. Elements can be viewed by users who may view the drawing.

## Linking elements in the XML

To link elements to NetBox objects in a drawing created outside of NetBox, add these properties to the element (in draw.io: **Edit Data...**, or by editing the XML):

| Property | Value |
|----------|-------|
| `netbox_type` | The object type, as `<app_label>.<model>`, e.g. `dcim.rack` |
| `netbox_id` | The object's ID |
| `netbox_display` | Optional: the object's name, shown in the editor |

In the XML, the element is then wrapped in an `<object>` element carrying these properties:

```xml
<object id="rack-r1" label="R1" netbox_type="dcim.rack" netbox_id="1" netbox_display="R1">
  <mxCell style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
    <mxGeometry x="160" y="200" width="60" height="100" as="geometry"/>
  </mxCell>
</object>
```
