import pytest
import pytest_asyncio
import sys
import os

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    browser,
    DEFAULT_TIMEOUT,
    process_test_data_async)
from playwright.async_api import async_playwright

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

# Client configuration
client = "missionfed"

# Test data configuration
data = [
    {
        'url': "https://stage.missionfed.com/auto-loans/?debug_all=1&cb=0",
        'wait_type': 'load'
    },
    {
        'url': "https://stage.missionfed.com/?debug_all=1&cb=0",
        'expected': {
            'h1': "Your Next Car, No Guesswork.",
            'h1__selector': "h1",
            'div': "DRIVE AWAY WITH BETTER RATES.",
            'div__selector': "div.pre-label",
            'wait_type': 'element'
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "", "password": ""}],
    indirect=True,
)
async def test_missionfeb_autoloan_stgtags_and_js_errors(
    browser
):
    print(f"Starting {client} hero ad test..")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = f'screenshots_{client}_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    
    # Set up JS error tracking
    error_tracker = []
    
    # CloudFront URLs for Finalytics validation (use generic staging URLs)
    cloudfront_urls = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")
    
    # Process the test data with JS and Finalytics validation
    await process_test_data_async(
        page, data, screenshots_directory,
        validate_js=True,
        validate_finalytics=True,
        client=client,
        error_tracker=error_tracker,
        cloudfront_urls=cloudfront_urls
    )

    print(f"{client} hero ad testing completed.")
