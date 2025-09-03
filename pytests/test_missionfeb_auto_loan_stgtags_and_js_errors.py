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

async def emulate_mobile_view_from_existing_session(existing_url, storage_path, screenshots_directory):
    async with async_playwright() as p:
        iphone_12 = p.devices["iPhone 12"]

        browser = await p.chromium.launch(headless=False)

        # Extract only the allowed keys from iphone_12 to avoid passing duplicate arguments
        device_settings = {
            "viewport": iphone_12["viewport"],
            "user_agent": iphone_12["user_agent"],
            "device_scale_factor": iphone_12["device_scale_factor"],
            "is_mobile": iphone_12["is_mobile"],
            "has_touch": iphone_12["has_touch"],
        }

        # Create a mobile context using the storage state
        mobile_context = await browser.new_context(
            **device_settings,
            storage_state=storage_path,
            locale="en-US",
            record_video_dir="videos/"
        )

        mobile_page = await mobile_context.new_page()

        # Navigate directly to the target URL to load the correct state
        await mobile_page.goto(existing_url, timeout=DEFAULT_TIMEOUT)
        await mobile_page.wait_for_load_state('load')

        try:
            local_storage_after = await mobile_page.evaluate("Object.assign({}, window.localStorage)")
            print("[MOBILE CONTEXT] LocalStorage AFTER navigation:", local_storage_after)
        except Exception as e:
            print("[WARNING] Failed to read localStorage AFTER navigation:", e)

        # Optional: dismiss cookie popup in mobile view too
        cookie_dismiss_button = mobile_page.locator('a.cc-btn.cc-dismiss', has_text="Close")
        if await cookie_dismiss_button.count() > 0:
            try:
                await cookie_dismiss_button.wait_for(state="attached", timeout=5000)
                await mobile_page.evaluate("(el) => el.click()", await cookie_dismiss_button.element_handle())
                print("Cookie message dismiss click triggered via JS.")
            except Exception as e:
                print(f"Cookie dismiss element found but could not be clicked: {e}")

        await mobile_page.screenshot(path=f"{screenshots_directory}/mobile_iphone12_emulation.png")
        print(f"Took a mobile screenshot as '{screenshots_directory}/mobile_iphone12_emulation.png'")

        await browser.close()

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "", "password": ""}],
    indirect=True,
)
async def test_missionfeb_autoloan_stgtags_and_js_errors(
    browser,
    homepage_url="https://stage.missionfed.com/?debug_all=1&cb=0",
    test_scenario_url="https://stage.missionfed.com/auto-loans/",
    expected_ad_heading="DRIVE AWAY WITH BETTER RATES.",
    hero_heading_selector="#main > div.new-container > div.hero > div.hero__content > div > div > div",   #main > div.hero > div.hero__content > div > div > div
    expected_ad_title="Your Next Car, No Guesswork.",
    hero_title_selector="#main > div.new-container > div.hero > div.hero__content > div > div > h1",
    client="missionfed",
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
        time.sleep(20)
        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        time.sleep(20)
        # await page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        # await page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        time.sleep(25)
        print(f"Waiting for {hero_heading_selector} on the homepage...")
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')

        # Use a more specific and reliable locator to close the cookie message button
        cookie_dismiss_button = page.locator('a.cc-btn.cc-dismiss', has_text="Close")

        # Check if the element exists and is visible, then click and wait for it to disappear
        if await cookie_dismiss_button.count() > 0:
            await cookie_dismiss_button.wait_for(state="visible")
            await cookie_dismiss_button.click()
            print("Close cookie message button was found and clicked")

            # Wait for it to disappear from the page
            try:
                await cookie_dismiss_button.wait_for(state="detached", timeout=5000)
                print("Cookie message was successfully dismissed.")
            except PlaywrightTimeoutError:
                print("Cookie message was not dismissed after clicking.")
        else:
            print("Close cookie message button not found")

        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=DEFAULT_TIMEOUT)
        # Take a screenshot after the close cookie message button is no longer displayed
        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_desktop_screenshot.png')
        print("Taking screenshot after cookie message was dismissed")

        # Check the heading
        ad_heading = await page.locator(hero_heading_selector).inner_text()
        if expected_ad_heading != ad_heading:
            pytest.fail(f"Ad heading'{ad_heading}' does not match expected heading '{expected_ad_heading}'")
        else:
            print(f"Ad heading {ad_heading}' matches expected heading '{expected_ad_heading}'")

        # Check the title also
        ad_title = await page.locator(hero_title_selector).inner_text()
        if expected_ad_title != ad_title:
            pytest.fail(f"Ad title '{ad_title}' does not match expected title '{expected_ad_title}'")
        else:
            print(f"Ad title '{ad_title}' matches expected title'{expected_ad_title}'")

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

        # Save session from existing desktop context
        await page.context.storage_state(path="storage_state.json")

        # Emulate mobile view with same session + URL
        print(f"Existing page URL is {page.url} and passing the current storage_state.json")
        await emulate_mobile_view_from_existing_session(page.url,"storage_state.json",screenshots_directory)

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
