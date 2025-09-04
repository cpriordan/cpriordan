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
client = "marketusafcu_personalization_off_company_setting"

# Test data configuration
data = [
    "https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    {
        'url': "https://www.stgfinalyticsdemo.com/demo/marketusafcu?api=stg&cb=1&debug_all=1",
        'expected': {
            'h1': "Banking with the Best",
            'h1__selector': "#test > div > div > div > div > h1",
            'wait_type': "element"
        }
    }
]

@pytest.mark.asyncio
async def test_marketusafcu_auto_loan_personalization_off(
    browser
):
    print(f"Starting {client} hero ad test..")
    print(sys.version)

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = f'screenshots_{client}_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    
    # Process the test data using the new unified function
    await process_test_data_async(page, data, screenshots_directory)

    print(f"{client} hero ad testing completed.")
