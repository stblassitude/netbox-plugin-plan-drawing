# Netbox Plugin: Plan Drawing

This plugin provides the ability to add plan drawings, like floor plans, to Netbox, and place objects like devices, racks, or locations on those plans.

The plugin embeds draw.io to create and update the drawings. Each object in the drawing can be associated with a Netbox object. A draw.io plugin implements the necessary GUI to select the Netbox object to attach to a draw.io object in the drawing.

Besides a list of drawings and the ability to edit them with draw.io, a drawing viewer shows a drawing and the Netbox objects associated with the drawing objects in that file. A search allows to highlight elements based on their Netbox objects. Netbox object pages are extended with links to the drawing viewer, so a single click takes you from an object to the drawing it is in, and hightlights the element for that objects.

## Bundled draw.io

draw.io is included in the plugin: the Python package contains the draw.io web application, and NetBox serves it as static files from its own origin. There is no separate draw.io service to install or maintain, and the editor works without Internet access; draw.io's online integrations (Google Drive, OneDrive, GitHub, etc.) are turned off.

The bundled version is pinned in [scripts/fetch_drawio.py](scripts/fetch_drawio.py), and is updated with new releases of the plugin. draw.io is licensed under the Apache License 2.0; its license is included with the bundled copy.

## Data Model

A **Plan Drawing** has a name, an optional site and location, a description, comments, and tags, and the drawing itself in draw.io's XML format (`content`). A drawing can have multiple pages.

A drawing element (a draw.io shape or connector) is linked to a NetBox object through custom properties on the element: `netbox_type` (`<app_label>.<model>`, e.g. `dcim.rack`) and `netbox_id`, plus `netbox_display`, the object's name at the time it was linked. Whenever a drawing is saved, the plugin indexes its linked elements as **Plan Drawing Elements** (drawing, page, element ID, label, and the linked object); this index is what the viewer, the object pages, and the REST API use. Elements linked to objects that have since been deleted are shown as unavailable.

### Linkable object types

By default, elements can be linked to every model of the `dcim`, `circuits`, and `wireless` apps that can represent a physical object: sites, locations, racks, devices, modules, device components (interfaces, console, power and pass-through ports, power outlets, device and module bays), inventory items, cables, power panels and feeds, cooling equipment, virtual chassis, circuits and circuit terminations, provider networks, and wireless links. Models that describe kinds of things or organize them (device types, templates, roles, manufacturers, platforms, regions, site and rack groups, providers, etc.) are excluded. The list can be changed in the plugin configuration (see below).

## User Interface

* **Plan Drawings** in the navigation menu lists the drawings. Adding a drawing asks for its name, site, and location; the drawing itself starts out empty.
* The **drawing page** shows the drawing, with page selection and zoom, next to the list of linked elements. Clicking an element in the drawing selects it in the list, and vice versa; hovering over the list highlights the element in the drawing. The search box filters the list by object name, element label, or object type, and highlights all matching elements.
* **Edit Drawing** opens the drawing in draw.io. To link an element to a NetBox object, select it and click **Link to NetBox Object** above the editor, or use **Link to NetBox Object...** in the element's context menu; then choose the object type, and search for the object. Linked elements are marked with a link badge in the editor. **Save** stores the drawing; if someone else saved the same drawing since you opened it, saving is refused, so that their changes are not overwritten.
* The page of every linkable object shows a **Plan Drawings** panel listing the drawings the object appears in; each links to the drawing page with the object's elements highlighted (`?highlight=dcim.rack:12`). Site and location pages also list the drawings assigned to them.
* Drawings are included in NetBox's global search.

### Permissions

Viewing a drawing requires the `view` permission on Plan Drawings, editing it requires `change`. Linked elements are visible to everyone who may view the drawing; the linked objects themselves are only shown by name to users who may view them.

## Configuration

```python
PLUGINS_CONFIG = {
    "netbox_plugin_plan_drawing": {
        # Apps whose models can be linked to drawing elements.
        "object_type_apps": ["dcim", "circuits", "wireless"],
        # Models of those apps that cannot be linked. When set, replaces the built-in list
        # (see netbox_plugin_plan_drawing/object_types.py).
        "exclude_object_types": None,
        # Additional linkable models from other apps or plugins.
        "extra_object_types": [],
    },
}
```

