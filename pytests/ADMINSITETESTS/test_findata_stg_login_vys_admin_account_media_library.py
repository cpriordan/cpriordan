import os
import shutil
import pytest
import re
import time
# from playwright.sync_api import sync_playwright, expect
import asyncio
from playwright.async_api import async_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv

class LoginPage:
    def __init__(self, page):
        self.page = page

    async def navigate(self):
        await self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')


    async def login(self, username, password):
        await self.page.get_by_label("Username:").click()
        await self.page.get_by_label("Username:").fill(username)
        await self.page.wait_for_timeout(300)
        await self.page.get_by_label("Password").fill(password)
        await self.page.wait_for_timeout(300)
        await self.page.get_by_role("button", name="Login").click()
        await self.page.wait_for_load_state("networkidle")


    async def enter_2fa_code(self):
        otp_input = self.page.locator('#id_token-otp_token')
        await self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
        await self.page.wait_for_timeout(300)
        await otp_input.wait_for(state="visible", timeout=30000)
        # Before filling out the TOTP code, check the remaining time and generate a fresh one if needed
        remaining_time = totp.interval - (int(time.time()) % totp.interval)
        if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
            # time.sleep(remaining_time + 1)
            await asyncio.sleep(remaining_time + 1)
        otp_code = totp.now()
        # otp_input.fill(otp_code)
        # self.page.wait_for_timeout(300)
        await otp_input.fill(otp_code)
        await self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")


    async def take_screenshot(self, path):
        await self.page.screenshot(path=path)

