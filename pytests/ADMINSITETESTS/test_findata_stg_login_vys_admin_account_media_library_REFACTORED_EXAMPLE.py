import pytest
import os
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qa_tools import (
    AdminLoginPage, 
    setup_admin_test_environment,
    admin_browser_context_async,
    clear_screenshots_directory,
    validate_admin_login_success_async,
    validate_admin_no_server_error_async
)

# Page Object Models that could also be consolidated further
class MediaLibraryPage:
    """Simplified media library page using consolidated base functionality."""
    
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0)
        self.content_nav_link = page.get_by_text("Content").nth(0)
        self.media_library_nav_link = page.get_by_text("Media Library")
        self.add_new_asset_button = page.get_by_text("Add New Asset")
        
    async def navigate_to_media_library(self, screenshots_dir):
        """Navigate to media library with consolidated screenshot management."""
        await self.admin_link.click()
        await self.page.screenshot(path=f'{screenshots_dir}2_after_clicked_admin_top_nav.png')
        await self.page.wait_for_load_state("networkidle")
        
        await self.content_nav_link.wait_for(state="visible", timeout=30000)
        await self.content_nav_link.click()
        await self.page.wait_for_load_state("networkidle")

@pytest.mark.asyncio
async def test_media_library_navigation():
    """Refactored async admin test using consolidated qa_tools functions."""
    # Use consolidated async browser context
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        import os
        headless = os.environ.get("HEADLESS", "false").lower() == "true"
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Setup environment using consolidated function
            findata_user, findata_pw, findata_otp, test_env, totp, screenshots_dir = setup_admin_test_environment('vys')
            
            # Clear screenshots directory
            await clear_screenshots_directory(screenshots_dir)
            
            # Initialize consolidated async login page
            login_page = AdminLoginPage(page, is_async=True)
            media_library_page = MediaLibraryPage(page)
            
            # Perform login flow using consolidated async methods
            await login_page.navigate(test_env)
            await login_page.login(findata_user, findata_pw)
            await login_page.enter_2fa_code(totp)
            await page.get_by_role("button", name="Login").click()
            
            # Validate login using consolidated async function
            await login_page.take_screenshot(f'{screenshots_dir}1_successful_login_using_2fa.png')
            await validate_admin_login_success_async(page, test_env)
            
            # Navigate to media library
            await media_library_page.navigate_to_media_library(screenshots_dir)
            
            # Validate no server errors using consolidated function
            await validate_admin_no_server_error_async(page)
            await page.screenshot(path=f'{screenshots_dir}3_media_library_access_validated.png')
            
            print("Successfully navigated to media library without errors")
            
        finally:
            await context.close()
            await browser.close()