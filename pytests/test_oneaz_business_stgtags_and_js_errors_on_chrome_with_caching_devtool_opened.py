"""
Test OneAZ Business Personalization with STG Tags and JS Error Validation

Version History:
- 2025-11-23: Added dismiss_oneaz_alert function to handle site-specific popup alert
    - Added click handler for "#unignorable-alert-close-ae7df19f-9c36-4e33-af69-ce78fef0b061" close button
"""

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


async def dismiss_oneaz_alert(page):
    """Dismiss the OneAZ site-specific alert popup if present."""
    try:
        # Try to find and click the close button for the OneAZ alert
        close_button_selector = "#unignorable-alert-close-ae7df19f-9c36-4e33-af69-ce78fef0b061"
        close_button = page.locator(close_button_selector)
        if await close_button.count() > 0:
            await close_button.click()
            print(f"OneAZ alert dismissed using selector: {close_button_selector}")
        else:
            print("No OneAZ alert found")
    except Exception as e:
        print(f"Error dismissing OneAZ alert: {e}")

# Client configuration
client = "oneaz"

# Test data configuration
data = [
    "https://oneazcuqa.oneazcu.com/?api=stg&session_init=1&debug_all=1",
    "https://oneazcuqa.oneazcu.com/business?api=stg",
    {
        'url': "https://oneazcuqa.oneazcu.com/?api=stg",
        'expected': {
            'h1': "Banking Built for Business Growth",
            'h1__selector': "#copyCol > h1",
            'wait_type': 'element'
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "OneAZ", "password": "pugs r potatoes!3"}],
    indirect=True,
)
async def test_oneaz_stgtags_and_js_errors(
    browser
):
    print(f"Starting {client} hero ad test...")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = f'screenshots_{client}_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    # First, go to the homepage and dismiss the OneAZ alert
    await page.goto("https://oneazcuqa.oneazcu.com/?api=stg")
    await page.wait_for_load_state('load')
    await dismiss_oneaz_alert(page)

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
