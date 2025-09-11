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

def test_findata_login_using_2fa(admin_browser_context_sync):
    """Test 2FA login using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment and authentication using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, screenshots_directory = setup_admin_test_environment('gocu')
    screenshots_directory = 'screenshots_adminsite_using_pytest'
    
    # Clear screenshots directory  
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page
    login_page = AdminLoginPage(page, is_async=False)
    
    # Perform complete login flow using consolidated methods
    login_page.navigate(test_env)
    print(f"Username {findata_user} and password were filled.")
    login_page.login(findata_user, findata_pw)
    
    # Handle 2FA using consolidated method with automatic timing validation
    print("Waiting for 2FA input field...")
    otp_code = login_page.enter_2fa_code(totp)
    
    # Complete login with proper navigation handling
    login_page.complete_2fa_login(test_env)
    
    # Take screenshot and validate using consolidated function
    login_page.take_screenshot(f'{screenshots_directory}/successful_gocu_admin_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    print(f"Successful login is saved in {screenshots_directory}")