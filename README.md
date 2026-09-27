# Netbox Plugin: Plan Drawing

This plugin provides the ability to add plan drawings, like floor plans, to Netbox, and place objects like devices, racks, or locations on those plans.

The plugin embeds draw.io to create and update the drawings. Each object in the drawing can be associated with a Netbox object. A draw.io plugin implements the necessary GUI to select the Netbox object to attach to a draw.io object in the drawing.

Besides a list of drawings and the ability to edit them with draw.io, a drawing viewer shows a drawing and the Netbox objects associated with the drawing objects in that file. A search allows to highlight elements based on their Netbox objects. Netbox object pages are extended with links to the drawing viewer, so a single click takes you from an object to the drawing it is in, and hightlights the element for that objects.

draw.io is included in the plugin and served by NetBox itself: there is no separate service to install, and nothing is sent to draw.io's online services.

![The drawing viewer, with the access point ap1 highlighted](https://raw.githubusercontent.com/stblassitude/netbox-plugin-plan-drawing/main/docs/images/viewer.png)

**Documentation: <https://stblassitude.github.io/netbox-plugin-plan-drawing/>**

* [Overview](https://stblassitude.github.io/netbox-plugin-plan-drawing/): viewing and editing drawings, and linking elements to NetBox objects
* [Installation](https://stblassitude.github.io/netbox-plugin-plan-drawing/installation/): installation and configuration
* [REST API](https://stblassitude.github.io/netbox-plugin-plan-drawing/rest-api/)
* [Development](https://stblassitude.github.io/netbox-plugin-plan-drawing/development/) and [implementation notes](https://stblassitude.github.io/netbox-plugin-plan-drawing/implementation/)

## Compatibility

| NetBox Version | Plugin Version |
|-----------------|----------------|
| 4.7 - 4.99      | 1.0.0          |

## Installation

```bash
pip install netbox-plugin-plan-drawing
```

Add `"netbox_plugin_plan_drawing"` to `PLUGINS` in NetBox's `configuration.py`, then run `python manage.py migrate` and `python manage.py collectstatic --no-input`, and restart NetBox. See the [installation guide](https://stblassitude.github.io/netbox-plugin-plan-drawing/installation/) for details and configuration options.

## Development

```bash
docker compose up -d --build
```

This starts NetBox with the plugin installed from the source tree, and demo data, at <http://localhost:8000/> (`admin` / `admin`). Run the tests with `docker compose exec netbox python manage.py test netbox_plugin_plan_drawing`. See the [development guide](https://stblassitude.github.io/netbox-plugin-plan-drawing/development/) for more.

## License

MIT; see [LICENSE](LICENSE). The bundled [draw.io](https://github.com/jgraph/drawio) is licensed under the Apache License 2.0.
