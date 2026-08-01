#!/usr/bin/env python3
"""
NYMCU Control Bar CTA Link Regression Test — STG Environment

Smoke test: selects the first product in the control bar dropdown,
captures its first CTA href, and verifies the URL returns a valid HTTP response.

Run:
    pytest test_nymcu_controlbar_cta_link_STG.py -v
    python test_nymcu_controlbar_cta_link_STG.py
"""

import sys
import io
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if not hasattr(sys, '_called_from_pytest') and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL  = 'https://www.nymcu.org'
START_URL = 'https://www.nymcu.org/home-ext?session_init=1&debug_all=1&cb=1'

PRODUCTS_SELECT_SELECTORS = [
    'select#finalytics-cb-products',
    'select[id*="product"]',
    '.finalytics-control-bar select',
    '#finalytics-controlbar select',
    '[id*="control"] select',
    '[class*="control"] select',
    'select',
]

HERO_CTA_SELECTORS = [
    '.finalytics-hero a[href]',
    '.finalytics-hero-cta a[href]',
    '.finalytics-ad a[href]',
    '.hero a[href]',
    'section.hero a[href]',
    '.hero-cta a[href]',
    '.hero-buttons a[href]',
    '[class*="hero"] a[href]',
]


def build_full_url(href: str) -> str:
    if href.startswith('http'):
        return href
    return urljoin(BASE_URL, href)


def find_select(page):
    for sel in PRODUCTS_SELECT_SELECTORS:
        for el in page.query_selector_all(sel):
            if el.is_visible():
                return el
    return None


def check_url_status(page, url: str) -> dict:
    parsed = urlparse(url)
    url_no_fragment = parsed._replace(fragment='').geturl()
    result = {'url': url_no_fragment, 'status': None, 'ok': False, 'note': ''}
    try:
        response = page.goto(url_no_fragment, timeout=20000, wait_until='domcontentloaded')
        if response:
            result['status'] = response.status
            if response.status == 200:
                title = page.title().lower()
                h1_texts = ' '.join(el.inner_text().lower()
                                    for el in page.query_selector_all('h1') if el.inner_text())
                combined = title + ' ' + h1_texts
                if any(kw in combined for kw in ('not found', '404', "can't find", 'page not found')):
                    result['note'] = f'Soft 404 (title: "{page.title()}")'
                else:
                    result['ok'] = True
            else:
                result['note'] = f'HTTP {response.status}'
        else:
            result['note'] = 'No response object'
    except PlaywrightTimeoutError:
        result['note'] = 'Timeout'
    except Exception as exc:
        result['note'] = str(exc)[:120]
    return result


def test_nymcu_controlbar_first_product_first_cta_link():
    """
    Regression: select the first product in the NYMCU control bar,
    grab its first CTA href, and assert the URL is reachable (HTTP 200).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            ignore_https_errors=True,
        )
        page = context.new_page()

        # ── Navigate to STG page with control bar ──
        print(f'\nNavigating to {START_URL}')
        page.goto(START_URL, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        # ── Find the Products dropdown ──
        select_el = find_select(page)
        assert select_el is not None, 'Could not find Products <select> in the control bar'

        options_data = select_el.evaluate(
            'el => Array.from(el.options).map(o => ({value: o.value, text: o.text.trim()}))'
        )
        valid_options = [o for o in options_data
                         if o['value'] and o['text'].lower() not in ('select', '-- select --', '')]
        assert valid_options, 'No valid product options found in control bar dropdown'

        first_opt = valid_options[0]
        print(f'Selected product: {first_opt["text"]!r}')

        # ── Re-navigate cleanly, then select the product ──
        page.goto(START_URL, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(2500)

        select_el = find_select(page)
        assert select_el is not None, 'Could not re-find Products <select> after navigation'

        try:
            select_el.select_option(value=first_opt['value'])
        except Exception:
            select_el.select_option(label=first_opt['text'])

        page.wait_for_timeout(3000)

        # ── Capture first CTA href from hero ──
        first_cta = None
        for selector in HERO_CTA_SELECTORS:
            for el in page.query_selector_all(selector):
                if not el.is_visible():
                    continue
                href = el.get_attribute('href') or ''
                text = (el.inner_text() or '').strip()
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                first_cta = {'text': text, 'href': href}
                break
            if first_cta:
                break

        assert first_cta is not None, (
            f'No CTA links found in hero for product {first_opt["text"]!r}'
        )

        full_url = build_full_url(first_cta['href'])
        print(f'CTA: {first_cta["text"]!r} → {full_url}')

        # ── Check the URL is reachable ──
        result = check_url_status(page, full_url)
        print(f'HTTP status: {result["status"]} — {"OK" if result["ok"] else "FAIL: " + result["note"]}')

        browser.close()

    assert result['ok'], (
        f'CTA link for product {first_opt["text"]!r} returned '
        f'HTTP {result["status"]} ({result["note"]}): {full_url}'
    )


if __name__ == '__main__':
    test_nymcu_controlbar_first_product_first_cta_link()
    print('\nRegression test passed.')
