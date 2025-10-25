import os
import shutil
import pytest
import re
import time
from playwright.sync_api import sync_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv

class LoginPage:
    def __init__(self, page):
        self.page = page

    def navigate(self):
        self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def login(self, username, password):
        self.page.get_by_label("Username:").click()
        self.page.get_by_label("Username:").fill(username)
        # Instead of time.sleep(1), do a short wait_for_timeout if needed
        self.page.wait_for_timeout(300)  # a brief pause to mimic user pause
        self.page.get_by_label("Password").fill(password)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_load_state("networkidle", timeout=60000)

    def enter_2fa_code(self, otp_code):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000) # Ensure the token input field is visible
        # Before filling out the TOTP code, check the remaining time and generate a fresh one if needed
        remaining_time = totp.interval - (int(time.time()) % totp.interval)
        if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
            time.sleep(remaining_time + 1)
        otp_code = totp.now()
        otp_input.fill(otp_code)
        self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")
    def take_screenshot(self, path):
        self.page.screenshot(path=path)


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

def validate_no_server_error(page):
    """
    Validates that the page does not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error ", "Page not found"]
    page_text = page.inner_text("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]

    assert not found_errors, f"Error messages found on the page: {', '.join(found_errors)}"

def check_admin_site_site_administration_page_first_link(page, screenshots_directory):
    print(f'Inside check_admin_site_site_administration_page_first_link function and screenshots directory is {screenshots_directory}')

    # CLICK THE FIRST "ADMIN" link ON TOP OF THE PAGE TO GO TO THE SITE ADMINISTRATION PAGE AS AN ADMIN USER
    link_label = "Admin"  # Replace with the actual label of the link
    # INCREASE TIMEOUT
    page.locator(f"text={link_label}").nth(0).click(timeout=60000)

    # Allow for the page to load completely before checking the links
    page.wait_for_load_state("networkidle", timeout=60000)

    # Find all rows with class starting with "model-"
    locator_of_rows_in_table_of_class_model_on_admin_site_page = "div.app-app.module table tr[class^='model-']"
    rows = page.locator(locator_of_rows_in_table_of_class_model_on_admin_site_page)

    # Locator of the first link on the results table of all the site site administration pages
    locator_of_first_link_on_the_results_table = "#result_list tbody tr:first-child th.field-first_field_display a:last-child"

    for i in range(rows.count()):
        # Click on the <th scope="row"> link of the current row
        row = rows.nth(i)

        # Screenshot count
        screenshot_counter = i + 2

        # Extract and click the link in the <th scope="row">
        link_element = row.locator("th[scope='row'] a")
        if link_element.count() > 0:
            link_text = link_element.inner_text()
            link_href = link_element.get_attribute("href")
            print(f"Clicking link: {link_text} ({link_href}) and URL is https://{test_env}finalyticsdata.com{link_href}")
            link_element.click(timeout=60000)

            # Wait for the next page to load
            page.wait_for_load_state("networkidle", timeout=60000)

            # Check if the next page has a table with id="result_list"
            if page.locator(locator_of_first_link_on_the_results_table).count() > 0:
                # Click the first link in the table
                first_link = page.locator(locator_of_first_link_on_the_results_table).first
                first_link_text = first_link.inner_text()
                first_link_href = first_link.get_attribute("href")
                print(f"Clicking on first link in the table: {first_link_text} on {first_link_href} and URL is https://{test_env}finalyticsdata.com{first_link_href}")
                first_link.click(timeout=60000)

                # Wait for the page to load
                page.wait_for_load_state("networkidle", timeout=60000)

                # Validate the page for no server errors
                validate_no_server_error(page)

                # Take a screenshot
                page.screenshot(path=f"{screenshots_directory}/check_admin_site_administration_page/{screenshot_counter}_screenshot_{link_text}_{first_link_text}.png")

                # Go back to the second-level page
                page.go_back()
                page.wait_for_load_state("networkidle", timeout=60000)

            else:
                print(f"No links found in the table on the {link_text} page.")
                # Go back to the main admin page

            page.go_back()
            page.wait_for_load_state("networkidle", timeout=60000)


# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_VYS_USER")
findata_pw = os.environ.get("FINDATA_VYS_PW")
findata_otp = os.environ.get("FINDATA_VYS_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables FINDATA_TRU_USER, FINDATA_TRU_PW, FINDATA_TRU_OTP or TEST_ENVIRONMENT are not set!")

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


def test_admin_site_site_administration_page_first_link(browser_context):
    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)

    screenshots_directory = 'screenshots_adminsite_using_pytest/check_admin_site_administration_page/'
    # Only clear the screenshots that are being updated by this script
    clear_screenshots_directory(screenshots_directory)

    # Perform login steps
    login_page.navigate()
    login_page.login(findata_user, findata_pw)
    # Wait for the 2FA input field to appear and ensure it's visible
    print(f"Username {findata_user} and password were filled.")

    # Use the login_page method to automatically generate the OTP code and enter it once
    otp_code = generate_otp_code()
    login_page.enter_2fa_code(otp_code)

    print("2FA token automatically generated and entered and about to click the login button")

    # Click the LOGIN button AFTER filling out the TOTP
    page.get_by_role("button", name="Login").click()

    # Take screenshot and verify redirection

    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    # expect(page).to_have_url(f'https://{test_env}finalyticsdata.com')

    # Get the current URL and only verify after the redirection
    current_url = page.url
    print(f"Current URL after login is {current_url} and about to check if equals the expected URL https://{test_env}finalyticsdata.com/.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')
    print(f"Checked that {current_url} is equal the expected URL https://{test_env}finalyticsdata.com/.")
    print(f"Successful login screenshot saved in {screenshots_directory} AND about to call check_admin_site_site_administration_page_first_link.")

    # Take screenshot after login and before checking the links
    page.screenshot(path=f'{screenshots_directory}2_after_successful_login_using_2fa.png')

    # Run the test
    check_admin_site_site_administration_page_first_link(page, screenshots_directory)

    # Take screenshot after done checking links
    page.screenshot(path=f'{screenshots_directory}3_after_checking_all_links.png')


