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

class UTMCampaignConnectorPage:
    """Page object for UTM campaign connector functionality."""
    def __init__(self, page):
        self.page = page
        self.scenarios_menu_link = page.get_by_text("Scenarios").first
        self.create_new_scenario_link = page.get_by_text("Create New Scenario").first
        self.external_campaign_link = page.get_by_text("Connect to an External/Paid Campaign").first
        self.single_campaign_url_link = page.get_by_text("Single Campaign URL")
        self.continue_button = page.get_by_text("Continue")

    def navigate_to_utm_connector(self, screenshots_directory):
        # TRU staff navigation: Scenarios → Create New Scenario → Connect to External/Paid Campaign
        self.scenarios_menu_link.wait_for(state="visible", timeout=30000)
        self.scenarios_menu_link.click()
        print("Clicked Scenarios menu link...")
        self.page.wait_for_load_state("networkidle")

        self.create_new_scenario_link.wait_for(state="visible", timeout=30000)
        self.create_new_scenario_link.click()
        print("Clicked Create New Scenario submenu...")
        self.page.wait_for_load_state("networkidle")

        self.external_campaign_link.wait_for(state="visible", timeout=30000)
        self.external_campaign_link.click()
        print("Clicked Connect to an External/Paid Campaign link...")
        self.page.wait_for_load_state("networkidle")

        # Verify we're on the campaign-type page
        print(f"Current URL: {self.page.url}")

        # Click Single Campaign URL link instead of UTM Campaign Connector
        self.single_campaign_url_link.wait_for(state="visible", timeout=30000)
        self.single_campaign_url_link.click()
        print("Clicked Single Campaign URL link...")
        self.page.wait_for_load_state("networkidle")

    def fill_campaign_form_and_submit(self, product_option, segment_option, screenshots_directory):
        """Fill out the campaign form with product and segment selections."""
        # Wait for PRODUCTS menu to load
        self.page.wait_for_selector("#select2-product-container")
        self.page.screenshot(path=f'{screenshots_directory}2_form_waiting_for_products_menu.png')

        # Select product from dropdown
        self.page.click("#select2-product-container")
        self.page.locator("li.select2-results__option", has_text=product_option).click()
        print(f"Selected product: {product_option}")
        self.page.screenshot(path=f'{screenshots_directory}3_after_product_selection.png')

        # Wait for SEGMENTS menu to load
        self.page.wait_for_selector("#select2-segment-container")
        self.page.screenshot(path=f'{screenshots_directory}4_waiting_for_segments_menu.png')

        # Select segment from dropdown
        self.page.click("#select2-segment-container")
        self.page.locator("li.select2-results__option", has_text=segment_option).click()
        print(f"Selected segment: {segment_option}")
        self.page.screenshot(path=f'{screenshots_directory}5_after_segment_selection.png')

        # Click Continue button to submit form
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")
        print(f"Submitted form, current URL: {self.page.url}")

def test_connect_to_a_campaign(admin_browser_context_sync):
    """Test connecting to a campaign using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = os.path.join(os.path.dirname(__file__), 'screenshots_adminsite_using_pytest/connect_campaign/')
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    utm_connector_page = UTMCampaignConnectorPage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to Single Campaign URL form
        utm_connector_page.navigate_to_utm_connector(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}6_single_campaign_url_form.png')

        # Fill out and submit the campaign form
        product_option = "adjustable rate mortgage"
        segment_option = "female"
        utm_connector_page.fill_campaign_form_and_submit(product_option, segment_option, screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}7_campaign_form_submitted.png')

        # Verify we're on the campaign-url page with correct parameters
        current_url = page.url
        print(f"Final URL after campaign connection: {current_url}")
        assert "scenarios/campaign-url" in current_url, f"Expected campaign-url in URL, got: {current_url}"
        assert f"utm_fin={product_option.replace(' ', '%20')}" in current_url or f"utm_fin={product_option.replace(' ', ' ')}" in current_url
        assert f"utm_segments={segment_option}" in current_url

        print("Successfully connected to campaign with product and segment")
        page.screenshot(path=f'{screenshots_directory}8_final_campaign_connection_state.png')

    except Exception as e:
        print(f"Error during campaign connection test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_campaign_connection.png')
        raise