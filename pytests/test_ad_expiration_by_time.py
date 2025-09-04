import pytest
import pytest_asyncio
import sys
import os

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    browser_no_auth,
    DEFAULT_TIMEOUT,
    process_test_data_async)
from playwright.async_api import async_playwright

# Test data configuration
data = [
    "https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    {
        'url': "https://www.stgfinalyticsdemo.com/qa/expire/30seconds",
        'expected': {
            'h1': "Car Loan Ad 2 that expires 30 seconds after session starts",
            'h1__selector': '.col-md-8 > h1:nth-child(1)',
            'wait_type': 'element'
        }
    },
    {
        'url': "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1449&age__minutes=1",
        'expected': {
            'h1': "Car Loan Ad 1 that expires 30 seconds after session starts",
            'h1__selector': '.col-md-8 > h1:nth-child(1)',
            'wait_type': 'element'
        }
    },
    {
        'url': "https://www.stgfinalyticsdemo.com/qa/expire/30seconds?ad_ids=1460&age__minutes=1",
        'expected': {
            'h1': "Banking with the Best",
            'h1__selector': '.col-md-8 > h1:nth-child(1)',
            'wait_type': 'element'
        }
    }
]

@pytest.mark.asyncio
async def test_check_ad_expiration_by_time(
    browser_no_auth
):
    print("Starting ad expiration testing...")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = 'screenshots_ad_expiration_by_time_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser_no_auth.new_page()
    
    # Process the test data using the new unified function
    await process_test_data_async(page, data, screenshots_directory)

    print(f"Ad expiration testing completed.")