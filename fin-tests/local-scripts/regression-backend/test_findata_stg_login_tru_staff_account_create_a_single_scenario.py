import pytest
import time
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

class CreateASingleScenarioPage:
    """Page object for creating single scenarios using the scenario wizard."""
    def __init__(self, page):
        self.page = page
        # self.admin_link = page.get_by_text("Admin").nth(0)  # Admin link no longer exists
        self.scenarios_nav_link = page.get_by_text("Scenarios").first  # Use .first to get main Scenarios link
        self.create_new_scenario_link = page.get_by_text("Create New Scenario")
        self.create_a_single_scenario_link = page.get_by_text("Create a Single Scenario").first
        # self.target_a_product_checkbox = page.get_by_label("Target a Product")
        # UI has changed - Dark Matter: Product is now a styled button card, click the visible label
        self.target_a_product_checkbox = page.get_by_text("Product", exact=True)
        self.continue_button = page.get_by_text("Continue")
        # AUTO LOAN is changed to CAR LOAN in the new UI
        self.car_loan_link = page.get_by_text("Car Loan").first
        self.choose_homepage = page.get_by_text("Home Page")
        self.home_hero_template_link = page.get_by_text("Trustone Financial | home hero")

    def navigate_to_single_scenario_wizard(self, screenshots_directory):
        """Navigate: Scenarios → Create New Scenario → Create a Single Scenario"""
        # Admin link no longer exists, start directly with Scenarios
        self.scenarios_nav_link.wait_for(state="visible", timeout=30000)
        self.scenarios_nav_link.click()
        print("Clicked Scenarios link...")
        self.page.wait_for_load_state("networkidle")

        self.create_new_scenario_link.wait_for(state="visible", timeout=30000)
        self.create_new_scenario_link.click()
        print("Clicked Create New Scenario link...")
        self.page.wait_for_load_state("networkidle")

        self.create_a_single_scenario_link.wait_for(state="visible", timeout=30000)
        self.create_a_single_scenario_link.click()
        print("Clicked Create a Single Scenario link...")
        self.page.wait_for_load_state("networkidle")

    def configure_scenario_wizard(self):
        """Check 'Target a Product' → Continue → Select Car Loan → Select Home Page → Select Template"""
        # Click "Product" button card (Dark Matter UI: styled card, not a raw checkbox)
        self.target_a_product_checkbox.wait_for(state="visible", timeout=30000)
        self.target_a_product_checkbox.click()
        self.page.wait_for_load_state("networkidle")
        print("Clicked Product button card...")

        # Click Continue button
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()
        print("Clicked Continue button...")
        self.page.wait_for_load_state("networkidle")

        # Select Car Loan product type
        self.car_loan_link.wait_for(state="visible", timeout=30000)
        self.car_loan_link.click()
        print("Clicked Car Loan link...")
        self.page.wait_for_load_state("networkidle")

        # Select Home Page
        self.choose_homepage.wait_for(state="visible", timeout=30000)
        self.choose_homepage.click()
        print("Clicked Home Page link...")
        self.page.wait_for_load_state("networkidle")

        # Select template
        self.home_hero_template_link.wait_for(state="visible", timeout=30000)
        self.home_hero_template_link.click()
        print("Clicked Trustone Financial | home hero template...")
        self.page.wait_for_load_state("networkidle")

def test_create_a_single_scenario(admin_browser_context_sync):
    """Test creating a single scenario using the scenario creation wizard."""
    page = admin_browser_context_sync.new_page()

    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = os.path.join(os.path.dirname(__file__), 'screenshots_adminsite_using_pytest/create_scenario/')

    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)

    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    scenario_page = CreateASingleScenarioPage(page)

    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()

    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)

    try:
        # Navigate through the scenario wizard: Scenarios → Create New Scenario → Create a Single Scenario
        scenario_page.navigate_to_single_scenario_wizard(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}2_create_single_scenario_page.png')

        # Configure the scenario: Target Product → Continue → Car Loan → Home Page → Template
        scenario_page.configure_scenario_wizard()
        page.screenshot(path=f'{screenshots_directory}3_scenario_wizard_configured.png')

        print("Successfully navigated through scenario creation wizard")
        page.screenshot(path=f'{screenshots_directory}4_final_scenario_wizard_state.png')

    except Exception as e:
        print(f"Error during scenario creation test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_scenario_creation.png')
        raise