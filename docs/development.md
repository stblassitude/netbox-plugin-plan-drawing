# Development

## Development environment

The repository includes a Docker Compose setup that runs NetBox with the plugin installed from the source tree:

```bash
docker compose up -d --build
```

Once the `netbox` service reports healthy, log in at <http://localhost:8000/> with `admin` / `admin`. The demo data from [`docker/seed_demo_data.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/docker/seed_demo_data.py) is created automatically:

* a site with two locations: a server room with two racks, a few devices, an access point, and a power panel, and a network closet with a small 12U rack and a switch
* the drawing *Demo Site Floor Plan*, with a page for each room, and the elements linked to these objects

The demo data is only created on an empty database. To start over, remove the stack including its database volume, and start it again:

```bash
docker compose down -v
docker compose up -d --build
```

!!! warning
    This setup uses fixed, published credentials, and is meant for development and testing only.

After changing the plugin, rebuild the image with `docker compose up -d --build`.

## Tests

The tests run inside NetBox, in the running container:

```bash
docker compose exec netbox python manage.py test netbox_plugin_plan_drawing
```

The CI workflow builds the package, checks that the wheel contains draw.io, and runs the tests in the Docker Compose setup.

## draw.io

The draw.io web application is not kept in git. [`scripts/fetch_drawio.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/scripts/fetch_drawio.py) downloads the release pinned in the script, verifies its SHA-256 checksum, unpacks the parts needed to run draw.io embedded, and adds the files from [`drawio-overrides/`](https://github.com/stblassitude/netbox-plugin-plan-drawing/tree/main/drawio-overrides). The result goes into `netbox_plugin_plan_drawing/static/netbox_plugin_plan_drawing/drawio/`.

Building the package runs the script automatically ([`setup.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/setup.py)), and so does building the Docker image. To unpack draw.io into the source tree directly, e.g. to run the plugin from the source tree, run:

```bash
python scripts/fetch_drawio.py
```

Downloads are cached in `.cache/drawio/`, or in the directory given by `DRAWIO_CACHE_DIR`.

### Updating draw.io

1. Change `DRAWIO_VERSION` and `DRAWIO_SHA256` in `scripts/fetch_drawio.py`. The checksum is shown as the `digest` of `draw.war` on the release's GitHub page, or with `curl -s https://api.github.com/repos/jgraph/drawio/releases/tags/v<version>`.
2. Update `drawio-overrides/LICENSE` if draw.io's license changed.
3. Rebuild, and check that editing, linking, saving, and viewing drawings still work. The plugin relies on some draw.io internals (see the [implementation notes](implementation.md#drawio)).

## Documentation

The documentation is built with [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), and published to GitHub Pages by the `docs` workflow on every push to `main` that changes it. To preview it locally:

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

The screenshots are taken from the development environment with its demo data, with [Playwright](https://playwright.dev/python/):

```bash
pip install playwright && playwright install chromium
python scripts/docs_screenshots.py
```

## Releasing

Pushing a tag `v<version>` creates a GitHub release, and publishes the package to PyPI (using PyPI's trusted publishing); the package version is taken from the tag.
