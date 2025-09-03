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

class PublishUnpublishPage:
    """Page object for campaign publish/unpublish functionality."""
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.campaigns_nav_link = page.get_by_text("Campaigns")
        self.publish_button = page.get_by_role("button", name="Publish")
        self.unpublish_button = page.get_by_role("button", name="Unpublish")
        
    def navigate_to_campaigns(self, screenshots_directory):
        self.admin_link.click()
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.campaigns_nav_link.wait_for(state="visible", timeout=30000)
        self.campaigns_nav_link.click()
        self.page.wait_for_load_state("networkidle")

    def publish_campaign(self):
        self.publish_button.click()
        self.page.wait_for_load_state("networkidle")

    def unpublish_campaign(self):
        self.unpublish_button.click()
        self.page.wait_for_load_state("networkidle")

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
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to campaigns
        publish_page.navigate_to_campaigns(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_campaigns_page.png')
        
        # Publish campaign
        publish_page.publish_campaign()
        page.screenshot(path=f'{screenshots_directory}4_campaign_published.png')
        print("Campaign published successfully")
        
        # Unpublish campaign
        publish_page.unpublish_campaign()
        page.screenshot(path=f'{screenshots_directory}5_campaign_unpublished.png')
        print("Campaign unpublished successfully")
        
        page.screenshot(path=f'{screenshots_directory}6_final_publish_unpublish_state.png')
        
    except Exception as e:
        print(f"Error during publish/unpublish campaign test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_publish_unpublish.png')
        raise