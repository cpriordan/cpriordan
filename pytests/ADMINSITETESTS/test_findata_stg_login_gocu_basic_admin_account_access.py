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

def test_check_basic_admin_account_access(admin_browser_context_sync):
    """Test basic admin account access using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment and authentication using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, screenshots_directory = setup_admin_test_environment('gocu')
    screenshots_directory = 'screenshots_adminsite_using_pytest/admin_access/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page
    login_page = AdminLoginPage(page, is_async=False)
    
    # Perform login steps using consolidated methods
    login_page.navigate(test_env)
    print(f"Username {findata_user} and password were filled.")
    login_page.login(findata_user, findata_pw)
    
    # Handle 2FA using consolidated method
    print("Waiting for 2FA input field...")
    otp_code = login_page.enter_2fa_code(totp)
    
    # Complete login with proper navigation handling
    login_page.complete_2fa_login(test_env)
    
    # Take screenshot after successful login
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    
    # Get current URL for logging
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    print(f"Successful login screenshot saved in {screenshots_directory}.")
    
    # Validate login success and check permissions using consolidated function
    expected_permissions = {
        "AI Scenarios": False,  # Should not be visible for basic users
        "Content": True         # Should be visible for basic users
    }
    validate_admin_login_success(page, test_env, expected_permissions)
    
    print("Verified Content link is accessible and AI Scenarios link not accessible for a basic user")
    
    # Final screenshot
    page.screenshot(path=f'{screenshots_directory}2_basic_admin_account_accessible_links.png')