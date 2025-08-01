# Playwright Script for GitHub Actions with JS Error Detection and checking of prod finalytics tags

import asyncio
import os
import shutil
import time
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def clear_old_screenshot_directories(base_dir, client_prefix):
    if not os.path.exists(base_dir):
        return
    for name in os.listdir(base_dir):
        dir_path = os.path.join(base_dir, name)
        if os.path.isdir(dir_path) and name.startswith(f'screenshots_{client_prefix}_'):
            try:
                shutil.rmtree(dir_path)
                print(f"Removed old screenshot directory: {dir_path}")
            except Exception as e:
                print(f"Failed to delete {dir_path}. Reason: {e}")

def save_page_source(page, filepath):
    try:
        html_content = page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker, screenshots_directory):
    def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'

        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)

            screenshot_path = os.path.join(screenshots_directory, f"js_error_{client}.png")
            asyncio.create_task(page.screenshot(path=screenshot_path))
            print(f"Screenshot of JS error saved at {screenshot_path} for client {client}")

    page.on('console', handle_console_message)

async def wait_for_js_and_element(page, selector, timeout=60000):
    try:
        await page.wait_for_function('document.readyState === "complete"', timeout=timeout)
        print("Page fully loaded.")
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        print(f"Element {selector} is visible.")
    except PlaywrightTimeoutError:
        print(f"Timeout waiting for page or element: {selector}")

async def run():
    homepage_url = "https://www.oneazcu.com/"
    test_scenario_url = "https://www.oneazcu.com/business"
    expected_heading = "From startup to level-up."
    hero_heading_selector = "#copyCol > h1"
    client = "oneaz"
    html_finalytics_prod_cloudfront2 = "https://dfy3oyzv6dw2d.cloudfront.net"
    desired_finalytics_tags = [
        "finalytics-function_div.css",
        "finalytics.js",
        "finalytics-function.js",
        "settings_div.js"
    ]
    specific_js_files = [
        'finalytics.js', 'finalytics-function.js', 'settings_div.js',
        'settings.js', 'controlbar.js', 'settings.js?code=oneaz', 'settings.js?code=oneaz:80'
    ]

    base_dir = "PROD"
    clear_old_screenshot_directories(base_dir, client)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshots_directory = os.path.join(base_dir, f'screenshots_{client}_{timestamp}', 'chromium')
    os.makedirs(screenshots_directory, exist_ok=True)
    error_tracker = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(http_credentials={"username": "OneAZ", "password": "pugs r potatoes!3"})
        page = await context.new_page()

        detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, screenshots_directory)

        try:
            print(f"Going to homepage: {homepage_url}")
            await page.goto(homepage_url, timeout=60000)
            await page.wait_for_load_state("load")
            time.sleep(10)
            await page.screenshot(path=f'{screenshots_directory}/homepage_screenshot.png', full_page=True)

            html = await page.content()
            if html_finalytics_prod_cloudfront2 not in html:
                raise Exception(f"Expected cloudfront URL not found: {html_finalytics_prod_cloudfront2}")
            for tag in desired_finalytics_tags:
                if tag not in html:
                    raise Exception(f"Missing tag in page source: {tag}")

            await page.goto(test_scenario_url, timeout=60000)
            await page.wait_for_load_state("load")
            time.sleep(10)
            await page.screenshot(path=f'{screenshots_directory}/product_page_for_ad_screenshot.png', full_page=True)

            await page.goto(homepage_url, timeout=60000)
            await page.wait_for_load_state("load")
            time.sleep(10)
            await page.screenshot(path=f'{screenshots_directory}/homepage_before_selector_screenshot.png', full_page=True)

            await wait_for_js_and_element(page, hero_heading_selector, timeout=60000)
            await page.screenshot(path=f'{screenshots_directory}/hero_ad1_screenshot_on_chromium.png', full_page=True)
            ad_heading = await page.locator(hero_heading_selector).inner_text()

            if expected_heading != ad_heading:
                raise Exception(f"Expected '{expected_heading}', but got '{ad_heading}'")
            else:
                print(f"Ad heading matched: {expected_heading}")

            if error_tracker:
                raise Exception(f"Detected JavaScript errors: {error_tracker}")

        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
