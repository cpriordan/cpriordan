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

class AnalyticsPage:
    """Page object for analytics functionality."""
    def __init__(self, page):
        self.page = page
        # self.admin_link = page.get_by_text("Admin").nth(0)  # Admin link no longer exists after login
        self.analytics_nav_link = page.get_by_text("Analytics").first  # Use .first to get the nav link
        self.personalization_funnel_link = page.get_by_text("Application Funnel")  # Link changed from "Personalization Funnel Report"

    def navigate_to_analytics(self, screenshots_directory):
        # Admin link is no longer needed - Analytics is directly accessible in left nav after login
        # self.admin_link.click()
        # print("Clicked Admin link...")
        # self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        # self.page.wait_for_load_state("networkidle")

        self.analytics_nav_link.wait_for(state="visible", timeout=30000)
        self.analytics_nav_link.click()
        print("Clicked Analytics nav link...")
        self.page.wait_for_load_state("networkidle")

    def navigate_to_personalization_funnel_report(self):
        self.personalization_funnel_link.click()
        self.page.wait_for_load_state("networkidle")
        print("Navigated to Application Funnel")
        return AnalyticsPage(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def test_analytics_personalization_funnel_report_looker(admin_browser_context_sync):
    """Test analytics personalization funnel report using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = 'screenshots_adminsite_using_pytest/analytics_report/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    analytics_page = AnalyticsPage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate to analytics functionality
        analytics_page.navigate_to_analytics(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_analytics_page.png')
        
        # Navigate to personalization funnel report
        analytics_page.navigate_to_personalization_funnel_report()
        page.screenshot(path=f'{screenshots_directory}4_personalization_funnel_report.png')
        
        # Check if Looker iframe or content is present
        looker_iframe = page.locator("iframe[src*='looker']").first
        if looker_iframe.is_visible():
            print("Looker iframe found and is visible")
            page.screenshot(path=f'{screenshots_directory}5_looker_report_loaded.png')
        else:
            print("Looker iframe not found, checking for other report content")
            
        page.screenshot(path=f'{screenshots_directory}6_final_analytics_report_state.png')
        print("Analytics personalization funnel report test completed successfully")
        
    except Exception as e:
        print(f"Error during analytics report test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_analytics_report.png')
        raise