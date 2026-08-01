import os
import sys
import time
import pytest
from playwright.sync_api import expect

# Add parent directory to path to import qa_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qa_tools import (browser_context, clear_screenshots_directory, 
                      validate_no_server_error, check_link_on_page, 
                      generate_otp_code, setup_environment_variables, LoginPage)

# Setup environment variables
findata_user, findata_pw, findata_otp, test_env, totp = setup_environment_variables(
    "FINDATA_GOCU_USER", "FINDATA_GOCU_PW", "FINDATA_GOCU_OTP"
)


def test_check_basic_admin_account_access(browser_context):
    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)

    screenshots_directory = 'screenshots_adminsite_using_pytest/admin_access/'
    clear_screenshots_directory(screenshots_directory)

    # Perform login steps
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)

    # Wait for the 2FA input field and enter OTP
    print(f"Username {findata_user} and password were filled.")
    print("Waiting for 2FA input field...")
    login_page.enter_2fa_code(totp)

    # Click the login button after filling out the TOTP
    page.get_by_role("button", name="Login").click()

    # Take screenshot and verify redirection
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # After successful login, assert that can't find the "AI Scenario" link and only "Content" link for basic access
    # Check that the "AI Scenarios" link does not exist for a basic user
    ai_scenarios_present = check_link_on_page(page, "AI Scenarios")
    assert not ai_scenarios_present, "AI Scenarios link should not be visible for basic users."

    # Check that the "Content" link exists for basic users
    content_link_present = check_link_on_page(page, "Content")
    assert content_link_present, "Content link should be visible for basic users."

    print("Verified Content link is accessible and AI Scenarios link not accessible for a basic user")

    # Validate no server errors
    validate_no_server_error(page)

    # Assert that not a server error
    page.screenshot(path=f'{screenshots_directory}2_basic_admin_account_accessible_links.png')

