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
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.campaigns_nav_link = page.get_by_text("Campaigns")
        self.utm_connector_link = page.get_by_text("UTM Campaign Connector")
        self.connect_button = page.get_by_role("button", name="Connect")
        
    def navigate_to_utm_connector(self, screenshots_directory):
        self.admin_link.click()
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.campaigns_nav_link.wait_for(state="visible", timeout=30000)
        self.campaigns_nav_link.click()
        self.page.wait_for_load_state("networkidle")

        self.utm_connector_link.wait_for(state="visible", timeout=30000)
        self.utm_connector_link.click()
        self.page.wait_for_load_state("networkidle")

    def connect_to_campaign(self):
        self.connect_button.click()
        self.page.wait_for_load_state("networkidle")

def test_connect_to_a_campaign(admin_browser_context_sync):
    """Test connecting to a campaign using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/connect_campaign/'
    
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
        # Navigate to UTM campaign connector
        utm_connector_page.navigate_to_utm_connector(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_utm_connector_page.png')
        
        # Connect to campaign
        utm_connector_page.connect_to_campaign()
        page.screenshot(path=f'{screenshots_directory}4_campaign_connected.png')
        
        print("Successfully connected to campaign")
        page.screenshot(path=f'{screenshots_directory}5_final_campaign_connection_state.png')
        
    except Exception as e:
        print(f"Error during campaign connection test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_campaign_connection.png')
        raise