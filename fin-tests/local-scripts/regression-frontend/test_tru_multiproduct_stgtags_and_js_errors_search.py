"""
Test TRU Multiproduct Checking Hero — STG Tags, JS Errors, and Search Trigger

Two flows are tested back-to-back in the same session:

  Flow 1 (Direct URL):  session_init → /checking-and-savings/checking-accounts/ → homepage → validate ad
  Flow 2 (Search URL):  session_init → /?s=checking+accounts → homepage → validate ad

Discovery results (confirmed):
  - WordPress standard search URL confirmed: /?s=checking+accounts
  - Search trigger CONFIRMED to display "CHECKING ACCOUNTS" ad on homepage
"""

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

client = "tru"

BASE_URL    = "https://trustonestage.wpenginepowered.com"
HOME_PARAMS = "?api=stg"

SEARCH_TERM    = "checking accounts"
EXPECTED_H1    = "CHECKING ACCOUNTS"
H1_SELECTOR    = "#primary > section:nth-child(1) > div > div > div.container > div > div > div > div > div.eyebrow"
CLOUDFRONT_URL = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")


async def _get_search_url_params(browser_ctx) -> str:
    """
    Navigate to the homepage, trigger a search via the UI, and return the
    extracted query string.  Falls back to the WordPress standard /?s=term
    if the search icon is not found in the page.
    """
    page = await browser_ctx.new_page()
    try:
        print("  [search] Navigating to homepage with session reset...")
        await page.goto(
            f"{BASE_URL}/?api=stg&session_init=1",
            wait_until="domcontentloaded",
            timeout=DEFAULT_TIMEOUT,
        )
        await page.wait_for_timeout(2000)

        for open_sel in [
            ".swbi-open", "button.search-toggle", ".search-toggle",
            "a[aria-label*='search' i]", "button[aria-label*='search' i]",
            ".header-search button", ".search-open", ".search-icon",
        ]:
            try:
                el = page.locator(open_sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        for inp_sel in ["input[name='s']", "input[type='search']"]:
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

        params = urllib.parse.urlencode({"s": SEARCH_TERM})
        print(f"  [search] Search UI not found — using WordPress standard: {params}")
        return params
    finally:
        await page.close()


@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "trustonestage", "password": "TruStone2024!!"}],
    indirect=True,
)
async def test_tru_multiproduct_stgtags_and_js_errors_search(browser):
    print(f"Starting {client} hero ad test (with search trigger)..")
    print(sys.version)

    search_url_params = await _get_search_url_params(browser)

    data = [
        # ── Flow 1: Direct URL trigger ──────────────────────────────────────
        {
            "url": f"{BASE_URL}/checking-and-savings/checking-accounts/?api=stg",
            "wait_type": "load",
        },
        # Give getads time to register the intent signal before checking the
        # homepage -- without this pause, CI (which navigates faster/more
        # consistently than a local machine) can race ahead of the backend
        # personalization decision and see the generic default ad instead.
        5,
        {
            "url": f"{BASE_URL}/?api=stg&session_init=1",
            "expected": {
                "h1": EXPECTED_H1,
                "h1__selector": H1_SELECTOR,
                "wait_type": "element",
            },
            "validate_finalytics": True,
        },

        # ── Flow 2: Search URL trigger ───────────────────────────────────────
        # Reset session first, then trigger via search results page
        {
            "url": f"{BASE_URL}/?api=stg&session_init=1",
            "expected": {"wait_type": "load"},
        },
        {
            "url": f"{BASE_URL}/?{search_url_params}",
            "expected": {"wait_type": "load"},
        },
        5,
        {
            "url": f"{BASE_URL}/{HOME_PARAMS}",
            "expected": {
                "h1": EXPECTED_H1,
                "h1__selector": H1_SELECTOR,
                "wait_type": "element",
            },
            "validate_finalytics": True,
        },
    ]

    screenshots_directory = f"screenshots_{client}_using_pytest/"
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    error_tracker = []

    await process_test_data_async(
        page, data, screenshots_directory,
        screenshots=True,
        validate_js=True,
        validate_finalytics=True,
        client=client,
        error_tracker=error_tracker,
        cloudfront_urls=CLOUDFRONT_URL,
        username="trustonestage",
        password="TruStone2024!!",
    )

    print(f"{client} hero ad testing completed.")
