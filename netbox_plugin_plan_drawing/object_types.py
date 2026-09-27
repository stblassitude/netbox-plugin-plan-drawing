"""
The NetBox object types that drawing elements can be linked to.

By default, these are all models of the apps listed in the object_type_apps setting that can
represent a physical object: sites, locations, racks, devices and their components, cables,
power panels and feeds, circuits, and so on. Models that describe kinds of things (types,
templates, roles), organize them (regions, groups), or are internal bookkeeping are excluded.
"""
from functools import cache

from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from netbox.plugins import get_plugin_config

PLUGIN_NAME = 'netbox_plugin_plan_drawing'

DEFAULT_EXCLUDED_OBJECT_TYPES = (
    # dcim: kinds of things, organization, and bookkeeping
    'dcim.cablepath',
    'dcim.cabletermination',
    'dcim.devicerole',
    'dcim.devicetype',
    'dcim.inventoryitemrole',
    'dcim.macaddress',
    'dcim.manufacturer',
    'dcim.modulebaytype',
    'dcim.moduletype',
    'dcim.moduletypeprofile',
    'dcim.platform',
    'dcim.portmapping',
    'dcim.porttemplatemapping',
    'dcim.rackgroup',
    'dcim.rackreservation',
    'dcim.rackrole',
    'dcim.racktype',
    'dcim.region',
    'dcim.sitegroup',
    'dcim.virtualdevicecontext',
    # circuits: providers, kinds of circuits, and virtual circuits
    'circuits.circuitgroup',
    'circuits.circuitgroupassignment',
    'circuits.circuittype',
    'circuits.provider',
    'circuits.provideraccount',
    'circuits.virtualcircuit',
    'circuits.virtualcircuittermination',
    'circuits.virtualcircuittype',
    # wireless: logical networks
    'wireless.wirelesslan',
    'wireless.wirelesslangroup',
)


def object_type_label(model):
    return f'{model._meta.app_config.verbose_name} > {model._meta.verbose_name.title()}'


def object_type_key(model):
    return f'{model._meta.app_label}.{model._meta.model_name}'


def _is_linkable(model):
    # Only concrete models with their own detail page can be shown and linked to.
    return (
        not model._meta.abstract
        and not model._meta.proxy
        and not model._meta.model_name.endswith('template')
        and hasattr(model, 'get_absolute_url')
    )


@cache
def get_linkable_models():
    """
    Return the linkable models, sorted by label.
    """
    excluded = get_plugin_config(PLUGIN_NAME, 'exclude_object_types')
    if excluded is None:
        excluded = DEFAULT_EXCLUDED_OBJECT_TYPES
    excluded = {name.lower() for name in excluded}

    models = []
    for app_label in get_plugin_config(PLUGIN_NAME, 'object_type_apps'):
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            continue
        models.extend(
            model for model in app_config.get_models()
            if _is_linkable(model) and object_type_key(model) not in excluded
        )

    for name in get_plugin_config(PLUGIN_NAME, 'extra_object_types'):
        try:
            model = apps.get_model(name)
        except (LookupError, ValueError):
            continue
        if model not in models:
            models.append(model)

    return tuple(sorted(models, key=object_type_label))


def get_linkable_model_keys():
    return tuple(object_type_key(model) for model in get_linkable_models())


def get_linkable_model(key):
    """
    Return the linkable model for '<app_label>.<model_name>', or None.
    """
    for model in get_linkable_models():
        if object_type_key(model) == key.lower():
            return model
    return None


def get_linkable_content_types():
    return ContentType.objects.get_for_models(*get_linkable_models())
