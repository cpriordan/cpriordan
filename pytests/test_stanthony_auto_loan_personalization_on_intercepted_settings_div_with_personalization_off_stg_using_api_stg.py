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

async def save_page_source(page, filepath):
    try:
        html_content = await page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
    async def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'

        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)

            screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot of JS error saved at {screenshot_path}")

    page.on('console', lambda msg: asyncio.ensure_future(handle_console_message(msg)))

@pytest_asyncio.fixture
async def browser(request):
    username = request.param.get("username")
    password = request.param.get("password")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])
        context = await browser.new_context(http_credentials={"username": username, "password": password})
        context.set_default_timeout(40000)
        yield context
        await browser.close()

async def wait_for_js_and_element_with_frame_capture(page, selector, screenshots_directory):
    from datetime import datetime
    import os
    import io
    from PIL import Image

    await page.wait_for_selector(selector, state='attached', timeout=15000)

    # Scroll to element to trigger potential lazy load
    await page.locator(selector).scroll_into_view_if_needed()

    # Disable only cache headers and keep stylesheets and images to avoid flickering
    await page.route("**/*", lambda route: route.continue_())
    await page.evaluate("""
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names)
                    caches.delete(name);
            });
        }
    """)

    print("Capturing key render phase screenshots...")

    try:
        # BEFORE FCP
        await page.wait_for_timeout(500)  # wait a bit before FCP
        buffer = await page.locator(selector).screenshot()
        with open(os.path.join(screenshots_directory, "render_before_fcp.png"), "wb") as f:
            f.write(buffer)

        # DURING FCP
        await page.wait_for_timeout(700)  # target window of FCP
        buffer = await page.locator(selector).screenshot()
        with open(os.path.join(screenshots_directory, "render_during_fcp.png"), "wb") as f:
            f.write(buffer)

        # AFTER full render (wait until selector stable or delay)
        await page.wait_for_timeout(3000)
        buffer = await page.locator(selector).screenshot()
        with open(os.path.join(screenshots_directory, "render_after_complete.png"), "wb") as f:
            f.write(buffer)

    except Exception as e:
        print(f"Error during selective render capture: {e}")
# async def wait_for_js_and_element_with_frame_capture(page, selector, screenshots_directory):
#     from datetime import datetime
#     import os
#     import io
#     from PIL import Image, ImageChops
#
#     await page.wait_for_selector(selector, state='attached', timeout=15000)
#
#     # Scroll to element to trigger potential lazy load
#     await page.locator(selector).scroll_into_view_if_needed()
#
#     # Fully disable caching and force rerender
#     await page.route("**/*", lambda route: route.continue_())
#     await page.evaluate("""
#         if ('caches' in window) {
#             caches.keys().then(function(names) {
#                 for (let name of names)
#                     caches.delete(name);
#             });
#         }
#     """)
#
#     print("Capturing frame-by-frame screenshots before, during, and after selector is rendered...")
#
#     frame_index = 0
#     start = datetime.now()
#     captured_frames = []
#     last_image = None
#
#     # Schedule next capture using efficient timestamps
#     end_time = start.timestamp() + 3  # Reduce max capture to 3s to minimize test impact
#     aggressive_phase = start.timestamp() + 1.5
#
#     while datetime.now().timestamp() < end_time:
#         now = datetime.now().timestamp()
#         try:
#             buffer = await page.locator(selector).screenshot(type='png')
#             current_image = Image.open(io.BytesIO(buffer))
#
#             if last_image is None or ImageChops.difference(current_image, last_image).getbbox():
#                 filename = f"frame_{frame_index:03}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
#                 path = os.path.join(screenshots_directory, filename)
#                 with open(path, "wb") as f:
#                     f.write(buffer)
#                 captured_frames.append(path)
#                 frame_index += 1
#                 last_image = current_image
#
#             # Avoid blocking render thread, back off slightly
#             await page.wait_for_timeout(60 if now < aggressive_phase else 120)
#         except Exception as e:
#             print(f"Frame capture error: {e}")
#             break
#
#     print(f"Captured {len(captured_frames)} distinct frames.")

