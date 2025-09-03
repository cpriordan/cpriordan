import os
import sys
import pytest
import time
import re
import urllib.parse
from playwright.sync_api import expect
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Add parent directory to path to import qa_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qa_tools import (browser_context, clear_screenshots_directory, 
                      validate_no_server_error, generate_otp_code, 
                      setup_environment_variables, LoginPage)


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
        remaining_time = auth_handler.interval - (int(time.time()) % auth_handler.interval)
        if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
            time.sleep(remaining_time + 1)
        otp_code = auth_handler.now()
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
        # NEED TO UPDATE WITH EXISTING TEST SCENARIO AND IT IS IMPORTANT THAT THIS CAMPAIGN IS CREATED BY AN ADMIN USER SINCE STAFF DOES NOT HAVE PERMISSION
        self.existing_campaign_link = page.get_by_text("Test Core products Publish and Test")

    def fill_out_required_field_and_campaign(self,campaign_name):
        # Wait for page to load before clickign the text field
        self.page.wait_for_load_state("networkidle")
        self.create_a_new_campaign_textfield.click()
        self.page.wait_for_load_state("networkidle")
        self.create_a_new_campaign_textfield.fill(campaign_name)
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
        self.generated_ad_to_delete = page.get_by_text("Trustone Auto Loan Test Automation")
        self.delete_ad_button = page.get_by_text("Delete")
        self.delete_button = page.get_by_role("button", name="Delete")  # Find the button
        self.yes_im_sure_confirm_button = page.get_by_text("Yes, I’m sure")

    def navigate_to_ads(self):
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

