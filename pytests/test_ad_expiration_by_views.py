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

@pytest.mark.asyncio
async def test_check_ad_expiration_by_views(
    browser_no_auth,
    homepage_url="https://www.stgfinalyticsdemo.com/",
    test_scenario_url="https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    page_qa_expire_views_url="https://www.stgfinalyticsdemo.com/qa/expire/views",
    page_qa_expire_views_url_ad1="https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1344&age__views=2",
    page_qa_expire_views_url_ad2="https://www.stgfinalyticsdemo.com/qa/expire/views?ad_ids=1345&age__views=2",
    expected_h1_for_first_ad="New Car Loan Ad 1 that expires by views",
    expected_h1_after_first_ad_expires="New Car Loan Ad 2 that expires by views",
    expected_h1_after_second_ad_expires="Banking with the Best",
    hero_selector=".c-hero"
):
    print("Starting ad expiration testing...")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = 'screenshots_ad_expiration_by_views_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser_no_auth.new_page()  # This now works as `browser_no_auth` is correctly awaited

    # Navigate to homepage and capture screenshot
    await page.goto(homepage_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}1_homepage_screenshot.png')

    # Trigger ad by visiting scenario URL
    await page.goto(test_scenario_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}2_page_for_ad_screenshot.png')

    # Check the first ad heading
    await page.goto(page_qa_expire_views_url)
    await page.wait_for_load_state('load')
    # Wait until network activity settles before going to the next step
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element_async(page, hero_selector)
    ad_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}3_hero_ad1_screenshot.png')
    # Assert to check if the ad heading matches the expected heading for the first ad
    assert expected_h1_for_first_ad == ad_on_hero_content_h1, (
        f"Ad has heading '{ad_on_hero_content_h1}' but expected heading was '{expected_h1_for_first_ad}'"
    )

    # Expire the first ad
    # NOTE: If the assertion fails, check the ad ID that gets returned by getads and use that in page_qa_expire_views_url_ad1 so correct ad gets expired
    await page.goto(page_qa_expire_views_url_ad1)
    await page.wait_for_load_state('load')
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element_async(page, hero_selector)
    ad2_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of the second ad after first ad expired is *** {ad2_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}4_hero_reloaded_after_aging_first_ad.png')
    # Assert to check if the ad heading matches the expected heading after first ad expires
    assert expected_h1_after_first_ad_expires == ad2_on_hero_content_h1, (
        f"Ad has heading '{ad2_on_hero_content_h1}' but expected heading was '{expected_h1_after_first_ad_expires}'"
    )

    # Expire the second ad
    await page.goto(page_qa_expire_views_url_ad2)
    await page.wait_for_load_state('load')
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element_async(page, hero_selector)
    ad3_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of default page after second ad expired *** {ad3_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}5_hero_reloaded_after_aging_second_ad.png')
    # Assert to check if the ad heading matches the expected heading after second ad expires
    assert expected_h1_after_second_ad_expires == ad3_on_hero_content_h1, (
        f"Ad has heading '{ad3_on_hero_content_h1}' but expected heading was '{expected_h1_after_second_ad_expires}'"
    )

    print(f"Ad expiration testing completed.")