class MediaLibraryPage:
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        self.easterly_company_link = page.get_by_text("Easterly").nth(0) # Use the first instance
        self.drag_and_drop_files_here_button = page.locator('h4.message')
        self.enter_img_url = page.get_by_text("Enter Image URL")
        self.media_library_nav_link = page.get_by_text("Media Library")
        self.content_nav_link = page.get_by_text("Content").nth(0) # Use the first instance
        self.add_new_asset_button = page.get_by_text("Add New Asset")
        self.continue_button = page.locator("button:has-text('Continue')").nth(1)  # Select second button instance for the image upload
        self.save_asset_button = page.get_by_text("Save Asset")
        self.enter_image_url = page.get_by_text("Enter Image URL")
        self.save_button = page.get_by_text("Save").nth(1) # Use the second instance since suzy saver segment matched

    async def navigate_to_media_library(self, screenshots_directory):
        await self.admin_link.click()
        print("Clicked Admin link...")
        await self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        await self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize

        await self.content_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}3_before_clicked_content_left_nav_link.png')
        await self.content_nav_link.click()
        print("Clicked Content left nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}4_after_clicked_content_left_nav_link.png')
        await self.page.wait_for_load_state("networkidle")
        # Scroll down to media library link
        await self.scroll_left_navigation_menu()
        print("Used left nav scrollbar to scroll down and view the Media Library link...")
        await self.page.screenshot(path=f'{screenshots_directory}5_use_left_nav_scroll_bar_to_view_media_library_link.png')
        # Click media library link
        await self.media_library_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}6_before_click_media_library_link.png')
        await self.media_library_nav_link.click()
        await self.page.screenshot(path=f'{screenshots_directory}7_after_click_media_library_link.png')
        await self.page.wait_for_load_state("networkidle")
        # Easterly link gets displayed after clicking the Media Library link
        if await self.easterly_company_link.is_visible():
            print("Clicking Easterly company link...")
            await self.page.screenshot(path=f'{screenshots_directory}8_before_click_easterly_link.png')
            await self.easterly_company_link.wait_for(state="visible", timeout=10000)
            await self.easterly_company_link.click()
            await self.page.screenshot(path=f'{screenshots_directory}8_after_click_easterly_link.png')
            await self.page.wait_for_load_state("networkidle")
        else:
            print("Easterly company link not found so go to link on https://stgfinalyticsdata.com/content/media-library/vys/?cu_id=68490 instead...")
            await self.page.goto("https://stgfinalyticsdata.com/content/media-library/vys/?cu_id=68490", wait_until="networkidle")
            await self.page.screenshot(path=f'{screenshots_directory}8_go_to_easterly_url_instead.png')

    async def click_add_new_asset_button(self, screenshots_directory):
        # await self.page.screenshot(path=f'{screenshots_directory}13_before_add_new_asset_button.png')
        await self.add_new_asset_button.wait_for(state="visible", timeout=30000)
        # await self.page.screenshot(path=f'{screenshots_directory}14_add_new_asset_button_visible.png')
        await self.add_new_asset_button.click()
        await self.page.screenshot(path=f'{screenshots_directory}9_after_add_new_asset_button_visible.png')


    async def click_continue_button(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")  # Ensure AJAX requests are done

        # Scroll and take a screenshot before checking button
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await self.page.wait_for_timeout(2000)
        await self.page.screenshot(path=f'{screenshots_directory}11_after_scroll_continue_button_for_img_upload.png')

        correct_button = None
        frame_page = self.page  # Default to main page

        # Check if the button is inside an iframe
        for frame in self.page.frames:
            continue_buttons = frame.locator("a#cont_btn_img_upload")
            if await continue_buttons.count() > 0:
                print(f"Found 'Continue' button inside iframe {frame.name}. Switching context.")
                correct_button = continue_buttons.first
                frame_page = frame.page  # Use the page context from the frame
                break

        # If button is not inside an iframe, check main page
        if not correct_button:
            correct_button = self.page.locator("a#cont_btn_img_upload")

        # Validate button presence
        if await correct_button.count() == 0:
            print("Error: The 'Continue' button with ID 'cont_btn_img_upload' was not found.")
            await self.page.screenshot(path=f"{screenshots_directory}error_no_correct_continue_button.png")
            raise Exception("The correct 'Continue' button was not found.")

        # Ensure the button is fully interactable before clicking
        await correct_button.wait_for(state="attached", timeout=10000)
        await correct_button.wait_for(state="visible", timeout=10000)

        # Check if the button is enabled before clicking
        is_enabled = await correct_button.is_enabled()
        print(f"Button enabled state: {is_enabled}")

        if not is_enabled:
            print("Warning: The 'Continue' button is disabled. Retrying...")
            for attempt in range(5):  # Retry for 10 seconds
                await self.page.wait_for_timeout(2000)
                is_enabled = await correct_button.is_enabled()
                print(f"Retry {attempt + 1}: Button enabled state: {is_enabled}")
                if is_enabled:
                    break

        if not is_enabled:
            print("Error: The 'Continue' button never became enabled.")
            await self.page.screenshot(path=f"{screenshots_directory}error_continue_button_disabled.png")
            raise Exception("The 'Continue' button is disabled and not clickable.")

        # Ensure the button is within the viewport
        await correct_button.scroll_into_view_if_needed()
        await self.page.wait_for_timeout(500)

        # Try clicking multiple times in case of failures
        for attempt in range(3):
            try:
                await correct_button.hover()
                await correct_button.click(force=True)
                print("Successfully clicked the correct 'Continue' button.")
                # Wait for the create asset page to fully load before taking screenshot
                await self.page.wait_for_load_state("networkidle")
                break
            except Exception as e:
                print(f"Click attempt {attempt + 1} failed: {e}")
                await self.page.wait_for_timeout(1000)

        # Capture screenshot after clicking using the main page context
        await self.page.screenshot(path=f'{screenshots_directory}after_click_continue_before_save_asset.png')


    async def click_continue_button(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")  # Ensure AJAX requests are done

        # Scroll and take a screenshot before checking button
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await self.page.wait_for_timeout(2000)
        await self.page.screenshot(path=f'{screenshots_directory}11_after_scroll_continue_img_upload_button.png')

        correct_button = None
        frame_page = self.page  # Default to main page

        # Check if the button is inside an iframe
        for frame in self.page.frames:
            continue_buttons = frame.locator("a#cont_btn_img_upload")
            if await continue_buttons.count() > 0:
                print(f"Found 'Continue' button inside iframe {frame.name}. Switching context.")
                correct_button = continue_buttons.first
                frame_page = frame.page  # Use the page context from the frame
                break

        # If button is not inside an iframe, check main page
        if not correct_button:
            correct_button = self.page.locator("a#cont_btn_img_upload")

        # Validate button presence
        if await correct_button.count() == 0:
            print("Error: The 'Continue' button with ID 'cont_btn_img_upload' was not found.")
            await self.page.screenshot(path=f"{screenshots_directory}error_no_correct_continue_button.png")
            raise Exception("The correct 'Continue' button was not found.")

        # Ensure the button is fully interactable before clicking
        await correct_button.wait_for(state="attached", timeout=10000)
        await correct_button.wait_for(state="visible", timeout=10000)

        # Check if the button is enabled before clicking
        is_enabled = await correct_button.is_enabled()
        print(f"Button enabled state: {is_enabled}")

        if not is_enabled:
            print("Warning: The 'Continue' button is disabled. Retrying...")
            for attempt in range(5):  # Retry for 10 seconds
                await self.page.wait_for_timeout(2000)
                is_enabled = await correct_button.is_enabled()
                print(f"Retry {attempt + 1}: Button enabled state: {is_enabled}")
                if is_enabled:
                    break

        if not is_enabled:
            print("Error: The 'Continue' button never became enabled.")
            await self.page.screenshot(path=f"{screenshots_directory}error_continue_button_disabled.png")
            raise Exception("The 'Continue' button is disabled and not clickable.")

        # Ensure the button is within the viewport
        await correct_button.scroll_into_view_if_needed()
        await self.page.wait_for_timeout(500)

        # Try clicking multiple times in case of failures
        for attempt in range(3):
            try:
                await correct_button.hover()
                await correct_button.click(force=True)
                print("Successfully clicked the correct 'Continue' button.")
                break
            except Exception as e:
                print(f"Click attempt {attempt + 1} failed: {e}")
                await self.page.wait_for_timeout(1000)

        # Capture screenshot after clicking using the main page context
        await self.page.screenshot(path=f'{screenshots_directory}12_after_clicked_continue_and_save_asset.png')

    async def click_save_asset_button(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")

        # Scroll down gradually until the button is visible
        for _ in range(20):  # Increased scroll steps for better visibility
            await self.page.evaluate("window.scrollBy(0, 500)")
            await self.page.wait_for_timeout(1000)
            if await self.save_asset_button.is_visible():
                break

        # Check if the button is inside an iframe
        correct_button = None
        frame_page = self.page

        for frame in self.page.frames:
            save_buttons = frame.locator("button:has-text('Save Asset')")
            if await save_buttons.count() > 0:
                print(f"Found 'Save Asset' button inside iframe {frame.name}. Switching context.")
                correct_button = save_buttons.first
                frame_page = frame.page  # Use frame's page context
                break

        if not correct_button:
            print("Error: 'Save Asset' button was not found on the page or inside any iframe.")
            await self.page.screenshot(path=f"{screenshots_directory}error_no_save_asset_button.png")
            raise Exception("The 'Save Asset' button was not found.")

        # Ensure the button is fully interactable before clicking
        await correct_button.wait_for(state="attached", timeout=30000)
        await correct_button.wait_for(state="visible", timeout=30000)
        is_enabled = await correct_button.is_enabled()
        print(f"Save Asset button enabled state: {is_enabled}")

        if not is_enabled:
            print("Warning: The 'Save Asset' button is disabled. Retrying...")
            for attempt in range(5):  # Retry for 10 seconds
                await self.page.wait_for_timeout(2000)
                is_enabled = await correct_button.is_enabled()
                print(f"Retry {attempt + 1}: Button enabled state: {is_enabled}")
                if is_enabled:
                    break

        if not is_enabled:
            print("Error: The 'Save Asset' button never became enabled.")
            await self.page.screenshot(path=f"{screenshots_directory}error_save_asset_button_disabled.png")
            raise Exception("The 'Save Asset' button is disabled and not clickable.")

        # Debugging: Screenshot before clicking
        await frame_page.screenshot(path=f'{screenshots_directory}13_after_scroll_for_save_asset_button.png')

        # Save the short_url field so that can check after a certain delay if the URL is valid after saving the asset
        short_url_input = frame_page.locator('#short_url')
        short_url = await short_url_input.get_attribute('value')
        print(f"Short URL which needs to be checked a few seconds later if valid after saving teh asset: {short_url}")


        # Click the Save Asset button
        await correct_button.hover()
        await correct_button.click()

        # Wait for 5 seconds to check if the short_url is valid and returns a status of 400 when accessed
        time.sleep(10)
        print("Sleeping for 10 seconds before checking if the assert is uploaded on S3 bucket")

        # Debugging: Screenshot after clicking
        await frame_page.screenshot(path=f'{screenshots_directory}14_after_clicked_save_asset_and_waited.png')
        print("Save Asset button clicked successfully.")

        # Click on the image to see if it exists
        # 1. Wait for the success alert
        await frame_page.wait_for_selector("#alert-msg", timeout=10000)
        print("Success alert appeared!")

        # 2. Wait for image(s) inside image gallery to load
        image_locator = self.page.locator(".image-gallery img")
        await image_locator.first.wait_for(state="visible", timeout=10000)

        # 3. Check if image actually loaded by verifying naturalWidth > 0
        # This indicates that the image loaded successfully
        image_loaded = await image_locator.first.evaluate("img => img.complete && img.naturalWidth > 0")

        if image_loaded:
            print(f"The image was rendered and has a valid S3 bucket URL {short_url}")
        else:
            print(f"The image was NOT rendered and has a valid S3 bucket {short_url}")


        # INSTEAD OF GOING TO THE SHORT URL, OPEN A NEW TAB, LOAD THE SHORT_URL as IMG AND DISPLAY THE IMG SOURCE
        new_page = await self.page.context.new_page()
        try:
            # Initial blank page load
            await new_page.goto("about:blank")

            # HTML content with embedded image and proper body background
            html_content = f"""
            <html>
            <head><title>Preview</title></head>
            <body style='margin:0;display:flex;align-items:center;justify-content:center;height:100vh;background:#f0f0f0;'>
                <img id='uploadedImage' src='{short_url}' alt='Uploaded Image' style='max-width:100%;max-height:100%;object-fit:contain;border:2px solid #ccc;padding:10px;'>
            </body>
            </html>
            """

            await new_page.set_content(html_content, wait_until="load")
            await new_page.wait_for_selector("#uploadedImage", timeout=10000)

            await new_page.screenshot(path=f"{screenshots_directory}16_image_asset_rendered_in_page.png",
                                      full_page=True)
            print(f"Screenshot captured for image URL embedded manually into HTML.")

            # Add logic to inspect the image element to show the URL
            image_element = await new_page.query_selector("#uploadedImage")
            image_src = await image_element.get_attribute("src")
            print(f"Inspected image element src attribute: {image_src}")

            # CDP workaround: expose image URL in the DOM for manual visibility
            await new_page.evaluate("""
                const src = document.getElementById('uploadedImage').src;
                const div = document.createElement('div');
                div.textContent = 'Image Source: ' + src;
                div.style.position = 'fixed';
                div.style.top = '10px';
                div.style.left = '10px';
                div.style.padding = '10px';
                div.style.backgroundColor = '#fff';
                div.style.border = '1px solid #000';
                div.style.zIndex = '9999';
                document.body.appendChild(div);
            """)

            await new_page.wait_for_timeout(5000)
            await new_page.screenshot(
                path=f"{screenshots_directory}17b_IMAGE_URL_ON_S3_and_rendered_on_a_page.png",
                full_page=True)

        except Exception as e:
            print(f"Error embedding image URL {short_url} into HTML: {e}")
            await new_page.screenshot(path=f"{screenshots_directory}error_embedding_image_url.png")
        finally:
            await new_page.close()

    async def scroll_left_navigation_menu(self):
        left_nav_menu = self.page.locator('div.scroll-scrolly_visible:nth-child(3) > div:nth-child(1) > div:nth-child(3)')
        await left_nav_menu.evaluate("element => element.scrollTop = element.scrollHeight")

    async def take_screenshot(self, path):
        await self.page.screenshot(path=path)

    async def upload_img_file(self, local_file_path, screenshots_directory):
        """
        Uploads an image using Playwright via Dropzone drag-and-drop or hidden file input.
        """

        # Ensure Dropzone is ready (DO NOT CLICK IT)
        dropzone = self.page.locator(".dropzone.dz-clickable")
        await dropzone.wait_for(state="visible", timeout=10000)
        print("Dropzone is visible.")

        # Ensure the hidden file input is accessible
        file_input = self.page.locator("input.dz-hidden-input")

        # Debugging: Check if file input exists
        count = await file_input.count()
        if count == 0:
            print("The hidden file input field was not found!")
            await self.page.screenshot(path=f"{screenshots_directory}hidden_file_input_not_found.png")
            return

        print("Found the hidden file input field!")

        # Ensure the file input is not disabled or hidden
        await self.page.evaluate("""
            const input = document.querySelector('input.dz-hidden-input');
            if (input) {
                input.removeAttribute('hidden');
                input.removeAttribute('disabled');
                input.style.display = 'block';
                input.style.visibility = 'visible';
                input.style.opacity = '1';
                input.style.width = '200px';  // Small but interactable
                input.style.height = '30px';
                input.style.position = 'absolute';
                input.style.zIndex = '1000';  // Ensure it's above other elements
            }
        """)

        # Wait until the file input is both attached and visible
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.wait_for(state="visible", timeout=5000)

        # Convert file path to absolute path
        absolute_image_path = os.path.abspath(local_file_path)

        # Ensure Windows format for Playwright
        if os.name == 'nt':  # Check if running on Windows
            absolute_image_path = absolute_image_path.replace("/", "\\")

        # Debugging: Print file path
        print(f"Using file path: {absolute_image_path}")

        # Retry file upload multiple times in case of failure
        for attempt in range(3):
            try:
                print(f"Attempt {attempt + 1}: Uploading file...")
                # await file_input.set_input_files(absolute_image_path)

                # Updated block:
                await file_input.wait_for(state="attached", timeout=5000)
                await file_input.wait_for(state="visible", timeout=5000)
                await file_input.scroll_into_view_if_needed()
                await file_input.set_input_files(absolute_image_path)
                print(f"File '{absolute_image_path}' uploaded successfully.")

                # Dispatch a 'change' event manually
                await self.page.evaluate("""
                    const input = document.querySelector('input.dz-hidden-input');
                    const event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);
                """)
                print("Dispatched change event after file upload.")

                print(f"File '{absolute_image_path}' uploaded successfully.")
                break  # Exit loop on success
            except Exception as e:
                print(f"Upload attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)  # Wait before retrying


async def clear_screenshots_directory(directory):
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

class AssetsPage:
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        self.admin_home_left_nav_link = page.get_by_text("Admin Home")
        self.easterly_company_link = page.get_by_text("Easterly").nth(0) # Use the first instance
        self.easterly_assets_button = page.get_by_text("Assets").nth(4) # Use the fourth instance
        # self.newly_uploaded_image_on_first_row_link = page.locator("#result_list tbody tr:first-child a")
        self.newly_uploaded_image_on_first_row_link = page.locator(".field-first_field_display > a:nth-child(2)").first
        self.delete_asset_button = page.get_by_text("Delete")
        self.confirm_deletion_button = page.get_by_text("Yes, I'm sure")
        self.deletion_success_message = page.locator(".success")

    async def navigate_to_assets_for_easterly(self, screenshots_directory):
        await self.admin_home_left_nav_link.click()
        print("Clicked Admin Home Left Nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}16_after_clicked_admin_top_nav_for_image_deletion.png')
        await self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize

        await self.easterly_assets_button.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}18_before_clicked_assets_button_for_easterly.png')
        await self.easterly_assets_button.click()
        print("Clicked Easterly Assets Button...")
        await self.page.screenshot(path=f'{screenshots_directory}19_after_clicked_assets_button_for_easterly.png')
        await self.page.wait_for_load_state("networkidle")

    async def select_newly_uploaded_asset_for_deletion(self, screenshots_directory):
        # Select the first row link which is the newly uploaded image
        await self.newly_uploaded_image_on_first_row_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}20_before_clicked_assets_button_for_easterly.png')
        await self.newly_uploaded_image_on_first_row_link.click()
        await self.page.screenshot(path=f'{screenshots_directory}21_after_clicked_assets_button_for_easterly.png')

    async def click_delete_button_and_confirm(self, screenshots_directory):
        # Scroll down the delete assets page to see the delete button
        await self.delete_asset_button.scroll_into_view_if_needed()
        await self.page.wait_for_timeout(500)
        await self.delete_asset_button.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}22_after_scrolling_to_view_delete_asset_button.png')
        await self.delete_asset_button.click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.screenshot(path=f'{screenshots_directory}23_after_clicked_delete_asset_button.png')
        # Wait for delete confirmation button to be visible
        # Locate and click the 'Yes, I'm sure' button
        confirmation_button = self.page.locator("input[type='submit'][value='Yes, I’m sure']")

        await confirmation_button.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}24_after_confirm_deletion_button_was_visible.png')
        # await self.confirm_deletion_button.click()
        await confirmation_button.click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.screenshot(path=f'{screenshots_directory}25_after_SUCCESS_image_deleted_message.png')

    async def validate_image_deletion_success(self, page, screenshots_directory):
        success_message_locator = page.locator(".success")
        success_message_text = await success_message_locator.text_content()
        if success_message_text:
            success_message_text = success_message_text.strip()
        print(f"Actual success message: {success_message_text}")

        # Check for partial match ignoring asset filename
        assert "was deleted successfully" in success_message_text, \
            f"Expected 'was deleted successfully' in message, but got: {success_message_text}"

        await page.screenshot(path=f'{screenshots_directory}26_after_successful_image_deletion.png')

# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_VYS_USER")
findata_pw = os.environ.get("FINDATA_VYS_PW")
findata_otp = os.environ.get("FINDATA_VYS_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables FINDATA_VYS_USER, FINDATA_VYS_PW, FINDATA_VYS_OTP or TEST_ENVIRONMENT are not set!")

# Configure TOTP using pyotp
totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")

@pytest.fixture(scope="function")
async def browser_context():
    """Fixture to set up and tear down the Playwright browser context."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        yield context
        await context.close()
        await browser.close()


def generate_otp_code():
    import time
    remaining_time = totp.interval - (int(time.time()) % totp.interval)
    if remaining_time < 5:
        # short pause so the token rolls over
        # from playwright.sync_api import sync_playwright
        time.sleep(remaining_time + 1)
    return totp.now()

async def validate_no_server_error(page, screenshots_directory):
    """
    Validates that the page does not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error", "Page not found"]
    page_text = await page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    # await page.screenshot(path=f'{screenshots_directory}15_after_saved_asset_with_success_message.png')
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)


