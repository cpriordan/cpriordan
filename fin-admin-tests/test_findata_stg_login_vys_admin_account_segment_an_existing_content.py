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

class SegmentExistingContent:
    def __init__(self, page):
        self.name_and_text_label_of_ad_with_adcopy = "Earn Higher Interest with a CD"
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        # self.ai_scenarios_link = page.get_by_text("AI Scenarios")
        self.ai_scenarios_link = page.get_by_text("Scenarios").nth(0)
        self.create_new_scenarios_link = page.get_by_text("Create New Scenario")
        self.segment_content_link = page.get_by_text("Segment an Existing Content Module")
        # Instead of "New Minnesota Geo Branch", use "Earn Higher Interest with a CD" ad which has an adcopy CHANGED and SCROLL DOWN
        # Instead of clicking on the ad based on the link label name, go to a specific URL that uses ad_id 50 which has an adcopy and a production campaign
        # self.existing_content_link = page.get_by_text("Earn Higher Interest with a CD").nth(0) # Click the first instance
        self.existing_content_link= "https://stgfinalyticsdata.com/scenarios/adcopy-segment?ad_ids=50"
        self.easterly_company_link = page.locator('a[dd="vys"]').first
        self.continue_button = page.get_by_text("Continue")
        self.business_segment_radio_option =page.get_by_text("business")
        self.save_button = page.get_by_text("Save").nth(1) # Use the second instance since suzy saver segment matched

    def navigate_to_input_scenario_content(self, screenshots_directory):
        self.admin_link.click()
        self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        self.ai_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.create_new_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        # Since the ad which has an adcopy is way below the page, SCROLL DOWN TO THE VERY BOTTOM before clicking the link
        # No need to scroll down since at the top
        # self.scroll_down_to_an_ad_with_adcopy_if_needed(self.name_and_text_label_of_ad_with_adcopy)
        # print(f"About to scroll down to view ad {self.name_and_text_label_of_ad_with_adcopy} and wait for the page to load")
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f"{screenshots_directory}2_segment_an_existing_content_module.png")
        self.segment_content_link.click()
        # No need to select the company link if signed in using trustone after Segment Existing Content Module link
        # Select an existing content link
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f"{screenshots_directory}3_click_an_existing_ad_link.png")
        # Instead of clicking the link for the "Earn Higher Interest wih a CD" ad id 50, go to the URL
        # self.existing_content_link.click()
        # NEED TO CLICK "Easterly" link label first
        self.easterly_company_link.click()
        # GO TO THE ACTUAL URL link
        self.page.goto("https://stgfinalyticsdata.com/scenarios/adcopy-segment?ad_ids=50")
        # Click the continue button on replace image URL to go to input scenario content page
        self.page.wait_for_load_state("networkidle")
        # COMMENTED OUT SINCE NOT SURE WHY FLOW CHANGED HERE WHEN USING THE EARN HIGH INTEREST MODULE AND CONTINUE BUTTON GETS CLICKED WITH FIELDS ARE POPULATED
        # self.page.screenshot(path=f"{screenshots_directory}before_click_continue_button_on_existing_ad.png")
        # self.continue_button.wait_for(state="visible", timeout=30000)
        # self.continue_button.click()
        return ScenarioContentPage(self.page)

    def click_continue_button(self):
        self.page.wait_for_load_state("networkidle")
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()

    def click_company_link(self):
        self.easterly_company_link.click()

    def click_save_button(self):
        self.page.wait_for_load_state("networkidle")
        self.save_button.wait_for(state="visible", timeout=30000)
        self.save_button.click()

    def click_business_segment(self):
        self.page.wait_for_load_state("networkidle")
        self.business_segment_radio_option.wait_for(state="visible", timeout=30000)
        self.business_segment_radio_option.click()

    def scroll_down_to_save_if_needed(self):
        # Find the element by its text content
        element = self.page.locator("text=Save").nth(1)
        element.scroll_into_view_if_needed()

    # def scroll_down_to_an_ad_with_adcopy_if_needed(self, ad_with_adcopy_text_label):
    #     # Find the element by its text content
    #     # element = self.page.locator("text=Save").nth(1)
    #     print(f"In scroll_down_to_an_ad_with_adcopy_if_needed and looking for link label {ad_with_adcopy_text_label}")
    #     element = self.page.locator(f"text={ad_with_adcopy_text_label}").first()
    #     element.scroll_into_view_if_needed()

    def scroll_down_to_an_ad_with_adcopy_if_needed(self, ad_with_adcopy_text_label):
        print(f"In scroll_down_to_an_ad_with_adcopy_if_needed and looking for link label {ad_with_adcopy_text_label}")

        # Explicitly wait for the element to be present before trying to scroll
        try:
            element = self.page.wait_for_selector(f"text={ad_with_adcopy_text_label}",
                                                  timeout=60000)  # Increased timeout
            element.scroll_into_view_if_needed()
        except TimeoutError:
            print(f"Timeout waiting for ad: {ad_with_adcopy_text_label}. It may not exist on the page.")
            raise

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

