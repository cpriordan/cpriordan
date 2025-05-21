import asyncio
import pytest
import pytest_asyncio
import sys
import os
import time
import shutil
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

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
# @pytest_asyncio.fixture
# async def browser(request):
#     """Fixture to launch the browser with HTTP credentials."""
#     username = request.param.get("username")
#     password = request.param.get("password")
#     async with async_playwright() as playwright:
#         browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])
#         context = await browser.new_context(http_credentials={"username": username, "password": password})
#         context.set_default_timeout(40000)
#         yield context
#         await browser.close()

# @pytest.fixture(params=["chromium", "firefox", "opera", "edge"])
# def browser(request):
#     with sync_playwright() as p:
#         browser_type_name = request.param
#         browser_args = ["--start-maximized", "--auto-open-devtools-for-tabs"]
#
#         if browser_type_name in ["opera", "edge"]:
#             executable_path = {
#                 "opera": "C:/Users/c_p_r/AppData/Local/Programs/Opera/opera.exe",
#                 "edge": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
#             }[browser_type_name]
#
#             browser = p.chromium.launch(
#                 headless=False,
#                 executable_path=executable_path,
#                 args=browser_args
#             )
#         else:
#             # Make sure browser_type_name is used correctly here
#             browser_type = getattr(p, browser_type_name)
#             browser = browser_type.launch(
#                 headless=False,
#                 args=browser_args
#             )
#
#         context = browser.new_context()
#         yield context
#         browser.close()

# @pytest.fixture(params=["chromium", "firefox", "opera", "edge"])
@pytest_asyncio.fixture
async def browser(request):
    # Extract the browser name and custom credentials from the param
    browser_config = request.param
    if not isinstance(browser_config, dict):
        raise ValueError("Expected 'request.param' to be a dict with keys like 'browser', 'username', and 'password'.")

    browser_name = browser_config.get("browser", "chromium")  # default to chromium if not specified
    username = browser_config.get("username")
    password = browser_config.get("password")

    browser_args = ["--start-maximized", "--auto-open-devtools-for-tabs"]

    async with async_playwright() as p:
        if browser_name == "firefox":
            browser_type = p.firefox
            browser = await browser_type.launch(headless=False, args=browser_args)
        elif browser_name == "webkit":
            browser_type = p.webkit
            browser = await browser_type.launch(headless=False, args=browser_args)
        elif browser_name == "edge":
            executable_path = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
            browser = await p.chromium.launch(
                headless=False,
                executable_path=executable_path,
                args=browser_args
            )
        elif browser_name == "opera":
            executable_path = "C:/Users/c_p_r/AppData/Local/Programs/Opera/opera.exe"
            browser = await p.chromium.launch(
                headless=False,
                executable_path=executable_path,
                args=browser_args
            )
        else:
            browser_type = p.chromium
            browser = await browser_type.launch(
                headless=False,
                args=browser_args
            )

        # context = await browser.new_context()
        # if username and password:
        #     await context.set_http_credentials({"username": username, "password": password})

        http_credentials = {"username": username, "password": password} if username and password else None
        context = await browser.new_context(http_credentials=http_credentials)

        context.set_default_timeout(40000)
        yield context
        await browser.close()


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

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

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
        await wait_for_js_and_element(page, hero_heading_selector, timeout=90000)
        # Strip any white space in the heading
        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert expected_heading == ad_on_hero_content_h1_normalized, (
            f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{expected_heading}'"
        )

        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot.png', timeout=90000)

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
