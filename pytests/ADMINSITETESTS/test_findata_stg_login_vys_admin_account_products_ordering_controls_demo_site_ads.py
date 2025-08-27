import os
import shutil
import pytest
import time
import re
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

class ProductsPage:
    def __init__(self, page):
        self.page = page
        self.products_page_for_easterly = f'https://{test_env}finalyticsdata.com/ai-settings/products?cu_id=68490'
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        self.settings_left_nav_link = page.get_by_text("Settings").nth(2) # Use the third instance
        self.products_left_nav_link = page.get_by_text("Products").nth(0)  # Use the first instance
        self.easterly_company_link = page.locator('a[dd="vys"]').first
        # Kanban board used for drag and drop
        self.kanban_board = page.locator(".kanban-drag")
        self.credit_card_default_product = page.locator("main.kanban-drag[title='Credit Card']")
        self.cd_default_product = page.locator("main.kanban-drag[title='CD']")
        self.default_segment = page.locator("main.kanban-drag[title='default']")
        self.top_card = self.kanban_board.locator("div.kanban-item").first
        self.credit_card_card = page.locator("div.kanban-item", has_text="Credit Card").nth(0) # First instance
        # Products that used in Default Segment
        self.credit_card = page.locator("main.kanban-drag[title='default'] div.kanban-item",
                                             has_text="Credit Card")
        self.cd = page.locator("main.kanban-drag[title='default'] div.kanban-item", has_text="CD")
        self.car_loan = page.locator("main.kanban-drag[title='default'] div.kanban-item", has_text="Car Loan")

    def navigate_to_product_ordering(self, screenshots_directory):
        self.admin_link.click()
        self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        # Navigate to product ordering page
        self.settings_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.products_left_nav_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}2_navigated_to_products.png')
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}3_before_clicked_easterly.png')
        self.easterly_company_link.click()
        self.page.wait_for_load_state("networkidle")
        self.page.screenshot(path=f'{screenshots_directory}4_products_ordering_for_easterly_with_CD_as_TOP_PRIORITY_of_DEFAULT_SEGMENT.png')
        return ProductsPage(self.page)

    def go_directly_to_product_mapping(self, screenshots_directory):
        self.page.goto(self.products_page_for_easterly)
        self.page.wait_for_load_state("networkidle")
        # self.page.screenshot(path=f'{screenshots_directory}8_product_ordering_direct_jump.png')

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
        # Ensure the element is scrolled into view before dragging and dropping of CREDIT CARD to CD
        self.credit_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)  # optional: slight wait after scroll
        self.credit_card.drag_to(self.cd)

    def drag_and_drop_a_product_on_top_of_default_segment(self, product_to_prioritize, screenshots_directory):
        # Wait for page to load
        self.page.wait_for_load_state("networkidle")
        # Wait for Kanban board to load for drag and drop functionality
        self.page.wait_for_locator(self.kanban_board)
        # Wait for Kanban board to load the DEFAULT segment for drag and drop functionality
        self.page.wait_for_locator(self.default_segment)

        # The top or first product card within the Kanban board was defined in init
        # Simulate the drag and drop of CREDIT CARD as the top of the product
        self.credit_card.drag_to(self.top_card)
        # Wait for the drag and drop to get completed and displayed
        self.page.wait_for_timeout(2000)

    def drag_and_drop_credit_card_on_top_of_default_segment(self, screenshots_directory, desired_segment):
        self.page.core_product = "Credit Card"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(".kanban-drag")
        # self.page.wait_for_selector("main.kanban-drag[title='Default']")
        # With this updated version to catch timeout or visibility issues:
        try:
            # Update the wait_for_selector call accordingly to lower case for the title:
            # self.page.wait_for_selector("main.kanban-drag[title='default']", timeout=10000, state="visible")
            self.page.wait_for_selector(f"main.kanban-drag[title='{desired_segment.lower()}']", timeout=10000, state="visible")
        except Exception as e:
            self.page.screenshot(path=f'{screenshots_directory}ERROR_locator_default_segment_not_found.png')
            raise RuntimeError(
                "Failed to find 'Default' segment on Kanban board. Check if the page structure changed or user permissions are correct.") from e

        self.page.screenshot(
            path=f'{screenshots_directory}6_BEFORE_dragged_and_drop_CREDIT_CARD_on_top_of_default_segment.png')

        # Change the locator based on desired segment parameter
        # Update the segment selector to lowercase in this line since actual HTML shows HTML uses title="default" (lowercase

        # Ensure desired_segment is also lowercase:
        locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment.lower()}'] div.kanban-item"
        # locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment}'] div.kanban-item"
        print(f"Locator based on desired segment parameter is {locator_based_on_desired_segment}")

        # Identify the top card dynamically at the time of drag
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
            path=f'{screenshots_directory}7_AFTER_dragged_and_drop_CREDIT_CARD_on_top_of_default_segment.png')

        # Return the substring to check the ad title on the demo page
        if self.page.core_product:
            words = self.page.core_product.strip().split()
            ad_title_substring_to_check_on_demo_based_on_product = words[0].lower() if words else ""
        else:
            ad_title_substring_to_check_on_demo_based_on_product = ""

        print(f"Substring to check on ad title is {ad_title_substring_to_check_on_demo_based_on_product}")
        return ad_title_substring_to_check_on_demo_based_on_product


    def drag_and_drop_cd_product_on_top_of_default_segment(self, screenshots_directory, desired_segment):
        self.page.core_product = "CD"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_selector(".kanban-drag")
        try:
            # Update the wait_for_selector call accordingly to lower case for the title:
            # self.page.wait_for_selector("main.kanban-drag[title='default']", timeout=10000, state="visible")
            self.page.wait_for_selector(f"main.kanban-drag[title='{desired_segment.lower()}']", timeout=10000,
                                        state="visible")
        except Exception as e:
            self.page.screenshot(path=f'{screenshots_directory}ERROR_locator_default_segment_not_found.png')
            raise RuntimeError(
                "Failed to find 'Default' segment on Kanban board. Check if the page structure changed or user permissions are correct.") from e

        # Segment is default for CD so still need to convert to lower case
        locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment.lower()}'] div.kanban-item"
        # locator_based_on_desired_segment = f"main.kanban-drag[title='{desired_segment}'] div.kanban-item"
        print(f"Locator based on desired segment parameter is {locator_based_on_desired_segment}")
        top_card = self.page.locator(locator_based_on_desired_segment).first

        # Scroll source and destination into view
        self.cd.scroll_into_view_if_needed()
        top_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(1000)

        # Perform precise mouse actions for drag and drop
        source_box = self.cd.bounding_box()
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
        # self.page.screenshot(
        #     path=f'{screenshots_directory}10_AFTER_dragged_and_drop_CD_on_top_of_default_segment.png')

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
        self.login_link = page.get_by_text("LOGIN") # Login link on top of the nav bar
        self.username_field = page.get_by_label("Username")
        self.password_field = page.get_by_label("Password")
        self.login_button = page.get_by_text("Login")

    def navigate_to_demo_page_using_a_new_tab_without_a_segment(self, screenshots_directory):
        self.page.goto(f'https://www.{test_env}finalyticsdemo.com/?api=stg')
        self.page.wait_for_load_state("networkidle", timeout=60000)
        print(f"Went to https://www.{test_env}finalyticsdemo.com/?api=stg after waiting for page load and NO segment")
        self.page.screenshot(path=f'{screenshots_directory}7_navigated_to_demo_page_without_a_segment.png')

    def navigate_to_demo_page_using_an_existing_tab_and_current_segment_and_product(self, screenshots_directory):

        try:
            self.page.goto(
                f'https://www.{test_env}finalyticsdemo.com/?api=stg',
                timeout=60000
            )
            self.page.wait_for_load_state("networkidle")

            # Adjust locator based on updated HTML structure
            login_link = self.page.locator("a#login", has_text="Login")

            try:
                login_link.scroll_into_view_if_needed()
                login_link.click(timeout=5000)
            except Exception:
                print("LOGIN link not interactable normally, attempting JS click...")
                # Use proper handle for the JS element click
                login_handle = login_link.element_handle()
                if login_handle:
                    self.page.evaluate("el => el.click()", login_handle)
                else:
                    raise RuntimeError("Login link handle not found for JS click")

            # Wait for login panel to show inputs
            username_field = self.page.locator("#login-panel input#mobile-username")
            password_field = self.page.locator("#login-panel input#mobile-password")

            username_field.wait_for(state="visible", timeout=10000)
            username_field.fill("new")

            password_field.wait_for(state="visible", timeout=10000)
            password_field.fill("demo")

            # Submit login form
            self.page.locator("#login-panel button.btn-primary[type='submit']").click()
            self.page.wait_for_load_state("networkidle")

            print(f"Went to https://www.{test_env}finalyticsdemo.com/?api=stg and logged in as user 'new'")

            # ADD LOGIC TO CLICK Logout
            logout_link = self.page.locator("a.logout")
            try:
                logout_link.scroll_into_view_if_needed()
                logout_link.click(timeout=5000)
                # Wait for page to load after logout
                self.page.wait_for_load_state("networkidle")

            except Exception:
                print("LOGOUT link not interactable normally, attempting JS click...")
                logout_handle = logout_link.element_handle()
                if logout_handle:
                    self.page.evaluate("el => el.click()", logout_handle)
                else:
                    raise RuntimeError("Logout link handle not found for JS click")

            print("Successfully logged out after login and waited for page to load.")

            # Screenshot of demo page with current DEFAULT segment and current CD product
            self.page.screenshot(path=f'{screenshots_directory}5_DEMO_page_with_current_default_segment_and_CD_product_ad.png')

        except Exception as e:
            print(f"Failed to navigate to demo page for segment: {e}")
            self.page.screenshot(path=f'{screenshots_directory}ERROR_failed_to_load_demo_page.png')
            raise


    # Updated section to click the LOGIN button even if not visible due to JS-triggered login panel
    def navigate_to_demo_page_using_an_existing_tab_and_desired_segment(self, screenshots_directory, desired_segment):
        encoded_segment = urllib.parse.quote(desired_segment)
        try:
            self.page.goto(
                f'https://www.{test_env}finalyticsdemo.com/?api=stg',
                timeout=60000
            )
            self.page.wait_for_load_state("networkidle")

            # Adjust locator based on updated HTML structure
            login_link = self.page.locator("a#login", has_text="Login")

            try:
                login_link.scroll_into_view_if_needed()
                login_link.click(timeout=5000)
            except Exception:
                print("LOGIN link not interactable normally, attempting JS click...")
                # Use proper handle for the JS element click
                login_handle = login_link.element_handle()
                if login_handle:
                    self.page.evaluate("el => el.click()", login_handle)
                else:
                    raise RuntimeError("Login link handle not found for JS click")

            # Wait for login panel to show inputs
            username_field = self.page.locator("#login-panel input#mobile-username")
            password_field = self.page.locator("#login-panel input#mobile-password")

            username_field.wait_for(state="visible", timeout=10000)
            username_field.fill("new")

            password_field.wait_for(state="visible", timeout=10000)
            password_field.fill("demo")

            # Submit login form
            self.page.locator("#login-panel button.btn-primary[type='submit']").click()
            self.page.wait_for_load_state("networkidle")

            print(f"Went to https://www.{test_env}finalyticsdemo.com/?api=stg and logged in as user 'new'")

            # ADD LOGIC TO CLICK Logout
            logout_link = self.page.locator("a.logout")
            try:
                logout_link.scroll_into_view_if_needed()
                logout_link.click(timeout=5000)
                # Wait for page to load after logout
                self.page.wait_for_load_state("networkidle")

            except Exception:
                print("LOGOUT link not interactable normally, attempting JS click...")
                logout_handle = logout_link.element_handle()
                if logout_handle:
                    self.page.evaluate("el => el.click()", logout_handle)
                else:
                    raise RuntimeError("Logout link handle not found for JS click")

            print("Successfully logged out after login and waited for page to load.")

        except Exception as e:
            print(f"Failed to navigate to demo page for segment: {e}")
            self.page.screenshot(path=f'{screenshots_directory}ERROR_failed_to_load_demo_page.png')
            raise

    def refresh_the_demo_page_on_the_existing_tab_using_desired_segment(self, screenshots_directory, desired_segment):
        encoded_segment = urllib.parse.quote(desired_segment)
        self.page.goto(f'https://www.{test_env}finalyticsdemo.com/?api=stg&segments={desired_segment}')
        self.page.screenshot(path=f'{screenshots_directory}9_refreshed_demo_page_after_changing_the_segment.png')

    def refresh_the_demo_page_on_the_existing_tab(self, screenshots_directory):
        self.page.goto(f'https://www.{test_env}finalyticsdemo.com/?api=stg')
        self.page.screenshot(path=f'{screenshots_directory}9_refreshed_demo_page_after_product_ordering.png')

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

