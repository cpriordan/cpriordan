import os
import shutil
import pytest
import time
import re
import urllib.parse
from playwright.sync_api import sync_playwright, expect
from playwright.async_api import async_playwright
from pyotp import TOTP
from dotenv import load_dotenv
from datetime import datetime


class LoginPage:
    def __init__(self, page):
        self.page = page

    def navigate(self):
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
        otp_input.wait_for(state="visible", timeout=30000) # Ensure the token input field is visible
        # Before filling out the TOTP code, check the remaining time and generate a fresh one if needed
        remaining_time = totp.interval - (int(time.time()) % totp.interval)
        if remaining_time < 5:  # Generate a fresh TOTP if less than 5 seconds remain
            time.sleep(remaining_time + 1)
        otp_code = totp.now()
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
        # Instead of automatically filling out the OTP code, manually enter as a temporary workaround and force a 10-second manual wait
        self.page.wait_for_timeout(10000)
        print(f"OTP code entered.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class ProductToSegmentMappingPage:
    def __init__(self, page):
        self.page = page
        self.product_mapping_page_for_easterly = f'https://{test_env}finalyticsdata.com/ai-settings/product-mapping?cu_id=68490'
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        self.settings_left_nav_link = page.get_by_text("Settings").nth(2) # Use the third instance
        self.segments_left_nav_link = page.get_by_text("Segments").nth(0) # Use the first instance
        self.available_segments_left_nav_link = page.get_by_text("Segments").nth(1)  # Use the second instance
        self.product_mapping_left_nav_link = page.get_by_text("Product Mapping")
        self.easterly_company_link = page.locator('a[dd="vys"]').first
        # Kanban board used for drag and drop
        self.kanban_board = page.locator(".kanban-drag")
        self.bargain_lovers_segment = page.locator("main.kanban-drag[title='Bargain Lovers']")
        self.top_card = self.kanban_board.locator("div.kanban-item").first
        self.checking_account_card = page.locator("div.kanban-item", has_text="Checking Account").nth(0) # First instance
        # Products that can be mapped to a segment
        self.life_insurance = page.locator("main.kanban-drag[title='Bargain Lovers'] div.kanban-item",
                                             has_text="Life Insurance")
        self.checking_account = page.locator("main.kanban-drag[title='Bargain Lovers'] div.kanban-item", has_text="Checking Account")
        self.credit_card = page.locator("main.kanban-drag[title='Bargain Lovers'] div.kanban-item", has_text="Credit Card")

    def navigate_to_available_segments_and_product_to_segment_mapping(self, screenshots_directory):
        self.admin_link.click()
        self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        self.settings_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}2_navigated_to_settings.png')
        self.segments_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}3_navigated_to_segments.png')
        # Also, show available segments
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}4_navigated_to_available_segments.png')
        self.available_segments_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}5_before_clicked_easterly.png')
        self.easterly_company_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}6_after_clicked_easterly.png')
        # Navigate to product to segment mapping
        self.product_mapping_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}7_product_mapping_for_easterly.png')
        return ProductToSegmentMappingPage(self.page)

    def go_directly_to_product_mapping(self, screenshots_directory):
        self.page.goto(self.product_mapping_page_for_easterly)
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}15_product_mapping_for_easterly_after_dragging_CREDIT_CARD.png')

    def drag_element_on_top_of(self, source, target):
        source.scroll_into_view_if_needed()
        target.scroll_into_view_if_needed()
        self.page.wait_for_timeout(1000)
        source_box = source.bounding_box()
        target_box = target.bounding_box()

        # Drag from center of source to near top of target
        self.page.mouse.move(source_box["x"] + source_box["width"] / 2, source_box["y"] + source_box["height"] / 2)
        self.page.mouse.down()
        self.page.wait_for_timeout(500)
        self.page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + 5)
        self.page.wait_for_timeout(500)
        self.page.mouse.up()

    def drag_and_drop_selected_product_on_top_of_desired_segment(self, product_to_prioritize, segment_to_use):
        # Wait for page to load
        self.page.wait_for_load_state("networkidle")
        # Wait for Kanban board to load for drag and drop functionality
        self.page.wait_for_selector(".kanban-drag")
        # Simulate the drag and drop of checking account to life insurance
        # Ensure the element is scrolled into view before dragging and dropping of checking account to life insurance
        self.checking_account.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)  # optional: slight wait after scroll
        self.checking_account.drag_to(self.life_insurance)

    def drag_and_drop_a_product_on_top_of_bargain_lovers_segment(self, product_to_prioritize, screenshots_directory):
        # Wait for page to load
        self.page.wait_for_load_state("networkidle")
        # Wait for Kanban board to load for drag and drop functionality
        self.page.wait_for_locator(self.kanban_board)
        # Wait for Kanban board Bargain Lovers Segment to load for drag and drop functionality
        self.page.wait_for_locator(self.bargain_lovers_segment)

        # The top or first product card within the Kanban board was defined in init
        # Simulate the drag and drop of checking account as the top of the product
        self.checking_account.drag_to(self.top_card)
        # Wait for the drag and drop to get completed and displayed
        self.page.wait_for_timeout(2000)

    def drag_and_drop_checking_product_on_top_of_bargain_lovers_segment(self, screenshots_directory, desired_segment):
        self.page.core_product = "Checking Account"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(".kanban-drag")
        self.page.wait_for_selector("main.kanban-drag[title='Bargain Lovers']")
        self.page.screenshot(
            path=f'{screenshots_directory}16_BEFORE_dragged_and_drop_CHECKING_on_top_of_bargain_lovers_segment.png')

        # Change the locator based on desired segment parameter
        locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment}'] div.kanban-item"
        print(f"Locator based on desired segment parameter is {locator_based_on_desired_segment}")

        # Identify the top card dynamically at the time of drag
        top_card = self.page.locator(locator_based_on_desired_segment).first

        # Scroll source and destination into view
        self.checking_account.scroll_into_view_if_needed()
        top_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(1000)

        # Perform precise mouse actions for drag and drop
        source_box = self.checking_account.bounding_box()
        target_box = top_card.bounding_box()

        self.page.mouse.move(source_box["x"] + source_box["width"] / 2,
                             source_box["y"] + source_box["height"] / 2)
        self.page.mouse.down()
        self.page.wait_for_timeout(500)
        self.page.mouse.move(target_box["x"] + target_box["width"] / 2,
                             target_box["y"] + 5)  # Slightly above top card
        self.page.wait_for_timeout(500)
        self.page.mouse.up()

        self.page.wait_for_timeout(3000)
        self.page.screenshot(
            path=f'{screenshots_directory}17_AFTER_dragged_and_drop_CHECKING_on_top_of_bargain_lovers_segment.png')

        # Return the substring to check the ad title on the demo page
        if self.page.core_product:
            words = self.page.core_product.strip().split()
            ad_title_substring_to_check_on_demo_based_on_product = words[0].lower() if words else ""
        else:
            ad_title_substring_to_check_on_demo_based_on_product = ""

        print(f"Substring to check on ad title is {ad_title_substring_to_check_on_demo_based_on_product}")
        return ad_title_substring_to_check_on_demo_based_on_product


    def drag_and_drop_credit_card_product_on_top_of_bargain_lovers_segment(self, screenshots_directory, desired_segment):
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(".kanban-drag")
        self.page.wait_for_selector("main.kanban-drag[title='Bargain Lovers']")
        self.page.core_product = "Credit Card"
        # THE SCREENSHOT BELOW IS PROBABLY NOT NUMBERED CORRECTLY???
        self.page.screenshot(
            path=f'{screenshots_directory}10_BEFORE_dragged_and_drop_CREDIT_CARD_on_top_of_bargain_lovers_segment.png')

        # Identify the top card dynamically at the time of drag
        locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment}'] div.kanban-item"
        print(f"Locator based on desired segment parameter is {locator_based_on_desired_segment}")
        top_card = self.page.locator(locator_based_on_desired_segment).first

        # Scroll source and destination into view
        self.credit_card.scroll_into_view_if_needed()
        top_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(1000)

        # Perform precise mouse actions for drag and drop
        source_box = self.credit_card.bounding_box()
        target_box = top_card.bounding_box()

        self.page.mouse.move(source_box["x"] + source_box["width"] / 2,
                             source_box["y"] + source_box["height"] / 2)
        self.page.mouse.down()
        self.page.wait_for_timeout(500)
        self.page.mouse.move(target_box["x"] + target_box["width"] / 2,
                             target_box["y"] + 5)  # Slightly above top card
        self.page.wait_for_timeout(500)
        self.page.mouse.up()

        self.page.wait_for_timeout(3000)
        self.page.screenshot(
            path=f'{screenshots_directory}11_AFTER_dragged_and_drop_CREDIT_CARD_on_top_of_bargain_lovers_segment.png')

        # Return the substring to check the ad title on the demo page
        if self.page.core_product:
            words = self.page.core_product.strip().split()
            ad_title_substring_to_check_on_demo_based_on_product = words[0].lower() if words else ""
        else:
            ad_title_substring_to_check_on_demo_based_on_product = ""

        print(f"Substring to check on ad title is {ad_title_substring_to_check_on_demo_based_on_product}")
        return ad_title_substring_to_check_on_demo_based_on_product

    def take_screenshot(self, path):
        self.page.screenshot(path=path)

