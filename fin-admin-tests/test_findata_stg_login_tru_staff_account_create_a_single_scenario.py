import os
import shutil
import pytest
import time
import re
import urllib.parse
from playwright.sync_api import sync_playwright, expect
from playwright.async_api import async_playwright
from pyotp import TOTP
from dotenv import load_dotenv
from datetime import datetime


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
        # Instead of automatically filling out the OTP code, manually enter as a temporary workaround and force a 10-second manual wait
        self.page.wait_for_timeout(10000)
        print(f"OTP code entered.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class CreateASingleScenarioPage:
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        # self.ai_scenarios_link = page.get_by_text("AI Scenarios")
        self.ai_scenarios_link = page.get_by_text("Scenarios").nth(0)
        self.create_new_scenarios_link = page.get_by_text("Create New Scenario")
        self.create_a_scenario_link = page.get_by_text("Create a Scenario")
        self.target_a_product_link = page.get_by_text("Target a Product").nth(0) # first instance
        self.easterly_company_link = page.locator('a[dd="vys"]').first
        self.continue_button = page.get_by_text("Continue")
        self.auto_loan_scenario_type_link = page.get_by_text("Auto Loan")
        self.home_hero_template_link = page.get_by_text("Trustone Financial | home hero")

    def navigate_to_input_scenario_content(self):
        # self.admin_link.click()
        # self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        self.ai_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.create_new_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        # Click on create a scenario link
        self.create_a_scenario_link.click()
        self.page.wait_for_load_state("networkidle")
        # Click the first "Target a Product" link
        self.target_a_product_link.click()
        self.page.wait_for_load_state("networkidle")
        # Click on "Auto Loan" scenario type link
        self.auto_loan_scenario_type_link.click()
        self.page.wait_for_load_state("networkidle")
        # Click on the desired template
        self.home_hero_template_link.click()
        self.page.wait_for_load_state("networkidle")
        return CreateASingleScenarioPage(self.page)

    def choose_template_by_text(self, selector, text, index=None):
        self.page.wait_for_selector(selector, state="visible", timeout=30000)
        dropdown = self.page.locator(selector).locator(f"text={text}")
        if dropdown.count() > 1:
            if index is not None:
                dropdown.nth(index).click()
            else:
                raise ValueError(f"Multiple matches found for text '{text}'. Please specify an index.")
        else:
            dropdown.click()

    def click_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class InputScenarioContentPage:
    def __init__(self, page):
        self.page = page
        self.scenario_name_textfield = page.get_by_text('Scenario Name')
        self.headline_textfield = page.get_by_text('Headline')
        self.bodycopy_textfield = page.get_by_text('Body copy')
        self.link_textfield = page.get_by_text('Link').nth(0) # Use the first instance
        self.imagelink_textfield = page.get_by_text('Img link')
        self.save_and_continue_button = page.get_by_text("Save and Continue")

    def fill_out_required_content_form_fields(self, scenario_name, headline, body_copy, link, image_link):
        self.page.get_by_label("Scenario Name").click()
        self.page.get_by_label("Scenario Name").fill(scenario_name)
        self.page.get_by_label("Headline").click()
        self.page.get_by_label("Headline").fill(headline)
        self.page.get_by_label("Body copy").click()
        self.page.get_by_label("Body copy").fill(body_copy)
        self.page.get_by_label("Link").nth(0).click()
        self.page.get_by_label("Link").nth(0).fill(link)
        self.page.get_by_label("Img link").click()
        self.page.get_by_label("Img link").fill(image_link)
    def click_save_and_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.save_and_continue_button.click()

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class UploadImage:
    def __init__(self, page):
        self.page = page
        self.enter_image_url = page.get_by_text("Enter Image URL")
        self.continue_button = page.get_by_text("Continue").nth(1) #Second instance close to image URL

    def fill_image_url(self, img_url):
        self.page.wait_for_selector("#inp_img_url", state="visible", timeout=10000)
        self.enter_image_url.fill(img_url)

    def click_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.continue_button.click()
    def take_screenshot(self, path):
        self.page.screenshot(path=path)


class ChooseStagingCampaignPage:
    def __init__(self, page):
        self.page = page
        # self.create_a_new_campaign_textfield = page.get_by_text('Create a new campaign')
        # Define the create a new campaign text field using a locator instead of by label
        self.create_a_new_campaign_textfield = page.locator("#name")
        self.save_and_continue_button = page.get_by_text("Save and Continue")
        self.test_core_products_link = page.get_by_text('Test Core Products')
        # self.existing_campaign_link = page.get_by_text("Test March Promotion")
        # NEED TO UPDATE WITH EXISTING TEST SCENARIO
        # self.existing_campaign_link = page.get_by_text("Test Core product and publish")
        self.existing_campaign_link = page.get_by_text("Test Core Products Publish and Test")

    def fill_out_required_field_and_campaign(self,campaign_name):
        # Wait for page to load before clickign the text field
        self.page.wait_for_load_state("networkidle")
        # self.page.get_by_label("Create a new campaign").click()
        # Click on the Create a new campaign text field using a locator since not found by name
        self.create_a_new_campaign_textfield.click()
        self.page.wait_for_load_state("networkidle")
        self.create_a_new_campaign_textfield.fill(campaign_name)
        # self.page.get_by_label("Save and Continue").click()
        self.page.get_by_role("button", name="Save and Continue").click()
        self.page.wait_for_load_state("networkidle")

    def select_an_existing_campaign(self):
        self.existing_campaign_link.click()
        self.page.wait_for_load_state("networkidle")

    def click_save_and_continue_button(self):
        self.save_and_continue_button.click()
        self.page.wait_for_load_state("networkidle")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class ScenarioSetupCompletePage:
    def __init__(self, page):
        self.page = page
        self.scenario_setup_complete_title = page.get_by_text("Scenario Setup Complete")
        self.scenario_setup_description = page.get_by_text("You successfully setup")
        self.preview_now_staging_button = page.get_by_text("Preview Now (Staging)")
        self.create_another_scenario_button = page.get_by_text("Create Another Scenario")
        # Link below was removed for ads that do not have a production campaign
        # self.publish_campaign_to_production_button = page.get_by_text("Publish Campaign to Production")

    def get_link_of_preview_now_staging_button(self):
        # Retrieve the href attribute
        href = self.page.locator("a.btn:nth-child(2)").get_attribute("href")
        print(f"Preview now staging link is {href}")
        return href

    def get_link_of_create_a_scenario_button(self):
        # Retrieve the href attribute
        href = self.page.locator("a.btn:nth-child(3)").get_attribute("href")
        print(f"Create a scenario button link is {href}")
        return href

    def get_link_of_publish_campaign_to_production_button(self):
        # Retrieve the href attribute
        href = self.page.locator("a.btn:nth-child(4)").get_attribute("href")
        print(f"Publish campaign to production button link is {href}")
        return href

    def open_preview_now_staging_button_on_a_new_tab(self):
        self.page.wait_for_selector("a.btn:nth-child(2)", state="visible", timeout=10000)
        with self.page.context.expect_page() as new_tab_info:
            self.page.locator("a.btn:nth-child(2)").click()
        return new_tab_info.value

    def open_a_scenario_setup_complete_link_in_new_tab(self, link_url):
        with self.page.context.expect_page() as new_tab_info:
            self.page.evaluate(f"window.open('{link_url}', '_blank')")
        new_tab = new_tab_info.value
        return new_tab

    def open_preview_now_staging_button(self):
        self.page.wait_for_selector("a.btn:nth-child(2)", state="visible", timeout=10000)
        self.page.locator("a.btn:nth-child(2)").click()

    def open_create_another_scenario_button_on_a_new_tab(self):
        self.page.wait_for_selector("a.btn:nth-child(3)", state="visible", timeout=10000)
        with self.page.context.expect_page() as new_tab_info:
            self.page.locator("a.btn:nth-child(3)").click()
        return new_tab_info.value

    def open_create_another_scenario_button_link_in_new_tab(self, link_url):
        with self.page.context.expect_page() as new_tab_info:
            self.page.evaluate(f"window.open('{link_url}', '_blank')")
        new_tab = new_tab_info.value
        return new_tab

    def open_a_scenario_setup_complete_link_in_new_tab_with_authentication(self, link_url):
        """
        Opens the given link in a new tab and handles HTTP authentication if prompted.
        """
        print(f"Opening link in a new tab: {link_url}")

        # Create a new browser context with authentication credentials
        auth_context = self.page.context.browser.new_context(
            http_credentials={"username": "trustonestage", "password": "TruStone2024!!"}
        )

        # Open a new tab within the authenticated context
        new_tab = auth_context.new_page()
        new_tab.goto(link_url)

        # Wait for the page to fully load
        new_tab.wait_for_load_state("networkidle")

        print("New tab opened successfully with authentication.")
        return new_tab

    def open_create_another_scenario_button(self):
        self.page.wait_for_selector("a.btn:nth-child(3)", state="visible", timeout=10000)
        self.page.locator("a.btn:nth-child(3)").click()

    def open_publish_campaign_to_production_button_on_a_new_tab(self):
        self.page.wait_for_selector("a.btn:nth-child(4)", state="visible", timeout=10000)
        with self.page.context.expect_page() as new_tab_info:
            self.page.locator("a.btn:nth-child(4)").click()
        return new_tab_info.value

    def open_publish_campaign_to_production_button(self):
        self.page.wait_for_selector("a.btn:nth-child(4)", state="visible", timeout=10000)
        self.page.locator("a.btn:nth-child(4)").click()

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

    # def take_screenshot_without_fonts(self, path):
    #     """
    #     Takes a screenshot without waiting for fonts to load by using `omit_background=True`
    #     and disabling waiting for fonts.
    #     """
    #     self.page.screenshot(path=path, timeout=60000, omit_background=True)

    def check_url_contains_pattern(self, pattern):
        """
        Checks if the current URL of the given page contains the specified pattern.
        Args:
            pattern: The string pattern to check for in the URL.
        Returns:
            True if the pattern is found in the URL, False otherwise.
        """
        current_url = self.page.url
        return pattern in current_url

    def validate_url_after_segment_an_existing_content(self, base_url, param_patterns):
        current_url = self.page.url
        print(f"Current URL after segmenting content: {current_url}")
        url_parts = current_url.split("?")

        if len(url_parts) != 2 or url_parts[0] != base_url:
            print(f"Base URL {url_parts[0]} does not match the base pattern {base_url}.")
            return False

        params = url_parts[1].split("&")
        for param in params:
            param_name, value = param.split("=")
            if param_name not in param_patterns:
                print(f"Unexpected parameter: {param_name}")
                return False
            pattern = param_patterns[param_name]
            if pattern and not re.match(pattern, value):
                print(f"Parameter {param_name} does not match the expected pattern.")
                return False

        print("URL matches the expected pattern.")
        return True

    def validate_link_url_after_create_a_single_scenario(self, link_url, base_url, param_patterns):
        print(f"Link URL after creating a single scenario: {link_url}")
        url_parts = link_url.split("?")

        # Ensure base_url comparison ignores trailing slash
        normalized_base_url = base_url.rstrip("/")
        normalized_link_base = url_parts[0].rstrip("/")

        if normalized_link_base != normalized_base_url:
            print(f"Base URL {normalized_link_base} does not match the base pattern {normalized_base_url}.")
            return False

        if len(url_parts) != 2:
            print("Invalid URL format; missing query parameters.")
            return False

        params = url_parts[1].split("&")
        for param in params:
            param_name, value = param.split("=")
            if param_name not in param_patterns:
                print(f"Unexpected parameter: {param_name}")
                return False
            pattern = param_patterns[param_name]
            if pattern and not re.match(pattern, value):
                print(f"Parameter {param_name} does not match the expected pattern.")
                return False

        print("URL matches the expected pattern.")
        return True

class AdsAdminPage:
    def __init__(self, page):
        self.page = page
        self.generated_ad_to_delete = page.get_by_text("Trustone Auto Loan Test Automation").nth(0) # Use the first instance
        self.delete_ad_button = page.get_by_text("Delete")
        self.delete_button = page.get_by_role("button", name="Delete")  # Find the button
        self.yes_im_sure_confirm_button = page.get_by_text("Yes, I’m sure")

    def navigate(self):
        self.page.goto(f'https://{test_env}finalyticsdata.com/admin/app/ad/')

    def click_ad_to_delete(self):
        self.generated_ad_to_delete.click()
        self.page.wait_for_load_state("networkidle")

    def scroll_down_until_delete_button(self):
        self.delete_ad_button.click()
        self.page.wait_for_load_state("networkidle")

    def click_delete_ad_button(self):
        self.delete_ad_button.click()
        self.page.wait_for_load_state("networkidle")

    def click_confirm_ad_deletion_button(self):
        self.yes_im_sure_confirm_button.click()
        self.page.wait_for_load_state("networkidle")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class CampaignAdminPage:
    def __init__(self, page):
        self.page = page
        self.generated_campaign_to_delete = page.get_by_text("Trustone Auto Loan Test Automation").nth(0)
        self.delete_campaign_button = page.get_by_text("Delete")
        self.delete_button = page.get_by_role("button", name="Delete")  # Find the button
        self.yes_im_sure_confirm_button = page.get_by_text("Yes, I’m sure")

    def navigate(self):
        self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def click_campaign_to_delete(self):
        self.generated_campaign_to_delete.click()
        self.page.wait_for_load_state("networkidle")

    def scroll_down_until_delete_button(self):
        self.delete_ad_button.click()
        self.page.wait_for_load_state("networkidle")

    def click_delete_campaign_button(self):
        self.delete_campaign_button.click()
        self.page.wait_for_load_state("networkidle")

    def click_confirm_campaign_deletion_button(self):
        self.yes_im_sure_confirm_button.click()
        self.page.wait_for_load_state("networkidle")

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
    error_keywords = ["Server Error", "(500)", "error", "Page not found"]
    page_text = page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]

    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)


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