class PublishUnpublishPage:
    def __init__(self, page):
        self.page = page
        # self.ai_scenarios_link = page.get_by_text("AI Scenarios")
        self.ai_scenarios_left_nav_link = page.get_by_text("Scenarios").nth(0)
        self.publish_unpublish_scenarios_left_nav_link = page.get_by_text("Publish/Unpublish Scenarios").first
        self.publish_scenarios_link = page.get_by_role("link", name="Publish Scenarios", exact=True)
        self.unpublish_scenarios_link = page.get_by_text("Unpublish Scenarios").nth(2) # Select the third instance
        # IT IS IMPORTANT THAT THE CAMPAIGN NAME EXISTS AND CREATED BY A TEST ADMIN SINCE NO STAFF DOES NOT HAVE PERMISSION TO CREATE IT
        self.test_scenario_group_to_publish_link = page.get_by_text("Test Core Products Publish and Test | Mode:Test (Published)")
        # THE CAMPAIGN NAME BELOW CAN CHANGE BASED ON WHETHER IT IS PUBLISHED OR NOT
        self.test_scenario_group_to_unpublish_link = page.get_by_text("Core Products Publish and Test | Mode:Prod")
        self.first_checkbox_content_module = page.locator(
            "//li[contains(., 'Trustone Auto Loan Test Automation  (Published)')]//input[@type='checkbox']"
        ).first
        self.content_module_checkbox = page.locator("#option2220")
        self.choose_existing_production_target_button = page.get_by_text("Choose Existing Production Target")
        # THE PRODUCTION CAMPAIGN BELOW HAS TO EXIST ON STG IN PRODUCTION MODE AND NEEDS TO BE CREATED BY AN ADMIN
        # THE CAMPAIGN NAME BELOW CAN CHANGE BASED ON WHETHER IT IS PUBLISHED OR NOT
        self.existing_production_group_to_publish_link = page.get_by_text("Core Products Publish and Test | Mode:Prod")
        self.publish_confirmation_button = page.get_by_text("Publish!")
        self.unpublish_button = page.get_by_text("Unpublish This Campaign")


    def navigate(self, page):
        # Click the "AI Scenarios" left nav
        self.ai_scenarios_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        # Click the "Publish/Unpublish" left nav
        self.publish_unpublish_scenarios_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")

    def publish_campaign(self, page, screenshots_directory):
        # Click the "Publish Scenarios" link
        self.publish_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}11_existing_stg_campaign_to_publish.png')
        # Select the existing stg campaign
        self.test_scenario_group_to_publish_link.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}12_select_content_module_to_publish.png')
        # Select the first checkbox if there are multiple instances of the same content module
        self.first_checkbox_content_module.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}13_content_module_selected_to_publish.png')
        # Click the "Choose Existing Production Target" button to select the prod campaign
        self.choose_existing_production_target_button.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}14_prod_campaign_for_publish.png')
        # Select the prod campaign to use for publishing
        self.existing_production_group_to_publish_link.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}15_check_everything_looks_right_before_publish.png')
        # Select the confirm publish button
        self.publish_confirmation_button.click()
        self.page.wait_for_load_state("networkidle")

    def unpublish_campaign(self, page, screenshots_directory):
        # Click the "Publish Scenarios" link
        self.unpublish_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")

        # Select the campaign to unpublish
        self.test_scenario_group_to_unpublish_link.click()
        self.page.wait_for_load_state("networkidle")
        self.take_screenshot(f'{screenshots_directory}18_campaign_to_unpublish.png')

        # Select the first checkbox if there are multiple instances of the same content module
        self.first_checkbox_content_module.click()
        self.page.wait_for_load_state("networkidle")
        print("Selected scenario to unpublished")
        self.take_screenshot(f'{screenshots_directory}21_content_module_selected_to_unpublish.png')

        # Select the unpublish button
        self.unpublish_button.click()
        self.page.wait_for_load_state("networkidle")
        print("Selected unpublish button")


    def take_screenshot(self, path):
        self.page.screenshot(path=path)

    def validate_successful_publish(self, page, screenshots_directory):
        publish_success_message_locator = page.locator(".card-body > p:nth-child(1) > b:nth-child(1)")
        publish_success_message_text = publish_success_message_locator.text_content()
        if publish_success_message_text:
            publish_success_message_text = publish_success_message_text.strip()
        print(f"Actual success message: {publish_success_message_text}")

        # Check for partial match ignoring asset filename
        assert "Success! Content modules were published!" in publish_success_message_text, \
            f"Expected 'was published successfully' in message, but got: {publish_success_message_text}"

    def validate_successful_unpublish(self, page, screenshots_directory):
        unpublish_success_message_locator = page.locator(".card-body > p:nth-child(1) > b:nth-child(1)")
        unpublish_success_message_text = unpublish_success_message_locator.text_content()
        if unpublish_success_message_text:
            unpublish_success_message_text = unpublish_success_message_text.strip()
        print(f"Actual success message: {unpublish_success_message_text}")

        # Check for partial match ignoring asset filename
        assert "Success! Content modules were unpublished!" in unpublish_success_message_text, \
            f"Expected 'was unpublished successfully' in message, but got: {unpublish_success_message_text}"





# Setup environment variables
findata_user, findata_pw, findata_otp, test_env, auth_handler = setup_environment_variables(
    "FINDATA_TRU_USER", "FINDATA_TRU_PW", "FINDATA_TRU_OTP"
)

# PREVIOUS VERSION WITHOUT HTTP AUTHENTICATION
# @pytest.fixture(scope="function")
# def browser_context():
#     """Fixture to set up and tear down the Playwright browser context."""
#     with sync_playwright() as playwright:
#         browser = playwright.chromium.launch(headless=False)
#         context = browser.new_context()
#         yield context
#         context.close()
#         browser.close()

# HTTP credentials are now configured via environment variables in qa_tools.py
# Set HTTP_USERNAME=trustonestage and HTTP_PASSWORD=TruStone2024!! in your environment



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


