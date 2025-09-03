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

class PreviewContent:
    """Page object for content preview functionality."""
    def __init__(self, page):
        self.page = page
        self.preview_content_nav_link = page.get_by_text("Preview Content")
        self.content_modules_nav_link = page.locator(".sub-item:text('Content Modules')")
        self.test_core_products_link = page.get_by_text("Test Core Products: 2025-07")

    def navigate_to_content_modules(self):
        content_menu = self.page.get_by_text("Content").nth(0)
        if content_menu:
            content_menu.click()
            self.page.wait_for_timeout(500)

        self.content_modules_nav_link.scroll_into_view_if_needed()
        self.content_modules_nav_link.wait_for(state="visible", timeout=5000)
        self.content_modules_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        return PreviewContent(self.page)

    def navigate_to_preview_content(self):
        self.preview_content_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        return PreviewContent(self.page)

    def navigate_to_test_core_products(self):
        self.test_core_products_link.click()
        self.page.wait_for_load_state("networkidle")
        return PreviewContent(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class InstantSegments_CampaignPreviewTestCoreProducts:
    """Page object for instant segments functionality."""
    def __init__(self, page):
        self.page = page
        self.first_ad_segment_link = page.get_by_text("Segment").nth(0)

    def click_first_ad_segment(self):
        self.first_ad_segment_link.click()
        self.page.wait_for_load_state("networkidle")
        return InstantSegments_CampaignPreviewTestCoreProducts(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class AdCopy:
    """Page object for ad copy management."""
    def __init__(self, page):
        self.page = page
        self.first_adcopy_checkbox = self.page.locator("input[type='checkbox'].action-select").nth(0)
        self.second_adcopy_checkbox = self.page.locator("input[type='checkbox'].action-select").nth(1)
        self.action_dropdown = self.page.locator("select[name='action']")
        self.go_submit_button = self.page.locator("button[type='submit'][name='index']")
        self.delete_confirmation_button = self.page.get_by_role("button", name="Yes, I'm sure")

    def select_first_and_second_adcopy_checkboxes(self):
        self.first_adcopy_checkbox.check()
        self.second_adcopy_checkbox.check()
        self.page.wait_for_load_state("networkidle")
        return AdCopy(self.page)

    def select_delete_selected_adopy_menu_and_submit(self):
        try:
            action_dropdown = self.page.locator("select[name='action']")
            action_dropdown.wait_for(state="visible", timeout=10000)
            action_dropdown.scroll_into_view_if_needed()
            action_dropdown.click()
            self.page.wait_for_timeout(500)

            self.page.select_option("select[name='action']", value="delete_selected")

            go_button = self.page.locator("button[type='submit'][name='index']")
            go_button.wait_for(state="visible", timeout=5000)
            go_button.click()
            self.page.wait_for_load_state("networkidle")
            print("Delete selected ad copy action submitted.")
        except Exception as e:
            print("Error in selecting delete action and submitting:", e)
            self.page.screenshot(path="screenshots_adminsite_using_pytest/content_preview_segment/11_debug_action_submit_failed.png")
            raise

        return AdCopy(self.page)

    def click_delete_confirmation_button(self):
        try:
            self.page.wait_for_timeout(4000)
            self.delete_confirmation_button = self.page.get_by_role("button", name="Yes, I'm sure")
            self.delete_confirmation_button.wait_for(state="visible", timeout=10000)
            self.delete_confirmation_button.scroll_into_view_if_needed()
            self.page.wait_for_timeout(300)
            self.delete_confirmation_button.click()
            print("Confirmed deletion of selected ad copy.")
        except Exception as e:
            print("Failed to confirm deletion:", e)
            self.page.screenshot(path="screenshots_adminsite_using_pytest/content_preview_segment/debug_confirm_delete_failed.png")
            raise

        return AdCopy(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class Segments:
    """Page object for segments management."""
    def __init__(self, page):
        self.page = page
        self.first_segment_link_for_an_ad = page.get_by_text("Segment").nth(0)
        self.select_all_checkbox = page.locator("label:has-text(\"SELECT ALL\") >> input[type=checkbox]")
        self.first_segment_checkbox = page.locator(
            "input[type='checkbox'][name='segment_items'][value=\">$1000 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT\']")
        self.second_segment_checkbox = page.locator(
            "input[type='checkbox'][name='segment_items'][value=\">$2500 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT\']")
        self.continue_button = page.get_by_role("button", name="Continue")
    
    def select_first_segment_link_for_an_ad(self):
        self.first_segment_link_for_an_ad.click()
        self.page.wait_for_load_state("networkidle")
        return PreviewContent(self.page)

    def click_select_all_checkbox_and_first_two_checkboxes(self):
        checkbox = self.page.locator("#select_all")
        try:
            checkbox.wait_for(state="visible", timeout=10000)
            checkbox.scroll_into_view_if_needed()
            print("Checkbox with id #select_all is visible and scrolled into view.")
            checkbox.check()
            print("Select all checkbox is checked.")
            
            self.first_segment_checkbox.check()
            self.second_segment_checkbox.check()
            print("First two individual checkboxes checked.")
        except Exception as e:
            print(f"Error checking checkboxes: {e}")
            self.page.screenshot(path="screenshots_adminsite_using_pytest/content_preview_segment/debug_checkbox_error.png")
            raise

        return Segments(self.page)

    def click_continue_button(self):
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")
        return Segments(self.page)

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def test_content_preview_segment(admin_browser_context_sync):
    """Test content preview and segment functionality using consolidated qa_tools."""
    page = admin_browser_context_sync.new_page()
    
    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('gocu')
    screenshots_directory = 'screenshots_adminsite_using_pytest/content_preview_segment/'
    
    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)
    
    # Initialize consolidated login page and page objects
    login_page = AdminLoginPage(page, is_async=False)
    preview_content_page = PreviewContent(page)
    instant_segments_page = InstantSegments_CampaignPreviewTestCoreProducts(page)
    ad_copy_page = AdCopy(page)
    segments_page = Segments(page)
    
    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()
    
    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)
    
    # Navigate through the content preview workflow
    try:
        # Navigate to content modules
        preview_content_page.navigate_to_content_modules()
        page.screenshot(path=f'{screenshots_directory}2_content_modules_page.png')
        
        # Navigate to preview content
        preview_content_page.navigate_to_preview_content()
        page.screenshot(path=f'{screenshots_directory}3_preview_content_page.png')
        
        # Navigate to test core products
        preview_content_page.navigate_to_test_core_products()
        page.screenshot(path=f'{screenshots_directory}4_test_core_products_page.png')
        
        # Click first ad segment
        instant_segments_page.click_first_ad_segment()
        page.screenshot(path=f'{screenshots_directory}5_first_ad_segment_clicked.png')
        
        # Select and delete ad copy
        ad_copy_page.select_first_and_second_adcopy_checkboxes()
        page.screenshot(path=f'{screenshots_directory}6_adcopy_checkboxes_selected.png')
        
        ad_copy_page.select_delete_selected_adopy_menu_and_submit()
        page.screenshot(path=f'{screenshots_directory}7_delete_action_submitted.png')
        
        ad_copy_page.click_delete_confirmation_button()
        page.screenshot(path=f'{screenshots_directory}8_delete_confirmed.png')
        
        # Work with segments
        segments_page.click_select_all_checkbox_and_first_two_checkboxes()
        page.screenshot(path=f'{screenshots_directory}9_segments_selected.png')
        
        segments_page.click_continue_button()
        page.screenshot(path=f'{screenshots_directory}10_final_result.png')
        
        print("Content preview and segment test completed successfully")
        
    except Exception as e:
        print(f"Error during content preview segment test: {e}")
        page.screenshot(path=f'{screenshots_directory}error_final_state.png')
        raise