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

class PublishUnpublishPage:
    """Page object for campaign publish/unpublish functionality."""
    def __init__(self, page):
        self.page = page
        self.scenarios_menu_link = page.get_by_text("Scenarios").first
        self.publish_unpublish_scenarios_link = page.get_by_text("Publish/Unpublish Scenarios").first
        # Use href to target the specific publish/unpublish links
        self.publish_scenarios_link = page.locator('a[href="/scenarios/campaigns-list/publish"]')
        self.unpublish_scenarios_link = page.locator('a[href="/scenarios/campaigns-list/unpublish"]')

        # Campaign and content selectors - using existing test campaign
        self.test_scenario_group_to_publish = page.get_by_text("Test Core Products Publish and Test | Mode:Test (Published)")
        self.test_scenario_group_to_unpublish = page.get_by_text("Core Products Publish and Test | Mode:Prod")
        # Select any checkbox for content module (more flexible than looking for specific name)
        self.first_checkbox_content_module = page.locator('input[type="checkbox"]').first
        self.choose_existing_production_target_button = page.get_by_text("Choose Existing Production Target")
        self.existing_production_group = page.get_by_text("Core Products Publish and Test | Mode:Prod")
        self.publish_confirmation_button = page.get_by_text("Publish!")
        self.unpublish_button = page.get_by_text("Unpublish Selected Scenarios")

    def create_test_scenario(self, screenshots_directory):
        """Create a test scenario in the 'Test Core Products Publish and Test' campaign."""
        print("Creating test scenario for publish/unpublish test...")

        # Navigate: Scenarios > Create New Scenario > Create a Single Scenario
        self.scenarios_menu_link.wait_for(state="visible", timeout=30000)
        self.scenarios_menu_link.click()
        print("Clicked Scenarios link...")
        self.page.wait_for_load_state("networkidle")

        create_new_scenario_link = self.page.get_by_text("Create New Scenario")
        create_new_scenario_link.wait_for(state="visible", timeout=30000)
        create_new_scenario_link.click()
        print("Clicked Create New Scenario link...")
        self.page.wait_for_load_state("networkidle")

        create_single_scenario_link = self.page.get_by_text("Create a Single Scenario").first
        create_single_scenario_link.wait_for(state="visible", timeout=30000)
        create_single_scenario_link.click()
        print("Clicked Create a Single Scenario link...")
        self.page.wait_for_load_state("networkidle")

        # Step 1: Check "Target a Product" and continue
        target_product_checkbox = self.page.get_by_label("Target a Product")
        target_product_checkbox.check()
        self.page.wait_for_load_state("networkidle")
        print("Checked Target a Product checkbox...")

        continue_button = self.page.get_by_text("Continue").first
        continue_button.click()
        self.page.wait_for_load_state("networkidle")

        # Step 2: Select Car Loan > Home Page > Template
        car_loan_link = self.page.get_by_text("Car Loan").first
        car_loan_link.click()
        self.page.wait_for_load_state("networkidle")

        home_page_link = self.page.get_by_text("Home Page")
        home_page_link.click()
        self.page.wait_for_load_state("networkidle")

        template_link = self.page.get_by_text("Trustone Financial | home hero")
        template_link.click()
        self.page.wait_for_load_state("networkidle")
        print("Selected template...")

        # Step 3: Fill in content
        scenario_name = f"Test Scenario {int(time.time())}"
        self.page.get_by_label("Scenario Name").fill(scenario_name)
        self.page.get_by_label("Headline").fill("Test Car Loan Offer")
        self.page.get_by_label("Subheader").fill("Great rates on auto loans")
        self.page.get_by_label("Body copy").fill("Get pre-approved today.")
        print(f"Filled in content for scenario: {scenario_name}")

        # Save and Continue to Step 4
        save_continue_button = self.page.get_by_role("button", name="Save and Continue")
        save_continue_button.click()
        self.page.wait_for_load_state("networkidle")

        # Step 4: Select "Test Core Products Publish and Test" scenario group
        try:
            test_group = self.page.get_by_text("Test Core Products Publish and Test | Mode:Test (Published)")
            test_group.wait_for(state="visible", timeout=10000)
            test_group.click()
        except:
            # Try partial match if exact doesn't work
            test_group = self.page.get_by_text("Test Core Products Publish", exact=False).first
            test_group.scroll_into_view_if_needed()
            test_group.click()
        print("Selected Test Core Products Publish and Test campaign...")
        self.page.wait_for_load_state("networkidle")

        # Click Continue to complete wizard
        continue_button = self.page.get_by_text("Continue").first
        continue_button.click()
        self.page.wait_for_load_state("networkidle")

        # Verify success
        success_message = self.page.get_by_text("Scenario Setup Complete")
        success_message.wait_for(state="visible", timeout=30000)
        print(f"Successfully created scenario: {scenario_name}")
        self.page.screenshot(path=f'{screenshots_directory}0_scenario_created.png')

    def navigate_to_publish_unpublish(self):
        """Navigate to Publish/Unpublish Scenarios page."""
        # Click Scenarios menu
        self.scenarios_menu_link.wait_for(state="visible", timeout=30000)
        self.scenarios_menu_link.click()
        print("Clicked Scenarios menu link...")
        self.page.wait_for_load_state("networkidle")

        # Click Publish/Unpublish Scenarios submenu
        self.publish_unpublish_scenarios_link.wait_for(state="visible", timeout=30000)
        self.publish_unpublish_scenarios_link.click()
        print("Clicked Publish/Unpublish Scenarios link...")
        self.page.wait_for_load_state("networkidle")

    def publish_campaign(self, screenshots_directory):
        """Publish a test campaign to production."""
        # Click Publish Scenarios link
        self.publish_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}2_publish_scenarios_page.png')

        # Select existing STG campaign
        self.test_scenario_group_to_publish.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}3_selected_stg_campaign.png')

        # Select content module checkbox
        self.first_checkbox_content_module.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}4_selected_content_module.png')

        # Choose existing production target
        self.choose_existing_production_target_button.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}5_production_targets.png')

        # Select production campaign
        self.existing_production_group.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}6_ready_to_publish.png')

        # Confirm publish
        self.publish_confirmation_button.click()
        self.page.wait_for_load_state("networkidle")
        print("Published campaign successfully")

    def unpublish_campaign(self, screenshots_directory):
        """Unpublish a campaign from production."""
        # Click Unpublish Scenarios link
        self.unpublish_scenarios_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}8_unpublish_scenarios_page.png')

        # Select campaign to unpublish
        self.test_scenario_group_to_unpublish.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}9_selected_campaign_to_unpublish.png')

        # Select content module
        self.first_checkbox_content_module.click()
        self.page.wait_for_load_state("networkidle")
        print("Selected scenario to unpublish")
        self.page.screenshot(path=f'{screenshots_directory}10_selected_content_to_unpublish.png')

        # Click unpublish button
        self.unpublish_button.click()
        self.page.wait_for_load_state("networkidle")
        print("Unpublished campaign successfully")

    def validate_publish_success(self):
        """Validate that publish was successful."""
        success_message = self.page.locator(".card-body > p:nth-child(1) > b:nth-child(1)").text_content().strip()
        print(f"Publish success message: {success_message}")
        assert "Success! Content modules were published!" in success_message
        return True

    def validate_unpublish_success(self):
        """Validate that unpublish was successful."""
        success_message = self.page.locator(".card-body > p:nth-child(1) > b:nth-child(1)").text_content().strip()
        print(f"Unpublish success message: {success_message}")
        assert "Success! Content modules were unpublished!" in success_message
        return True

