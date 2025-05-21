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
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_load_state("networkidle")

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

class ConnectToACampaign:
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        # TEMPORARILY CHANGED TO SCENARIOS FOR TESTS TO EXECUTE
        self.ai_scenarios_link = page.get_by_text("Scenarios").nth(0)
        # self.ai_scenarios_link = page.get_by_text("AI Scenarios")
        self.create_new_scenarios_link = page.get_by_text("Create New Scenario")
        self.connect_to_a_campaign_link = page.get_by_text("Connect to an External/Paid Campaign")
        self.single_campaign_url_link = page.get_by_text("Single Campaign URL")
        self.easterly_company_link = page.locator('a[dd="vys"]').first
        self.continue_button = page.get_by_text("Continue")

    def navigate_to_utm_campaign_connector(self):
        self.admin_link.click()
        self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        self.ai_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.create_new_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.connect_to_a_campaign_link.click()
        self.page.wait_for_load_state("networkidle")
        # No need to company if using trustone account
        # self.easterly_company_link.wait_for(state="visible", timeout=30000)
        # self.easterly_company_link.click()
        self.single_campaign_url_link.click()
        self.page.wait_for_load_state("networkidle")
        return UTMCampaignConnectorPage(self.page)

    def click_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class UTMCampaignConnectorPage:
    def __init__(self, page):
        self.page = page
        self.continue_button = page.get_by_text("Continue")
    def click_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.continue_button.click()
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

def check_url_pattern(page, base_url, param_patterns):
    """
    Checks if the current URL of the page matches the base URL pattern with optional parameters.
    Args:
        page: The Playwright page object.
        base_url: The base URL pattern (without optional parameters).
        param_patterns: A dictionary where keys are parameter names and values are regular expressions for their values (or None for optional parameters).
    Returns:
        True if the pattern matches the URL, False otherwise.
    """
    current_url = page.url
    url_parts = current_url.split("?")

    if len(url_parts) != 2 or url_parts[0] != base_url:
        return False

    params = url_parts[1].split("&")
    for param in params:
        param_name, value = param.split("=")
        if param_name not in param_patterns:
            return False
        pattern = param_patterns[param_name]
        if pattern and not re.match(pattern, value):
            return False
    return True

# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_TRU_USER")
findata_pw = os.environ.get("FINDATA_TRU_PW")
findata_otp = os.environ.get("FINDATA_TRU_OTP")
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


def test_connect_to_a_campaign(browser_context):
    # Define the product, segment and base URL, parameter patterns
    product_menu_option_to_select = "adjustable rate mortgage"
    segment_menu_option_to_select = "female"
    product_menu_option_regex = product_menu_option_to_select.replace(" ", "(?: |%20)")
    segment_menu_option_regex = segment_menu_option_to_select.replace(" ", "(?: |%20)")
    base_url = f'https://{test_env}finalyticsdata.com/scenarios/campaign-url'
    param_patterns = {
        "utm_fin": fr"^{product_menu_option_regex}$",       # Matches only the value of product_menu_option_to_select as regex
        "utm_segments": fr"^{segment_menu_option_regex}$"   # Matches only the value of segment_menu_option_to_select as regex
    }
    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)
    connect_to_a_campaign_page = ConnectToACampaign(page)
    paid_external_utm_campaign_connector_page = UTMCampaignConnectorPage(page)

    # Only clear the directory that is being used by this script
    screenshots_directory = 'screenshots_adminsite_using_pytest/connect_to_a_campaign/'
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
    # expect(page).to_have_url("https://stgfinalyticsdata.com/admin/")
    # Get the current URL
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # Actions post-login
    paid_external_utm_campaign_connector_page = connect_to_a_campaign_page.navigate_to_utm_campaign_connector()

    # Wait for PRODUCTS menu options to fully load
    page.wait_for_selector("#select2-product-container")
    paid_external_utm_campaign_connector_page.take_screenshot(f'{screenshots_directory}2_paid_external_utm_campaign_connector_page_while_waiting_for_products_menu_to_load.png')

    # Select adjustable rate mortgage product
    # page.select_option("#select2-product-container", label=product_menu_option_to_select)

    # 1. Click the pseudo-dropdown to expand products options
    page.click("#select2-product-container")

    # 2. Locate the option in the dropdown that has the text matching product_menu_option_to_select
    page.locator("li.select2-results__option", has_text=product_menu_option_to_select).click()
    print(f"Selected product menu option: {product_menu_option_to_select}")

    # selected_menu_option = page.locator("#select2-product-container").input_value()
    # print(f"Selected menu option is : {selected_menu_option}")

    paid_external_utm_campaign_connector_page.take_screenshot(f'{screenshots_directory}3_paid_external_utm_campaign_connector_page_after_clicked_products_dropdown_menu.png')

    # Wait for SEGMENTS menu options to fully load
    page.wait_for_selector("#select2-segment-container")
    paid_external_utm_campaign_connector_page.take_screenshot(f'{screenshots_directory}4_paid_external_utm_campaign_connector_page_while_waiting_for_segments_menu_to_load.png')

    # Select female segment
    # page.select_option("#select2-segment-container", label=segment_menu_option_to_select)

    # 1. Click the pseudo-dropdown to expand segments options
    page.click("#select2-segment-container")

    # 2. Locate the option in the dropdown that has the text matching segment_menu_option_to_select
    page.locator("li.select2-results__option", has_text=segment_menu_option_to_select).click()
    print(f"Selected segment menu option: {segment_menu_option_to_select}")

    # selected_menu_option = page.locator("#select2-segment-container").input_value()
    # print(f"Selected menu option is : {selected_menu_option}")
    paid_external_utm_campaign_connector_page.take_screenshot(f'{screenshots_directory}5_paid_external_utm_campaign_connector_page_after_clicked_products_dropdown_menu.png')

    # Click continue button
    paid_external_utm_campaign_connector_page.click_continue_button()

    # Get the current URL
    current_url = page.url
    print(f"Current URL after connect to a campaign is {current_url}.")

    # Check if the URL matches the pattern
    if check_url_pattern(page, base_url, param_patterns):
        print("Connect to a campaign URL matches the expected pattern.")
    else:
        print("Connect to a campaign URL does not match the expected pattern.")

    # Only fail and display the message if these keywords are found in the page
    error_keywords = ["Server Error", "(500)", "error"]

    # Grab the entire page text. You can also specify a particular selector, e.g., "body" or "html".
    page_text = page.text_content("body")

    # Build a list of all error strings that actually appear in page_text
    found_errors = [msg for msg in error_keywords if msg in page_text]

    # If found_errors is not empty, raise an assertion with the joined error messages
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)

    # Assert that not a server error
    paid_external_utm_campaign_connector_page.take_screenshot(f'{screenshots_directory}6_connect_to_a_campaign_result.png')




