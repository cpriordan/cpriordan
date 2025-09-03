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
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

    print(f"About to go to home_url {homepage_url}")

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state("domcontentloaded", timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state("load", timeout=DEFAULT_TIMEOUT)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)
        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png', full_page=True)

        # Save the page source to a file
        page_source_filepath = f'{screenshots_directory}/homepage_source.html'
        await save_page_source_async(page, page_source_filepath)

        # Open the "View Source" page only if not using webkit since not valid URL format for webkit
        view_source_url = f"view-source:{homepage_url}"
        if browser_type != "webkit":
            await page.goto(view_source_url, timeout=DEFAULT_TIMEOUT)
            # Take a screenshot of the "View Source" page
            await page.screenshot(path=f'{screenshots_directory}/homepage_source_screenshot.png')
            print("Screenshot with source code taken for browsers except webkit browser engine used by Safari.")
        else:
            print("Screenshot with source code NOT taken for webkit browser engine used by Safari.")

        # Call detect_js_errors_from_specific_files after navigating to the homepage
        await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)

        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png', full_page=True)

        # Call detect_js_errors_from_specific_files after navigating to the test scenario
        await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_function('document.readyState === "complete"')
        time.sleep(10)

        #INCREASE SLEEP TO CAPTURE SCREENSHOT OF THE CONSOLE WINDOW
        time.sleep(60)

        # ---------------------------------------------
        # CHANGED: Take ONLY the #homeSlider section screenshot and name it hero_ad_only
        # ---------------------------------------------
        print("Waiting for #homeSlider on the homepage...")  # CHANGED
        await wait_for_js_and_element_async(page, "#homeSlider", timeout=DEFAULT_TIMEOUT)  # CHANGED
        await page.wait_for_selector("#homeSlider", state='visible', timeout=DEFAULT_TIMEOUT)  # CHANGED

        # CHANGED: Capture only the targeted section instead of full-page
        await page.locator("#homeSlider").screenshot(  # CHANGED
            path=f'{screenshots_directory}/hero_ad_only.png'  # CHANGED
        )  # CHANGED
        print("Saved hero section screenshot as hero_ad_only.png")  # CHANGED
        # ---------------------------------------------

        # (Optional keep) Validate the text still if desired
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=DEFAULT_TIMEOUT)
        await page.wait_for_selector(hero_heading_selector, state='visible', timeout=DEFAULT_TIMEOUT)
        ad_heading = await page.locator(hero_heading_selector).inner_text()
        # Instead of comparing the heading, compare the images in folder BASELINE/hero_ad_only_baseline.png with the current /hero_ad_only.png using OCR
        if expected_heading != ad_heading:
            pytest.fail(f"Ad heading '{ad_heading}' does not match expected heading '{expected_heading}'")
        else:
            print(f"Ad heading '{ad_heading}' matches expected heading '{expected_heading}'")

        # Call detect_js_errors_from_specific_files after going back to the homepage to view the ad
        await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

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
