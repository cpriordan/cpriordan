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
client = "swfcu"

# Test data configuration
data = [
    {
        'url': "https://statewidefcu24.pixelspoke-staging.com/rv-boat-and-motorcycle-loans/",
        'wait_type': 'load'
    },
    {
        'url': "https://statewidefcu24.pixelspoke-staging.com/",
        'expected': {
            'h1': "Sail to low Rates",
            'h1__selector': "h1",
            'wait_type': "element"
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "statewidefcu", "password": "statewidefcu"}],
    indirect=True,
)
async def test_swfcu_rvboatloan_stgtags_and_js_errors(
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
        cloudfront_urls=cloudfront_urls,
        username="statewidefcu",
        password="statewidefcu"
    )

    print(f"{client} hero ad testing completed.")
