"""
Test TRU Multiproduct - Checking Hero with Card Ads

Version History:
- 2025-11-25: Fixed strict mode violation and selector issues
    - Problem: Generic selector 'div.eyebrow' matched 8 elements across the page:
      1. CHECKING ACCOUNTS (target element)
      2. VISA CREDIT CARDS
      3. MORTGAGE
      4. THIS JUST IN
      5. YOUR NEIGHBORHOOD CREDIT UNION
      6. Budgeting
      7. Buying a House
      8. Fraud
    - Solution: Found working selector pattern from test_tru_rates_page_js_errors.py
    - Changed selector from 'div.eyebrow' to '#primary > section:nth-child(1) > div > div > div.container > div > div > div > div > div.eyebrow'
    - This specific selector uniquely targets the eyebrow div within the hero section only
    - Also changed expected key from 'div' to 'h1' to match qa_tools conventions
    - Changed 'div__selector' to 'h1__selector' for consistency
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
        'url': "https://trustonestage.wpenginepowered.com/checking-and-savings/checking-accounts/?api=stg",
        'wait_type': 'load'
    },
    {
        'url': "https://trustonestage.wpenginepowered.com/?api=stg&session_init=1",
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
