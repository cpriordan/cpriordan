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
client = "barcons"

# Test data configuration
data = [
    "https://www.stgfinalyticsdemo.com/demo/barcons?api=stg&cb=1&debug_all=1",
    "https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    {
        'url': "https://www.stgfinalyticsdemo.com/demo/barcons?api=stg&cb=1&debug_all=1",
        'expected': {
            'h1': "Drive Your Dream Car Today",
            'h1__selector': "body > main > div.layout.c-hero.light > div > div > div > h1",
            'wait_type': 'element'
        }
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "uccustaging", "password": "LoveWYBank2021!"}],
    indirect=True,
)
async def test_barcons_auto_loan_personalization_on(
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
