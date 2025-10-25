import asyncio
import pytest
import pytest_asyncio
import sys
import os
import shutil
import time
# from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
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

# async def save_page_source(page, filepath):
#     """Saves the page's source code to a file."""
#     try:
#         html_content = await page.content()
#         with open(filepath, 'w', encoding='utf-8') as file:
#             file.write(html_content)
#         print(f"Page source saved to {filepath}")
#     except Exception as e:
#         print(f"Failed to save page source: {e}")

def save_page_source(page, filepath):
    try:
        html_content = page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

# def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
#     """
#     Listens for console messages to detect JavaScript errors from specific files.
#     Updates the error_tracker with detected errors.
#     """
#     async def handle_console_message(msg):
#         location = msg.location
#         file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
#
#         # Check if the message is an error and from a specific JS file
#         if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
#             error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
#             print(error_message)
#
#             # Add error message to the tracker
#             error_tracker.append(error_message)
#
#             # Take a screenshot for debugging
#             screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
#             await page.screenshot(path=screenshot_path)
#             print(f"Screenshot of JS error saved at {screenshot_path}")
#
#     # Listen for console events on the page
#     page.on('console', lambda msg: asyncio.ensure_future(handle_console_message(msg)))
#

# UPDATED TO OPEN THE DEV CONSOLE WHEN A JS ERROR IS DETECTED
# def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
#     """Detect JavaScript errors from specific files."""
#     opened_dev_console = False  # Initialize the flag here
#     def handle_console_message(msg):
#         nonlocal opened_dev_console  # Declare the variable as non-local to access it from the outer scope
#         location = msg.location
#         file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
#
#         if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
#             error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
#             print(error_message)
#             error_tracker.append(error_message)
#
#             if not opened_dev_console:
#                 print("Opening DevTools console for debugging...")
#                 # Open the DevTools console in the current browser instance
#                 page.context.new_page().goto("devtools://devtools")
#                 opened_dev_console = True
#
#             screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
#             page.screenshot(path=screenshot_path)
#             print(f"Screenshot of JS error saved at {screenshot_path} with dev console opened for client {client}")
#
#     page.on('console', handle_console_message)


def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker, browser_instance, browser_type):
    """Detect JavaScript errors from specific files."""
    def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
        screenshots_directory = f'screenshots_{client}_using_pytest/{browser_type}'

        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)

            screenshot_path = os.path.join(screenshots_directory, f"/js_error_{client}.png")
            page.screenshot(path=screenshot_path)
            print(f"Screenshot of JS error saved at {screenshot_path} for client {client}")

    page.on('console', handle_console_message)

# Fixture to set up Playwright and launch ONE browser
# @pytest_asyncio.fixture
# async def browser():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch()
#         yield browser  # Use `yield` to ensure teardown after test
#         await browser.close()  # Close the browser after the test

# Fixture to set up Playwright and launch MULTIPLE browsers
# def wait_for_js_and_element(page, hero_heading_selector, timeout=60000):
#     try:
#         page.evaluate('''new Promise(resolve => {
#             if (document.readyState === 'complete') {
#                 resolve();
#             } else {
#                 window.addEventListener('load', resolve);
#             }
#         });''')
#         print("Page fully loaded.")
#     except PlaywrightTimeoutError:
#         print("Timeout while waiting for page load.")
#
#     # Wait for the specific element to be visible
#     try:
#         page.wait_for_function(
#             f'document.querySelector("{hero_heading_selector}") !== null && document.querySelector("{hero_heading_selector}").offsetHeight > 0',
#             timeout=timeout
#         )
#         print(f"Element {hero_heading_selector} is visible.")
#     except PlaywrightTimeoutError:
#         print(f"Timeout waiting for element: {hero_heading_selector}")

async def wait_for_js_and_element(page, selector, timeout=60000):
    try:
        await page.wait_for_function(
            'document.readyState === "complete"',
            timeout=timeout
        )
        print("Page fully loaded.")
    except PlaywrightTimeoutError:
        print("Timeout while waiting for page load.")

    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        print(f"Element {selector} is visible.")
    except PlaywrightTimeoutError:
        print(f"Timeout waiting for element: {selector}")


@pytest_asyncio.fixture
async def browser(request):
    """Fixture to launch the browser with HTTP credentials."""
    username = request.param.get("username")
    password = request.param.get("password")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])
        context = await browser.new_context(http_credentials={"username": username, "password": password})
        context.set_default_timeout(40000)
        yield context
        await browser.close()

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "OneAZ", "password": "pugs r potatoes!3"}],
    indirect=True,
)

