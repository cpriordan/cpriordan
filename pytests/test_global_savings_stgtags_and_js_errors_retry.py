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
    DEFAULT_CLOUDFRONT_URLS,
    process_test_data_async,
    login_if_redirected)
from playwright.async_api import async_playwright

# Client configuration
client = "glbl"

# Test data configuration
data = [
    # Step 1: Go to homepage (with login)
    "https://globaluat.cms.globalcu.org/?api=stg",
    10,  # Sleep 20 seconds as in original test
    
    # Step 2: Go to credit cards page to trigger personalization
    {
        'url': "https://globaluat.cms.globalcu.org/credit-cards/",
        'expected': {
            'wait_type': 'element',
            'h1__selector': 'h1, .hero h1, .page-title'
        }
    },
    10,  # Sleep 20 seconds as in original test
    
    # Step 3: Return to homepage and validate personalized ad with retry logic
    {
        'url': "https://globaluat.cms.globalcu.org/?api=stg",
        'expected': {
            'h1': "Earn rewards with every purchase",
            'h1__selector': "div.hero-body > h1", 
            'wait_type': "element"
        },
        'validate_finalytics': True  # Validate Finalytics tags on final page
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "gcu", "password": "!gcu/Cmsviewer1$"}],
    indirect=True,
)
async def test_global_savings_stgtags_and_js_errors(
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
    
    # Process the test data with JS and Finalytics validation
    await process_test_data_async(
        page, data, screenshots_directory,
        validate_js=True,
        validate_finalytics=True,
        client=client,
        error_tracker=error_tracker,
        cloudfront_urls=DEFAULT_CLOUDFRONT_URLS,
        username="gcu",
        password="!gcu/Cmsviewer1$"
    )

    print(f"{client} hero ad testing completed.")
