#!/usr/bin/env python3
"""
UHFCU Car Loan Search-Trigger Regression Test — STG Environment

Smoke test: performs a site search for "car loan", then navigates back to
the STG homepage and verifies a Car Loan hero ad is displayed (and that
its CTA link is reachable).

Discovery notes (verified live):
  - get_ads() includes the search-matched Car Loan ad
    ("Car Loan - Oct 2025", algorithms: "search") in its response
    immediately after the search, alongside the existing geo-segment
    hero ad -- unlike Langley FCU, the hero slot here shows the
    search-matched ad on the very first return to the homepage, no
    reload/retry needed.
  - Search uses standard WordPress search (?s=<query>), not a dedicated
    search endpoint.

Run:
    pytest test_uhfcu_carloan_search_STG.py -v
    python test_uhfcu_carloan_search_STG.py
"""

import sys
import io
import time
from urllib.parse import urljoin, urlparse

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if not hasattr(sys, '_called_from_pytest') and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://uhfcustage.wpenginepowered.com'
HOME_URL_INIT = f'{BASE_URL}/?session_init=1&debug_all=1&api=stg&cb=1'
SEARCH_URL = f'{BASE_URL}/?s=car+loan'
HOME_URL_RETURN = f'{BASE_URL}/?session_init=1&debug_all=1&cb=1'

HERO_HEADING_SELECTOR = 'h2.slider-heading'
HERO_CTA_SELECTOR = 'a[data-fin][href]'

EXPECTED_KEYWORD = 'car'

MAX_AD_RETRIES = 5
RETRY_SLEEP = 3
POST_RELOAD_WAIT = 4000  # ms


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


def find_hero_heading_text(page):
    for el in page.query_selector_all(HERO_HEADING_SELECTOR):
        if el.is_visible():
            text = (el.inner_text() or '').strip()
            if text and EXPECTED_KEYWORD in text.lower():
                return text
    return None


def test_uhfcu_carloan_search_STG():
    """
    Regression: search "car loan" on UHFCU's site search, navigate back to
    the STG homepage, and assert a Car Loan hero ad is displayed with a
    reachable CTA link.
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

        # ── Establish session on the homepage ──
        print(f'\nOpening homepage (session_init): {HOME_URL_INIT}')
        home_init_response = page.goto(HOME_URL_INIT, timeout=60000, wait_until='networkidle')
        assert home_init_response is not None and home_init_response.status == 200, (
            f'Initial homepage did not load successfully (status: '
            f'{home_init_response.status if home_init_response else "no response"})'
        )
        page.wait_for_timeout(2000)

        # ── Perform the search ──
        print(f'Searching: {SEARCH_URL}')
        search_response = page.goto(SEARCH_URL, timeout=30000, wait_until='networkidle')
        assert search_response is not None and search_response.status == 200, (
            f'Search page did not load successfully (status: '
            f'{search_response.status if search_response else "no response"})'
        )
        page.wait_for_timeout(2000)
        print(f'Search page title: {page.title()!r}')

        # ── Go back to the STG homepage ──
        print(f'Navigating to homepage: {HOME_URL_RETURN}')
        home_response = page.goto(HOME_URL_RETURN, timeout=60000, wait_until='networkidle')
        assert home_response is not None and home_response.status == 200, (
            f'Homepage did not load successfully (status: '
            f'{home_response.status if home_response else "no response"})'
        )
        page.wait_for_timeout(POST_RELOAD_WAIT)

        # ── Verify the Car Loan hero ad displays (retry with reloads for resilience) ──
        heading_text = find_hero_heading_text(page)
        attempt = 1
        while heading_text is None and attempt < MAX_AD_RETRIES:
            attempt += 1
            print(f'Car Loan ad not shown yet. Reloading — attempt {attempt}/{MAX_AD_RETRIES}...')
            time.sleep(RETRY_SLEEP)
            page.reload(timeout=60000, wait_until='networkidle')
            page.wait_for_timeout(POST_RELOAD_WAIT)
            heading_text = find_hero_heading_text(page)

        assert heading_text is not None, (
            f'No Car Loan hero ad appeared after searching "car loan" and '
            f'reloading the homepage {MAX_AD_RETRIES} times'
        )
        print(f'Hero heading found after {attempt} attempt(s): {heading_text!r}')

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
        f'Car Loan hero CTA link returned HTTP {result["status"]} '
        f'({result["note"]}): {full_url}'
    )


if __name__ == '__main__':
    test_uhfcu_carloan_search_STG()
    print('\nRegression test passed.')
