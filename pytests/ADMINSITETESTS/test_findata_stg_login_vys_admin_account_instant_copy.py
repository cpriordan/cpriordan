import pytest
import asyncio
import aiohttp
from playwright.async_api import async_playwright, expect
from colorama import Fore, Style
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qa_tools import (
    AdminLoginPage, 
    setup_admin_test_environment,
    validate_admin_no_server_error_async
)

async def clear_screenshots_directory(directory):
    """Clear screenshots directory for async tests."""
    import os
    import shutil
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(directory)

class InstantCopyPage:
    """Page object for instant copy functionality."""
    def __init__(self, page):
        self.page = page
        self.instant_copy_nav_link = page.get_by_text("Instant Copy")
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.content_nav_link = page.get_by_text("Content").nth(0)
        self.first_adcopy_checkbox = page.locator("input[type='checkbox'].action-select").nth(0)
        self.second_adcopy_checkbox = page.locator("input[type='checkbox'].action-select").nth(1)
        self.third_adcopy_checkbox = page.locator("input[type='checkbox'].action-select").nth(2)
        self.action_dropdown = page.locator("select[name='action']")
        self.go_submit_button = page.locator("button[type='submit'][name='index']")

    async def navigate_to_instant_copy(self, screenshots_directory):
        await self.admin_link.click()
        print("Clicked Admin link...")
        await self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        await self.page.wait_for_load_state("networkidle")

        await self.content_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}3_before_clicked_content_left_nav_link.png')
        await self.content_nav_link.click()
        print("Clicked Content left nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}4_after_clicked_content_left_nav_link.png')
        await self.page.wait_for_load_state("networkidle")

        await self.instant_copy_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}5_before_clicked_instant_copy_left_nav_link.png')
        await self.instant_copy_nav_link.click()
        print("Clicked Instant Copy left nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}6_after_clicked_instant_copy_left_nav_link.png')
        await self.page.wait_for_load_state("networkidle")

    async def select_first_three_adcopy_checkboxes(self):
        await self.first_adcopy_checkbox.check()
        await self.second_adcopy_checkbox.check()
        await self.third_adcopy_checkbox.check()
        await self.page.wait_for_load_state("networkidle")
        return InstantCopyPage(self.page)

    async def select_replicate_to_vys_menu_and_submit(self):
        try:
            action_dropdown = self.page.locator("select[name='action']")
            await action_dropdown.wait_for(state="visible", timeout=10000)
            await action_dropdown.scroll_into_view_if_needed()
            await action_dropdown.click()
            await self.page.wait_for_timeout(500)

            await self.page.select_option("select[name='action']", value="replicate_to_vys")

            go_button = self.page.locator("button[type='submit'][name='index']")
            await go_button.wait_for(state="visible", timeout=5000)
            await go_button.click()
            await self.page.wait_for_load_state("networkidle")
            print("Replicate to VYS action submitted.")
        except Exception as e:
            print("Error in selecting replicate action and submitting:", e)
            await self.page.screenshot(path="screenshots_adminsite_using_pytest/instant_copy/debug_replicate_submit_failed.png")
            raise

        return InstantCopyPage(self.page)

    async def take_screenshot(self, path):
        await self.page.screenshot(path=path)

@pytest.mark.asyncio
async def test_instant_copy_replicate_to_vys():
    """Test instant copy functionality using consolidated qa_tools functions."""
    async with async_playwright() as p:
        import os
        headless = os.environ.get("HEADLESS", "false").lower() == "true"
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Setup environment using consolidated function
            findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
            
            screenshots_directory = 'screenshots_adminsite_using_pytest/instant_copy/'
            await clear_screenshots_directory(screenshots_directory)
            print(f"Cleared screenshots directory {screenshots_directory}.")
            
            # Initialize consolidated login page and page objects
            login_page = AdminLoginPage(page, is_async=True)
            instant_copy_page = InstantCopyPage(page)
            
            # Perform login using consolidated async methods
            await login_page.navigate(test_env)
            print(f"About to login...")
            await login_page.login(findata_user, findata_pw)
            
            await login_page.enter_2fa_code(totp)
            await page.get_by_role("button", name="Login").click()
            
            await login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
            
            current_url = page.url
            print(f"Current URL after login is {current_url}.")
            expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')
            
            # Navigate to instant copy functionality
            await instant_copy_page.navigate_to_instant_copy(screenshots_directory)
            
            # Select ad copies and replicate
            await instant_copy_page.select_first_three_adcopy_checkboxes()
            await page.screenshot(path=f'{screenshots_directory}7_adcopy_checkboxes_selected.png')
            
            await instant_copy_page.select_replicate_to_vys_menu_and_submit()
            await page.screenshot(path=f'{screenshots_directory}8_replicate_action_submitted.png')
            
            # Validate no server errors using consolidated function
            await validate_admin_no_server_error_async(page)
            print(f"Page was validated to not have any errors after instant copy operation")
            await page.screenshot(path=f'{screenshots_directory}9_SUCCESS_instant_copy_completed.png')
            
            print("Instant copy test completed successfully")
            
        finally:
            await context.close()
            await browser.close()