async def wait_for_js_and_element_with_frame_capture(page, selector, screenshots_directory):
    from datetime import datetime
    import os
    import io
    from PIL import Image, ImageChops

    try:
        # Try to wait for selector with both 'attached' and 'visible' states
        await page.wait_for_selector(selector, state='visible', timeout=15000)
    except PlaywrightTimeoutError:
        # If selector is not visible, attempt fallback wait for 'attached'
        print(f"WARNING: Selector {selector} not visible after 15s, retrying with 'attached' state.")
        await page.wait_for_selector(selector, state='attached', timeout=5000)

    await page.locator(selector).scroll_into_view_if_needed()

    # Fully disable caching and force rerender
    await page.route("**/*", lambda route: route.continue_())
    await page.evaluate("""
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names)
                    caches.delete(name);
            });
        }
    """)

    print("Capturing frame-by-frame screenshots before, during, and after selector is rendered...")

    frame_index = 0
    start = datetime.now()
    captured_frames = []
    last_image = None

    # Schedule next capture using efficient timestamps
    end_time = start.timestamp() + 3  # Reduce max capture to 3s to minimize test impact
    aggressive_phase = start.timestamp() + 1.5

    while datetime.now().timestamp() < end_time:
        now = datetime.now().timestamp()
        try:
            buffer = await page.locator(selector).screenshot(type='png')
            current_image = Image.open(io.BytesIO(buffer))

            if last_image is None or ImageChops.difference(current_image, last_image).getbbox():
                filename = f"frame_{frame_index:03}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
                path = os.path.join(screenshots_directory, filename)
                with open(path, "wb") as f:
                    f.write(buffer)
                captured_frames.append(path)
                frame_index += 1
                last_image = current_image

            await page.wait_for_timeout(60 if now < aggressive_phase else 120)
        except Exception as e:
            print(f"Frame capture error: {e}")
            break

    print(f"Captured {len(captured_frames)} distinct frames.")

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "uccustaging", "password": "LoveWYBank2021!"}],
    indirect=True,
)
async def test_marketusafcu_auto_loan_personalization_off(
    browser,
    homepage_url="https://www.stgfinalyticsdemo.com/demo/stantcu?api=stg&cb=1&debug_all=1",
    test_scenario_url="https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    expected_heading="Banking with the Best", # Default heading
    hero_heading_selector="#test > div > div > div > div > h1",  # PERSONALIZATION WILL BE OFF IF window.personalization is false in settings so use different locators
    hero_class_selector="#test > div > div > div", # PERSONALIZATION WILL BE OFF IF window.personalization is false in settings so use different locators#
    client="stantcu_personalization_on_settings_div_personaliztion_off_ad_not_displayed",
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

    # Intercept settings_div.js so can route to a different settings_div.js that was modified to have window.personalization=false
    async def intercept_settings_div_js(route, request):
        target_url = "https://d1v4vw9mwf7wyh.cloudfront.net/v3/stantcu/settings_div.js"
        redirect_url = "https://d1v4vw9mwf7wyh.cloudfront.net/v3/stantcu/personalization_disabled/settings_div.js"

        if request.url == target_url:
            print(f"Intercepted {target_url} — redirecting to personalization_disabled version.")
            await route.continue_(url=redirect_url)
        else:
            print(f"Did not intercept: {request.url}")
            await route.continue_()

    await page.route("**/settings_div.js", intercept_settings_div_js)

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        # Capture screenshot only after selector is visible to prevent blank page
        # await page.wait_for_selector(hero_class_selector, timeout=15000)
        # await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')

        # Capture screenshot only after selector is visible to prevent blank page
        try:
            await page.wait_for_selector("body", timeout=10000)  # ensure main body loads
            if await page.locator(hero_class_selector).is_visible():
                await page.wait_for_selector(hero_class_selector, timeout=10000)
            else:
                print(f"WARNING: {hero_class_selector} not visible after 10s, capturing fallback screenshot.")
            await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png')
        except PlaywrightTimeoutError:
            await save_page_source(page, os.path.join(screenshots_directory, "page_source_timeout.html"))
            await page.screenshot(path=f'{screenshots_directory}/selector_timeout_fallback_screenshot.png')
            pytest.fail(f"Timeout waiting for hero_class_selector: {hero_class_selector}")

        print(f"Returning to homepage_url {homepage_url} to check that the ad is NOT displayed since personalization is disabled for MarketUSA FCU")
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
        # if error_tracker:
        #     pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        if error_tracker:
            page_source_path = os.path.join(screenshots_directory, "js_error_page_source.html")
            html_content = await page.content()
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved HTML at time of JS error to {page_source_path}")

            # Optionally log the JS error visibly in the browser itself
            await page.evaluate("console.error('Test Script JS Error:', arguments[0])", error_tracker[0])
            await page.screenshot(path=os.path.join(screenshots_directory, "js_error_with_console_overlay.png"))
            # CHECK IF SHOULD FAIL THE TEST
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
