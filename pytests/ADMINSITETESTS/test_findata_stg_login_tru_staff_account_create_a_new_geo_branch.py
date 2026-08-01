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

class CreateGeoBranchScenario:
    """Page object for geo branch scenario creation."""
    def __init__(self, page):
        self.page = page
        # self.admin_link = page.get_by_text("Admin").nth(0)  # Admin link no longer exists
        self.scenarios_link = page.get_by_text("Scenarios").first
        self.create_new_scenario_link = page.get_by_text("Create New Scenario")
        self.branch_events_link = page.get_by_text("Branch Events")
        self.branch_opening_link = page.get_by_text("Branch Opening")
        self.continue_button = page.get_by_text("Continue")

    def navigate_to_zipcode_text_field(self, screenshots_directory):
        """Navigate: Scenarios → Create New Scenario → Branch Events → Branch Opening"""
        # Admin link no longer exists, start directly with Scenarios
        self.scenarios_link.wait_for(state="visible", timeout=30000)
        self.scenarios_link.click()
        print("Clicked Scenarios link...")
        self.page.wait_for_load_state("networkidle")

        self.create_new_scenario_link.wait_for(state="visible", timeout=30000)
        self.create_new_scenario_link.click()
        print("Clicked Create New Scenario link...")
        self.page.wait_for_load_state("networkidle")

        self.branch_events_link.wait_for(state="visible", timeout=30000)
        self.branch_events_link.click()
        print("Clicked Branch Events link...")
        self.page.wait_for_load_state("networkidle")

        self.branch_opening_link.wait_for(state="visible", timeout=30000)
        self.branch_opening_link.click()
        print("Clicked Branch Opening link...")
        self.page.wait_for_load_state("networkidle")

        return ZipCodePage(self.page)

    def click_continue_button(self):
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")

class ZipCodePage:
    """Page object for zip code entry and continuation."""
    def __init__(self, page):
        self.page = page
        self.zipcode_text_field = page.locator("#zipcode")
        self.continue_button = page.get_by_text("Continue").first

    def fill_zipcode(self, zipcode):
        """Fill in the zipcode field with validation."""
        if not zipcode.isdigit() or len(zipcode) != 5:
            raise ValueError("Invalid ZIP code. Please provide a 5-digit numeric code.")

        self.page.wait_for_selector("#zipcode", state="visible", timeout=10000)
        self.zipcode_text_field.fill(zipcode)
        print(f"Entered ZIP code: {zipcode}")

    def click_continue_button_after_zipcode_entry(self):
        """Click continue after entering zipcode."""
        self.page.wait_for_selector(".btn-success", state="visible", timeout=10000)
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")

    def click_continue_button_on_counties_page(self):
        """Click continue on the counties selection page."""
        self.page.wait_for_selector("#getselectedpoints_top", state="visible", timeout=10000)
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")

def test_create_a_new_geo_branch(admin_browser_context_sync):
    """Test creating a new geo branch using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()

    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = os.path.join(os.path.dirname(__file__), 'screenshots_adminsite_using_pytest/create_geo_branch/')

    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)

    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    geo_branch_page = CreateGeoBranchScenario(page)

    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()

    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)

    try:
        # Navigate to zipcode text field: Scenarios → Create New Scenario → Branch Events → Branch Opening
        zip_code_page = geo_branch_page.navigate_to_zipcode_text_field(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}2_branch_opening_zipcode_form.png')

        # Fill zipcode and continue
        test_zip = "30388"
        zip_code_page.fill_zipcode(test_zip)
        page.screenshot(path=f'{screenshots_directory}3_zipcode_entered.png')

        # Click continue after entering zipcode
        zip_code_page.click_continue_button_after_zipcode_entry()
        page.screenshot(path=f'{screenshots_directory}4_counties_page.png')

        # Click continue on counties selection page
        zip_code_page.click_continue_button_on_counties_page()
        page.screenshot(path=f'{screenshots_directory}5_after_counties_continue.png')

        print(f"Successfully navigated geo branch creation flow for zip {test_zip}")
        page.screenshot(path=f'{screenshots_directory}6_final_geo_branch_state.png')

    except Exception as e:
        print(f"Error during geo branch creation test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_geo_branch_creation.png')
        raise