class ScenarioContentPage:
    def __init__(self, page):
        self.page = page
        self.scenario_name_text_field = page.locator("#name")
        self.headline_text_field = page.locator("#headline")
        self.body_copy_text_field = page.locator("#body_copy")
        self.link_label_text_field = page.locator("#link_label")
        self.link_text_field = page.locator("#link")
        self.save_and_continue_button = page.get_by_text("Save and Continue")

    def input_scenario_content(self, scenario_name, headline, body, link_label, link, screenshots_directory):
        self.page.wait_for_load_state("networkidle")  # Ensure the page is fully loaded
        # Wait for the button to be visible and then click
        self.page.wait_for_selector("#name", state="visible", timeout=10000)
        self.scenario_name_text_field.fill(scenario_name)
        self.page.wait_for_selector("#headline", state="visible", timeout=10000)
        self.headline_text_field.fill(headline)
        self.page.wait_for_selector("#body_copy", state="visible", timeout=10000)
        self.body_copy_text_field.fill(body)
        # No link label if signed in as a trustone staff
        # self.page.wait_for_selector("#link_label", state="visible", timeout=10000)
        # self.link_label_text_field.fill(link_label)
        self.page.wait_for_selector("#link", state="visible", timeout=10000)
        self.link_text_field.fill(link)

    def click_save_and_continue_button_after_content_entry(self):
        # self.page.wait_for_selector("#getselectedpoints_top", state="visible", timeout=10000)
        self.page.wait_for_selector(".btn-success", state="visible", timeout=10000)
        self.save_and_continue_button.click()

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

    def validate_link_url_after_segment_an_existing_content(self, link_url, base_url, param_patterns):
        print(f"Link URL after segmenting content: {link_url}")
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
findata_user = os.environ.get("FINDATA_VYS_USER")
findata_pw = os.environ.get("FINDATA_VYS_PW")
findata_otp = os.environ.get("FINDATA_VYS_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables FINDATA_VYS_USER, FINDATA_VYS_PW, FINDATA_VYS_OTP or TEST_ENVIRONMENT are not set!")

# Configure TOTP using pyotp
totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")