def test_publish_and_unpublish_campaign(admin_browser_context_sync):
    """Test publishing and unpublishing campaigns using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/publish_unpublish_campaign/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    publish_page = PublishUnpublishPage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    login_page.complete_2fa_login(test_env)

    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)

    try:
        # Create a test scenario to ensure the campaign has content to publish
        publish_page.create_test_scenario(screenshots_directory)

        # Navigate to Publish/Unpublish Scenarios page
        publish_page.navigate_to_publish_unpublish()
        page.screenshot(path=f'{screenshots_directory}1_publish_unpublish_page.png')

        # Publish campaign
        publish_page.publish_campaign(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}7_campaign_published.png')

        # Validate publish success
        publish_page.validate_publish_success()
        print("Successfully published campaign")

        # Navigate back to publish/unpublish page for unpublish
        publish_page.navigate_to_publish_unpublish()

        # Unpublish campaign
        publish_page.unpublish_campaign(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}11_campaign_unpublished.png')

        # Validate unpublish success
        publish_page.validate_unpublish_success()
        print("Successfully unpublished campaign")

        page.screenshot(path=f'{screenshots_directory}12_final_publish_unpublish_state.png')

    except Exception as e:
        print(f"Error during publish/unpublish campaign test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_publish_unpublish.png')
        raise