"""
Versioned URLs for the plugin's static files.

NetBox serves static files with a long cache lifetime, and the plugin's files keep their names
across releases; a content hash in the query string makes browsers load changed files.
"""
import hashlib
from functools import cache

from django.contrib.staticfiles import finders
from django.templatetags.static import static


@cache
def static_digest(path):
    found = finders.find(path)
    if not found:
        return None
    with open(found, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def versioned_static(path):
    url = static(path)
    digest = static_digest(path)
    return f'{url}?v={digest}' if digest else url
