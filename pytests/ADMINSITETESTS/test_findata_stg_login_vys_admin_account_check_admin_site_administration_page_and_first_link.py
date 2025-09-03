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

def test_check_admin_site_administration_page_and_first_link(admin_browser_context_sync):
    """Test admin site administration page access using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = 'screenshots_adminsite_using_pytest/admin_page_check/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page
    login_page = AdminLoginPage(page, is_async=False)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    # Check administration page access
    try:
        # Navigate to Administration section
        admin_link = page.get_by_text("Administration")
        if admin_link.is_visible():
            admin_link.click()
            page.wait_for_load_state("networkidle")
            page.screenshot(path=f'{screenshots_directory}2_administration_section_accessed.png')
            print("Successfully accessed Administration section")
        else:
            print("Administration link not visible for this user type")
            
        # Check first administration link if available
        first_admin_link = page.locator("a").first
        if first_admin_link.is_visible():
            first_admin_link.click()
            page.wait_for_load_state("networkidle")
            page.screenshot(path=f'{screenshots_directory}3_first_admin_link_clicked.png')
            print("Successfully clicked first administration link")
            
        page.screenshot(path=f'{screenshots_directory}4_final_admin_page_state.png')
        print("Admin site administration page test completed successfully")
        
    except Exception as e:
        print(f"Error during administration page test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_admin_page.png')
        raise