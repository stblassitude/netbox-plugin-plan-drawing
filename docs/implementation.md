# Implementation Notes

## Data model

**`PlanDrawing`** is a regular NetBox model (a `PrimaryModel`, with description, comments, owner, tags, custom fields, journal, and change log). It holds the drawing in draw.io's XML format in `content`, uncompressed, plus the optional `site` and `location` it belongs to.

**`PlanDrawingElement`** is an index of the elements linked to NetBox objects: the drawing, the page and element (draw.io "cell") IDs, the element's label, and a generic foreign key to the linked object. It is rebuilt from the drawing's content every time the drawing is saved (`PlanDrawing.save()` calls `sync_elements()`), so it is not a NetBox model with its own change log or permissions. Elements are visible to users who may view their drawing (`PlanDrawingElementQuerySet.restrict()`). The index is what the viewer, the object pages, and the REST API filters use; without it, finding the drawings an object appears in would mean parsing every drawing.

Links to objects that no longer exist are kept, and shown as unavailable; deleting an object does not change drawings.

## Drawing format

A draw.io file is an `<mxfile>` with a `<diagram>` per page. Each page contains an `<mxGraphModel>`, either as XML, or compressed (the URL-encoded XML, deflated, and base64 encoded). The editor is configured to save uncompressed XML, but [`drawio.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/drawio.py) reads both, as well as a bare `<mxGraphModel>`.

An element with custom properties is wrapped in an `<object>` (or `<UserObject>`) element carrying the properties as attributes; the plugin uses `netbox_type`, `netbox_id`, and `netbox_display` (see the [REST API](rest-api.md#linking-elements-in-the-xml) page). The XML is parsed with `defusedxml`. Validation (`PlanDrawing.clean()`) rejects invalid XML, incomplete links, and links to object types that cannot be linked.

## Linkable object types

[`object_types.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/object_types.py) computes the linkable models from Django's app registry: all concrete models of the configured apps that have a detail page, except templates and an exclude list. This list is also used to register the Plan Drawings panel for the object pages, which happens when NetBox starts; changing the configuration requires a restart.

## draw.io

### Bundling

draw.io is served by NetBox as static files of the plugin, from NetBox's own origin. Besides keeping everything local, this is what makes the integration straightforward: draw.io only loads custom plugins from its own origin, and pages on the same origin can call into each other directly.

The stock `js/PreConfig.js` and `js/PostConfig.js` are replaced (from `drawio-overrides/`):

* `PreConfig.js` turns off draw.io's online services and integrations (Google Drive, OneDrive, GitHub, GitLab, Dropbox, Trello, math typesetting, the export server).
* `PostConfig.js` registers the plugin's draw.io plugin in draw.io's list of built-in plugins, as `netbox`.

draw.io's `offline=1` mode is not used, since it also disables plugins; `stealth=1` and the settings above take its place.

### Editor

The editor page ([`editor.js`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/static/netbox_plugin_plan_drawing/editor.js)) embeds draw.io in an iframe with `embed=1&proto=json&configure=1&p=netbox`, and uses draw.io's [embed protocol](https://www.drawio.com/doc/faq/embed-mode) (JSON messages over `postMessage`):

1. draw.io sends `configure`; the page sets draw.io's configuration (uncompressed XML, no online fonts).
2. draw.io sends `init`; the page sends `load` with the drawing.
3. When the user saves, draw.io sends `save` with the drawing's XML. The page posts it to the plugin's `drawings/<id>/content/` endpoint, together with the drawing's `last_updated` time from when it was loaded. If the drawing has changed since, the endpoint responds with *409 Conflict*; otherwise it saves the drawing like any other change (with a change log entry), and returns the new `last_updated` time.
4. `exit` returns to the drawing page.

### draw.io plugin

The draw.io plugin ([`drawio-netbox.js`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/static/netbox_plugin_plan_drawing/drawio-netbox.js)) runs inside draw.io, and adds:

* the **Link to NetBox Object...** and **Remove NetBox Link** actions, in the context menu;
* badges on linked elements (draw.io cell overlays, which are not saved with the drawing);
* notifications to the page when the selection or the drawing changes.

The object picker is part of the NetBox page, not of draw.io, so that it can use NetBox's REST API with the user's session. The plugin and the page call each other directly: the page provides `window.netboxPlanDrawingEditor` (`pick()`, `selectionChanged()`, `modifiedChanged()`, `register()`), which the plugin reaches as `window.parent.netboxPlanDrawingEditor`; the plugin registers `linkSelection()` and `unlinkSelection()` for the buttons above the editor. The picker searches the REST API list endpoint of the chosen object type (`?brief=1&q=`).

### Viewer

The viewer ([`viewer.js`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/static/netbox_plugin_plan_drawing/viewer.js)) uses draw.io's `viewer-static.min.js` (`GraphViewer`), with its paths pointed at the bundled copy. Its own toolbar replaces draw.io's, which is designed for diagrams embedded in text; the viewer fits the drawing into a fixed-height, scrollable container instead of sizing the container to the drawing.

The page renders the list of linked elements, and passes the same data, the drawing, and the `?highlight=` parameter to the viewer as JSON. The viewer's graph is read-only, so it fires no click events; clicks are detected from mouse down and up events on the same spot. Highlights are draw.io `mxCellHighlight`s, redrawn when the page changes. The highlight color is defined once, as the CSS variable `--plan-drawing-select-color`.

### Static files and caching

NetBox serves static files with a cache lifetime of one day, and the plugin's files keep their names from release to release. The plugin's templates therefore reference its JavaScript and CSS files with a content hash in the query string ([`assets.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/assets.py)). The editor passes the hash of the draw.io plugin to draw.io as the `nbv` URL parameter, which `PostConfig.js` adds to the plugin's URL.

## Permissions

The viewer and the object page panel only show drawings the user may view, and objects the user may view (others are listed without their name). The editor and the save endpoint require the *change* permission, including object-level permission constraints: a save that would put the drawing outside the user's constraints is rolled back.