@pytest.mark.asyncio
# async def test_media_library_addition_and_deletion_of_images(browser_context):
async def test_media_library_addition_and_deletion_of_images():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()  # Create an isolated browser context
        page = await context.new_page()  # Open a new page (tab)
        # page = browser_context.new_page()
        # page = await browser_context.new_page()
        login_page = LoginPage(page)
        media_library_page = MediaLibraryPage(page)
        assets_page = AssetsPage(page)

        # The image car_image.jpg must exist in the Downloads folder to work or adjust the patch with NAME car_image and NOT car_image.jpg since format is .jpg
        # CHANGE LOCAL FILE PATH TO ABSOLUTE
        # local_image_to_upload = '/Downloads/car_image.jpg'
        # local_image_to_upload = "C:\\Users\\c_p_r\\Downloads\\car_image" # NO .jpg as FILENAME since .jpg is the img format
        # ANOTHER POSSIBLE NON-HARDCODED PATH
        local_image_to_upload = os.path.join(os.environ["USERPROFILE"], "Downloads", "car_image.jpg")
        screenshots_directory = 'screenshots_adminsite_using_pytest/media_library/'
        await clear_screenshots_directory(screenshots_directory)
        print(f"Cleared screenshots directory {screenshots_directory}.")

        # Perform login steps
        await login_page.navigate()
        print(f"About to login...")
        await login_page.login(findata_user, findata_pw)

        await login_page.enter_2fa_code()
        await page.get_by_role("button", name="Login").click()

        await login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')

        current_url = page.url
        print(f"Current URL after login is {current_url}.")
        expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')


        # Navigate to media library after login
        await media_library_page.navigate_to_media_library(screenshots_directory)
        await media_library_page.click_add_new_asset_button(screenshots_directory)

        try:
            await media_library_page.upload_img_file(local_image_to_upload, screenshots_directory)
            await page.screenshot(path=f'{screenshots_directory}10_after_img_upload.png')
            print(f"Uploaded a local image...")
        except Exception as e:
            print(f"Error uploading local image {local_image_to_upload}: {e}")

        # Pause for 10 seconds
        print("Pause for a few seconds before clicking continue to allow time for continue button to get activated")
        time.sleep(15)

        # Click Continue
        await media_library_page.click_continue_button(screenshots_directory)
        print(f"Continue button clicked after image upload")
        # await media_library_page.take_screenshot(f'{screenshots_directory}13_continue_after_img_upload.png')
        await media_library_page.click_save_asset_button(screenshots_directory)
        print(f"Save Asset was clicked")
        # await media_library_page.take_screenshot(f'{screenshots_directory}14_after_saved_asset.png')

        # **Check for success message after clicking Save Asset
        success_message_locator = page.locator("#alert-msg > strong:nth-child(1)")
        await expect(success_message_locator).to_contain_text("New Asset Created!")
        print("Verified success message appeared after saving asset.")

        # Check that the page does not have any internal server error or any error message
        await validate_no_server_error(page, screenshots_directory)
        print(f"Page was validated to not have any errors after image upload")
        await page.screenshot(path=f'{screenshots_directory}15_SUCCESS_new_asset_created_and_stored_on_S3_bucket.png')

        # Somehow, the cu_id used is "caribefederal" when navigate to Easterly assets page after selecting Easterly on stg so  HARD CODE TO USE THE cu_id for vys using URL
        stg_easterly_assets_link_url = "https://stgfinalyticsdata.com/admin/app/asset/?company__id__exact=18619&cu_id=vys"
        await page.goto(stg_easterly_assets_link_url)
        print(f"Navigated to stg_easterly_assets_link_url " + stg_easterly_assets_link_url)

        # Delete the newly uploaded image for clean-up
        # await assets_page.navigate_to_assets_for_easterly(screenshots_directory)
        # print(f"Navigated to assets page for Easterly")

        await assets_page.select_newly_uploaded_asset_for_deletion(screenshots_directory)
        print(f"Selected newly uploaded image asset for deletion")
        await assets_page.click_delete_button_and_confirm(screenshots_directory)
        print(f"Clicked delete and confirm image asset deletion")

        await assets_page.validate_image_deletion_success(page, screenshots_directory)
        print("Verified successful image deletion")

        # Check that the page does not have any internal server error or any error message after image deletion
        await validate_no_server_error(page, screenshots_directory)
        print(f"Page was validated to not have any errors after image deletion")
        await page.screenshot(path=f'{screenshots_directory}26_after_validated_no_error.png')
