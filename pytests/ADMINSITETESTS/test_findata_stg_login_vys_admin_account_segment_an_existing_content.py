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

class ScenarioContentPage:
    """Page object for scenario content functionality."""
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.content_nav_link = page.get_by_text("Content").nth(0)
        self.scenarios_nav_link = page.get_by_text("Scenarios")
        self.first_scenario_link = page.get_by_text("Test Core Products: 2025-07").nth(0)
        self.first_ad_segment_link = page.get_by_text("Segment").nth(0)
        
    def navigate_to_scenarios(self, screenshots_directory):
        self.admin_link.click()
        print("Clicked Admin link...")
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.content_nav_link.wait_for(state="visible", timeout=30000)
        self.content_nav_link.click()
        print("Clicked Content left nav link...")
        self.page.wait_for_load_state("networkidle")

        self.scenarios_nav_link.wait_for(state="visible", timeout=30000)
        self.scenarios_nav_link.click()
        print("Clicked Scenarios nav link...")
        self.page.wait_for_load_state("networkidle")

    def navigate_to_test_core_products(self):
        self.first_scenario_link.click()
        self.page.wait_for_load_state("networkidle")
        return ScenarioContentPage(self.page)

    def click_first_ad_segment(self):
        self.first_ad_segment_link.click()
        self.page.wait_for_load_state("networkidle")
        return ScenarioContentPage(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class ScenarioSetupCompletePage:
    """Page object for scenario setup completion."""
    def __init__(self, page):
        self.page = page
        self.select_all_checkbox = page.locator("#select_all")
        self.continue_button = page.get_by_role("button", name="Continue")

    def click_select_all_checkbox(self):
        try:
            self.select_all_checkbox.wait_for(state="visible", timeout=10000)
            self.select_all_checkbox.scroll_into_view_if_needed()
            self.select_all_checkbox.check()
            print("Select all checkbox is checked.")
        except Exception as e:
            print(f"Error checking select all checkbox: {e}")
            self.page.screenshot(path="debug_select_all_error.png")
            raise

        return ScenarioSetupCompletePage(self.page)

    def click_continue_button(self):
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")
        return ScenarioSetupCompletePage(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def test_segment_an_existing_content(admin_browser_context_sync):
    """Test segmenting existing content using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = 'screenshots_adminsite_using_pytest/segment_existing_content/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    scenario_content_page = ScenarioContentPage(page)
    scenario_setup_page = ScenarioSetupCompletePage(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    try:
        # Navigate through the segmentation workflow
        scenario_content_page.navigate_to_scenarios(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_scenarios_page.png')
        
        scenario_content_page.navigate_to_test_core_products()
        page.screenshot(path=f'{screenshots_directory}4_test_core_products_page.png')
        
        scenario_content_page.click_first_ad_segment()
        page.screenshot(path=f'{screenshots_directory}5_first_ad_segment_clicked.png')
        
        # Setup segments
        scenario_setup_page.click_select_all_checkbox()
        page.screenshot(path=f'{screenshots_directory}6_select_all_checked.png')
        
        scenario_setup_page.click_continue_button()
        page.screenshot(path=f'{screenshots_directory}7_final_segmentation_result.png')
        
        print("Content segmentation test completed successfully")
        
    except Exception as e:
        print(f"Error during content segmentation test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_final_state.png')
        raise