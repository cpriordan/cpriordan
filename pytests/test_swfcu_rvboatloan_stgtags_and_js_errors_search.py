"""
Test SWFCU RV/Boat Loan Personalization with STG Tags and JS Error Validation

Version History:
- 2025-11-23: Fixed test failures
    - Changed first URL to use 'load' wait type to avoid networkidle timeout
    - Added debug_all=1&session_init=1 to enable personalization
    - Fixed domain mismatch issue: Changed all URLs from statewidefcu.pixelspoke-staging.com
      to statewidefcu24.pixelspoke-staging.com (with "24") as the latter has the correct
      Finalytics cloudfront scripts configured. Without proper cloudfront URLs, personalization
      cannot work.
- 2026-04-27: Added search URL trigger case
    - Added second flow that triggers via search URL
      (?s=rv%2C+boat+and+motorcycle+loans) and validates the same rvboatloan ad
      ("Sail to low Rates") appears on the homepage afterward.
    - Session is reset with session_init=1 between the two flows to ensure a clean state.
- 2026-04-27: Added --env parameter support (stg / prod)
    - URLs are now built dynamically based on the --env CLI argument.
    - STG base: https://statewidefcu24.pixelspoke-staging.com (requires HTTP basic auth,
      uses ?api=stg param, STG cloudfront)
    - PROD base: https://www.statewidefcu.org (no basic auth, no ?api=stg, PROD cloudfront)
    - Run with: pytest test_swfcu_rvboatloan_stgtags_and_js_errors.py --env prod
- 2026-05-05: Dynamic search URL extraction via UI interaction
    - The search URL params are no longer hardcoded (?s=rv%2C+boat+and+motorcycle+loans).
    - Before building the data list, _get_search_url_params() navigates to the homepage,
      clicks the search icon (.swbi-open), types "rv boat and motorcycle loans", presses
      Enter, and extracts the resulting query string from the browser URL (e.g.
      's=rv%2C+boat+and+motorcycle+loans') to use as the search trigger URL.
"""

import asyncio
import pytest
import pytest_asyncio
import sys
import os
import urllib.parse

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    browser,
    DEFAULT_TIMEOUT,
    process_test_data_async)
from playwright.async_api import async_playwright

# Client configuration
client = "swfcu"

EXPECTED_H1  = "Sail to low Rates"
H1_SELECTOR  = "h1"
MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries

# Environment-specific configuration
ENV_CONFIG = {
    "stg": {
        "base_url": "https://statewidefcu24.pixelspoke-staging.com",
        "home_params": "?api=stg&debug_all=1",   # STG requires ?api=stg
        "username": "statewidefcu",
        "password": "statewidefcu",
        "cloudfront_urls": (
            "//d1v4vw9mwf7wyh.cloudfront.net",
            "https://d1v4vw9mwf7wyh.cloudfront.net",
        ),
    },
    "prod": {
        "base_url": "https://www.statewidefcu.org",
        "home_params": "?debug_all=1",            # PROD has no ?api=stg
        "username": "",
        "password": "",
        "cloudfront_urls": (
            "//dfy3oyzv6dw2d.cloudfront.net",
            "https://dfy3oyzv6dw2d.cloudfront.net",
        ),
    },
}


