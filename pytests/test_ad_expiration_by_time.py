import asyncio
import pytest
import pytest_asyncio
import sys
import os
import shutil
from playwright.async_api import async_playwright

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


# Fixture to set up Playwright and launch the browser
@pytest_asyncio.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser  # Use `yield` to ensure teardown after test
        await browser.close()  # Close the browser after the test

async def wait_for_js_and_element(page, hero_selector, timeout=40000):
    # Wait for the document to be fully loaded
    await page.evaluate('''
        new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });
    ''')

    # Wait for the specific element to be visible
    await page.wait_for_function(
        f'document.querySelector("{hero_selector}") !== null && document.querySelector("{hero_selector}").offsetHeight > 0',
        timeout=timeout
    )

@pytest.mark.asyncio
async def test_check_ad_expiration_by_time(
    browser,
    homepage_url="https://www.stgfinalyticsdemo.com/",
    test_scenario_url="https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    page_qa_expire_time_url="https://www.stgfinalyticsdemo.com/qa/expire/30seconds",
    page_qa_expire_time_url_age_first_ad_by_minutes="https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1460&age__minutes=1", #ad_ids=1460&age__minutes=1
    page_qa_expire_time_url_age_second_ad_by_minutes="https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1449&age__minutes=1", #ad_ids=1449&age__minutes=1
    expected_h1_for_first_ad="Car Loan Ad 1 that expires 30 seconds after session starts",
    expected_h1_after_first_ad_expires="Car Loan Ad 2 that expires 30 seconds after session starts",
    expected_h1_after_second_ad_expires="Banking with the Best",
    hero_selector=".c-hero"
):
    print("Starting ad expiration testing...")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = 'screenshots_ad_expiration_by_time_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()  # This now works as `browser` is correctly awaited

    # Navigate to homepage and capture screenshot
    await page.goto(homepage_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}1_homepage_screenshot.png')

    # Trigger ad by visiting scenario URL
    await page.goto(test_scenario_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}2_page_for_ad_screenshot.png')

    # Check the first ad heading
    await page.goto(page_qa_expire_time_url)
    await page.wait_for_load_state('load')
    # Wait until network activity settles before going to the next step
    await page.wait_for_load_state('networkidle')

    # Enhancements to reduce maintenance by listening to the ad_id that gets returned first to determine how to age
    # Use async response handler and wait until first_ad_id is set instead of relying on window.firstAdCaptured
    # Updated: Ensure getads listener is attached before navigation, and wait for specific response instead of looping blindly

    # Attach the listener before navigating so we don't miss the request
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

    # Navigate to the expire time page AFTER attaching listener
    await page.goto(page_qa_expire_time_url)
    await page.wait_for_load_state('networkidle')

    # Wait up to 10 seconds for first_ad_id to be set after navigation
    max_wait_time = 10
    elapsed = 0
    while first_ad_id is None and elapsed < max_wait_time:
        await asyncio.sleep(0.5)
        elapsed += 0.5

    if first_ad_id is None:
        raise TimeoutError("Timed out waiting for first_ad_id from getads API")

    expected_heading1_number_before_expire_ad = ""
    expected_heading2_number_before_expire_ad = ""

    # Decide which URL to use for aging the first ad
    if first_ad_id == 1460:
        expire_first_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1460&age__minutes=1"
        expire_second_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1449&age__minutes=1"
        expected_heading1_number_before_expire_ad = "1"
        expected_heading2_number_before_expire_ad = "2"
    elif first_ad_id == 1449:
        expire_first_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1449&age__minutes=1"
        expire_second_ad_url = "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1460&age__minutes=1"
        expected_heading1_number_before_expire_ad = "2"
        expected_heading2_number_before_expire_ad = "1"

    else:
        raise ValueError(f"Unexpected ad_id returned: {first_ad_id}")

    print(f"--> expire_FIRST_ad_url is  {expire_first_ad_url}  and  expire_SECOND_ad_url  is {expire_second_ad_url }***")

    await wait_for_js_and_element(page, hero_selector)
    ad_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}3_hero_ad1_screenshot.png')
    # Assert to check if the ad heading matches the expected heading for the first ad
    dynamic_expected_heading1 = "Car Loan Ad " + expected_heading1_number_before_expire_ad + " that expires 30 seconds after session starts"

    assert dynamic_expected_heading1 == ad_on_hero_content_h1, (
        f"Ad has heading '{ad_on_hero_content_h1}' but expected heading was '{dynamic_expected_heading1}'"
    )

    # Expire the first ad
    # GO TO FIRST AD URL BASED ON CAPTURED FIRST AD
    await page.goto(expire_first_ad_url)
    await page.wait_for_load_state('load')
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element(page, hero_selector)
    ad2_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of the second ad is *** {ad2_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}4_hero_reloaded_after_aging_first_ad.png')
    # Dynamically generate the expected heading based on the ad that gets displayed first
    dynamic_expected_heading_after_aging_first_ad = "Car Loan Ad " + expected_heading2_number_before_expire_ad +  " that expires 30 seconds after session starts"
    # Use the dynamic heading
    assert dynamic_expected_heading_after_aging_first_ad == ad2_on_hero_content_h1, (
        f"Ad has heading '{ad2_on_hero_content_h1}' but expected heading was '{dynamic_expected_heading1}'"
    )


    # Expire the second ad
    # await page.goto(page_qa_expire_time_url_age_second_ad_by_minutes) HARDCODED URL URL USED
    await page.goto(expire_second_ad_url)
    await page.wait_for_load_state('load')
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element(page, hero_selector)
    ad3_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of default page after second ad expired *** {ad3_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}5_hero_reloaded_after_aging_second_ad.png')

    # When BOTH ad expires, the heading is the DEFAULT HEADING
    # Use the dynamic heading
    assert expected_h1_after_second_ad_expires == ad3_on_hero_content_h1, (
        f"Ad has heading '{ad2_on_hero_content_h1}' but expected heading was '{dynamic_expected_heading1}'"
    )


    print(f"Ad expiration testing completed.")
