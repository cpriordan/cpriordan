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
async def test_check_ad_expiration_by_views(
    browser,
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
    await page.goto(page_qa_expire_views_url)
    await page.wait_for_load_state('load')
    # Wait until network activity settles before going to the next step
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element(page, hero_selector)
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
    await wait_for_js_and_element(page, hero_selector)
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
    await wait_for_js_and_element(page, hero_selector)
    ad3_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of default page after second ad expired *** {ad3_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}5_hero_reloaded_after_aging_second_ad.png')
    # Assert to check if the ad heading matches the expected heading after second ad expires
    assert expected_h1_after_second_ad_expires == ad3_on_hero_content_h1, (
        f"Ad has heading '{ad3_on_hero_content_h1}' but expected heading was '{expected_h1_after_second_ad_expires}'"
    )

    print(f"Ad expiration testing completed.")
