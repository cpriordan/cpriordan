#!/usr/bin/env python3
"""
MissionFed Hispanic Checking Funnel Regression Test — STG Environment
(simplified: apply-form-flow boundary only, see "Known blocker" below)

STG adaptation of the "hispanic checking" scenario from
fin-tests/PROD/test_missionfed_funnel_scenarios_github_actions_PROD.py
(the ScenarioConfig entry named "hispanic checking" in that file's
generic, data-driven test_missionfed_hero_ad_generic).

Flow covered by this test:
  1. Homepage with session_init=1 (establishes the funnel session).
  2. Hispanic support page (/hispanicsupport/) -- screenshot.
  3. Checking product page (/checking-spending/) -- screenshot.
  4. Click the hero CTA and verify it lands on the "New Member
     Application" apply form (/apps/joinnow/).

KNOWN BLOCKER -- why this test stops at the apply form, rather than
completing the full funnel round-trip like the PROD version does:
  The PROD scenario continues past this point: select a product from an
  Angular Material dropdown on the apply form, which used to redirect to
  an external apply platform -- arriving at that external URL is what
  registers funnel intent with Finalytics, which is what makes the
  homepage subsequently show the "FINISH OPENING MY ACCOUNT" funnel CTA.

  As of this test (2026-07), missionfed.com/apps/joinnow/ has been
  replaced with a completely different "New Member Application" form (a
  multi-field application with a "Select at least 1 product" control),
  not the old Angular Material dropdown the PROD test's selectors
  (.mat-mdc-select-arrow-wrapper / #mat-option-1) expect. This is an
  already-documented, pre-existing break in the PROD source scenario
  itself -- per prior investigation, checking/savings/cd/hispanic checking
  all currently fail in the PROD test for this exact reason (only
  "personal loan" and "credit card" still pass, since those scenarios'
  CTAs skip the product-dropdown step entirely).

  This STG test deliberately does NOT attempt to drive the new joinnow
  form or fabricate a path to the funnel-CTA verification -- that would
  require real investigative/product work on the new form's structure,
  out of scope for a straightforward STG port. It verifies everything
  that genuinely still works (session_init, hispanic support page,
  checking product page, hero CTA click landing on the apply form) and
  stops there.

Run:
    pytest test_missionfed_funnel_hispanic_checking_STG.py -v -s
    python test_missionfed_funnel_hispanic_checking_STG.py
"""

import sys
import io
import re

import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if not hasattr(sys, '_called_from_pytest') and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://stage.missionfed.com'
HOME_WITH_INIT = f'{BASE_URL}/?session_init=1&debug_all=1&cb=0'
HISPANIC_URL = f'{BASE_URL}/hispanicsupport/'
CHECKING_URL = f'{BASE_URL}/checking-spending/'

# Current hero CTA label -- was "Apply Today" in the PROD scenario config;
# verified live (2026-07) that the checking-page hero now shows this label
# instead.
HERO_CTA_LABEL = 'OPEN AN ACCOUNT'
EXPECTED_APPLY_FORM_URL_FRAGMENT = 'apps/joinnow'
EXPECTED_APPLY_FORM_TITLE_FRAGMENT = 'new member application'

COOKIE_ACCEPT_SELECTOR = 'a.cc-btn.cc-dismiss'


def wait_for_document_complete(page, timeout=70000):
    page.wait_for_load_state('domcontentloaded', timeout=timeout)
    page.wait_for_load_state('load', timeout=timeout)


def try_click_cookie_accept(page):
    page.wait_for_timeout(1500)
    try:
        locator = page.locator(COOKIE_ACCEPT_SELECTOR)
        if locator.count() > 0:
            locator.first.click(timeout=3000)
            page.wait_for_timeout(500)
    except Exception:
        pass


