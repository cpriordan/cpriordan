
import os
import sys
import time

import pytest
from playwright.sync_api import expect

# Add parent directory to path to import qa_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qa_tools import browser_context, clear_screenshots_directory, setup_environment_variables

# Setup environment variables and authentication
findata_user, findata_pw, findata_otp, test_env, totp = setup_environment_variables(
    "FINDATA_GOCU_USER", "FINDATA_GOCU_PW", "FINDATA_GOCU_OTP"
)

def test_findata_login_using_2fa(browser_context):
    page = browser_context.new_page()

    screenshots_directory = 'screenshots_adminsite_using_pytest'
    clear_screenshots_directory(screenshots_directory)

    # Navigate to data site and perform login
    page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')
    page.get_by_label("Username:").click()
    page.get_by_label("Username:").fill(findata_user)
    # Add delay to mimic user interaction
    time.sleep(1)
    page.get_by_label("Password").fill(findata_pw)
    time.sleep(1)
    page.get_by_role("button", name="Login").click()
    time.sleep(2)  # Allow the page to process login

    # Wait for the 2FA input field to appear and ensure it's visible
    print(f"Username {findata_user} and password were filled.")
    print("Waiting for 2FA input field...")
    page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
    time.sleep(1)
    otp_input = page.locator('#id_token-otp_token')
    time.sleep(1)
    otp_input.wait_for(state="visible", timeout=30000)  # Ensure the field is visible
    print("2FA input field is visible.")
    #otp_input.wait_for(state="enabled", timeout=30000) # Ensure the field is enabled but there not be an enabled state so added a delay

    # Fill the TOTP code into the 2FA input field
    ## otp_input.fill(totp.now())

    # Before filling out the TOTP code, check the remaining time and generate a fresh one if needed
    remaining_time = totp.interval - (int(time.time()) % totp.interval)
    if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
        time.sleep(remaining_time + 1)
    otp_code = totp.now()
    otp_input.fill(otp_code)
    print(f"OTP code {otp_code} entered.")

    # Click the login button after filling out the TOTP
    page.get_by_role("button", name="Login").click()

    # Take screenshot and verify that the user is redirected to the admin home page
    page.screenshot(path=f'{screenshots_directory}/successful_gocu_admin_login_using_2fa.png')
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login is saved in {screenshots_directory}")

