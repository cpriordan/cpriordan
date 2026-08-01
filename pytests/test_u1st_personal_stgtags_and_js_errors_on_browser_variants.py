"""
Test U1st Personal Loans with STG Tags and JS Error Validation

Version History:
- 2025-11-25: Fixed content assertion and added debug parameters
    - Problem: Test was failing due to outdated expected heading and ad campaign changes
      - Initially expected "Big Dreams, Small Payments"
      - Then saw "Pass it on: You Both Earn $50" (referral campaign)
      - Currently showing "Your Holiday Loan Is Here" (holiday campaign)
      - Missing debug_all parameter prevented proper personalization session
      - Simple string URLs were using default 'networkidle' wait type
    - Changes made:
      1. Added debug_all=1&session_init=1 to first URL for proper personalization
      2. Converted all URLs to dictionary format with explicit 'load' wait type
      3. Updated expected h1 heading to "Your Holiday Loan Is Here" (current holiday campaign)
      4. Note: Ad content may change as campaigns are updated
    - Note: Test runs across 4 browsers (chromium, firefox, opera, edge)
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
client = "u1st"

# Test data configuration
data = [
    {
        'url': "https://1stunitedcu.cms.banno-staging.com/?api=stg&debug_all=1&session_init=1",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/personal-loans-and-lines",
        'expected': {
            'wait_type': 'load'
        }
    },
    {
        'url': "https://1stunitedcu.cms.banno-staging.com/?api=stg",
        'expected': {
            'h1': "Your Holiday Loan Is Here",
            'h1__selector': "#slideshow--main > div > div > div > div > div > div > div.hero__slider-content.d-flex.flex-row.align-content-center.justify-start.align-items-center > div > div > div > div > div > div > div > h2",
            'wait_type': 'element'
        },
        'validate_finalytics': True
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [
        {"browser": "chromium", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "firefox", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "opera", "username": "uccustaging", "password": "LoveWYBank2021!"},
        {"browser": "edge", "username": "uccustaging", "password": "LoveWYBank2021!"}
    ],
    indirect=True,
)
async def test_u1st_personal_stgtags_and_js_errors(
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
