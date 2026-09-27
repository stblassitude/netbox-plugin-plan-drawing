from django import template

from .. import assets

register = template.Library()


@register.simple_tag
def versioned_static(path):
    return assets.versioned_static(path)
