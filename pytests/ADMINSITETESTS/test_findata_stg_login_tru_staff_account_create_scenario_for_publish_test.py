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

class CreateScenarioForPublishTestPage:
    """Page object for creating scenarios for the Test Core Products Publish and Test campaign."""
    def __init__(self, page):
        self.page = page
        self.scenarios_nav_link = page.get_by_text("Scenarios").first
        self.create_new_scenario_link = page.get_by_text("Create New Scenario")
        self.create_a_single_scenario_link = page.get_by_text("Create a Single Scenario").first
        self.target_a_product_checkbox = page.get_by_label("Target a Product")
        self.continue_button = page.get_by_text("Continue").first
        self.save_and_continue_button = page.get_by_role("button", name="Save and Continue")
        self.car_loan_link = page.get_by_text("Car Loan").first
        self.choose_homepage = page.get_by_text("Home Page")
        self.home_hero_template_link = page.get_by_text("Trustone Financial | home hero")
        # Step 4: Scenario Group selection
        self.test_scenario_group_link = page.get_by_text("Test Core Products Publish and Test | Mode:Test (Published)")
        self.save_button = page.get_by_text("Save")

    def navigate_to_single_scenario_wizard(self, screenshots_directory):
        """Navigate: Scenarios > Create New Scenario > Create a Single Scenario"""
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

    def configure_scenario_wizard(self, screenshots_directory):
        """Complete all wizard steps: Type > Placement > Content > Scenario Group > Save"""
        # Step 1: Check "Target a Product" checkbox
        self.target_a_product_checkbox.check()
        self.page.wait_for_load_state("networkidle")
        print("Checked Target a Product checkbox...")
        self.page.screenshot(path=f'{screenshots_directory}2_step1_target_product.png')

        # Click Continue to go to Step 2
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()
        print("Clicked Continue button (Step 1 to Step 2)...")
        self.page.wait_for_load_state("networkidle")

        # Step 2: Select Car Loan product type
        self.car_loan_link.wait_for(state="visible", timeout=30000)
        self.car_loan_link.click()
        print("Clicked Car Loan link...")
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}3_step2_car_loan.png')

        # Step 2: Select Home Page
        self.choose_homepage.wait_for(state="visible", timeout=30000)
        self.choose_homepage.click()
        print("Clicked Home Page link...")
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}4_step2_homepage.png')

        # Step 2: Select template
        self.home_hero_template_link.wait_for(state="visible", timeout=30000)
        self.home_hero_template_link.click()
        print("Clicked Trustone Financial | home hero template...")
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}5_step2_template.png')

        # Step 3: Enter content (already on this page after template selection)
        # Fill in scenario name
        scenario_name = f"Test Scenario {int(time.time())}"
        scenario_name_input = self.page.get_by_label("Scenario Name")
        scenario_name_input.wait_for(state="visible", timeout=30000)
        scenario_name_input.fill(scenario_name)
        print(f"Entered scenario name: {scenario_name}")

        # Fill in headline
        headline_input = self.page.get_by_label("Headline")
        headline_input.fill("Test Car Loan Offer")

        # Fill in subheader
        subheader_input = self.page.get_by_label("Subheader")
        subheader_input.fill("Great rates on auto loans")

        # Fill in body copy
        body_copy_input = self.page.get_by_label("Body copy")
        body_copy_input.fill("Get pre-approved today with competitive rates.")

        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}6_step3_content.png')
        print("Filled in content fields...")

        # Click Save and Continue to go to Step 4 (Scenario Group)
        self.save_and_continue_button.wait_for(state="visible", timeout=30000)
        self.save_and_continue_button.click()
        print("Clicked Save and Continue button (Step 3 to Step 4)...")
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}7_step4_scenario_group_selection.png')

        # Step 4: Select "Test Core Products Publish and Test" scenario group
        # Try to find the link - it might need scrolling or may be a partial match
        try:
            # Try exact match first
            self.test_scenario_group_link.wait_for(state="visible", timeout=10000)
            self.test_scenario_group_link.click()
            print("Selected 'Test Core Products Publish and Test | Mode:Test (Published)' scenario group...")
        except:
            # Try partial match
            print("Exact match not found, trying partial match...")
            partial_match = self.page.get_by_text("Test Core Products Publish", exact=False).first
            partial_match.wait_for(state="visible", timeout=30000)
            # Scroll into view if needed
            partial_match.scroll_into_view_if_needed()
            partial_match.click()
            print("Selected scenario group using partial match...")

        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}8_step4_selected_scenario_group.png')

        # Step 5: Click Continue to finish (wizard will auto-complete and show success)
        self.continue_button.wait_for(state="visible", timeout=30000)
        self.continue_button.click()
        print("Clicked Continue button to complete wizard...")
        self.page.wait_for_load_state("networkidle")

        # Verify success
        success_message = self.page.get_by_text("Scenario Setup Complete")
        success_message.wait_for(state="visible", timeout=30000)
        print("Scenario created successfully!")
        self.page.screenshot(path=f'{screenshots_directory}9_scenario_created_success.png')

def test_create_scenario_for_publish_test(admin_browser_context_sync):
    """Create a scenario in the 'Test Core Products Publish and Test' campaign for the publish/unpublish test."""
    page = admin_browser_context_sync.new_page()

    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/create_scenario_for_publish/'

    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)

    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    scenario_page = CreateScenarioForPublishTestPage(page)

    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    login_page.complete_2fa_login(test_env)

    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)

    try:
        # Navigate through the scenario wizard
        scenario_page.navigate_to_single_scenario_wizard(screenshots_directory)

        # Complete the full wizard including selecting the scenario group
        scenario_page.configure_scenario_wizard(screenshots_directory)

        print("Successfully created scenario for 'Test Core Products Publish and Test' campaign")
        page.screenshot(path=f'{screenshots_directory}11_final_success.png')

    except Exception as e:
        print(f"Error during scenario creation for publish test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_scenario_creation.png')
        raise
