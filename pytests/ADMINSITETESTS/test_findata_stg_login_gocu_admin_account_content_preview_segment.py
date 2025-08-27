import os
import shutil
import pytest
import time
from playwright.sync_api import sync_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv

class LoginPage:
    def __init__(self, page):
        self.page = page

    def navigate(self):
        # self.page.goto("https://stgfinalyticsdata.com/account/login/?next=/")
        self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def login(self, username, password):
        self.page.get_by_label("Username:").click()
        self.page.get_by_label("Username:").fill(username)
        # Instead of time.sleep(1), do a short wait_for_timeout if needed
        self.page.wait_for_timeout(300)  # a brief pause to mimic user pause
        self.page.get_by_label("Password").fill(password)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_load_state("networkidle")

    def enter_2fa_code(self, otp_code):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        otp_input.fill(otp_code)
        self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")

    def retry_login_with_new_token(self):
        for attempt in range(2):  # Attempt login up to 2 times
            try:
                otp_code = generate_otp_code()
                print(f"Attempt {attempt + 1}: Entering OTP code {otp_code}.")
                self.enter_2fa_code(otp_code)
                # Check if login was successful by verifying the URL
                if f'https://{test_env}finalyticsdata.com/admin/' in self.page.url:
                    print("Login successful.")
                    return
            except Exception as e:
                print(f"Login attempt {attempt + 1} failed: {e}")

        raise Exception("Failed to login after multiple attempts.")

    def manually_enter_2fa_code(self):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        # Instead of automatically filling out the OTP code, manually enter as a temporary workaround
        # otp_input.fill(otp_code)
        # Temporarily let user type in code. This forces a 10-second manual wait
        self.page.wait_for_timeout(10000)
        print(f"OTP code entered.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class PreviewContent:
    def __init__(self, page):
        self.page = page
        self.preview_content_nav_link = page.get_by_text("Preview Content")
        # Updated locator to find span with the exact text inside the sidebar
        self.content_modules_nav_link = page.locator(".sub-item:text('Content Modules')")
        # Updated the campaign to July since June no longer exists after manual testing duplicate feature
        self.test_core_products_link = page.get_by_text("Test Core Products: 2025-07")

    def navigate_to_content_modules(self):
        # First ensure the dropdown that reveals 'Content' menu
        content_menu = self.page.get_by_text("Content").nth(0)
        if content_menu:
            content_menu.click()
            self.page.wait_for_timeout(500)  # give time for dropdown to expand

        # Scroll and click on the submenu link
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
    def __init__(self, page):
        self.page = page
        self.first_adcopy_checkbox = self.page.locator("input[type='checkbox'].action-select").nth(0)
        self.second_adcopy_checkbox = self.page.locator("input[type='checkbox'].action-select").nth(1)
        self.action_dropdown = self.page.locator("select[name='action']")
        # self.delete_selected_adcopy_menu = self.page.select_option("select[name='action']", value="delete_selected")

        # Wait for the delete option to become visible within the dropdown
        # self.page.wait_for_timeout(500)  # brief pause to ensure dropdown is expanded
        # self.page.select_option("select[name='action']", value="delete_selected")

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
            self.page.wait_for_timeout(500)  # Allow dropdown to render visually

            # Remove the explicit wait_for() on the hidden option, select_option works on hidden options
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
            self.delete_confirmation_button = self.page.get_by_role("button", name="Yes, I’m sure")
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
    def __init__(self, page):
        self.page = page
        # Updated to locate the actual checkbox input next to the "SELECT ALL" label
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
        # Directly locate checkbox by its id if it's #select_all
        checkbox = self.page.locator("#select_all")

        try:
            checkbox.wait_for(state="visible", timeout=10000)
            checkbox.scroll_into_view_if_needed()
            print("Checkbox with id #select_all is visible and scrolled into view.")

            if checkbox.is_checked():
                checkbox.uncheck()
                print("Checkbox was checked, now unchecked.")
            else:
                print("Checkbox was already unchecked.")

        except Exception as e:
            print("Checkbox interaction failed:", e)
            self.page.screenshot(
                path="screenshots_adminsite_using_pytest/content_preview_segment/debug_checkbox_by_id_failed.png")
            raise

        # No need to wait for networkidle — checkboxes don’t trigger navigation
        self.page.wait_for_timeout(500)

        # Click first two checkboxes based on input value
        try:
            first_value = ">$1000 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT"
            second_value = ">$2500 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT"

            first_checkbox = self.page.locator(
                f"input[type=\"checkbox\"][name=\"segment_items\"][value=\"{first_value}\"]")
            second_checkbox = self.page.locator(
                f"input[type=\"checkbox\"][name=\"segment_items\"][value=\"{second_value}\"]")

            first_checkbox.wait_for(state="visible", timeout=5000)
            second_checkbox.wait_for(state="visible", timeout=5000)
            first_checkbox.scroll_into_view_if_needed()
            second_checkbox.scroll_into_view_if_needed()
            first_checkbox.check()
            second_checkbox.check()
            print("First two segment checkboxes checked.")

        except Exception as e:
            print("Failed to check specific segment checkboxes:", e)
            self.page.screenshot(
                path="screenshots_adminsite_using_pytest/content_preview_segment/debug_check_segment_checkboxes_failed.png")
            raise

        return Segments(self.page)
    def scroll_down_to_continue_button(self):
        self.continue_button.scroll_into_view_if_needed()
        self.continue_button.wait_for(state="visible")

    def click_continue_button(self):
        self.continue_button.click()
        self.page.wait_for_load_state("networkidle")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

def check_link_on_page(page, expected_text):
    body_text = page.inner_text("body")
    if expected_text in body_text:
        print(f"Found expected text in page body: {expected_text}")
        return True
    else:
        print("Expected text not found. Full body content snippet:")
        print(body_text[:1000])  # print first 1000 characters to help debug
        return False

def clear_screenshots_directory(directory):
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

# Load environment variables from .env
load_dotenv()

# Validate environment variables
findata_user = os.environ.get("FINDATA_GOCU_USER")
findata_pw = os.environ.get("FINDATA_GOCU_PW")
findata_otp = os.environ.get("FINDATA_GOCU_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables FINDATA_GOCU_USER, FINDATA_GOCU_PW, FINDATA_GOCU_OTP or TEST_ENVIRONMENT are not set!")

# Configure TOTP using pyotp
totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")

@pytest.fixture(scope="function")
def browser_context():
    """Fixture to set up and tear down the Playwright browser context."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()

def generate_otp_code():
    import time
    remaining_time = totp.interval - (int(time.time()) % totp.interval)
    if remaining_time < 5:
        # short pause so the token rolls over
        # from playwright.sync_api import sync_playwright
        time.sleep(remaining_time + 1)
    return totp.now()


def test_content_preview_segment(browser_context):
    page = browser_context.new_page()
    # Initialize page objects
    login_page = LoginPage(page)
    preview_content_page = PreviewContent(page)
    segments_page = Segments(page)
    instant_segments_page = InstantSegments_CampaignPreviewTestCoreProducts(page)
    adcopy_page = AdCopy(page)
    first_selected_segment = ">$1000 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT"
    second_selected_segment = ">$2500 DEBIT TRANSFER 0-15 DAYS AFTER TRIAL DEPOSIT"

    screenshots_directory = 'screenshots_adminsite_using_pytest/content_preview_segment/'
    clear_screenshots_directory(screenshots_directory)

    # Perform login steps
    login_page.navigate()
    login_page.login(findata_user, findata_pw)

    # Wait for the 2FA input field to appear and ensure it's visible
    print(f"Username {findata_user} and password were filled.")
    print("Waiting for 2FA input field...")
    page.wait_for_selector('#id_token-otp_token', timeout=60000)  # Wait up to 60 seconds
    time.sleep(1)
    otp_input = page.locator('#id_token-otp_token')
    time.sleep(1)
    otp_input.wait_for(state="visible", timeout=30000)  # Ensure the field is visible
    print("2FA input field is visible.")

    # Fill the TOTP code into the 2FA input field
    ## otp_input.fill(totp.now())

    # Before filling out the TOTP code, check the remaining time and generate a fresh one if needed
    remaining_time = totp.interval - (int(time.time()) % totp.interval)
    if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
        time.sleep(remaining_time + 1)
    otp_code = totp.now()
    otp_input.fill(otp_code)
    print(f"OTP code {otp_code} entered.")

    # Click the login button after filling out the TOTP
    page.get_by_role("button", name="Login").click()


    # Take screenshot and verify redirection
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    # expect(page).to_have_url("https://stgfinalyticsdata.com/admin/")
    # Get the current URL
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # After successful login, click on "Preview Content" link and then the Test Core Products 2025-2026 campaign
    preview_content_page.navigate_to_content_modules()
    preview_content_page.navigate_to_preview_content()
    preview_content_page.take_screenshot(f'{screenshots_directory}2_preview_content_page.png')
    preview_content_page.navigate_to_test_core_products()
    preview_content_page.take_screenshot(f'{screenshots_directory}3_preview_page_test_campaign.png')

    # On the segments page, select the first segment link for an ad, deselect all the segments and only select the first two segments
    segments_page.select_first_segment_link_for_an_ad()
    preview_content_page.take_screenshot(f'{screenshots_directory}4_available_segments.png')
    segments_page.click_select_all_checkbox_and_first_two_checkboxes()
    preview_content_page.take_screenshot(f'{screenshots_directory}5_selected_segments.png')
    # segments_page.select_first_segment_checkbox()
    # segments_page.second_segment_checkbox()
    # Scroll down and click continue button
    segments_page.scroll_down_to_continue_button()
    segments_page.take_screenshot(f'{screenshots_directory}6_scrolled_down_to_continue.png')
    segments_page.click_continue_button()

    # Go back to preview content and select the campaign to see the dynamically generated segments
    preview_content_page.navigate_to_content_modules()
    preview_content_page.navigate_to_preview_content()
    preview_content_page.navigate_to_test_core_products()
    preview_content_page.take_screenshot(f'{screenshots_directory}7_preview_content_with_segments.png')

    # Assert that the selected segment is displayed on the preview content page
    print(f"first_selected_segment without first character is: " + first_selected_segment[1:])
    print(f"second_selected_segment without first character is: " + second_selected_segment[1:])
    selected_first_segment_present = check_link_on_page(page, first_selected_segment[1:])
    selected_second_segment_present = check_link_on_page(page, second_selected_segment[1:])
    assert selected_first_segment_present, "First selected segment should be displayed on the preview content page"
    assert selected_second_segment_present, "Second selected segment should be displayed on the preview content page"

    print(f"Verified first_selected_segment " + first_selected_segment + " exists on the preview content page")
    print(f"Verified second_selected_segment " + second_selected_segment + " exists on the preview content page")

    # Only fail and display the message if these keywords are found on the page
    error_keywords = ["Server Error", "(500)", "error"]

    # Grab the entire page text. You can also specify a particular selector, e.g., "body" or "html".
    page_text = page.text_content("body")

    # Build a list of all error strings that actually appear in page_text
    found_errors = [msg for msg in error_keywords if msg in page_text]

    # If found_errors is not empty, raise an assertion with the joined error messages
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)

    # Assert that not a server error
    page.screenshot(path=f'{screenshots_directory}8_no_server_error.png')

    # Clean up the adcopies that were generated for the segment for the next run
    preview_content_page.navigate_to_content_modules()
    preview_content_page.take_screenshot(f'{screenshots_directory}9_content_moduled_adcopy.png')
    adcopy_page.select_first_and_second_adcopy_checkboxes()
    adcopy_page.take_screenshot(f'{screenshots_directory}10_first_and_second_adcopy_selected.png')
    adcopy_page.select_delete_selected_adopy_menu_and_submit()
    adcopy_page.take_screenshot(f'{screenshots_directory}11_confirm_adcopy_deletion.png')
    adcopy_page.click_delete_confirmation_button()
    adcopy_page.take_screenshot(f'{screenshots_directory}12_generated_segment_adcopy_deleted.png')

