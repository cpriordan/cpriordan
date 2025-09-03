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

class ZipCodePage:
    """Page object for zip code and geo branch functionality."""
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.zip_codes_nav_link = page.get_by_text("Zip Codes")
        self.add_zip_code_button = page.get_by_text("Add Zip Code")
        self.zip_code_input = page.locator("#id_zip_code")
        self.branch_name_input = page.locator("#id_branch_name")
        self.save_button = page.get_by_role("button", name="Save")
        
    def navigate_to_zip_codes(self, screenshots_directory):
        self.admin_link.click()
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.zip_codes_nav_link.wait_for(state="visible", timeout=30000)
        self.zip_codes_nav_link.click()
        self.page.wait_for_load_state("networkidle")

    def create_new_geo_branch(self, zip_code, branch_name):
        self.add_zip_code_button.click()
        self.page.wait_for_load_state("networkidle")
        
        self.zip_code_input.fill(zip_code)
        self.branch_name_input.fill(branch_name)
        self.save_button.click()
        self.page.wait_for_load_state("networkidle")

def test_create_a_new_geo_branch(admin_browser_context_sync):
    """Test creating a new geo branch using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/create_geo_branch/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    zip_code_page = ZipCodePage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to zip codes
        zip_code_page.navigate_to_zip_codes(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_zip_codes_page.png')
        
        # Create new geo branch
        test_zip = "90210"
        test_branch = "Test Branch Beverly Hills"
        zip_code_page.create_new_geo_branch(test_zip, test_branch)
        page.screenshot(path=f'{screenshots_directory}4_geo_branch_created.png')
        
        print(f"Successfully created geo branch: {test_branch} for zip {test_zip}")
        page.screenshot(path=f'{screenshots_directory}5_final_geo_branch_state.png')
        
    except Exception as e:
        print(f"Error during geo branch creation test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_geo_branch_creation.png')
        raise