async def validate_homepage_ad_with_retry(page, home_url, screenshots_directory, flow_label,
                                          error_tracker, cloudfront_urls, cfg):
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
                username=cfg["username"],
                password=cfg["password"],
            )
            print(f"[{flow_label}] Correct ad found on attempt {attempt}.")
            return
        except Exception as exc:
            last_error = exc
            print(f"[{flow_label}] Attempt {attempt} failed: {exc}")
            if attempt < MAX_AD_RETRIES:
                print(f"[{flow_label}] Waiting {RETRY_SLEEP}s before retry...")
                await asyncio.sleep(RETRY_SLEEP)

    raise Exception(
        f"[{flow_label}] Ad '{EXPECTED_H1}' not found after {MAX_AD_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


async def _get_search_url_params(browser, base_url, home_params):
    """
    Navigate to the homepage, trigger a search via the UI, and return the
    extracted query string from the resulting URL.

    Steps:
      1. Go to base_url/?...&session_init=1 (fresh session).
      2. Click .swbi-open to open the search input.
      3. Type "rv boat and motorcycle loans" and press Enter.
      4. Extract and return the query string from the resulting URL,
         e.g. 's=rv%2C+boat+and+motorcycle+loans'.
    """
    page = await browser.new_page()
    try:
        print("  [search] Navigating to homepage with session reset...")
        await page.goto(
            f"{base_url}/{home_params}&session_init=1",
            wait_until='load',
            timeout=DEFAULT_TIMEOUT,
        )

        print("  [search] Clicking search icon (.swbi-open)...")
        await page.click('.swbi-open')

        print("  [search] Waiting for search input (input[name='s']) to be visible...")
        await page.wait_for_selector("input[name='s']", state='visible', timeout=DEFAULT_TIMEOUT)

        print("  [search] Typing search query into input[name='s']...")
        await page.fill("input[name='s']", 'rv boat and motorcycle loans')

        print("  [search] Pressing Enter on search input and waiting for navigation...")
        async with page.expect_navigation(wait_until='load', timeout=DEFAULT_TIMEOUT):
            await page.press("input[name='s']", 'Enter')

        current_url = page.url
        search_url_params = urllib.parse.urlparse(current_url).query
        print(f"  [search] Result URL      : {current_url}")
        print(f"  [search] Extracted params: {search_url_params}")
        return search_url_params
    finally:
        await page.close()

@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "statewidefcu", "password": "statewidefcu"}],
    indirect=True,
)
async def test_swfcu_rvboatloan_stgtags_and_js_errors(browser, env):
    cfg = ENV_CONFIG[env]
    base_url = cfg["base_url"]
    home_params = cfg["home_params"]

    print(f"Starting {client} hero ad test.. (env={env})")
    print(sys.version)

    screenshots_directory = f'screenshots_{client}_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    home_url = f"{base_url}/{home_params}"

    # Dynamically extract search URL params by performing the search via the UI
    search_url_params = await _get_search_url_params(browser, base_url, home_params)

    # ── Flow 1: Direct URL trigger ──────────────────────────────────────────
    print("[Flow 1 (Direct URL)] Opening fresh browser page...")
    page1 = await browser.new_page()
    try:
        await process_test_data_async(
            page1,
            [
                {
                    'url': f"{base_url}/{home_params}&session_init=1",
                    'expected': {'wait_type': 'load'},
                },
                {
                    'url': f"{base_url}/rv-boat-and-motorcycle-loans/",
                    'expected': {'wait_type': 'load'},
                },
            ],
            screenshots_directory,
            validate_js=True,
            validate_finalytics=False,
            client=client,
            error_tracker=[],
            cloudfront_urls=cfg["cloudfront_urls"],
            username=cfg["username"],
            password=cfg["password"],
        )

        await validate_homepage_ad_with_retry(
            page1, home_url, screenshots_directory,
            flow_label="Flow 1 (Direct URL)",
            error_tracker=[],
            cloudfront_urls=cfg["cloudfront_urls"],
            cfg=cfg,
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
                    'url': f"{base_url}/{home_params}&session_init=1",
                    'expected': {'wait_type': 'load'},
                },
                {
                    'url': f"{base_url}/?{search_url_params}",
                    'expected': {'wait_type': 'load'},
                },
            ],
            screenshots_directory,
            validate_js=True,
            validate_finalytics=False,
            client=client,
            error_tracker=[],
            cloudfront_urls=cfg["cloudfront_urls"],
            username=cfg["username"],
            password=cfg["password"],
        )

        await validate_homepage_ad_with_retry(
            page2, home_url, screenshots_directory,
            flow_label="Flow 2 (Search URL)",
            error_tracker=[],
            cloudfront_urls=cfg["cloudfront_urls"],
            cfg=cfg,
        )
    finally:
        print("[Flow 2 (Search URL)] Closing browser page...")
        await page2.close()

    print(f"{client} hero ad testing completed.")