def test_product_ordering_control_of_demo_ads(browser_context):
    page = browser_context.new_page()  # Use the main page, not a new tab
    login_page = LoginPage(page)
    products_page = ProductsPage(page)
    easterly_demo_page = EasterlyDemoPage(page)
    claritas_segment_to_use = "Default"
    initial_priority_product = "CD"
    lowercased_core_product = [word.lower() for word in initial_priority_product.split()]
    ad_title_substring_to_check_on_demo_based_on_product = lowercased_core_product[0]
    screenshots_directory = 'screenshots_adminsite_using_pytest/product_ordering/'
    clear_screenshots_directory(screenshots_directory)
    login_page.navigate()
    login_page.login(findata_user, findata_pw)
    print(f"Username {findata_user} and password were filled.")

    otp_code = generate_otp_code()
    login_page.enter_2fa_code(otp_code)
    print("2FA token automatically generated and entered and about to click the login button")
    page.get_by_role("button", name="Login").click()
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    current_url = page.url
    print(f"Current URL after login is {current_url}.")
    expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')
    print(f"Successful login screenshot saved in {screenshots_directory}.")
    products_page.navigate_to_product_ordering(screenshots_directory)
    print(f"About to navigate to demo site using current segment DEFAULT and EXISTING product with CD as top priority ad")
    easterly_demo_page.navigate_to_demo_page_using_an_existing_tab_and_current_segment_and_product(screenshots_directory)
    products_page.go_directly_to_product_mapping(screenshots_directory)
    print(f"Went to product mapping using existing window so can change CREDIT CARD to be the top priority")
    # products_page.take_screenshot(f'{screenshots_directory}10_current_product_priority_page_BEFORE_dragging_products_to_change_product_priority.png')
    print("About to navigate to drag and drop a NEW credit card product on top of DEFAULT segment")
    expected_ad_title_substring_on_demo_page = products_page.drag_and_drop_credit_card_on_top_of_default_segment(
        screenshots_directory, claritas_segment_to_use)
    # products_page.take_screenshot(f'{screenshots_directory}6_credict_card_product_successfully_dragged_as_top_priority_for_default_segment.png')
    print(f"Expected ad title to check on demo page is {expected_ad_title_substring_on_demo_page} which was returned by drag_and_drop_credit_card_product_on_top_of_DEFAULT_segment function")
    print(f"About to navigate to demo site using desired segment {claritas_segment_to_use} with credit card as top priority ad")
    easterly_demo_page.navigate_to_demo_page_using_an_existing_tab_and_desired_segment(screenshots_directory, claritas_segment_to_use)
    heading_locator = define_heading_locator(page)
    expect(heading_locator).to_be_visible()
    heading_text = heading_locator.text_content()

    if heading_text:
        normalized_heading = re.sub(r'\s+', ' ', heading_text.strip().lower())
        normalized_expected_substring = re.sub(r'\s+', ' ', expected_ad_title_substring_on_demo_page.strip().lower())
        # print(f"[DEBUG] HEADING OUTER HTML: {heading_locator.evaluate('node => node.outerHTML')}")
        # print(f"[DEBUG] Raw heading text: {heading_text}")
        # print(f"[DEBUG] Normalized heading text: {normalized_heading}")
        # print(f"[DEBUG] Checking if expected substring '{normalized_expected_substring}' exists in heading '{normalized_heading}'")
        assert normalized_expected_substring in normalized_heading, \
            f"Expected '{expected_ad_title_substring_on_demo_page}' in heading, but got '{heading_text}'"
        print(f"Verified heading contains: '{expected_ad_title_substring_on_demo_page}' (case-insensitive)")
        easterly_demo_page.take_screenshot(f'{screenshots_directory}8_DEMO_PAGE_using_DEFAULT_segment_with_AFTER_CHANGED_PRODUCT_PRIORITY_CREDIT_CARD.png')

    else:
        raise AssertionError("Heading text was empty or not found.")

    # GO DIRECTLY TO PRODUCT MAPPING AND RESET PRODUCT PRIORITY TO CD FOR NEXT RUN
    products_page.go_directly_to_product_mapping(screenshots_directory)
    expected_ad_title_substring_on_demo_page = products_page.drag_and_drop_cd_product_on_top_of_default_segment(
        screenshots_directory, claritas_segment_to_use)
    products_page.take_screenshot(
        f'{screenshots_directory}9_CD_product_successfully_dragged_as_top_priority_of_default_segment_for_CLEANUP.png')
    print(f"Expected ad title to check on demo page is {expected_ad_title_substring_on_demo_page} which was returned by drag_and_drop_CD_product_on_top_of_default segment function")

    print(f"Review the relevant screenshots shown with CAPITAL letters in screenshot directory {screenshots_directory}")
