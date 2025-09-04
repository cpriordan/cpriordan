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
client = "tru"

# Test data configuration
data = [
    {
        'url': "https://trustonestage.wpenginepowered.com/checking-and-savings/checking-accounts/?api=stg",
        'wait_type': 'load'
    },
    {
        'url': "https://trustonestage.wpenginepowered.com/?api=stg&session_init=1",
        'expected': {
            'div': "CHECKING ACCOUNTS",
            'div__selector': "div.eyebrow",
            'wait_type': 'element'
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "trustonestage", "password": "TruStone2024!!"}],
    indirect=True,
)
async def test_tru_multiproduct_two_card_ads_no_js_errors(
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
    
    # Process the test data with JS and Finalytics validation (no screenshots to avoid font timeout)
    await process_test_data_async(
        page, data, screenshots_directory,
        screenshots=True,
        validate_js=True,
        validate_finalytics=True,
        client=client,
        error_tracker=error_tracker,
        cloudfront_urls=cloudfront_urls,
        username="trustonestage",
        password="TruStone2024!!"
    )

    print(f"{client} hero ad testing completed.")
