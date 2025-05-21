
import os
import shutil
import time

import pytest
from playwright.sync_api import sync_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv

def clear_screenshots_directory(directory):
    if os.path.exists(directory):
        # Remove all files in the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symbolic link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        # Create the directory if it doesn't exist
        os.makedirs(directory)

# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_GOCU_USER")
findata_pw = os.environ.get("FINDATA_GOCU_PW")
findata_otp = os.environ.get("FINDATA_GOCU_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp:
    raise ValueError("Required environment variables FINDATA_GOCU_USER, FINDATA_GOCU_PW, or FINDATA_GOCU_OTP are not set!")

# Configure TOTP using pyotp
totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")

@pytest.fixture(scope="function")
def browser_context():
    """Fixture to set up and tear down the Playwright browser context."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()

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

