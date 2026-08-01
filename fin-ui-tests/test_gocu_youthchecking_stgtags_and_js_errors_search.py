"""
Test GOCU Youth Checking Personalization — STG Tags, JS Errors, and Search Trigger

Two flows are tested back-to-back in the same session:

  Flow 1 (Direct URL):  session_init → /checking/i-check-youth-account → homepage → validate ad
  Flow 2 (Search URL):  session_init → /search-page#?cludoquery=youth+checking → homepage → validate ad

Discovery notes:
  - GOCU uses Cludo search with hash-based URL: /search-page#?cludoquery=youth+checking
"""

import pytest
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa_tools import (
    clear_screenshots_directory,
    browser,
    DEFAULT_TIMEOUT,
    process_test_data_async,
)

client = "gocu"

BASE_URL    = "https://georgiasownstg.wpengine.com"
HOME_PARAMS = "?cb=1&debug_all=1"

EXPECTED_H1    = "Banking that hits different"
H1_SELECTOR    = ".hero-content > div:nth-child(1) > h1:nth-child(2)"
CLOUDFRONT_URL = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")

SEARCH_URL = f"{BASE_URL}/search-page#?cludoquery=youth+checking"

MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries


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
            print(f"[{flow_label}] ✓ Correct ad found on attempt {attempt}.")
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


@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True,
)
async def test_gocu_youthchecking_stgtags_and_js_errors_search(browser):
    print(f"Starting {client} hero ad test (with search trigger)..")
    print(sys.version)

    screenshots_directory = f"screenshots_{client}_using_pytest/"
    clear_screenshots_directory(screenshots_directory)

    home_url = f"{BASE_URL}/{HOME_PARAMS}"

    # ── Flow 1: Direct URL trigger ──────────────────────────────────────────
    print("[Flow 1 (Direct URL)] Opening fresh browser page...")
    page1 = await browser.new_page()
    try:
        await process_test_data_async(
            page1,
            [
                {
                    "url": f"{BASE_URL}/?cb=1&debug_all=1&session_init=1",
                    "wait_type": "load",
                },
                # process_page_data_async only honors a "sleep" dict key when
                # wait_type == 'sleep'; with wait_type == 'load' (as above) it was
                # silently ignored, so getads never actually got the intended pause
                # to register the intent signal before the homepage check ran.
                # Standalone integers in the data list ARE honored (int branch).
                3,
                {
                    "url": f"{BASE_URL}/checking/i-check-youth-account",
                    "expected": {"wait_type": "load"},
                },
                10,
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
                    "url": f"{BASE_URL}/?cb=1&debug_all=1&session_init=1",
                    "wait_type": "load",
                },
                3,
                {
                    "url": SEARCH_URL,
                    "expected": {"wait_type": "load"},
                },
                10,
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