class EasterlyDemoPage:
    def __init__(self, page):
        self.page = page

    def navigate_to_demo_page_using_a_new_tab_without_a_segment(self, screenshots_directory):
        self.page.goto(f'https://www.{test_env}finalyticsdemo.com/?api=stg')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        print(f"Went to https://www.{test_env}finalyticsdemo.com/?api=stg after waiting for page load and NO segment")
        self.page.screenshot(path=f'{screenshots_directory}7_navigated_to_demo_page_without_a_segment.png')

    def navigate_to_demo_page_using_an_existing_tab_and_desired_segment(self, screenshots_directory, desired_segment):
        encoded_segment = urllib.parse.quote(desired_segment)
        # self.page.goto(f'https://{test_env}finalyticsdemo.com/?api=stg&segments={encoded_segment}')
        encoded_segment = urllib.parse.quote(desired_segment)

        try:
            self.page.goto(
                f'https://www.{test_env}finalyticsdemo.com/?api=stg&segments={encoded_segment}',
                timeout=60000  # wait up to 60 seconds for page load
            )
            self.page.wait_for_load_state("networkidle")
            print(f"Went to https://www.{test_env}finalyticsdemo.com/?api=stg&segments={encoded_segment} after waiting for page load using segment {desired_segment}")
        except Exception as e:
            print(f"Failed to navigate to demo page for segment '{desired_segment}': {e}")
            self.page.screenshot(path=f'{screenshots_directory}ERROR_failed_to_load_demo_segment_{encoded_segment}.png')
            raise


    def refresh_the_demo_page_on_the_existing_tab_using_desired_segment(self, screenshots_directory, desired_segment):
        encoded_segment = urllib.parse.quote(desired_segment)
        self.page.goto(f'https://www.{test_env}finalyticsdemo.com/?api=stg&segments={desired_segment}')
        self.page.screenshot(path=f'{screenshots_directory}9_refreshed_demo_page_after_changing_the_segment.png')

    def take_screenshot(self, path):
        self.page.screenshot(path=path)


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

