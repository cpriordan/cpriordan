#!/usr/bin/env python3
"""
NYMCU Checking Account Search-Trigger Regression Test — STG Environment

Smoke test: performs a site search for "checking account", then navigates
back to the STG homepage and verifies a checking-account hero ad is
displayed (and that its CTA link is reachable).

Run:
    pytest test_nymcu_checking_search_STG.py -v
    python test_nymcu_checking_search_STG.py
"""

import sys
import io
from urllib.parse import urljoin, urlparse

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if not hasattr(sys, '_called_from_pytest') and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://www.nymcu.org'
SEARCH_URL = (
    'https://www.nymcu.org/hs-search-results'
    '?term=checking+account&type=SITE_PAGE&type=BLOG_POST&type=LISTING_PAGE'
)
HOME_URL = 'https://www.nymcu.org/home-ext?cb=1&session_init=1&debug_all=1'

HERO_SELECTOR = '#home-hero'
HERO_HEADING_SELECTOR = f'{HERO_SELECTOR} h1'
HERO_CTA_SELECTOR = f'{HERO_SELECTOR} a[href]'

EXPECTED_KEYWORD = 'checking'


def build_full_url(href: str) -> str:
    if href.startswith('http'):
        return href
    return urljoin(BASE_URL, href)


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


def test_nymcu_checking_search_STG():
    """
    Regression: search "checking account" on NYMCU's site search, navigate
    back to the STG homepage, and assert a checking-account hero ad is
    displayed with a reachable CTA link.
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

        # ── Perform the search ──
        print(f'\nSearching: {SEARCH_URL}')
        search_response = page.goto(SEARCH_URL, timeout=30000, wait_until='domcontentloaded')
        assert search_response is not None and search_response.status == 200, (
            f'Search page did not load successfully (status: '
            f'{search_response.status if search_response else "no response"})'
        )
        page.wait_for_timeout(2000)
        print(f'Search page title: {page.title()!r}')

        # ── Go back to the STG homepage ──
        print(f'Navigating to homepage: {HOME_URL}')
        home_response = page.goto(HOME_URL, timeout=60000, wait_until='domcontentloaded')
        assert home_response is not None and home_response.status == 200, (
            f'Homepage did not load successfully (status: '
            f'{home_response.status if home_response else "no response"})'
        )
        page.wait_for_timeout(4000)

        # ── Verify a checking-account hero ad is displayed ──
        heading_el = page.query_selector(HERO_HEADING_SELECTOR)
        assert heading_el is not None, (
            f'Could not find hero heading ({HERO_HEADING_SELECTOR}) on homepage after search'
        )
        heading_text = heading_el.inner_text().strip()
        print(f'Hero heading: {heading_text!r}')
        assert EXPECTED_KEYWORD in heading_text.lower(), (
            f'Expected hero heading to mention {EXPECTED_KEYWORD!r} after searching '
            f'"checking account", but got: {heading_text!r}'
        )

        # ── Verify the hero's CTA link is reachable ──
        cta_el = page.query_selector(HERO_CTA_SELECTOR)
        assert cta_el is not None, f'No CTA link found in hero ({HERO_CTA_SELECTOR})'
        cta_text = (cta_el.inner_text() or '').strip()
        cta_href = cta_el.get_attribute('href') or ''
        full_url = build_full_url(cta_href)
        print(f'CTA: {cta_text!r} -> {full_url}')

        result = check_url_status(page, full_url)
        print(f'CTA HTTP status: {result["status"]} — {"OK" if result["ok"] else "FAIL: " + result["note"]}')

        browser.close()

    assert result['ok'], (
        f'Checking-account hero CTA link returned HTTP {result["status"]} '
        f'({result["note"]}): {full_url}'
    )


if __name__ == '__main__':
    test_nymcu_checking_search_STG()
    print('\nRegression test passed.')
