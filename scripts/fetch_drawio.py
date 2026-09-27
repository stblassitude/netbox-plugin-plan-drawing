#!/usr/bin/env python3
"""
Download a pinned draw.io release and unpack the web application into the plugin's static
files, so that NetBox can serve draw.io from its own origin.

The unpacked copy is not kept in git; it is created on demand by the package build (see
setup.py), by the Dockerfile, or by running this script directly:

    python scripts/fetch_drawio.py [--force]

Only the files needed to run draw.io embedded in a page are kept. Our own PreConfig.js and
PostConfig.js (from drawio-overrides/) replace the stock ones: they turn off draw.io's online
integrations and register the NetBox draw.io plugin.
"""
import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DRAWIO_VERSION = '31.5.3'
DRAWIO_SHA256 = '6c4ab25145c3479bf0097e4fccd20c602968615986bc999af8a214719fabd3f4'
DRAWIO_URL = 'https://github.com/jgraph/drawio/releases/download/v{version}/draw.war'

ROOT = Path(__file__).resolve().parent.parent
# Downloads are kept here; set DRAWIO_CACHE_DIR to share them between builds (e.g. in CI, where
# the wheel is built from an unpacked sdist in a temporary directory).
CACHE_DIR = Path(os.environ.get('DRAWIO_CACHE_DIR') or ROOT / '.cache' / 'drawio')
OVERRIDES_DIR = ROOT / 'drawio-overrides'
TARGET_DIR = ROOT / 'netbox_plugin_plan_drawing' / 'static' / 'netbox_plugin_plan_drawing' / 'drawio'
MARKER = '.drawio-version'

# Archive members that are not needed to run draw.io embedded in NetBox: the Java servlet
# parts, unminified sources (already contained in the *.min.js bundles), math typesetting
# (disabled in PreConfig.js), source maps, and the PWA service worker.
EXCLUDED_PREFIXES = (
    'WEB-INF/',
    'META-INF/',
    'js/diagramly/',
    'js/grapheditor/',
    'math4/',
    'service-worker.js',
    'workbox-',
)
EXCLUDED_SUFFIXES = ('.map',)


def is_installed(target=TARGET_DIR):
    marker = target / MARKER
    return marker.is_file() and marker.read_text().strip() == DRAWIO_VERSION


def download(version=DRAWIO_VERSION, expected_sha256=DRAWIO_SHA256):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive = CACHE_DIR / f'draw-{version}.war'
    if not archive.is_file():
        url = DRAWIO_URL.format(version=version)
        print(f'Downloading {url}', file=sys.stderr)
        partial = archive.with_suffix('.part')
        with urllib.request.urlopen(url) as response, open(partial, 'wb') as f:
            shutil.copyfileobj(response, f)
        partial.rename(archive)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_sha256:
        archive.unlink()
        raise RuntimeError(
            f'SHA-256 mismatch for draw.io {version}: expected {expected_sha256}, got {digest}'
        )
    return archive


def is_excluded(name):
    return name.startswith(EXCLUDED_PREFIXES) or name.endswith(EXCLUDED_SUFFIXES)


def copy_overrides(target=TARGET_DIR):
    for override in OVERRIDES_DIR.rglob('*'):
        if override.is_file():
            destination = target / override.relative_to(OVERRIDES_DIR)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(override, destination)


def install(force=False, target=TARGET_DIR):
    if is_installed(target) and not force:
        # The overrides are part of this repository and may have changed.
        copy_overrides(target)
        return False

    archive = download()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    with zipfile.ZipFile(archive) as war:
        for member in war.infolist():
            if member.is_dir() or is_excluded(member.filename):
                continue
            war.extract(member, target)

    copy_overrides(target)
    (target / MARKER).write_text(DRAWIO_VERSION + '\n')
    print(f'Installed draw.io {DRAWIO_VERSION} into {target}', file=sys.stderr)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--force', action='store_true', help='reinstall even if already present')
    args = parser.parse_args()
    if not install(force=args.force):
        print(f'draw.io {DRAWIO_VERSION} already installed in {TARGET_DIR}', file=sys.stderr)


if __name__ == '__main__':
    main()
