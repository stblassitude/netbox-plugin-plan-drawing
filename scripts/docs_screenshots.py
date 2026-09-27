#!/usr/bin/env python3
"""
Take the screenshots for the documentation from a NetBox instance with the demo data (see
docker/seed_demo_data.py), e.g. the Docker Compose development environment:

    pip install playwright && playwright install chromium
    python scripts/docs_screenshots.py [--url http://localhost:8000]

The images are written to docs/images/.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'images'
VIEWPORT = {'width': 1440, 'height': 900}


def screenshot(page, name):
    """
    Take a screenshot of the page, without NetBox's navigation sidebar.
    """
    left = page.evaluate(
        "(document.querySelector('.navbar-vertical') || {getBoundingClientRect: () => ({right: 0})})"
        ".getBoundingClientRect().right"
    )
    clip = {'x': left, 'y': 0, 'width': VIEWPORT['width'] - left, 'height': VIEWPORT['height']}
    page.screenshot(path=OUTPUT_DIR / name, clip=clip)


def object_id(page, base_url, endpoint, name):
    response = page.request.get(f'{base_url}/api/{endpoint}/?name={name}&brief=1')
    return response.json()['results'][0]['id']


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--url', default='http://localhost:8000', help='NetBox base URL')
    parser.add_argument('--username', default='admin')
    parser.add_argument('--password', default='admin')
    args = parser.parse_args()
    base_url = args.url.rstrip('/')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)

        page.goto(f'{base_url}/login/')
        page.fill('input[name=username]', args.username)
        page.fill('input[name=password]', args.password)
        page.click('button[type=submit]')

        drawing = page.request.get(f'{base_url}/api/plugins/plan-drawing/drawings/?brief=1').json()['results'][0]
        drawing_url = f'{base_url}/plugins/plan-drawing/drawings/{drawing["id"]}/'
        ap1 = object_id(page, base_url, 'dcim/devices', 'ap1')

        # Viewer, with the access point highlighted
        page.goto(f'{drawing_url}?highlight=dcim.device:{ap1}')
        page.wait_for_function('window.planDrawingViewer !== undefined')
        page.wait_for_timeout(500)
        screenshot(page, 'viewer.png')

        # Searching for racks
        page.goto(drawing_url)
        page.wait_for_function('window.planDrawingViewer !== undefined')
        page.fill('#plan-drawing-search', 'rack')
        page.wait_for_timeout(300)
        page.locator('.row', has=page.locator('#plan-drawing-viewer')).first.screenshot(
            path=OUTPUT_DIR / 'viewer-search.png',
        )

        # The drawing panel on the device page
        page.goto(f'{base_url}/dcim/devices/{ap1}/')
        page.locator('.card', has=page.locator('h2', has_text='Plan Drawings')).screenshot(
            path=OUTPUT_DIR / 'object-panel.png',
        )

        # Editor, with the access point selected
        page.goto(f'{drawing_url}draw/')
        frame = page.frame_locator('#plan-drawing-frame')
        frame.get_by_text('ap1', exact=True).click()
        # Move away to an empty spot of the canvas, which hides the tooltip.
        canvas = page.locator('#plan-drawing-frame').bounding_box()
        page.mouse.move(canvas['x'] + canvas['width'] / 2, canvas['y'] + canvas['height'] - 20, steps=5)
        page.wait_for_timeout(1000)
        screenshot(page, 'editor.png')

        # Object picker
        page.click('#plan-drawing-link')
        page.select_option('#plan-drawing-picker-type', 'dcim.device')
        page.wait_for_timeout(1000)
        screenshot(page, 'picker.png')

        browser.close()
    print(f'Screenshots written to {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
