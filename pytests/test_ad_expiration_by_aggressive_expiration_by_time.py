import asyncio
import pytest
import pytest_asyncio
import sys
import os
import shutil
from playwright.async_api import async_playwright

def clear_screenshots_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(directory)

@pytest_asyncio.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()

async def wait_for_js_and_element(page, hero_selector, timeout=40000):
    await page.evaluate('''
        new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });
    ''')
    await page.wait_for_function(
        f'document.querySelector("{hero_selector}") !== null && document.querySelector("{hero_selector}").offsetHeight > 0',
        timeout=timeout
    )

@pytest.mark.asyncio
async def test_ad_expiration_by_aggressive_expiration_by_time(
    browser,
    homepage_url="https://www.stgfinalyticsdemo.com/",
    test_scenario_url="https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    page_qa_expires_aggressively_url="https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire",
    page_qa_expires_aggressively_url_by_time="https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire?expire__aggressive=1&age__views=1&age__minutes=5",
    hero_selector=".c-hero"
):
    print("Starting ad expiration testing...")
    print(sys.version)

    screenshots_directory = 'screenshots_aggressive_expiration_by_time_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    await page.goto(homepage_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}1_homepage_screenshot.png')

    await page.goto(test_scenario_url)
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}2_page_for_ad_screenshot.png')

    # --- NEW: Listen for getads to determine first_ad_id ---
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

    await page.goto(page_qa_expires_aggressively_url)
    await page.wait_for_load_state('networkidle')

    # Wait for ad_id capture
    max_wait_time = 10
    elapsed = 0
    while first_ad_id is None and elapsed < max_wait_time:
        await asyncio.sleep(0.5)
        elapsed += 0.5
    if first_ad_id is None:
        raise TimeoutError("Timed out waiting for first_ad_id from getads API")

    # Decide dynamic expected headings based on ad_id
    if first_ad_id == 1348:
        dynamic_expected_h1_for_first_ad = "Car Loan Ad 1 that uses aggressive expire"
        dynamic_expected_h1_after_aggressive_expiration_by_time = "Banking with the Best"
    elif first_ad_id == 1349:
        dynamic_expected_h1_for_first_ad = "Car Loan Ad 2 that uses aggressive expire"
        dynamic_expected_h1_after_aggressive_expiration_by_time = "Banking with the Best"
    else:
        raise ValueError(f"Unexpected ad_id returned: {first_ad_id}")

    await wait_for_js_and_element(page, hero_selector)
    ad_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}3_hero_ad1_screenshot.png')
    assert dynamic_expected_h1_for_first_ad == ad_on_hero_content_h1

    # Expire aggressively by time
    await page.goto(page_qa_expires_aggressively_url_by_time)
    await page.wait_for_load_state('networkidle')
    await wait_for_js_and_element(page, hero_selector)
    ad2_on_hero_content_h1 = await page.locator('.col-md-8 > h1:nth-child(1)').inner_text()
    print(f"---> Heading after aggressive expiration is *** {ad2_on_hero_content_h1} ***")
    await page.screenshot(path=f'{screenshots_directory}4_hero_reloaded_after_aging_first_ad.png')
    assert dynamic_expected_h1_after_aggressive_expiration_by_time == ad2_on_hero_content_h1

    print("Ad expiration testing completed.")