def validate_no_server_error(page):
    """
    Validates that the page does not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error", "Page not found"]
    page_text = page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]

    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)


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

# PREVIOUS VERSION WITHOUT HTTP AUTHENTICATION
@pytest.fixture(scope="function")
def browser_context():
    """Fixture to set up and tear down the Playwright browser context."""
    with sync_playwright() as playwright: #Start the Playwright context
        browser = playwright.chromium.launch(headless=False) # Launch Chrome and show the browser
        context = browser.new_context() # Create a new browser context/tab which has it's own local storage
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


def take_screenshot_without_fonts(page, path):
    """
    Takes a screenshot without waiting for fonts to load by hiding text elements before capturing.
    """
    try:
        # Hide text elements to prevent font loading issues
        page.evaluate("""
            document.querySelectorAll('*').forEach(el => {
                if (window.getComputedStyle(el).fontFamily) {
                    el.style.visibility = 'hidden';
                }
            });
        """)

        # Take screenshot
        page.screenshot(path=path, timeout=60000)
    finally:
        # Restore visibility after screenshot
        page.evaluate("""
            document.querySelectorAll('*').forEach(el => {
                el.style.visibility = '';
            });
        """)

def define_heading_locator(page):
    return page.locator("h1").nth(0) # First instance

def test_claritas_segment_control_of_demo_ads(browser_context):
    page = browser_context.new_page()  # Use the main page, not a new tab
    # Initialize page objects
    login_page = LoginPage(page)
    product_to_segment_mapping_page = ProductToSegmentMappingPage(page)
    easterly_demo_page = EasterlyDemoPage(page)

    # Define variables that need to be shared between functions
    claritas_segment_to_use = "Bargain Lovers"
    initial_priority_product = "Checking Account"
    lowercased_core_product= [word.lower() for word in initial_priority_product.split()]
    ad_title_substring_to_check_on_demo_based_on_product = lowercased_core_product[0] #Only save the first element

    # Only clear the directory that is being used in this test
    screenshots_directory = 'screenshots_adminsite_using_pytest/claritas_segment/'
    clear_screenshots_directory(screenshots_directory)

    # Perform login steps
    login_page.navigate()
    login_page.login(findata_user, findata_pw)
    # Wait for the 2FA input field to appear and ensure it's visible
    print(f"Username {findata_user} and password were filled.")

    # Use the login_page method to automatically generate the OTP code and enter it once
    otp_code = generate_otp_code()
    login_page.enter_2fa_code(otp_code)

    print("2FA token automatically generated and entered and about to click the login button")

    # Click the LOGIN button AFTER filling out the TOTP
    page.get_by_role("button", name="Login").click()

    # Take screenshot and verify redirection
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    # Get the current URL
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")

    # Actions post-login
    # Show available Claritas segments for Easterly
    product_to_segment_mapping_page.navigate_to_available_segments_and_product_to_segment_mapping(screenshots_directory)
    product_to_segment_mapping_page.take_screenshot(f'{screenshots_directory}8_successful_navigation_to_product_to_segment_mapping_for_easterly.png')

    # Drag a product on top of the Claritas segment on the product to mapping page
    product_to_segment_mapping_page.take_screenshot(f'{screenshots_directory}9_current_product_to_segment_mapping_before_dragging_products.png')

    # Assert that credit card ad is displayed after Credit Card product was made the top priority
    expected_ad_title_substring_on_demo_page = product_to_segment_mapping_page.drag_and_drop_credit_card_product_on_top_of_bargain_lovers_segment(
        screenshots_directory, claritas_segment_to_use)
    product_to_segment_mapping_page.take_screenshot(
        f'{screenshots_directory}12_credict_card_product_successfully_dragged_as_top_priority_segment.png')
    print(f"Expected ad title to check on demo page is {expected_ad_title_substring_on_demo_page} which was returned by drag_and_drop_credit_card_product_on_top_of_bargain_lovers_segment function")

    # Go to the demo page using the Bargain Lover's segment to check that credit card ad is displayed
    print(f"About to navigate to demo site using desired segment {claritas_segment_to_use} with credit card as top priority ad")
    easterly_demo_page.navigate_to_demo_page_using_an_existing_tab_and_desired_segment(screenshots_directory,
                                                                                       claritas_segment_to_use)
    # Define locator for expected heading and check that visible
    heading_locator = define_heading_locator(page)
    expect(heading_locator).to_be_visible()
    heading_text = heading_locator.text_content()
    if heading_text:
        assert expected_ad_title_substring_on_demo_page.lower() in heading_text.lower(), \
            f"Expected '{expected_ad_title_substring_on_demo_page}' in heading, but got '{heading_text}'"
        print(f"Verified heading contains: '{expected_ad_title_substring_on_demo_page}' (case-insensitive)")
        easterly_demo_page.take_screenshot(f'{screenshots_directory}14_navigated_to_DEMO_PAGE_using_a_segment_with_top_priority_CREDIT_CARD.png')
    else:
        raise AssertionError("Heading text was empty or not found.")

    # Jump back to the product mapping for Easterly using the same page since previously navigated to the demo page
    product_to_segment_mapping_page.go_directly_to_product_mapping(screenshots_directory)
    print(f"Went to product mapping using existing window so can change checking to be the top priority")

    expected_ad_title_substring_on_demo_page = product_to_segment_mapping_page.drag_and_drop_checking_product_on_top_of_bargain_lovers_segment(screenshots_directory, claritas_segment_to_use)
    product_to_segment_mapping_page.take_screenshot(f'{screenshots_directory}18_checking_product_successfully_dragged_as_top_priority_segment.png')
    print(f"Expected ad title to check on demo page is {expected_ad_title_substring_on_demo_page} which was returned by drag_and_drop_checking_product_on_top_of_bargain_lovers_segment function")

    # Go to the demo page using the desired segment to check the ad displayed
    print(f"About to navigate to demo site using desired Claritas segment {claritas_segment_to_use} with checking account as top priority ad")
    easterly_demo_page.navigate_to_demo_page_using_an_existing_tab_and_desired_segment(screenshots_directory, claritas_segment_to_use)

    # Define locator for expected heading
    heading_locator = define_heading_locator(page)
    expect(heading_locator).to_be_visible()
    heading_text = heading_locator.text_content()
    if heading_text:
        assert expected_ad_title_substring_on_demo_page.lower() in heading_text.lower(), \
            f"Expected '{expected_ad_title_substring_on_demo_page}' in heading, but got '{heading_text}'"
        print(f"Verified heading contains: '{expected_ad_title_substring_on_demo_page}' (case-insensitive)")
        easterly_demo_page.take_screenshot(f'{screenshots_directory}19_navigated_to_DEMO_PAGE_with_CHANGED_ad_showing_new_CHECKING_TOP_PRIORITY_AD.png')
    else:
        raise AssertionError("Heading text was empty or not found.")

    print(f"Review the relevant screenshots shown with CAPITAL letters in screenshot directory {screenshots_directory}")

