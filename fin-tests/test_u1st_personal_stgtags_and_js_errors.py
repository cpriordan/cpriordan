import pytest
import pytest_asyncio
import sys
import os
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    save_page_source_async,
    detect_js_errors_from_specific_files_async,
    wait_for_js_and_element_async,
    validate_finalytics_tags,
    setup_screenshots_directory,
    get_common_js_files,
    get_common_finalytics_tags,
    browser)

async def wait_for_js_and_element(page, hero_heading_selector, timeout=40000):
    """
    Waits for the document to be fully loaded and for a specific element to become visible.
    """
    try:
        print("Waiting for the document to be fully loaded...")
        await page.evaluate('''new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });''')

        print(f"Waiting for the element '{hero_heading_selector}' to become visible...")

        await page.wait_for_function(
            f'document.querySelector("{hero_heading_selector}") !== null && '
            f'document.querySelector("{hero_heading_selector}").offsetHeight > 0',
            timeout=timeout
        )
        print(f"Element '{hero_heading_selector}' is now visible.")
    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout waiting for element '{hero_heading_selector}' to become visible: {e}")

# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     "browser",
#     [{"username": "uccustaging", "password": "LoveWYBank2021!"}],
#     indirect=True,
# )

# And in the test case, update the parametrize to include 'browser' key too

# Parametrize test across multiple browsers dynamically with credentials

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [
        {"browser": "chromium", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "firefox", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "opera", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "edge", "username": "uccustaging", "password": "LoveWYBank2021!"}
    ],
    indirect=True,
)
async def test_u1st_personal_stgtags_and_js_errors(
    browser,
    homepage_url="https://1stunitedcu.cms.banno-staging.com/?api=stg",
    test_scenario_url="https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/personal-loans-and-lines",
    expected_heading="Big Dreams, Small Payments",
    hero_heading_selector="#slideshow--main > div > div > div > div > div > div > div.hero__slider-content.d-flex.flex-row.align-content-center.justify-start.align-items-center > div > div > div > div > div > div > div > h2",
    client="u1st",
    html_finalytics_stg_cloudfront="//d1v4vw9mwf7wyh.cloudfront.net",
    html_finalytics_stg_cloudfront2="https://d1v4vw9mwf7wyh.cloudfront.net",
    finalytics_css_tag="finalytics-function_div.css",
    finalytics_js_tag="finalytics.js",
    finalytics_function_js_tag="finalytics-function.js",
    finalytics_settings_div_js_tag="settings_div.js",
):
    print(f"Starting {client} hero ad test..")

    screenshots_directory = 'screenshots_' + client + '_using_pytest/regression/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    specific_js_files = get_common_js_files()
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        try:
            await page.wait_for_load_state('networkidle', timeout=90000)
        except PlaywrightTimeoutError:
            print("Network idle timed out, falling back to domcontentloaded")
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
        # await page.wait_for_load_state('domcontentloaded', timeout=60000)
        # await page.wait_for_load_state('load', timeout=60000)
        # time.sleep(15)
        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        # await page.wait_for_load_state('networkidle', timeout=90000)
        await page.wait_for_load_state('domcontentloaded', timeout=90000)
        # await page.wait_for_load_state('load', timeout=60000)
        # time.sleep(15)
        # await page.wait_for_load_state('networkidle', timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)
        try:
            await page.wait_for_load_state('networkidle', timeout=90000)
        except PlaywrightTimeoutError:
            print("Network idle timed out, falling back to domcontentloaded")
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
        # await page.wait_for_load_state('load', timeout=60000)
        # await page.wait_for_load_state('domcontentloaded', timeout=60000)
        # time.sleep(20)
        print(f"Waiting for {hero_heading_selector} on the homepage...")
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=90000)
        # Strip any white space in the heading
        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert expected_heading == ad_on_hero_content_h1_normalized, (
            f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{expected_heading}'"
        )

        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot.png', timeout=90000)

        # Get page content for validation
        html_content = await page.content()
        
        # Use consolidated function for Finalytics tag validation
        cloudfront_urls = (html_finalytics_stg_cloudfront, html_finalytics_stg_cloudfront2)
        common_tags = get_common_finalytics_tags()
        required_tags = [
            common_tags['css_tag'],
            common_tags['js_tag'], 
            common_tags['function_js_tag'],
            common_tags['settings_div_js_tag']
        ]
        
        validate_finalytics_tags(html_content, cloudfront_urls, required_tags, client)

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