# PREVIOUS VERSION WITHOUT HTTP AUTHENTICATION
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


def take_screenshot_without_fonts(page, path):
    """
    Takes a screenshot without waiting for fonts to load by hiding text elements before capturing.
    """
    try:
        # Hide text elements to prevent font loading issues
        page.evaluate("""
            document.querySelectorAll('*').forEach(el => {
                if (window.getComputedStyle(el).fontFamily) {
                    el.style.visibility = 'hidden';
                }
            });
        """)

        # Take screenshot
        page.screenshot(path=path, timeout=60000)
    finally:
        # Restore visibility after screenshot
        page.evaluate("""
            document.querySelectorAll('*').forEach(el => {
                el.style.visibility = '';
            });
        """)


def test_create_a_single_scenario(browser_context):
    events_template_to_select = "Trustone Financial | home hero"
    ads_admin_page_url = f'http://{test_env}inalyticsdata.com/admin/app/ad/'
    page = browser_context.new_page()  # Use the main page, not a new tab
    # Initialize page objects
    login_page = LoginPage(page)
    single_scenario_page = CreateASingleScenarioPage(page)
    input_scenario_content_page = InputScenarioContentPage(page)
    enter_image_url_page = UploadImage(page)
    choose_staging_campaign_page = ChooseStagingCampaignPage(page)
    # scenario_setup_complete_page = ScenarioSetupCompletePage(page)
    scenario_setup_complete_page = ScenarioSetupCompletePage(page)
    ads_admin_page = AdsAdminPage(page)

    # Define the base URL and parameter patterns
    base_url = f'https://{test_env}finalyticsdata.com/scenarios/setup-complete'
    preview_staging_base_url = f'https://trustonestage.wpenginepowered.com/'  # Staging URL is for tru if used a tru account
    # New param patters
    param_patterns = {
        "ad_ids": r"\d+",  # Match any digits for ad_ids
        "asset_id": r"\d+",  # Match any digits for asset_id
        "adcopy_id": r"\d+",  # Match any digits for adcopy_id
        "products_recommended": r"auto loan"  # Match the selected product
    }
    # New preview staging URL pattern
    preview_staging_param_patterns = {
        "ad_ids": r"\d+",  # Match any digits for ad_ids
        "api": r"stg",
        # "products_recommended": urllib.parse.quote("auto loan")  # Encode space as %20
        "products_recommended": r"auto loan"  # Encode space as %20
    }
    create_scenario_relative_url = "/scenarios/create-single-scenario"
    publish_campaign_to_production_relative_url = "/scenarios/campaigns-list/publish/"

    # Only clear the directory that is being used in this test
    screenshots_directory = 'screenshots_adminsite_using_pytest/create_a_single_scenario/'
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
    # Get the current URL
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # Actions post-login
    single_scenario_page.navigate_to_input_scenario_content()
    single_scenario_page.take_screenshot(f'{screenshots_directory}2_successful_navigation_to_input_scenario_content.png')

    # Fill out the Input Scenario Content Form
    input_scenario_content_page.fill_out_required_content_form_fields("Trustone Auto Loan Test Automation",
                                                                      "Get a Great Trustone Auto Loan Rate!", "Hurry and get your auto loan before offer ends!", "https://trustonestage.wpenginepowered.com/rates/rates-loans", "https://www.stgfinalyticsdemo.com/static/app/assets/images/sample_hero_small_dark-7b4ffb01.jpg")
    input_scenario_content_page.take_screenshot(f'{screenshots_directory}3_input_scenario_content_page_after_filled_out_required_fields.png')

    # Click Save and Continue after entering the scenario content
    input_scenario_content_page.click_save_and_continue_button()
    # input_scenario_content_page.take_screenshot(f'{screenshots_directory}4_upload_image_page_after_save_and_continue.png')

    # Enter the image URL and continue
    enter_image_url_page.fill_image_url("https://www.stgfinalyticsdemo.com/static/app/assets/images/sample_hero_small_dark-7b4ffb01.jpg")
    enter_image_url_page.take_screenshot(f'{screenshots_directory}4_upload_image_page_with_url.png')
    enter_image_url_page.click_continue_button()

    # Choose a staging campaign and use a name that is dynamic and depends on the date and time and then click Save and Continue
    formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H")
    # dynamic_campaign_name = "Test " + formatted_datetime + " Promotion"
    dynamic_campaign_name = "Test Create A Single Scenario Test Automation"

    # Page before click on create a new campaign
    choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}5_choose_a_staging_campaign.png')
    # Use the 2 lines below to create a new campaign
    # choose_staging_campaign_page.fill_out_required_field_and_campaign(dynamic_campaign_name)
    # choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}6_choose_a_staging_campaign_filled_out.png')
    # NOTE: Use an existing campaign since can't delete generated campaign as staff user
    choose_staging_campaign_page.select_an_existing_campaign()
    choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}6_selected_an_existing_campaign.png')

    # Validate the Scenario Setup Complete page and the links for the three buttons
    current_url = page.url
    print(f"Current URL after successful scenario completion is {page.url}")

    # Check that the page does not have any internal server error or any error message after it is loaded
    page.wait_for_load_state()
    validate_no_server_error(page)
    # Scenario Setup Complete screenshot with buttons to validate
    scenario_setup_complete_page.take_screenshot(f'{screenshots_directory}7_scenario_setup_complete_page.png')

    # Get the link of preview now staging button instead of clicking since can control and use the tab, assert the URL and open it in a new tab and taken screenshot
    preview_staging_link_url = scenario_setup_complete_page.get_link_of_preview_now_staging_button()
    if not scenario_setup_complete_page.validate_link_url_after_create_a_single_scenario(preview_staging_link_url,
                                                                                         preview_staging_base_url,
                                                                                         preview_staging_param_patterns):
        raise AssertionError(
            f"Preview Now (Staging) button URL {preview_staging_link_url} does not match the expected URL using preview_staging_base_url {preview_staging_base_url} and parameters {preview_staging_param_patterns}")

    # Since there is a space in the product 'auto loan', split the base URL and query parameters
    parsed_url = urllib.parse.urlparse(preview_staging_link_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)  # Parse query parameters into a dictionary

    # Encode query parameters with spaces as '%20' instead of '+'
    encoded_query = urllib.parse.urlencode(query_params, doseq=True, quote_via=urllib.parse.quote)

    # Construct the final encoded URL
    url_encoded_preview_staging_link_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{encoded_query}"

    print(f"URL encoded preview staging link URL is {url_encoded_preview_staging_link_url}")
    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab_with_authentication(url_encoded_preview_staging_link_url)
    # Enter the authentication if prompted
    # new_tab.wait_for_load_state("networkidle", timeout=60000) #times out due to waiting for load so use load state instead
    # new_tab.wait_for_load_state("load", timeout=60000)
    new_tab.wait_for_selector("body", state="visible", timeout=60000)  # Ensure body is fully visible
    new_tab.wait_for_load_state("domcontentloaded", timeout=60000)  # Ensure DOM is loaded

    # Modify the retry screenshot logic to bypass font loading issues
    # SKIP TAKING SCREENSHOT FOR NOW DUE TO TIMEOUT ISSUE
    # screenshot_taken = False
    # retries = 3
    # for attempt in range(retries):
    #     try:
    #         # Scroll to top before taking a screenshot to ensure visibility
    #         new_tab.evaluate("window.scrollTo(0, 0)")
    #
    #         # Wait for an additional element to load
    #         new_tab.wait_for_selector("img, .loaded-content", timeout=10000)
    #
    #         # Take screenshot without waiting for fonts
    #         take_screenshot_without_fonts(new_tab, f'{screenshots_directory}8_preview_now_staging_page.png')
    #         screenshot_taken = True
    #         print("Preview Now staging page saved as 8_preview_now_staging_page.png")
    #         break
    #     except TimeoutError:
    #         print(f"Screenshot attempt {attempt + 1} failed due to timeout. Retrying after scrolling...")
    #         new_tab.evaluate("window.scrollBy(0, 100)")  # Scroll down slightly and retry
    #         time.sleep(10)
    #
    # if not screenshot_taken:
    #     raise Exception("Failed to take screenshot after multiple attempts.")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(new_tab)

    # Get the link of the create a scenario button instead of clicking since can control and use the tab, assert the URL and open it in a new tab and taken screenshot
    create_another_scenario_link_url = scenario_setup_complete_page.get_link_of_create_a_scenario_button()

    # Check the URL and content of the newly opened tab, take screenshot, validate the URL and then close
    print(f'Relative URL of Create Another Scenario button is: {create_another_scenario_link_url}')
    if create_another_scenario_link_url != create_scenario_relative_url:
        raise AssertionError(
            f"Create Another Scenario button relative URL {create_another_scenario_link_url} does not match the expected relative URL {create_scenario_relative_url}")

    # Open the create_another_scenario_link_url in a new tab, take a screenshot and check that there are no errors
    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab(
        create_another_scenario_link_url)
    # new_tab.wait_for_load_state("networkidle", timeout=60000) #times out due to waiting for load so use load state instead
    new_tab.wait_for_load_state("load")
    new_tab.screenshot(path=f'{screenshots_directory}9_create_another_scenario_link_page.png')
    print("Create Another Scenario page saved as 9_create_another_scenario_link_page.png")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(new_tab)

    # Get the link of the publish campaign to production button instead of clicking since can control and use the tab, assert the URL and open it in a new tab and taken screenshot
    publish_campaign_to_production_link_relative_url = scenario_setup_complete_page.get_link_of_publish_campaign_to_production_button()
    print(
        f'Relative URL of Publish Campaign to production button link is: {publish_campaign_to_production_link_relative_url}')
    # Assert the URL
    if not publish_campaign_to_production_relative_url in publish_campaign_to_production_link_relative_url:
        raise AssertionError(
            f"Publish Campaign to Production button relative URL link {publish_campaign_to_production_link_relative_url} does not contain expected URL {publish_campaign_to_production_relative_url}")

    # Open the publish_campaign_to_production_link_relative_url in a new tab, take a screenshot and check that there are no errors
    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab(
        publish_campaign_to_production_link_relative_url)
    new_tab.wait_for_load_state("load")
    new_tab.screenshot(path=f'{screenshots_directory}10_publish_campaign_to_production_page.png')
    print("Publish campaign to production page saved as 10_publish_campaign_to_production_page.png")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(new_tab)

    # Get all pages (tabs) in the browser context
    all_pages = page.context.pages

    # Identify the main page (first tab)
    main_page = all_pages[0]

    # Close all other pages (tabs and windows), keeping the main page open
    for p in all_pages:
        if p != main_page:  # Ensure we do not close the main page
            p.close()
    #
    # # Close all pages except the main page (first tab)
    # for p in all_pages[1:]:  # Skip closing the first page
    #     p.close()
    page.screenshot(path=f'{screenshots_directory}11_after_closing_all_tabs_and_opened_page_except_main_page.png')

    print(f"Current page URL before navigation is " + page.url)

    # Delete the generated product ad and test campaign
    # Delete "Trustone Auto Loan Test Automation" ad and "Test Create A Single Scenario Test Automation" campaign
    # Go to Ads on https://stgfinalyticsdata.com/admin/app/ad/ , select "Trustone Auto Loan Test Automation", scroll down and click "Delete"
    ads_admin_page = AdsAdminPage(page)  # Reuse the current page to go to the ads admin page since still opened
    ads_admin_page.navigate()
    page.wait_for_load_state("networkidle")  # Wait for full load

    # Ensure admin page is in focus
    page.bring_to_front()

    print(f"Current page URL is now " + page.url)

    ads_admin_page.take_screenshot(path=f'{screenshots_directory}12_main_page_used_to_view_admin_ads_page.png')
    ads_admin_page.click_ad_to_delete()
    # Scroll down to see the "delete" button
    ads_admin_page.scroll_down_until_delete_button()
    ads_admin_page.click_confirm_ad_deletion_button()
    ads_admin_page.take_screenshot(path=f'{screenshots_directory}13_generated_ad_deleted.png')


