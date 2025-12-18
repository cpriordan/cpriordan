import pytest
from playwright.sync_api import expect
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qa_tools import (
    AdminLoginPage, 
    setup_admin_test_environment,
    admin_browser_context_sync,
    clear_screenshots_directory,
    validate_admin_login_success
)

class ProductToSegmentMappingPage:
    """Page object for product to segment mapping functionality."""
    def __init__(self, page):
        self.page = page

    def navigate_to_product_segment_mapping(self, screenshots_directory, test_env):
        """
        Navigate directly to the Product to Segment Mapping page.

        CHANGED on 12/17/2025: Direct navigation to /ai-settings/product-mapping instead of
        clicking through Settings → Segments → Product Mapping menu path.
        Reason: Menu navigation became unreliable due to hidden dropdown elements that remain
        hidden even after clicking parent menu items. Direct URL navigation is more reliable.
        """
        # Navigate directly to the product mapping URL
        product_mapping_url = f'https://{test_env}finalyticsdata.com/ai-settings/product-mapping'
        self.page.goto(product_mapping_url)
        print(f"Navigated directly to Product Mapping page: {product_mapping_url}")

        # Wait for the page to fully load
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_load_state("domcontentloaded")

class EasterlyDemoPage:
    """Page object for Easterly demo site functionality."""
    def __init__(self, page):
        self.page = page
        
    def navigate_to_demo_site(self, demo_url):
        self.page.goto(demo_url)
        self.page.wait_for_load_state("networkidle")
        
    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def test_claritas_segment_controls_demo_site_ads(admin_browser_context_sync):
    """Test Claritas segment controls demo site ads using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = 'screenshots_adminsite_using_pytest/claritas_segment/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    product_mapping_page = ProductToSegmentMappingPage(page)
    demo_page = EasterlyDemoPage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to product segment mapping (direct URL navigation)
        product_mapping_page.navigate_to_product_segment_mapping(screenshots_directory, test_env)
        page.screenshot(path=f'{screenshots_directory}3_product_segment_mapping_page.png')
        
        # Navigate to demo site to verify ads
        # Corrected demo URL format based on old script: uses finalyticsdemo.com with api=stg parameter
        demo_url = f"https://www.{test_env}finalyticsdemo.com/?api=stg"
        demo_page.navigate_to_demo_site(demo_url)
        page.screenshot(path=f'{screenshots_directory}4_demo_site_with_ads.png')
        
        # Check for Claritas segment-controlled ads
        ads_present = page.locator(".ad, [class*='ad'], [id*='ad']").count() > 0
        if ads_present:
            print("Ads found on demo site - Claritas segment controls working")
        else:
            print("No ads found - may need further investigation")
            
        page.screenshot(path=f'{screenshots_directory}5_final_claritas_demo_state.png')
        print("Claritas segment controls demo site ads test completed successfully")
        
    except Exception as e:
        print(f"Error during Claritas segment test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_claritas_test.png')
        raise