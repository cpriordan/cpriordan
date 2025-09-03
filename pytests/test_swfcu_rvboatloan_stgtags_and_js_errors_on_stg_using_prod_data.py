import asyncio
import pytest
import pytest_asyncio
import sys
import os
import time
import shutil
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Function to clear the directory before saving new screenshots
def clear_screenshots_directory(directory):
    if os.path.exists(directory):
        # Remove all files in the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symbolic link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        # Create the directory if it doesn't exist
        os.makedirs(directory)

async def save_page_source(page, filepath):
    """Saves the page's source code to a file."""
    try:
        html_content = await page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
    """
    Listens for console messages to detect JavaScript errors from specific files.
    Updates the error_tracker with detected errors.
    """
    async def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'

        # Check if the message is an error and from a specific JS file
        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)

            # Add error message to the tracker
            error_tracker.append(error_message)

            # Take a screenshot for debugging
            screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot of JS error saved at {screenshot_path}")

    # Listen for console events on the page
    page.on('console', lambda msg: asyncio.ensure_future(handle_console_message(msg)))

# Fixture to set up Playwright and launch the browser
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
    [{"username": "statewidefcu", "password": "statewidefcu"}],
    indirect=True,
)
async def test_swfcu_rvboatloan_stgtags_and_js_errors(
    browser,
    homepage_url="https://statewidefcu.pixelspoke-staging.com/",
    test_scenario_url="https://statewidefcu.pixelspoke-staging.com/rv-boat-and-motorcycle-loans/",
    expected_heading="Sail to low Rates",
    hero_heading_selector="h1.co-fw_hero--title",
    client="swfcu",
    html_finalytics_stg_cloudfront="//d1v4vw9mwf7wyh.cloudfront.net",
    html_finalytics_stg_cloudfront2="https://d1v4vw9mwf7wyh.cloudfront.net",
    finalytics_css_tag="finalytics-function_div.css",
    finalytics_js_tag="finalytics.js",
    finalytics_function_js_tag="finalytics-function.js",
    finalytics_settings_div_js_tag="settings_div.js",
):
    print(f"Starting {client} hero ad test..")

    screenshots_directory = 'screenshots_' + client + '_using_pytest'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        # await page.wait_for_load_state('domcontentloaded', timeout=60000)
        # await page.wait_for_load_state('load', timeout=60000)
        # time.sleep(15)
        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        # await page.wait_for_load_state('domcontentloaded', timeout=60000)
        # await page.wait_for_load_state('load', timeout=60000)
        # time.sleep(15)
        # await page.wait_for_load_state('networkidle', timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        # await page.wait_for_load_state('load', timeout=60000)
        # await page.wait_for_load_state('domcontentloaded', timeout=60000)
        # time.sleep(20)
        print(f"Waiting for {hero_heading_selector} on the homepage...")
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')
        await wait_for_js_and_element(page, hero_heading_selector, timeout=60000)
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