def test_publish_unpublish_campaign(browser_context):
    # Define templates, URLs and campaigns that needs to exist on STG for the script to run properly
    events_template_to_select = "Trustone Financial | home hero"
    ads_admin_page_url = f'http://{test_env}finalyticsdata.com/admin/app/ad/'
    admin_page_url = f'http://{test_env}finalyticsdata.com/admin'
    page = browser_context.new_page()  # Use the main page, not a new tab
    # Initialize page objects
    login_page = LoginPage(page)
    single_scenario_page = CreateASingleScenarioPage(page)
    input_scenario_content_page = InputScenarioContentPage(page)
    enter_image_url_page = UploadImage(page)
    choose_staging_campaign_page = ChooseStagingCampaignPage(page)
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
    screenshots_directory = 'screenshots_adminsite_using_pytest/publish_unpublish_campaign/'
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
    page.wait_for_load_state("networkidle")

    # Take screenshot and verify redirection
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    # Get the current URL
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # Show the existing ads BEFORE publish by navigating to the "Ads" page
    ads_admin_page.navigate_to_ads()
    print(f"Navigated to ads page to show the existing ads before publish")
    ads_admin_page.take_screenshot(f'{screenshots_directory}2_navigated_to_ads_to_show_ads_before_publish.png')

    # Actions post-login
    single_scenario_page.navigate_to_input_scenario_content()
    single_scenario_page.take_screenshot(f'{screenshots_directory}3_successful_navigation_to_input_scenario_content.png')

    # Fill out the Input Scenario Content Form
    input_scenario_content_page.fill_out_required_content_form_fields("Trustone Auto Loan Test Automation",
                                                                      "Get a Great Trustone Auto Loan Rate!", "Hurry and get your auto loan before offer ends!", "https://trustonestage.wpenginepowered.com/rates/rates-loans", "https://www.stgfinalyticsdemo.com/static/app/assets/images/sample_hero_small_dark-7b4ffb01.jpg")
    input_scenario_content_page.take_screenshot(f'{screenshots_directory}4_input_scenario_content_page_after_filled_out_required_fields.png')

    # Click Save and Continue after entering the scenario content
    input_scenario_content_page.click_save_and_continue_button()
    # input_scenario_content_page.take_screenshot(f'{screenshots_directory}4_upload_image_page_after_save_and_continue.png')

    # Enter the image URL and continue
    enter_image_url_page.fill_image_url(f'https://www.{test_env}finalyticsdemo.com/static/app/assets/images/sample_hero_small_dark-7b4ffb01.jpg')
    enter_image_url_page.take_screenshot(f'{screenshots_directory}5_upload_image_page_with_url.png')
    enter_image_url_page.click_continue_button()

    # Choose a staging campaign and use a name that is dynamic and depends on the date and time and then click Save and Continue
    formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H")
    # dynamic_campaign_name = "Test " + formatted_datetime + " Promotion"
    dynamic_campaign_name = "Test Publish and Unpublish Campaign"

    # Page before click on create a new campaign
    choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}6_choose_a_staging_campaign.png')
    # Use the 2 lines below to create a new campaign
    # choose_staging_campaign_page.fill_out_required_field_and_campaign(dynamic_campaign_name)
    # choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}6_choose_a_staging_campaign_filled_out.png')
    # NOTE: Use an existing campaign since can't delete generated campaign as staff user
    choose_staging_campaign_page.select_an_existing_campaign()
    choose_staging_campaign_page.take_screenshot(f'{screenshots_directory}7_selected_an_existing_stg_campaign.png')

    # Validate the Scenario Setup Complete page and the links for the three buttons
    current_url = page.url
    print(f"Current URL after successful scenario completion is {current_url}")

    # Check that the page does not have any internal server error or any error message after it is loaded
    page.wait_for_load_state()
    validate_no_server_error(page)
    # Scenario Setup Complete screenshot with buttons to validate
    scenario_setup_complete_page.take_screenshot(f'{screenshots_directory}8_scenario_setup_complete_page.png')

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

    # View the preview staging ad URL and take a screenshot
    page.goto(url_encoded_preview_staging_link_url)
    # page.wait_for_load_state("domcontentloaded")
    time.sleep(10)  # Give ample time for fonts and delayed assets to load
    print(f"Went to preview ad on staging URL on {url_encoded_preview_staging_link_url} ")
    # The line below causes a timeout error when taking a screenshot due to font loading issue
    # page.screenshot(path=f'{screenshots_directory}9_PREVIEW_AD_NOW_ON_STG_before_publish.png')

    # Capture PDF instead of screenshot due to font issue on trustone
    pdf_path = f'{screenshots_directory}9_PREVIEW_AD_NOW_ON_STG_before_publish.pdf'
    page.emulate_media(media="screen")
    page.pdf(path=pdf_path, format="A4")


    # TAKING SCREENSHOT FAILS DUE TO FONT ISSUE SO COMMENT OUT FOR NOW BUT SHOW THAT GENERATED AD CAN BE PREVIEWED
    # try:
    #     # Try normal screenshot
    #     page.screenshot(path=f'{screenshots_directory}9_PREVIEW_AD_NOW_ON_STG_before_publish.png', timeout=60000)
    # except Exception as e:
    #     print(f"Screenshot timeout encountered: {e}. Retrying without fonts...")
    #
    #     try:
    #         # Hide text elements to prevent font loading issues
    #         page.evaluate("""
    #             document.querySelectorAll('*').forEach(el => {
    #                 if (window.getComputedStyle(el).fontFamily) {
    #                     el.style.visibility = 'hidden';
    #                 }
    #             });
    #         """)
    #
    #         # Retry screenshot
    #         page.screenshot(path=f'{screenshots_directory}9_PREVIEW_AD_NOW_ON_STG_before_publish_fallback.png', timeout=60000)
    #     except Exception as retry_error:
    #         print(f"Retry screenshot also failed: {retry_error}")
    #     finally:
    #         # Restore visibility regardless of screenshot success
    #         page.evaluate("""
    #             document.querySelectorAll('*').forEach(el => {
    #                 el.style.visibility = '';
    #             });
    #         """)

    # Navigate back to the admin page after viewing the ad on stg
    page.goto(admin_page_url)
    print(f"Went to admin page URL {admin_page_url} after previewing the ad on truestone STG" )

    # Parse and save the generated ad_ids from the url_encoded_preview_staging_link_url so can navigate to view the ad_id and check if published in prod if prod campaign was aded
    # Parse the URL
    parsed_url = urlparse(url_encoded_preview_staging_link_url)
    # Extract all the URL parameters as a dictionary so ad_ids is the first item with key ad_ids is the generated ad for URL https://trustonestage.wpenginepowered.com?ad_ids=2524&api=stg&products_recommended=auto%20loan
    url_params = parse_qs(parsed_url.query)
    # The first key value pair is ad_ids so access as first item in the list
    generated_ad_id = url_params.get("ad_ids", [None])[0]

    print(f"url_params are {url_params} and generated ad_id is {generated_ad_id}")
    # NO NEED TO OPEN A NEW TAB WHICH WAS FOR PREVIOUS CASE

    print(f"Current page URL before navigation is " + page.url)

    # Publish using the publish/unpublish campaign flow instead of the publish campaign to production button
    publish_unpublish_page = PublishUnpublishPage(page)
    # Navigate to the publish/unpublish page
    publish_unpublish_page.navigate(page)
    # Take screenshot after navigation
    publish_unpublish_page.take_screenshot((f'{screenshots_directory}10_navigated_to_publish_unpublish_campaign_page.png'))
    # Publish the scenario that was generated using an existing prod campaign
    publish_unpublish_page.publish_campaign(page,screenshots_directory)
    # Take screenshot after published campaign
    publish_unpublish_page.take_screenshot((f'{screenshots_directory}15_success_message_PUBLISHED_campaign.png'))
    # Save the current page URL which has information on the campaign that was published
    publish_success_url_with_campaign_information = page.url
    print(f"Publish success URL with campaign information is {publish_success_url_with_campaign_information}")

    # Check the publish success message and take screenshot
    publish_unpublish_page.validate_successful_publish(page, (f'{screenshots_directory}17_successful_published_campaign_validation.png'))


    # Add more steps to show that the PUBLISH WAS SUCCESSFUL by viewing the generated ad which was saved during PREVIEW campaign which was saved as url_encoded_preview_staging_link_url BUT parse the ad_id from the URL and navigate to view the Ad instead based on the generated ad_id
    # Use the saved generated_ad_id to view the ad_id and take a screenshot showing that the PROD campaign was added to the generate ad after published
    url_to_view_generated_ad_id_on_stg = f"https://{test_env}finalyticsdata.com/admin/app/ad/{generated_ad_id}"
    print(f"Dynamically generated URL to view the ad_id of the generated ad is {url_to_view_generated_ad_id_on_stg}")
    # Navigate to the URL and take a screenshot to show that the PROD campaign was added
    page.goto(url_to_view_generated_ad_id_on_stg)
    page.wait_for_load_state("networkidle")
    # Scroll to the campaign section
    campaign_locator = page.locator("#id_campaigns_to > option:nth-child(1)")
    campaign_locator.scroll_into_view_if_needed()
    print(f"Waited for URL on {url_to_view_generated_ad_id_on_stg} to load, scrolled to campaign section and about to check if the ad shows the prod campaign and take screnshot...")
    # HARD CODE THE prod campaign for now but this can be defined in main and passed to publish and unpublish
    expect(page.locator("#id_campaigns_to > option:nth-child(1)")).to_have_text("Trustone Financial Core Products Publish and Test")
    page.screenshot(path=f'{screenshots_directory}16_CHECK_generated_ad_was_modified_to_include_PROD_campaign_after_published.png', full_page=True)

    # Navigate to Unpublish scenarios
    publish_unpublish_page.navigate(page)
    # Take screenshot after navigation
    publish_unpublish_page.take_screenshot(
        (f'{screenshots_directory}19_navigated_to_unpublish_campaign_page.png'))
    # UnPublish the campaign
    publish_unpublish_page.unpublish_campaign(page, screenshots_directory)
    # Take screenshot after published campaign
    publish_unpublish_page.take_screenshot((f'{screenshots_directory}21_success_message_UNPUBLISHED_campaign.png'))
    # Check the publish success message and take screenshot
    publish_unpublish_page.validate_successful_unpublish(page, (
        f'{screenshots_directory}20_success_message_unpublished_campaign.png'))


    # ALSO, check that the ad no longer has the prod campaign AFTER UNPUBLISH
    # Navigate to the URL and take a screenshot to show that the PROD campaign was added
    page.goto(url_to_view_generated_ad_id_on_stg)
    page.wait_for_load_state("networkidle")
    # Scroll to the campaign section
    campaign_locator = page.locator("#id_campaigns_to > option:nth-child(1)")
    campaign_locator.scroll_into_view_if_needed()
    print(
        f"Waited for URL on {url_to_view_generated_ad_id_on_stg} to load, scrolled to campaign section and about to check if the ad shows the prod campaign and take screnshot...")
    # HARD CODE THE prod campaign for now but this can be defined in main and passed to publish and unpublish
    expect(page.locator("#id_campaigns_to > option:nth-child(1)")).not_to_have_text("Trustone Financial Core Products Publish and Test")
    page.screenshot(
        path=f'{screenshots_directory}22_CHECK_generated_ad_was_modified_to_remove_PROD_campaign_after_unpublished.png',
        full_page=True)


    # Scroll down to the delete button and delete the ad for cleanup
    delete_button_locator = page.locator("a.btn")
    delete_button_locator.scroll_into_view_if_needed()
    # Click the delete button
    delete_button_locator.click()
    page.wait_for_load_state("networkidle")
    yes_im_sure_confirm_button = page.get_by_text("Yes, I’m sure")
    yes_im_sure_confirm_button.click()
    page.screenshot(path=f'{screenshots_directory}23_generated_ad_was_deleted_for_cleanup.png')
