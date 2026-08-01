#!/usr/bin/env python3
"""
Langley FCU Certificate Search-Trigger Regression Test — STG Environment

Smoke test: performs a site search for "certificate", then navigates back
to the STG homepage and verifies a CD/Certificate hero ad is eventually
displayed (retrying with page reloads, since the hero ad slot rotates
between multiple eligible ads rather than deterministically switching to
the search-matched ad on the very next reload).

Discovery notes (verified live):
  - get_ads() DOES include the search-matched Certificate ad
    ("Share Certificate: 11-month Promo...", algorithms: "search") in its
    response immediately after the search, alongside two other eligible
    ads (a "segment"-algorithm Savings/High-Yield-Savings ad and a static
    Forbes-award "segment" ad).
  - Which of those eligible ads actually renders in the hero slot on any
    given page load is NOT deterministic on the very first reload -- in
    manual verification it took 2 reloads before the Certificate ad won
    the slot over the High-Yield-Savings ad. This test retries with
    reloads (MAX_AD_RETRIES) rather than asserting after exactly one
    refresh, to avoid flaking in CI depending on which ad the rotation
    happens to pick.

Run:
    pytest test_langley_certificate_search_STG.py -v
    python test_langley_certificate_search_STG.py
"""

import sys
import io
import time

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if not hasattr(sys, '_called_from_pytest') and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://www.langleyfcu.org'
HOME_URL_INIT = f'{BASE_URL}/dev/stage/?cb=1&api=stg&debug_all=1&session_init=1'
SEARCH_URL = f'{BASE_URL}/search/?q=certificate'
HOME_URL_RETURN = f'{BASE_URL}/dev/stage/?cb=1&api=stg&debug_all=1'

HERO_HEADING_SELECTORS = ['h1', 'h2']
EXPECTED_KEYWORDS = ('certificate', 'cd')

MAX_AD_RETRIES = 8
RETRY_SLEEP = 3        # seconds before triggering the next reload
POST_RELOAD_WAIT = 5000  # ms to wait after each reload -- this needs to be
                         # long enough for the page's impression-tracking
                         # beacon to actually register the view; too short
                         # and the "High Yield Savings has been shown enough
                         # times" expiration threshold never gets credited,
                         # so reloads that fire too fast don't count.


def find_hero_heading_text(page):
    """Return the text of the first visible h1/h2 whose text mentions a
    CD/Certificate product, or None if no such heading is currently visible."""
    for selector in HERO_HEADING_SELECTORS:
        for el in page.query_selector_all(selector):
            if not el.is_visible():
                continue
            text = (el.inner_text() or '').strip()
            if text and any(keyword in text.lower() for keyword in EXPECTED_KEYWORDS):
                return text
    return None


def test_langley_certificate_search_STG():
    """
    Regression: search "certificate" on Langley FCU's site search, navigate
    back to the STG homepage, and assert a CD/Certificate hero ad is
    eventually displayed (retrying with reloads since the hero ad slot
    rotates between multiple eligible ads).
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

        # ── Verify a CD/Certificate hero ad eventually displays, retrying with reloads ──
        heading_text = find_hero_heading_text(page)
        attempt = 1
        while heading_text is None and attempt < MAX_AD_RETRIES:
            attempt += 1
            print(f'CD/Certificate ad not shown yet (currently showing a different eligible ad). '
                  f'Reloading — attempt {attempt}/{MAX_AD_RETRIES}...')
            time.sleep(RETRY_SLEEP)
            page.reload(timeout=60000, wait_until='networkidle')
            page.wait_for_timeout(POST_RELOAD_WAIT)
            heading_text = find_hero_heading_text(page)

        print(f'Hero heading found after {attempt} attempt(s): {heading_text!r}')

        browser.close()

    assert heading_text is not None, (
        f'No CD/Certificate hero ad appeared after searching "certificate" and '
        f'reloading the homepage {MAX_AD_RETRIES} times'
    )


if __name__ == '__main__':
    test_langley_certificate_search_STG()
    print('\nRegression test passed.')
