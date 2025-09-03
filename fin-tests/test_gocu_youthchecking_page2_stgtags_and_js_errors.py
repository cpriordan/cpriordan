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

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True,
)
async def test_gocu_youthchecking_stgtags_and_js_errors(
    browser,
    homepage_url="https://georgiasownstg.wpengine.com/?cb=1",
    test_scenario_url="https://georgiasownstg.wpengine.com/checking/student-access",
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

    screenshots_directory = setup_screenshots_directory(client)

    page = await browser.new_page()

    specific_js_files = get_common_js_files()
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        # await page.wait_for_load_state('networkidle', timeout=60000)
        await page.wait_for_load_state('domcontentloaded', timeout=60000)
        await page.wait_for_load_state('load', timeout=60000)
        time.sleep(15)
        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await page.wait_for_load_state('domcontentloaded', timeout=60000)
        await page.wait_for_load_state('load', timeout=60000)
        time.sleep(15)
        # await page.wait_for_load_state('networkidle', timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)
        # await page.wait_for_load_state('networkidle', timeout=60000)
        await page.wait_for_load_state('load', timeout=60000)
        await page.wait_for_load_state('domcontentloaded', timeout=60000)
        time.sleep(20)
        print(f"Waiting for {hero_heading_selector} on the homepage...")
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot.png')

        ad_heading = await page.locator(hero_heading_selector).inner_text()
        if expected_heading != ad_heading:
            pytest.fail(f"Ad heading '{ad_heading}' does not match expected heading '{expected_heading}'")
        else:
            print(f"Ad heading '{ad_heading}' matches expected heading '{expected_heading}'")

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