async def test_oneaz_stgtags_and_js_errors(
    browser,
    homepage_url="https://oneazcuqa.oneazcu.com/?api=stg",
    test_scenario_url="https://oneazcuqa.oneazcu.com/business?api=stg",
    expected_heading="From startup to level-up.",
    hero_heading_selector="#copyCol > h1", #finalytics > li > div > div > div > h1
    client="oneaz",
    html_finalytics_stg_cloudfront="//d1v4vw9mwf7wyh.cloudfront.net",
    html_finalytics_stg_cloudfront2="https://d1v4vw9mwf7wyh.cloudfront.net",
    finalytics_css_tag="finalytics-function_div.css",
    finalytics_js_tag="finalytics.js",
    finalytics_function_js_tag="finalytics-function.js",
    finalytics_settings_div_js_tag="settings_div.js"
):
    print(f"Starting {client} hero ad test...")
    print(sys.version)

    browser_instance = browser
    browser_type = "chromium"
    print(f"\nSTARTING **{client}** hero ad test using BROWSER TYPE ***{browser_type}***...")
    print(sys.version)

    # Directory for screenshots
    screenshots_directory = f'screenshots_{client}_using_pytest/{browser_type}'
    clear_screenshots_directory(screenshots_directory)

    # Open a new page in the provided context (await needed because this is async Playwright)
    page = await browser_instance.new_page()

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js', 'settings.js?code=oneaz', 'settings.js?code=oneaz:80']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, browser_instance, browser_type)

    print(f"About to go to home_url {homepage_url}")

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded", timeout=60000)
        await page.wait_for_load_state("load", timeout=60000)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)
        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png', full_page=True)

        # Save the page source to a file
        page_source_filepath = f'{screenshots_directory}/homepage_source.html'
        save_page_source(page, page_source_filepath)

        # Open the "View Source" page only if not using webkit since not valid URL format for webkit
        view_source_url = f"view-source:{homepage_url}"
        if browser_type != "webkit":
            await page.goto(view_source_url, timeout=60000)
            # Take a screenshot of the "View Source" page
            await page.screenshot(path=f'{screenshots_directory}/homepage_source_screenshot.png')
            print("Screenshot with source code taken for browsers except webkit browser engine used by Safari.")
        else:
            print("Screenshot with source code NOT taken for webkit browser engine used by Safari.")

        # Call detect_js_errors_from_specific_files after navigating to the homepage
        detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, browser_instance, browser_type)

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await page.wait_for_load_state('domcontentloaded', timeout=60000)
        await page.wait_for_load_state('load', timeout=60000)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)

        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png', full_page=True)

        # Call detect_js_errors_from_specific_files after navigating to the test scenario
        detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, browser_instance, browser_type)

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('load', timeout=60000)
        await page.wait_for_load_state('domcontentloaded', timeout=60000)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)

        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        # ---------------------------------------------
        # CHANGED: Take ONLY the #homeSlider section screenshot and name it hero_ad_only
        # ---------------------------------------------
        print("Waiting for #homeSlider on the homepage...")  # CHANGED
        await wait_for_js_and_element(page, "#homeSlider", timeout=60000)  # CHANGED
        await page.wait_for_selector("#homeSlider", state='visible', timeout=60000)  # CHANGED

        # CHANGED: Capture only the targeted section instead of full-page
        await page.locator("#homeSlider").screenshot(  # CHANGED
            path=f'{screenshots_directory}/hero_ad_only.png'  # CHANGED
        )  # CHANGED
        print("Saved hero section screenshot as hero_ad_only.png")  # CHANGED
        # ---------------------------------------------

        # (Optional keep) Validate the text still if desired
        await wait_for_js_and_element(page, hero_heading_selector, timeout=60000)
        await page.wait_for_selector(hero_heading_selector, state='visible', timeout=60000)
        ad_heading = await page.locator(hero_heading_selector).inner_text()
        # Instead of comparing the heading, compare the images in folder BASELINE/hero_ad_only_baseline.png with the current /hero_ad_only.png using OCR
        if expected_heading != ad_heading:
            pytest.fail(f"Ad heading '{ad_heading}' does not match expected heading '{expected_heading}'")
        else:
            print(f"Ad heading '{ad_heading}' matches expected heading '{expected_heading}'")

        # Call detect_js_errors_from_specific_files after going back to the homepage to view the ad
        detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, browser_instance, browser_type)

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
