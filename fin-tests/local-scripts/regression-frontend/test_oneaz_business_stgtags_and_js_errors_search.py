"""
Test OneAZ Business Personalization — STG Tags, JS Errors, and Search Trigger

Two flows are tested back-to-back in the same session:

  Flow 1 (Direct URL):  session_init → /business?api=stg → homepage → validate ad
  Flow 2 (Search URL):  session_init → /search-results/?keywords=business+banking → homepage → validate ad

Discovery results (confirmed):
  - Search input selector: input[type='search'] (directly visible, no toggle button needed)
  - Search URL confirmed: /search-results/?keywords=business+banking
  - OneAZ uses a custom search endpoint (/search-results/?keywords=query)

Special handling:
  - OneAZ has a site-specific popup that must be dismissed before proceeding
"""

import asyncio
import pytest
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa_tools import (
    clear_screenshots_directory,
    browser,
    DEFAULT_TIMEOUT,
    process_test_data_async,
)

client = "oneaz"

MAX_AD_RETRIES = 4
RETRY_SLEEP    = 5  # seconds between retries

BASE_URL    = "https://oneazcuqa.oneazcu.com"
HOME_PARAMS = "?api=stg&debug_all=1"

SEARCH_TERM    = "business banking"
EXPECTED_H1    = "Empower Your Enterprise"
H1_SELECTOR    = "#copyCol > h1"
CLOUDFRONT_URL = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")


async def validate_homepage_ad_with_retry(page, home_url, screenshots_directory, flow_label,
                                          error_tracker, cloudfront_urls):
    """
    Navigate to home_url and assert the expected H1 is shown.
    Retries up to MAX_AD_RETRIES times (reload between each attempt) before raising.
    Uses direct navigation with a sleep to allow personalization to render on slow staging.
    """
    last_error = None

    for attempt in range(1, MAX_AD_RETRIES + 1):
        print(f"[{flow_label}] Homepage ad validation — attempt {attempt}/{MAX_AD_RETRIES}")
        try:
            await page.goto(home_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("load", timeout=60000)
            await _dismiss_oneaz_alert(page)
            await asyncio.sleep(15)  # allow personalization to render (CI networking is more variable than local)
            h1 = await page.locator(H1_SELECTOR).first.inner_text(timeout=25000)
            print(f"  H1 ({flow_label}): {h1}")
            assert h1 == EXPECTED_H1, f"Expected '{EXPECTED_H1}' but got '{h1}'"
            slug = flow_label.lower().replace(" ", "_").replace("(", "").replace(")", "")
            await page.screenshot(path=f"{screenshots_directory}homepage_ad_{slug}.png")
            print(f"[{flow_label}] Correct ad found on attempt {attempt}.")
            return
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


async def _dismiss_oneaz_alert(page) -> None:
    """Dismiss the OneAZ site-specific alert popup if present."""
    try:
        close_btn = page.locator(
            "#unignorable-alert-close-7fcb1e6f-a34c-41d3-9cc1-ba45e080c29c"
        ).first
        if await close_btn.count() > 0:
            await close_btn.click()
            print("  [oneaz] Alert dismissed.")
        else:
            print("  [oneaz] No alert found.")
    except Exception as e:
        print(f"  [oneaz] Alert dismiss error: {e}")


async def _get_search_url_params(browser_ctx) -> str:
    """
    Navigate to the homepage, dismiss the alert, perform a search via
    input[type='search'], and return the extracted query string.
    """
    page = await browser_ctx.new_page()
    try:
        print("  [search] Navigating to homepage with session reset...")
        await page.goto(
            f"{BASE_URL}/?api=stg&session_init=1&debug_all=1",
            wait_until="domcontentloaded",
            timeout=DEFAULT_TIMEOUT,
        )
        await _dismiss_oneaz_alert(page)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(1000)

        # OneAZ: search input is visible directly without needing a toggle button
        for inp_sel in ["input[type='search']", "input[name='s']",
                        "input[placeholder*='search' i]", "input[name='keywords']"]:
            try:
                inp = page.locator(inp_sel).first
                if await inp.count() > 0 and await inp.is_visible():
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

        # Fall back to confirmed search URL pattern for OneAZ
        params = urllib.parse.urlencode({"keywords": SEARCH_TERM})
        print(f"  [search] Search UI not found — using known OneAZ pattern: {params}")
        return params
    finally:
        await page.close()

@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "OneAZ", "password": "pugs r potatoes!3"}],
    indirect=True,
)
async def test_oneaz_business_stgtags_and_js_errors_search(browser):
    print(f"Starting {client} hero ad test (with search trigger)..")
    print(sys.version)

    # Dismiss the OneAZ popup on the browser context's first page before collecting test data
    setup_page = await browser.new_page()
    await setup_page.goto(f"{BASE_URL}/?api=stg", wait_until="domcontentloaded")
    await _dismiss_oneaz_alert(setup_page)
    await setup_page.wait_for_load_state("load")
    await setup_page.close()

    screenshots_directory = f"screenshots_{client}_using_pytest/"
    clear_screenshots_directory(screenshots_directory)

    home_url = f"{BASE_URL}/?api=stg"
    search_url_params = await _get_search_url_params(browser)

    # ── Flow 1: Direct URL trigger ──────────────────────────────────────────
    print("[Flow 1 (Direct URL)] Opening fresh browser page...")
    page1 = await browser.new_page()
    try:
        await process_test_data_async(
            page1,
            [
                f"{BASE_URL}/?api=stg&session_init=1&debug_all=1",
                f"{BASE_URL}/business?api=stg",
            ],
            screenshots_directory,
            validate_js=True,
            validate_finalytics=False,
            client=client,
            error_tracker=[],
            cloudfront_urls=CLOUDFRONT_URL,
        )

        await validate_homepage_ad_with_retry(
            page1, home_url, screenshots_directory,
            flow_label="Flow 1 (Direct URL)",
            error_tracker=[],
            cloudfront_urls=CLOUDFRONT_URL,
        )
    finally:
        print("[Flow 1 (Direct URL)] Closing browser page...")
        await page1.close()

    # ── Flow 2: Search URL trigger ───────────────────────────────────────────
    print("[Flow 2 (Search URL)] Opening fresh browser page...")
    page2 = await browser.new_page()
    try:
        await process_test_data_async(
            page2,
            [
                f"{BASE_URL}/?api=stg&session_init=1&debug_all=1",
                {
                    "url": f"{BASE_URL}/search-results/?{search_url_params}",
                    "expected": {"wait_type": "load"},
                },
            ],
            screenshots_directory,
            validate_js=True,
            validate_finalytics=False,
            client=client,
            error_tracker=[],
            cloudfront_urls=CLOUDFRONT_URL,
        )

        await validate_homepage_ad_with_retry(
            page2, home_url, screenshots_directory,
            flow_label="Flow 2 (Search URL)",
            error_tracker=[],
            cloudfront_urls=CLOUDFRONT_URL,
        )
    finally:
        print("[Flow 2 (Search URL)] Closing browser page...")
        await page2.close()

    print(f"{client} hero ad testing completed.")
