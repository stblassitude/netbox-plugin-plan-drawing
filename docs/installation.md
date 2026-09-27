# Installation

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
| 4.7 - 4.99     | 1.0.0          |

## Installing the plugin

Install the plugin into your NetBox virtual environment:

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-plugin-plan-drawing
```

To have the plugin reinstalled when NetBox is upgraded, add it to NetBox's `local_requirements.txt`:

```bash
echo netbox-plugin-plan-drawing >> /opt/netbox/local_requirements.txt
```

Enable the plugin in NetBox's `configuration.py`:

```python
PLUGINS = [
    "netbox_plugin_plan_drawing",
]
```

Then run the database migrations, collect the static files, and restart NetBox:

```bash
cd /opt/netbox/netbox
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart netbox netbox-rq
```

!!! note "Static files"
    The plugin's static files include draw.io, about 130 MB in about 3,000 files. `collectstatic` copies them into NetBox's static files directory, from where they are served like NetBox's own.

The PyPI package contains draw.io. Installing from a source checkout or from the source distribution instead downloads the pinned draw.io release from GitHub while building the package.

### netbox-docker

With [netbox-docker](https://github.com/netbox-community/netbox-docker), add the plugin to `plugin_requirements.txt`, enable it in `configuration/plugins.py`, and build a custom image, as described in netbox-docker's [plugin documentation](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins). The image build runs `collectstatic`.

## Configuration

The plugin works without configuration. The object types that drawing elements can be linked to can be changed in `PLUGINS_CONFIG`:

```python
PLUGINS_CONFIG = {
    "netbox_plugin_plan_drawing": {
        # Apps whose models can be linked to drawing elements.
        "object_type_apps": ["dcim", "circuits", "wireless"],
        # Models of those apps that cannot be linked, as "<app_label>.<model>". When set,
        # replaces the built-in list.
        "exclude_object_types": None,
        # Additional linkable models from other apps or plugins.
        "extra_object_types": [],
    },
}
```

By default, all models of the `dcim`, `circuits`, and `wireless` apps can be linked, except for templates (e.g. `dcim.interfacetemplate`), and for the models listed in `DEFAULT_EXCLUDED_OBJECT_TYPES` in [`object_types.py`](https://github.com/stblassitude/netbox-plugin-plan-drawing/blob/main/netbox_plugin_plan_drawing/object_types.py): types, roles, groups, and similar organizational models. To make, say, VLANs linkable as well, add `"extra_object_types": ["ipam.vlan"]`.

## Change log

Every save of a drawing is recorded in NetBox's change log, with the complete drawing before and after the change. For large drawings that are saved often, this can make the change log grow noticeably. This command shows how much space drawings take up in the change log:

```bash
python manage.py plan_drawing_changelog_stats
```

```
Drawing                                     Content  Changes  Log stored     Log raw  Per change
------------------------------------------------------------------------------------------------
Demo Site Floor Plan                        3.6 KiB        3     6.7 KiB    21.2 KiB     2.2 KiB
------------------------------------------------------------------------------------------------
Total                                                      3     6.7 KiB    21.2 KiB     2.2 KiB

Change log table core_objectchange: 160.0 KiB in total, 3 entries for all object types.
```

*Log stored* is the size after PostgreSQL's compression, *Log raw* the uncompressed size. NetBox's [`CHANGELOG_RETENTION`](https://netboxlabs.com/docs/netbox/configuration/miscellaneous/#changelog_retention) setting limits how long change log entries are kept.
