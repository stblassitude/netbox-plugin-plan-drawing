from netbox.plugins import PluginConfig


class PlanDrawingConfig(PluginConfig):
    name = 'netbox_plugin_plan_drawing'
    verbose_name = 'Plan Drawings'
    description = 'Plan drawings (floor plans etc.) edited with draw.io, with elements linked to NetBox objects'
    version = '1.0.0'
    author = 'Stefan Bethke'
    author_email = 'stb@lassitu.de'
    base_url = 'plan-drawing'
    min_version = '4.7.0'
    max_version = '4.99.99'
    default_settings = {
        # Apps whose models can be linked to drawing elements.
        'object_type_apps': ['dcim', 'circuits', 'wireless'],
        # Models from those apps that cannot be linked, as '<app_label>.<model_name>'. Replaces
        # the built-in default list (see object_types.DEFAULT_EXCLUDED_OBJECT_TYPES) when set.
        'exclude_object_types': None,
        # Additional linkable models from other apps or plugins, as '<app_label>.<model_name>'.
        'extra_object_types': [],
    }


config = PlanDrawingConfig