## REST API

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/plugins/plan-drawing/drawings/` | GET, POST | List / create drawings |
| `/api/plugins/plan-drawing/drawings/<id>/` | GET, PUT, PATCH, DELETE | Retrieve / update / delete a drawing |
| `/api/plugins/plan-drawing/elements/` | GET | List linked drawing elements |
| `/api/plugins/plan-drawing/elements/<id>/` | GET | Retrieve a linked drawing element |

Drawings include their `content` (draw.io XML); writing `content` validates it and re-indexes the linked elements, as saving in the editor does. Drawings can be filtered by `site_id`, `location_id`, and by linked object with `object_type` and `object_id`. Elements are read-only, and can be filtered by `drawing_id`, `assigned_object_type` (e.g. `dcim.rack`), and `assigned_object_id`. Element IDs change whenever the drawing is saved.

Example: find the drawings a rack appears in, and where

```
GET /api/plugins/plan-drawing/elements/?assigned_object_type=dcim.rack&assigned_object_id=1
Authorization: Token <your-api-token>
```

```json
{
  "count": 1,
  "results": [
    {
      "id": 26,
      "url": "https://netbox.example.com/api/plugins/plan-drawing/elements/26/",
      "display": "R1 (Demo Site Floor Plan)",
      "drawing": {
        "id": 1,
        "url": "https://netbox.example.com/api/plugins/plan-drawing/drawings/1/",
        "display": "Demo Site Floor Plan",
        "name": "Demo Site Floor Plan",
        "description": ""
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
        "name": "R1"
      }
    }
  ]
}
```

## Change Log

Every save of a drawing is recorded in NetBox's change log like any other change, including the complete drawing XML before and after the change. For large drawings that are saved often, this can make the change log grow noticeably. To see how much space drawings take up in the change log, run:

```bash
python manage.py plan_drawing_changelog_stats
```

NetBox's [`CHANGELOG_RETENTION`](https://netboxlabs.com/docs/netbox/configuration/miscellaneous/#changelog_retention) setting limits how long change log entries are kept.

## Compatibility

| NetBox Version | Plugin Version |
|-----------------|----------------|
| 4.7 - 4.99      | 0.1.0          |

## Installation

Install the plugin into your NetBox virtual environment:

```bash
pip install netbox-plugin-plan-drawing
```

Enable it in your NetBox `configuration.py` (or `plugins.py`, if using [netbox-docker](https://github.com/netbox-community/netbox-docker)):

```python
PLUGINS = [
    "netbox_plugin_plan_drawing",
]
```

Then run migrations, collect the static files (which include draw.io, about 130 MB), and restart NetBox:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

Installing from a source checkout (or the sdist) downloads the pinned draw.io release from GitHub during the build.

## Development / Testing

A self-contained Docker Compose setup is included for trying the plugin out against a real NetBox instance. It builds a NetBox image with the plugin installed from this repository's source, so no packaging or PyPI publish is required.

```bash
docker compose up -d --build
```

Once the `netbox` service reports healthy, log in at <http://localhost:8000/> with `admin` / `admin`. A demo site is created automatically, with two locations: a server room with two racks, a few devices, and a power panel, and a network closet with a small 12U rack and a switch. The drawing *Demo Site Floor Plan* has a page for each room, with the elements linked to these objects.

Run the tests inside the running container:

```bash
docker compose exec netbox python manage.py test netbox_plugin_plan_drawing
```

To stop and remove the stack (including its database volume):

```bash
docker compose down -v
```

### draw.io

The draw.io web application is not kept in git. Building the package (and the Docker image) runs [scripts/fetch_drawio.py](scripts/fetch_drawio.py), which downloads the pinned draw.io release, verifies its SHA-256 checksum, unpacks the files needed to run it embedded, and adds the files from [drawio-overrides/](drawio-overrides/): draw.io configuration that turns off online services and registers the NetBox draw.io plugin ([drawio-netbox.js](netbox_plugin_plan_drawing/static/netbox_plugin_plan_drawing/drawio-netbox.js)). Downloads are cached in `.cache/drawio/` (or in `$DRAWIO_CACHE_DIR`). Run the script directly to unpack draw.io into the source tree, e.g. for development:

```bash
python scripts/fetch_drawio.py
```

To update draw.io, change `DRAWIO_VERSION` and `DRAWIO_SHA256` in the script (the checksum is shown as the `digest` of `draw.war` on the release's GitHub page), and check that editing, linking, and viewing still work.
