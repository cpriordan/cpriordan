# Network throttling removed from homepage load, added only before final homepage ad view to avoid early timeout

import asyncio
import pytest
import pytest_asyncio
import sys
import os
import time
import shutil
from datetime import datetime
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
    browser
)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "uccustaging", "password": "LoveWYBank2021!"}],
    indirect=True,
)
async def test_barcons_auto_loan_personalization_on(
    browser,
    homepage_url="https://www.stgfinalyticsdemo.com/demo/barcons?api=prod&cb=1&debug_all=1",
    test_scenario_url="https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    expected_heading="Drive Your Dream Car Today",
    hero_heading_selector="body > main > div.layout.c-hero.light > div > div > div > h1",
    hero_class_selector="body > main > div.layout.c-hero.light",
    client="barcons",
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
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)

        # Enable network throttling AFTER initial loads
        client_cdp = await browser.new_cdp_session(page)
        await client_cdp.send('Network.enable')
        await client_cdp.send('Network.emulateNetworkConditions', {
            'offline': False,
            'latency': 150,
            'downloadThroughput': 500 * 1024 / 8,
            'uploadThroughput': 500 * 1024 / 8
        })

        render_start_time = datetime.now()
        nav_timing = await page.evaluate("performance.now()")
        print(f"Render Start Time: {render_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')} (Performance Start: {nav_timing} ms)")

        await wait_for_js_and_element_with_frame_capture(page, hero_class_selector, screenshots_directory)

        render_finish_time = datetime.now()
        render_end_perf = await page.evaluate("performance.now()")

        performance_timings = await page.evaluate('''(() => {
            const nav = performance.getEntriesByType('navigation')[0];
            return {
                domInteractive: nav.domInteractive,
                fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || null,
                loadEventEnd: nav.loadEventEnd
            };
        })()''')

        print(f"Render Finish Time: {render_finish_time.strftime('%Y-%m-%d %H:%M:%S.%f')} (Performance End: {render_end_perf} ms)")
        print(f"Total Render Duration (performance): {(render_end_perf - nav_timing):.2f} ms")
        total_render_duration_sec = (render_finish_time - render_start_time).total_seconds()
        print(f"Total Render Duration (clock): {total_render_duration_sec} seconds")

        print("\n--- Additional Performance Timings ---")
        print(f"DOMInteractive: {performance_timings['domInteractive']} ms")
        print(f"First Contentful Paint (FCP): {performance_timings['fcp']} ms")
        print(f"Load Event End: {performance_timings['loadEventEnd']} ms")

        if total_render_duration_sec > 4:
            pytest.fail(f"Render duration exceeded 4 seconds: {total_render_duration_sec} seconds")

        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of first Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert expected_heading == ad_on_hero_content_h1_normalized, (
            f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{expected_heading}'"
        )

        await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot.png', timeout=60000)

        html_content = await page.content()
        desired_cloudfront_urls = (html_finalytics_stg_cloudfront, html_finalytics_stg_cloudfront2)

        if not any(tag in html_content for tag in desired_cloudfront_urls):
            pytest.fail(
                f"HTML Finalytics STG cloudfront URL '{html_finalytics_stg_cloudfront2}' NOT FOUND in the page source!"
            )
        else:
            print(f"HTML Finalytics STG cloudfront URL '{html_finalytics_stg_cloudfront2}' exists in the homepage source.")

        desired_finalytics_tags = [finalytics_css_tag, finalytics_js_tag, finalytics_function_js_tag,
                                   finalytics_settings_div_js_tag]
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
