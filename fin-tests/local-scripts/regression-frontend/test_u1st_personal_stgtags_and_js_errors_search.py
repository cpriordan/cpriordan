"""
Test U1st Personal Loans Personalization — STG Tags, JS Errors, and Search Trigger

Two flows are tested back-to-back in the same session:

  Flow 1 (Direct URL):  session_init → /loans-and-credit/product/personal-loans-and-lines → homepage → validate ad
  Flow 2 (Search URL):  session_init → /search?q=personal+loans → homepage → validate ad

Discovery results (confirmed):
  - Search open button: .icon-search
  - Search input: input[type='search']
  - Search URL confirmed: /search?q=personal+loans
  - U1st uses the Banno platform with a /search?q=query endpoint
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

client = "u1st"

MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries

BASE_URL    = "https://1stunitedcu.cms.banno-staging.com"
HOME_PARAMS = "?api=stg"

SEARCH_TERM    = "personal loans"
EXPECTED_H1    = 'Turn "Someday" Into Right Now'
H1_SELECTOR    = "#slideshow--main > div > div > div > div > div > div > div.hero__slider-content.d-flex.flex-row.align-content-center.justify-start.align-items-center > div > div > div > div > div > div > div > h2"
CLOUDFRONT_URL = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")


async def validate_homepage_ad_with_retry(page, home_url, screenshots_directory, flow_label,
                                          error_tracker, cloudfront_urls):
    """
    Navigate to home_url and assert the expected H1 is shown.
    Retries up to MAX_AD_RETRIES times (reload between each attempt) before raising.
    """
    last_error = None

    for attempt in range(1, MAX_AD_RETRIES + 1):
        print(f"[{flow_label}] Homepage ad validation — attempt {attempt}/{MAX_AD_RETRIES}")
        try:
            await process_test_data_async(
                page,
                [
                    {
                        "url": home_url,
                        "expected": {
                            "h1": EXPECTED_H1,
                            "h1__selector": H1_SELECTOR,
                            "wait_type": "element",
                        },
                        "validate_finalytics": True,
                    }
                ],
                screenshots_directory,
                validate_js=True,
                validate_finalytics=True,
                client=client,
                error_tracker=error_tracker,
                cloudfront_urls=cloudfront_urls,
            )
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


async def _get_search_url_params(browser_ctx) -> str:
    """
    Navigate to the homepage, open the search via .icon-search, fill
    input[type='search'], and return the extracted query string.
    Falls back to the Banno standard /search?q=term if UI search not found.
    """
    page = await browser_ctx.new_page()
    try:
        print("  [search] Navigating to homepage with session reset...")
        for attempt in range(1, 4):
            try:
                await page.goto(
                    f"{BASE_URL}/?api=stg&debug_all=1&session_init=1",
                    wait_until="domcontentloaded",
                    timeout=DEFAULT_TIMEOUT,
                )
                break
            except Exception as e:
                if attempt == 3:
                    print(f"  [search] Page load failed after 3 attempts: {e}")
                    params = urllib.parse.urlencode({"q": SEARCH_TERM})
                    print(f"  [search] Falling back to Banno standard: {params}")
                    return params
                print(f"  [search] Attempt {attempt} timed out, retrying...")
                await page.wait_for_timeout(3000)
        await page.wait_for_timeout(2000)

        # U1st Banno platform: search icon opens the search input
        for open_sel in [
            ".icon-search", "button[class*='search']", "button[aria-label*='search' i]",
            "a[aria-label*='search' i]", ".search-toggle",
        ]:
            try:
                el = page.locator(open_sel).first
                if await el.count() > 0 and await el.is_visible():
                    print(f"  [search] Clicking search open button: {open_sel}")
                    await el.click()
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        for inp_sel in ["input[type='search']", "input[name='q']",
                        "input[name='s']", "input[placeholder*='search' i]"]:
            try:
                inp = page.locator(inp_sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await inp.fill(SEARCH_TERM)
                    print(f"  [search] Typing '{SEARCH_TERM}' and pressing Enter...")
                    async with page.expect_navigation(wait_until="load", timeout=DEFAULT_TIMEOUT):
                        await page.press(inp_sel, "Enter")
                    params = urllib.parse.urlparse(page.url).query
                    print(f"  [search] Result URL      : {page.url}")
                    print(f"  [search] Extracted params: {params}")
                    return params
            except Exception:
                pass

        # Fall back to confirmed Banno search URL pattern
        params = urllib.parse.urlencode({"q": SEARCH_TERM})
        print(f"  [search] Search UI not found — using Banno standard: {params}")
        return params
    finally:
        await page.close()

@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "uccustaging", "password": "LoveWYBank2021!"}],
    indirect=True,
)
async def test_u1st_personal_stgtags_and_js_errors_search(browser):
    print(f"Starting {client} hero ad test (with search trigger)..")
    print(sys.version)

    screenshots_directory = f"screenshots_{client}_using_pytest/"
    clear_screenshots_directory(screenshots_directory)

    home_url = f"{BASE_URL}/{HOME_PARAMS}"
    search_url_params = await _get_search_url_params(browser)

    # ── Flow 1: Direct URL trigger ──────────────────────────────────────────
    print("[Flow 1 (Direct URL)] Opening fresh browser page...")
    page1 = await browser.new_page()
    try:
        await process_test_data_async(
            page1,
            [
                {
                    "url": f"{BASE_URL}/?api=stg&debug_all=1&session_init=1",
                    "expected": {"wait_type": "load"},
                },
                {
                    "url": f"{BASE_URL}/loans-and-credit/product/personal-loans-and-lines?segments=nurturing,april 2026",
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
                {
                    "url": f"{BASE_URL}/?api=stg&debug_all=1&session_init=1",
                    "expected": {"wait_type": "load"},
                },
                {
                    "url": f"{BASE_URL}/search?{search_url_params}",
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
