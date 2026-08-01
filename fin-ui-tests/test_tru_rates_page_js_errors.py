"""
Test TRU Rates Page with JS Error Validation

Version History:
- 2025-11-25: Fixed networkidle timeout issues
    - Problem: Simple string URLs were using default 'networkidle' wait type which timed out after 30000ms
    - Solution: Converted all URLs to dictionary format with explicit 'load' wait type
    - Added debug_all=1&session_init=1 to first URL for proper personalization
    - Changes:
      1. First URL: Added debug_all=1&session_init=1 parameters with 'load' wait type
      2. Checking accounts URL: Changed from string to dict with 'load' wait type
      3. Rates homeloans URL: Changed from string to dict with 'load' wait type
    - This prevents timeout issues on sites with persistent network connections
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

# Client configuration
client = "tru"

# Test data configuration
data = [
    {
        'url': "https://trustonestage.wpenginepowered.com/?api=stg&debug_all=1&session_init=1",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://trustonestage.wpenginepowered.com/checking-and-savings/checking-accounts/",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://trustonestage.wpenginepowered.com/rates/rates-homeloans",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://trustonestage.wpenginepowered.com/?api=stg",
        'expected': {
            'h1': "CHECKING ACCOUNTS",
            'h1__selector': "#primary > section:nth-child(1) > div > div > div.container > div > div > div > div > div.eyebrow",
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
async def test_tru_mortgage_rates_stgtags_and_js_errors(
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
