"""
Test Global Credit Union MMA Personalization — STG Tags, JS Errors, and Search Trigger

Two flows are tested back-to-back in the same session:

  Flow 1 (Direct URL):  session_init → /accounts/ways-to-save/money-market/ → homepage → validate ad
  Flow 2 (Search URL):  session_init → /search/?q=money+market → homepage → validate ad

Discovery results:
  - Search button selector: button[aria-label*='search' i]
  - Search URL confirmed: /search/?q=money+market
  - Long waits (10 s) required for personalization to register — preserved from existing test

Special handling:
  - Cookie modal must be dismissed on first load
  - getads API responses are captured for debugging
"""

import asyncio
import json
import pytest
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    browser,
    DEFAULT_TIMEOUT,
    DEFAULT_CLOUDFRONT_URLS,
    dismiss_cookie_modal,
)

client = "glbl"

MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries

BASE_URL    = "https://globaluat.cms.globalcu.org"
HOME_PARAMS = "?api=stg"

SEARCH_TERM = "money market"
EXPECTED_H1 = "The more you save, the better the rate"
H1_SELECTOR = "div.hero-body > h1"
HERO_SELECTOR = ".hero-body"


async def validate_homepage_ad_with_retry(page, home_url, screenshots_path, flow_label):
    """
    Navigate to home_url and assert the expected H1 is shown.
    Retries up to MAX_AD_RETRIES times (reload between each attempt) before raising.
    Returns the H1 text on success.
    """
    last_error = None

    for attempt in range(1, MAX_AD_RETRIES + 1):
        print(f"[{flow_label}] Homepage ad validation — attempt {attempt}/{MAX_AD_RETRIES}")
        try:
            await page.goto(home_url)
            await page.wait_for_load_state("load")
            await asyncio.sleep(5)
            await wait_for_js_and_element_async(page, HERO_SELECTOR, timeout=30000)
            h1 = await page.locator(H1_SELECTOR).first.inner_text()
            print(f"  H1 ({flow_label}): {h1}")
            assert h1 == EXPECTED_H1, f"Expected '{EXPECTED_H1}' but got '{h1}'"
            await page.screenshot(path=screenshots_path)
            print(f"[{flow_label}] Correct ad found on attempt {attempt}.")
            return h1
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            last_error = exc
            print(f"[{flow_label}] Attempt {attempt} failed: {exc}")
            if attempt < MAX_AD_RETRIES:
                print(f"[{flow_label}] Waiting {RETRY_SLEEP}s before retry...")
                await asyncio.sleep(RETRY_SLEEP)

    raise Exception(
        f"[{flow_label}] Ad '{EXPECTED_H1}' not found after {MAX_AD_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


async def _get_search_url_params(browser_ctx) -> str:
    """
    Click the search button, fill the input, and return the extracted
    query string.  Falls back to /?s=term if the UI search is unavailable.
    """
    page = await browser_ctx.new_page()
    try:
        print("  [search] Navigating to homepage with session reset...")
        await page.goto(
            f"{BASE_URL}/?api=stg&session_init=1&debug_all=1",
            wait_until="domcontentloaded",
            timeout=DEFAULT_TIMEOUT,
        )
        await dismiss_cookie_modal(page)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(3000)

        # Click the search button (confirmed selector from discovery)
        for open_sel in [
            "button[aria-label*='search' i]", ".search-btn", ".search-button",
            "button[class*='search']", "a[class*='search']",
        ]:
            try:
                el = page.locator(open_sel).first
                if await el.count() > 0 and await el.is_visible():
                    print(f"  [search] Clicking search button: {open_sel}")
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

        for inp_sel in ["input[name='s']", "input[type='search']",
                        "input[name='query']", "input[name='q']"]:
            try:
                inp = page.locator(inp_sel).first
                await inp.wait_for(state="visible", timeout=5000)
                await inp.fill(SEARCH_TERM)
                print(f"  [search] Typing '{SEARCH_TERM}' and pressing Enter...")
                async with page.expect_navigation(wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT):
                    await page.press(inp_sel, "Enter")
                params = urllib.parse.urlparse(page.url).query
                print(f"  [search] Result URL      : {page.url}")
                print(f"  [search] Extracted params: {params}")
                return params
            except Exception:
                pass

        # Fall back to confirmed search URL (direct navigation confirmed working)
        params = urllib.parse.urlencode({"q": SEARCH_TERM})
        print(f"  [search] Search UI not found — using fallback: {params}")
        return params
    finally:
        await page.close()

@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "gcu", "password": "!gcu/Cmsviewer1$"}],
    indirect=True,
)
async def test_global_mma_stgtags_and_js_errors_search(browser):
    print(f"Starting {client} hero ad test with search trigger and getads monitoring..")
    print(sys.version)

    search_url_params = await _get_search_url_params(browser)

    screenshots_directory = f"screenshots_{client}_using_pytest/"
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    getads_responses = []

    async def handle_response(response):
        if "finalyticsdata.com/api/v1/getads/" in response.url:
            try:
                data = await response.json()
                getads_responses.append({"url": response.url, "status": response.status, "data": data})
                print(f"\n=== GETADS ({response.status}) ===")
                for ad in data.get("ads", []):
                    print(f"  Ad id={ad.get('id')} headline={ad.get('headline', 'N/A')}")
            except Exception as e:
                getads_responses.append({"url": response.url, "error": str(e)})

    page.on("response", handle_response)

    # ── Flow 1: Direct URL trigger ──────────────────────────────────────────
    print("\n--- Flow 1: Direct URL trigger ---")
    print("Step 1: Homepage with session_init")
    await page.goto(f"{BASE_URL}/?api=stg&session_init=1&debug_all=1")
    await page.wait_for_load_state("load")
    await dismiss_cookie_modal(page)
    await page.screenshot(path=f"{screenshots_directory}flow1_1_homepage.png")
    print("Sleeping 10 s...")
    await asyncio.sleep(10)

    print("Step 2: Money market page")
    await page.goto(f"{BASE_URL}/accounts/ways-to-save/money-market/")
    await page.wait_for_load_state("load")
    await page.screenshot(path=f"{screenshots_directory}flow1_2_mma_page.png")
    print("Sleeping 10 s...")
    await asyncio.sleep(10)

    print("Step 3: Return to homepage, check ad (with retry)")
    await validate_homepage_ad_with_retry(
        page, f"{BASE_URL}/{HOME_PARAMS}",
        f"{screenshots_directory}flow1_3_homepage_ad.png",
        flow_label="Flow 1 (Direct URL)",
    )

    # ── Flow 2: Search URL trigger ──────────────────────────────────────────
    print("\n--- Flow 2: Search URL trigger ---")
    print("Step 1: Homepage with session_init (reset)")
    await page.goto(f"{BASE_URL}/?api=stg&session_init=1&debug_all=1")
    await page.wait_for_load_state("load")
    await dismiss_cookie_modal(page)
    await page.screenshot(path=f"{screenshots_directory}flow2_1_homepage.png")
    print("Sleeping 10 s...")
    await asyncio.sleep(10)

    print(f"Step 2: Search results page (/search/?{search_url_params})")
    await page.goto(f"{BASE_URL}/search/?{search_url_params}")
    await page.wait_for_load_state("load")
    await page.screenshot(path=f"{screenshots_directory}flow2_2_search_page.png")
    print("Sleeping 10 s...")
    await asyncio.sleep(10)

    print("Step 3: Return to homepage, check ad (with retry)")
    await validate_homepage_ad_with_retry(
        page, f"{BASE_URL}/{HOME_PARAMS}",
        f"{screenshots_directory}flow2_3_homepage_ad.png",
        flow_label="Flow 2 (Search URL)",
    )

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n=== SUMMARY: {len(getads_responses)} getads API calls captured ===")
    print(f"{client} hero ad testing completed.")
