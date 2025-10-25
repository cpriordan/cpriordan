import os
import shutil
import pytest
import time
from playwright.sync_api import sync_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv

class LoginPage:
    def __init__(self, page):
        self.page = page

    def navigate(self):
        # self.page.goto("https://stgfinalyticsdata.com/account/login/?next=/")
        self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def login(self, username, password):
        self.page.get_by_label("Username:").click()
        self.page.get_by_label("Username:").fill(username)
        # Instead of time.sleep(1), do a short wait_for_timeout if needed
        self.page.wait_for_timeout(300)  # a brief pause to mimic user pause
        self.page.get_by_label("Password").fill(password)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_load_state("networkidle")

    def enter_2fa_code(self, otp_code):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        otp_input.fill(otp_code)
        self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")

    def retry_login_with_new_token(self):
        for attempt in range(2):  # Attempt login up to 2 times
            try:
                otp_code = generate_otp_code()
                print(f"Attempt {attempt + 1}: Entering OTP code {otp_code}.")
                self.enter_2fa_code(otp_code)
                # Check if login was successful by verifying the URL
                if f'https://{test_env}finalyticsdata.com/admin/' in self.page.url:
                    print("Login successful.")
                    return
            except Exception as e:
                print(f"Login attempt {attempt + 1} failed: {e}")

        raise Exception("Failed to login after multiple attempts.")

    def manually_enter_2fa_code(self):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        # Instead of automatically filling out the OTP code, manually enter as a temporary workaround
        # otp_input.fill(otp_code)
        # Temporarily let user type in code. This forces a 10-second manual wait
        self.page.wait_for_timeout(10000)
        print(f"OTP code entered.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def check_link_on_page(page, link_text, link_href=None):
    """Helper function to check if a specific link exists on the page."""
    if link_href:
        link = page.locator(f"a[href='{link_href}']")
    else:
        link = page.locator(f"text='{link_text}'")
    return link.count() > 0

def clear_screenshots_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(directory)

# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_GOCU_USER")
findata_pw = os.environ.get("FINDATA_GOCU_PW")
findata_otp = os.environ.get("FINDATA_GOCU_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables FINDATA_GOCU_USER, FINDATA_GOCU_PW, FINDATA_GOCU_OTP or TEST_ENVIRONMENT are not set!")

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


def generate_otp_code():
    import time
    remaining_time = totp.interval - (int(time.time()) % totp.interval)
    if remaining_time < 5:
        # short pause so the token rolls over
        # from playwright.sync_api import sync_playwright
        time.sleep(remaining_time + 1)
    return totp.now()


def test_check_basic_admin_account_access(browser_context):
    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)

    screenshots_directory = 'screenshots_adminsite_using_pytest/admin_access/'
    clear_screenshots_directory(screenshots_directory)

    # Perform login steps
    login_page.navigate()
    login_page.login(findata_user, findata_pw)


    # Wait for the 2FA input field to appear and ensure it's visible
    print(f"Username {findata_user} and password were filled.")
    print("Waiting for 2FA input field...")
    page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
    time.sleep(1)
    otp_input = page.locator('#id_token-otp_token')
    time.sleep(1)
    otp_input.wait_for(state="visible", timeout=30000)  # Ensure the field is visible
    print("2FA input field is visible.")

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


    # Take screenshot and verify redirection
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    # expect(page).to_have_url("https://stgfinalyticsdata.com/admin/")
    # Get the current URL
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

    # Only fail and display the message if these keywords are found in the page
    error_keywords = ["Server Error", "(500)", "error"]

    # Grab the entire page text. You can also specify a particular selector, e.g., "body" or "html".
    page_text = page.text_content("body")

    # Build a list of all error strings that actually appear in page_text
    found_errors = [msg for msg in error_keywords if msg in page_text]

    # If found_errors is not empty, raise an assertion with the joined error messages
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)

    # Assert that not a server error
    page.screenshot(path=f'{screenshots_directory}2_basic_admin_account_accessible_links.png')

