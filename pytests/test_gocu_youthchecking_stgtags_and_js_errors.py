import asyncio
import pytest
import pytest_asyncio
import sys
import os
import time
import shutil
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Function to clear the directory before saving new screenshots

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    detect_js_errors_from_specific_files_async,
    save_page_source_async,
    browser,
    DEFAULT_TIMEOUT)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True,
)
async def test_gocu_youthchecking_stgtags_and_js_errors(
    browser,
    homepage_url="https://georgiasownstg.wpengine.com/?cb=1",
    test_scenario_url="https://georgiasownstg.wpengine.com/checking/i-check-youth-account",
    expected_heading="Level up your financial game",
    hero_heading_selector=".hero-content > div:nth-child(1) > h1:nth-child(2)",
    client="gocu",
    html_finalytics_stg_cloudfront="//d1v4vw9mwf7wyh.cloudfront.net",
    html_finalytics_stg_cloudfront2="https://d1v4vw9mwf7wyh.cloudfront.net",
    finalytics_css_tag="finalytics-function_div.css",
    finalytics_js_tag="finalytics.js",
    finalytics_function_js_tag="finalytics-function.js",
    finalytics_settings_div_js_tag="settings_div.js"
):
    print(f"Starting {client} hero ad test..")

    screenshots_directory = 'screenshots_' + client + '_using_pytest'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        # await page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        time.sleep(15)
        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        time.sleep(15)
        # await page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        # await page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        time.sleep(20)
        print(f"Waiting for {hero_heading_selector} on the homepage...")
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=DEFAULT_TIMEOUT)
        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot.png')

        ad_heading = await page.locator(hero_heading_selector).inner_text()
        if expected_heading != ad_heading:
            pytest.fail(f"Ad heading '{ad_heading}' does not match expected heading '{expected_heading}'")
        else:
            print(f"Ad heading '{ad_heading}' matches expected heading '{expected_heading}'")

        # Verify the HTML snippet exists in the page source
        html_content = await page.content()

        # Modify to check for different possible tag HTML syntax since it can vary per client
        desired_cloudfront_urls = (html_finalytics_stg_cloudfront, html_finalytics_stg_cloudfront2)

        if not any(tag in html_content for tag in desired_cloudfront_urls):
            pytest.fail(
                f"HTML Finalytics STG cloudfront URL '{html_finalytics_stg_cloudfront2}' NOT FOUND in the page source!"
            )
        else:
            print(f"HTML Finalytics STG cloudfront URL '{html_finalytics_stg_cloudfront2}' exists in the homepage source.")

        # Define JS and CSS tags
        desired_finalytics_tags = [finalytics_css_tag, finalytics_js_tag, finalytics_function_js_tag,
                                   finalytics_settings_div_js_tag]
        # Check that all desired tags are present by looping through all the desired tags to check which ones are not in html_content and saves the ones that are missing
        missing_desired_finalytics_tags = [tag for tag in desired_finalytics_tags if tag not in html_content]

        if missing_desired_finalytics_tags:
            pytest.fail(
                f"The following Finalytics finalytics tags were NOT found in the page source: {', '.join(missing_desired_finalytics_tags)}"
            )
        print(
            f"The following Finalytics finalytics tags were found in the page source: {', '.join(desired_finalytics_tags)}")

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
