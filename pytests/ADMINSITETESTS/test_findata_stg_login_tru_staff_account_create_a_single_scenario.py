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
    """Page object for creating single scenarios."""
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.content_nav_link = page.get_by_text("Content").nth(0)
        self.scenarios_nav_link = page.get_by_text("Scenarios")
        self.add_scenario_button = page.get_by_text("Add Scenario")
        self.scenario_name_input = page.locator("#id_name")
        self.save_button = page.get_by_role("button", name="Save")
        
    def navigate_to_scenarios(self, screenshots_directory):
        self.admin_link.click()
        self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        self.page.wait_for_load_state("networkidle")

        self.content_nav_link.wait_for(state="visible", timeout=30000)
        self.content_nav_link.click()
        self.page.wait_for_load_state("networkidle")

        self.scenarios_nav_link.wait_for(state="visible", timeout=30000)
        self.scenarios_nav_link.click()
        self.page.wait_for_load_state("networkidle")

    def create_new_scenario(self, scenario_name):
        self.add_scenario_button.click()
        self.page.wait_for_load_state("networkidle")
        
        self.scenario_name_input.fill(scenario_name)
        self.save_button.click()
        self.page.wait_for_load_state("networkidle")

def test_create_a_single_scenario(admin_browser_context_sync):
    """Test creating a single scenario using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function for TRU
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('tru')
    screenshots_directory = 'screenshots_adminsite_using_pytest/create_scenario/'
    
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
        # Navigate to scenarios
        scenario_page.navigate_to_scenarios(screenshots_directory)
        page.screenshot(path=f'{screenshots_directory}3_scenarios_page.png')
        
        # Create new scenario
        scenario_name = f"Test Scenario {int(time.time())}"
        scenario_page.create_new_scenario(scenario_name)
        page.screenshot(path=f'{screenshots_directory}4_scenario_created.png')
        
        print(f"Successfully created scenario: {scenario_name}")
        page.screenshot(path=f'{screenshots_directory}5_final_scenario_creation_state.png')
        
    except Exception as e:
        print(f"Error during scenario creation test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_scenario_creation.png')
        raise