@pytest.fixture(scope="function")
def browser_context():
    """Fixture to set up and tear down the Playwright browser context."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        # Pass HTTP credentials directly while creating the new context
        context = browser.new_context(http_credentials={"username": "trustonestage", "password": "TruStone2024!!"})
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

def test_segment_an_existing_content(browser_context):
    # Define the base URL and parameter patterns
    name_and_text_label_of_ad_with_adcopy = "Earn Higher Interest with a CD"
    selected_segment = "business"
    base_url = f'https://{test_env}finalyticsdata.com/scenarios/setup-complete'
    preview_staging_base_url = f'https://www.stgfinalyticsdemo.com/'  # Staging URL is for vys if used a vys account
    # param_patterns = {
    #     "ad_ids": r"\d+",  # Match any digits for ad_ids
    #     "asset_id": r"\d+",  # Match any digits for asset_id
    #     "adcopy_id": r"\d+",  # Match any digits for adcopy_id
    # }
    # New param patters
    param_patterns = {
        "ad_ids": r"\d+",  # Match any digits for ad_ids
        "asset_id": r"\d+",  # Match any digits for asset_id
        "adcopy_id": r"\d+",  # Match any digits for adcopy_id
        "products_recommended": r"cd"  # Match the selected product
    }
    # preview_staging_param_patterns = {
    #     "ad_ids": r"\d+",  # Match any digits for ad_ids
    #     "api": r"stg",
    #     "segments": r"business" # Match the selected segment
    # }
    # New preview staging URL pattern
    preview_staging_param_patterns = {
        "ad_ids": r"\d+",  # Match any digits for ad_ids
        "api": r"stg",
        "segments": r"business", # Match the selected segment
        "products_recommended": r"cd"  # Match the selected product
    }
    create_scenario_relative_url = "/scenarios/create-single-scenario"
    publish_campaign_to_production_relative_url = "/scenarios/campaigns-list/publish/1"

    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)
    segment_existing_content_page = SegmentExistingContent(page)
    input_scenario_content_page = ScenarioContentPage(page)
    enter_image_url_page = UploadImage(page)
    scenario_setup_complete_page = ScenarioSetupCompletePage(page)

    # Only clear directory used in this test
    screenshots_directory = 'screenshots_adminsite_using_pytest/segment_existing_content/'
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
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # After login, navigate to segment an existing content module and input scenario content page AND pass the ad to use
    input_scenario_content_page = segment_existing_content_page.navigate_to_input_scenario_content(screenshots_directory)
    input_scenario_content_page.take_screenshot(f'{screenshots_directory}4_input_scenario_content_page.png')
    # Input the Scenario Content
    try:
        input_scenario_content_page.input_scenario_content(name_and_text_label_of_ad_with_adcopy, name_and_text_label_of_ad_with_adcopy, name_and_text_label_of_ad_with_adcopy, "Learn More", "/personal/bank/cd?segments=retired", screenshots_directory)
    except ValueError as e:
        print(f"Error: {e}")
        return
    # Take screenshot of input scenario content with fields populated
    input_scenario_content_page.take_screenshot(f'{screenshots_directory}5_input_scenario_content_page_after_fields_were_populated.png')

    # Click Save and Continue after input scenario content entry goes to upload image page
    input_scenario_content_page.click_save_and_continue_button_after_content_entry()
    input_scenario_content_page.take_screenshot(f'{screenshots_directory}6_upload_image_page.png')

    # Enter the image URL and continue
    enter_image_url_page.fill_image_url("https://www.stgfinalyticsdemo.com/static/app/assets/images/cd-family.jpg")
    enter_image_url_page.take_screenshot(f'{screenshots_directory}7_upload_image_page_with_url.png')
    enter_image_url_page.click_continue_button()

    # Select a segment
    segment_existing_content_page.click_business_segment()
    segment_existing_content_page.take_screenshot(f'{screenshots_directory}8_choose_segment_to_target_page_with_a_segment_selected.png')

    # Scroll down to view the Save button and save
    segment_existing_content_page.scroll_down_to_save_if_needed()
    segment_existing_content_page.take_screenshot(f'{screenshots_directory}9_choose_segment_to_target_page_after_scrolling_to_save.png')
    segment_existing_content_page.click_save_button()

    if not scenario_setup_complete_page.validate_url_after_segment_an_existing_content(base_url, param_patterns):
        raise AssertionError("Scenario setup complete URL does not match the expected pattern.")

    print(f"Current URL after successful scenario completion is {page.url}")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(page)

    # Scenario Setup Complete screenshot with buttons to validate
    scenario_setup_complete_page.take_screenshot(f'{screenshots_directory}10_scenario_setup_complete_page.png')

    # Get the link of preview now staging button instead of clicking since can control and use the tab, assert the URL and open it in a new tab and taken screenshot
    preview_staging_link_url = scenario_setup_complete_page.get_link_of_preview_now_staging_button()
    if not scenario_setup_complete_page.validate_link_url_after_segment_an_existing_content(preview_staging_link_url, preview_staging_base_url, preview_staging_param_patterns):
        raise AssertionError(f"Preview Now (Staging) button URL {preview_staging_link_url} does not match the expected URL using preview_staging_base_url {preview_staging_base_url} and parameters {preview_staging_param_patterns}")

    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab(preview_staging_link_url)
    new_tab.wait_for_load_state("networkidle", timeout=60000)
    new_tab.screenshot(path=f'{screenshots_directory}11_preview_not_staging_page.png')
    print("Preview Now staging page saved as 11_preview_not_staging_page.png")

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
    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab(create_another_scenario_link_url)
    new_tab.wait_for_load_state("networkidle")
    new_tab.screenshot(path=f'{screenshots_directory}11_create_another_scenario_link_page.png')
    print("Create Another Scenario page saved as 11_create_another_scenario_link_page.png")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(new_tab)

    # Get the link of the publish campaign to production button instead of clicking since can control and use the tab, assert the URL and open it in a new tab and taken screenshot
    publish_campaign_to_production_link_relative_url = scenario_setup_complete_page.get_link_of_publish_campaign_to_production_button()
    print(f'Relative URL of Publish Campaign to production button link is: {publish_campaign_to_production_link_relative_url}')
    # Assert the URL
    if publish_campaign_to_production_link_relative_url != publish_campaign_to_production_relative_url:
        raise AssertionError(
            f"Publish Campaign to Production button relative URL link {publish_campaign_to_production_link_relative_url} does not match the expected URL {publish_campaign_to_production_relative_url}")

    # Open the publish_campaign_to_production_link_relative_url in a new tab, take a screenshot and check that there are no errors
    new_tab = scenario_setup_complete_page.open_a_scenario_setup_complete_link_in_new_tab(publish_campaign_to_production_link_relative_url)
    new_tab.wait_for_load_state("load")
    new_tab.screenshot(path=f'{screenshots_directory}12_publish_campaign_to_production_page.png')
    print("Publish campaign to production page saved as 12_publish_campaign_to_production_page.png")

    # Check that the page does not have any internal server error or any error message
    validate_no_server_error(new_tab)