def follow_hero_cta(page, label=HERO_CTA_LABEL):
    """Click the hero CTA (in whichever tab it opens) and land back in the
    original tab at its destination."""
    pattern = re.compile(re.escape(label), re.I)
    candidates = [
        page.get_by_role('link', name=pattern),
        page.get_by_role('button', name=pattern),
        page.locator(f"a:has-text('{label}')"),
    ]
    target = None
    for cand in candidates:
        if cand.count() > 0:
            target = cand.first
            break
    assert target is not None, f"Could not locate hero CTA labeled '{label}'"

    apply_href = target.get_attribute('href')
    if apply_href:
        apply_href = apply_href if apply_href.startswith('http') else BASE_URL + apply_href

    prev_url = page.url
    new_tab = None
    try:
        with page.context.expect_page(timeout=7000) as page_info:
            target.click()
        new_tab = page_info.value
        new_tab.wait_for_load_state('domcontentloaded')
        try_click_cookie_accept(new_tab)
    except PlaywrightTimeoutError:
        pass

    if new_tab is not None:
        # The hero CTA opens the apply form in a new tab -- that's the
        # actual destination to verify, not the original tab.
        return new_tab, apply_href

    if not apply_href and page.url != prev_url:
        apply_href = page.url
    assert apply_href, f"Could not determine destination from hero CTA '{label}'"
    if page.url != apply_href:
        page.goto(apply_href, timeout=70000)
    wait_for_document_complete(page)
    return page, apply_href


def test_missionfed_funnel_hispanic_checking_STG():
    """
    Regression (partial, see module docstring "KNOWN BLOCKER"): hispanic
    checking funnel scenario on STG, verified up through the apply-form
    landing. Does not verify the funnel-completion homepage CTA, since
    that step is blocked by an already-broken apply form UI upstream.
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

        js_errors = []
        specific_js_files = ('finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js')

        def handle_console(msg):
            if msg.type == 'error':
                file_name = (msg.location.get('url') or '').split('/')[-1]
                if file_name in specific_js_files:
                    js_errors.append(f'{file_name}: {msg.text}')
        page.on('console', handle_console)

        # ── Establish funnel session on the homepage ──
        print(f'\nHomepage (session_init): {HOME_WITH_INIT}')
        resp = page.goto(HOME_WITH_INIT, timeout=70000)
        assert resp is not None and resp.status == 200, f'Homepage failed to load (status: {resp.status if resp else None})'
        wait_for_document_complete(page)
        try_click_cookie_accept(page)

        # ── Hispanic support page ──
        print(f'Hispanic support page: {HISPANIC_URL}')
        resp = page.goto(HISPANIC_URL, timeout=70000)
        assert resp is not None and resp.status == 200, f'Hispanic support page failed to load (status: {resp.status if resp else None})'
        wait_for_document_complete(page)
        try_click_cookie_accept(page)

        # ── Checking product page ──
        print(f'Checking product page: {CHECKING_URL}')
        resp = page.goto(CHECKING_URL, timeout=70000)
        assert resp is not None and resp.status == 200, f'Checking page failed to load (status: {resp.status if resp else None})'
        wait_for_document_complete(page)
        try_click_cookie_accept(page)

        # ── Click hero CTA -> verify it lands on the apply form ──
        print(f'Following hero CTA {HERO_CTA_LABEL!r}...')
        dest_page, apply_href = follow_hero_cta(page)
        dest_url = dest_page.url
        dest_title = dest_page.title()
        print(f'Landed on: {dest_url!r} (title: {dest_title!r})')

        assert EXPECTED_APPLY_FORM_URL_FRAGMENT in dest_url.lower(), (
            f"Expected hero CTA to land on the apply form (URL containing "
            f"'{EXPECTED_APPLY_FORM_URL_FRAGMENT}'), but got: {dest_url}"
        )
        assert EXPECTED_APPLY_FORM_TITLE_FRAGMENT in dest_title.lower(), (
            f"Expected apply form page title to contain "
            f"'{EXPECTED_APPLY_FORM_TITLE_FRAGMENT}', but got: {dest_title!r}"
        )
        print('Hero CTA correctly lands on the apply form.')

        if dest_page is not page:
            dest_page.close()
        browser.close()

    assert not js_errors, f'Detected JavaScript errors: {js_errors}'


if __name__ == '__main__':
    test_missionfed_funnel_hispanic_checking_STG()
    print('\nRegression test passed.')
