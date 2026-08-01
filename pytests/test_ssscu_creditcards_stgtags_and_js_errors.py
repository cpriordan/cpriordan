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

# Client configuration
client = "ssscu"

# Test data configuration
data = [
    # Use 'load' wait type to avoid networkidle timeout, add debug_all=1&session_init=1 for personalization
    {
        'url': "https://sscustage.wpenginepowered.com/?api=stg&debug_all=1&session_init=1",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://sscustage.wpenginepowered.com/loans-and-credit-cards/credit-cards",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://sscustage.wpenginepowered.com/?api=stg",
        'expected': {
            'h1': "CREDIT CARDS",
            'h1__selector': "h1.eyebrow",
            'wait_type': 'element'
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True,
)
async def test_ssscu_creditcards_stgtags_and_js_errors(
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

    # Refresh homepage 3 times to get past "Best of Vegas" ad to the standard personalization ad
    print("Refreshing homepage 3 times to ensure standard personalization ad displays...")
    homepage_url = data[0]['url']
    await page.goto(homepage_url)
    await page.wait_for_load_state('load')

    for i in range(3):
        print(f"Refreshing homepage (refresh {i+1}/3)...")
        await page.reload()
        await page.wait_for_load_state('load')

    print("Homepage refreshes complete. Proceeding with test data validation...")

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
