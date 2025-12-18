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

class MultiUTMCampaignConnectorPage:
    """Page object for multi-UTM campaign connector functionality."""
    def __init__(self, page):
        self.page = page
        self.scenarios_menu_link = page.get_by_text("Scenarios").first
        self.create_new_scenario_link = page.get_by_text("Create New Scenario").first
        self.external_campaign_link = page.get_by_text("Connect to an External/Paid Campaign").first
        self.paste_list_urls_link = page.get_by_text("Paste a List of URLs")
        self.continue_button = page.get_by_text("Continue")
        self.copy_to_clipboard_link = page.get_by_text("Copy to Clipboard")

    def navigate_to_multi_utm_connector(self, screenshots_directory):
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

        # Click "Paste a List of URLs" link
        self.paste_list_urls_link.wait_for(state="visible", timeout=30000)
        self.paste_list_urls_link.click()
        print("Clicked Paste a List of URLs link...")
        self.page.wait_for_load_state("networkidle")

    def paste_urls_and_submit(self, urls_text, screenshots_directory):
        """Paste multiple URLs and submit the form."""
        # Wait for textarea to paste URLs
        self.page.wait_for_selector("#urls")
        self.page.screenshot(path=f'{screenshots_directory}2_multi_campaign_form.png')

        # Paste URLs in the text area
        text_area = self.page.locator("#urls")
        text_area.fill(urls_text)
        print(f"Pasted {len(urls_text.strip().split(chr(10)))} URLs into textarea")
        self.page.screenshot(path=f'{screenshots_directory}3_pasted_urls.png')

        # Click Continue button
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")
        print(f"Submitted form, current URL: {self.page.url}")

    def validate_generated_urls(self):
        """Validate that generated campaign URLs contain utm_fin parameter."""
        # The page should now show generated URLs
        page_text = self.page.text_content("body")
        print(f"Generated campaign URLs page loaded")
        return "utm_fin" in page_text

def test_connect_to_multi_campaign(admin_browser_context_sync):
    """Test connecting to multi campaigns using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/connect_multi_campaign/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    multi_utm_page = MultiUTMCampaignConnectorPage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to Paste a List of URLs form
        multi_utm_page.navigate_to_multi_utm_connector(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}4_paste_urls_form.png')

        # Paste multiple URLs and submit
        multi_urls_to_paste = """https://sscustage.wpenginepowered.com/loans-and-credit-cards/personal-loans/personal-lines-of-credit/
https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/auto-loans
https://www.stgfinalyticsdemo.com/?api=stg"""

        multi_utm_page.paste_urls_and_submit(multi_urls_to_paste, screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}5_multi_campaign_urls_generated.png')

        # Verify we're on the campaign results page
        current_url = page.url
        print(f"Final URL after multi-campaign connection: {current_url}")

        # Validate that generated URLs contain utm_fin parameter
        has_utm_fin = multi_utm_page.validate_generated_urls()
        assert has_utm_fin, "Generated URLs should contain utm_fin parameter"

        print("Successfully connected to multiple campaigns with generated URLs")
        page.screenshot(path=f'{screenshots_directory}6_final_multi_campaign_state.png')

    except Exception as e:
        print(f"Error during multi campaign connection test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_multi_campaign_connection.png')
        raise