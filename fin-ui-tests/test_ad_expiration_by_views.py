"""
Test Ad Expiration by Views

Version History:
- 2025-11-22: Refactored to use dynamic ad detection logic
    - Added debug_all=1 homepage URL visit to establish debug session
    - Added response handler to capture first ad_id from getads API
    - Added dynamic URL selection based on which ad (1344 or 1345) appears first
    - Dynamically generates expected headings based on captured ad order
    - Fixed test failures caused by non-deterministic ad ordering from API
"""

import asyncio
import pytest
import pytest_asyncio
import sys
import os

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    browser_no_auth,
    DEFAULT_TIMEOUT)
from playwright.async_api import async_playwright

# Test configuration
HOMEPAGE_URL = "https://www.stgfinalyticsdemo.com/?debug_all=1"
TEST_SCENARIO_URL = "https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans"
PAGE_QA_EXPIRE_VIEWS_URL = "https://www.stgfinalyticsdemo.com/qa/expire/views"
EXPECTED_H1_AFTER_BOTH_ADS_EXPIRE = "Banking with the Best"
HERO_SELECTOR = ".c-hero"
H1_SELECTOR = ".col-md-8 > h1:nth-child(1)"

@pytest.mark.regression
@pytest.mark.asyncio
async def test_check_ad_expiration_by_views(
    browser_no_auth
):
    print("Starting ad expiration testing...")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = 'screenshots_ad_expiration_by_views_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser_no_auth.new_page()

    # Navigate to homepage with debug_all=1 to establish debug session
    await page.goto(HOMEPAGE_URL)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}1_homepage_screenshot.png')

    # Trigger ad by visiting scenario URL
    await page.goto(TEST_SCENARIO_URL)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}2_page_for_ad_screenshot.png')

    # Set up response handler to capture the first ad_id dynamically
    first_ad_id = None

    async def handle_response(response):
        nonlocal first_ad_id
        if "finalyticsdata.com/api/v1/getads/" in response.url:
            try:
                data = await response.json()
                if "ads" in data and len(data["ads"]) > 0:
                    first_ad_id = data["ads"][0].get("id")
                    print(f"Captured first ad_id: {first_ad_id}")
            except Exception as e:
                print(f"Error parsing getads response: {e}")

    page.on("response", handle_response)

    # Navigate to the expire views page AFTER attaching listener
    await page.goto(PAGE_QA_EXPIRE_VIEWS_URL)
    await page.wait_for_load_state('networkidle')

    # Wait up to 10 seconds for first_ad_id to be set after navigation
    max_wait_time = 10
    elapsed = 0
    while first_ad_id is None and elapsed < max_wait_time:
        await asyncio.sleep(0.5)
        elapsed += 0.5

    if first_ad_id is None:
        raise TimeoutError("Timed out waiting for first_ad_id from getads API")

    # Decide which URL to use for aging based on which ad appeared first
    if first_ad_id == 1344:
        expire_first_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1344&age__views=2"
        expire_second_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1345&age__views=2"
        expected_heading1_number = "1"
        expected_heading2_number = "2"
    elif first_ad_id == 1345:
        expire_first_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1345&age__views=2"
        expire_second_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1344&age__views=2"
        expected_heading1_number = "2"
        expected_heading2_number = "1"
    else:
        raise ValueError(f"Unexpected ad_id returned: {first_ad_id}")

    print(f"--> expire_FIRST_ad_url is {expire_first_ad_url} and expire_SECOND_ad_url is {expire_second_ad_url}")

    # Wait for hero element and verify first ad heading
    await wait_for_js_and_element_async(page, HERO_SELECTOR)
    ad_on_hero_content_h1 = await page.locator(H1_SELECTOR).inner_text()
    print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}3_hero_ad1_screenshot.png')

    # Assert first ad heading matches expected
    dynamic_expected_heading1 = f"New Car Loan Ad {expected_heading1_number} that expires by views"
    assert dynamic_expected_heading1 == ad_on_hero_content_h1, (
        f"Ad has heading '{ad_on_hero_content_h1}' but expected heading was '{dynamic_expected_heading1}'"
    )

    # Expire the first ad
    await page.goto(expire_first_ad_url)
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element_async(page, HERO_SELECTOR)
    ad2_on_hero_content_h1 = await page.locator(H1_SELECTOR).inner_text()
    print(f"---> Heading of the second ad is *** {ad2_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}4_hero_reloaded_after_aging_first_ad.png')

    # Assert second ad heading matches expected
    dynamic_expected_heading2 = f"New Car Loan Ad {expected_heading2_number} that expires by views"
    assert dynamic_expected_heading2 == ad2_on_hero_content_h1, (
        f"Ad has heading '{ad2_on_hero_content_h1}' but expected heading was '{dynamic_expected_heading2}'"
    )

    # Expire the second ad
    await page.goto(expire_second_ad_url)
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element_async(page, HERO_SELECTOR)
    ad3_on_hero_content_h1 = await page.locator(H1_SELECTOR).inner_text()
    print(f"---> Heading of default page after second ad expired *** {ad3_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}5_hero_reloaded_after_aging_second_ad.png')

    # When BOTH ads expire, the heading should be the DEFAULT HEADING
    assert EXPECTED_H1_AFTER_BOTH_ADS_EXPIRE == ad3_on_hero_content_h1, (
        f"Ad has heading '{ad3_on_hero_content_h1}' but expected heading was '{EXPECTED_H1_AFTER_BOTH_ADS_EXPIRE}'"
    )

    print("Ad expiration testing completed.")
