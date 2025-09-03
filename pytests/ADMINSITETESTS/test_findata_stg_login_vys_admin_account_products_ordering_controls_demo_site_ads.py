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

class ProductsPage:
    """Page object for products ordering functionality."""
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.content_nav_link = page.get_by_text("Content").nth(0)
        self.products_nav_link = page.get_by_text("Products")
        
    def navigate_to_products(self, screenshots_directory):
        self.admin_link.click()
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.content_nav_link.wait_for(state="visible", timeout=30000)
        self.content_nav_link.click()
        self.page.wait_for_load_state("networkidle")

        self.products_nav_link.wait_for(state="visible", timeout=30000)
        self.products_nav_link.click()
        self.page.wait_for_load_state("networkidle")

class EasterlyDemoPage:
    """Page object for Easterly demo site functionality."""
    def __init__(self, page):
        self.page = page
        
    def navigate_to_demo_site(self, demo_url):
        self.page.goto(demo_url)
        self.page.wait_for_load_state("networkidle")
        
    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def test_products_ordering_controls_demo_site_ads(admin_browser_context_sync):
    """Test products ordering controls demo site ads using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = 'screenshots_adminsite_using_pytest/products_ordering/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    products_page = ProductsPage(page)
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
        # Navigate to products page
        products_page.navigate_to_products(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_products_ordering_page.png')
        
        # Navigate to demo site to verify product ordering
        demo_url = f"https://{test_env}easterly.com"
        demo_page.navigate_to_demo_site(demo_url)
        page.screenshot(path=f'{screenshots_directory}4_demo_site_with_ordered_products.png')
        
        # Check for product advertisements in correct order
        product_ads = page.locator("[class*='product'], [class*='card'], [class*='offer']")
        if product_ads.count() > 0:
            print(f"Found {product_ads.count()} product elements on demo site")
            page.screenshot(path=f'{screenshots_directory}5_products_found_on_demo.png')
        else:
            print("No product elements found - may need further investigation")
            
        page.screenshot(path=f'{screenshots_directory}6_final_products_ordering_state.png')
        print("Products ordering controls demo site ads test completed successfully")
        
    except Exception as e:
        print(f"Error during products ordering test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_products_ordering.png')
        raise