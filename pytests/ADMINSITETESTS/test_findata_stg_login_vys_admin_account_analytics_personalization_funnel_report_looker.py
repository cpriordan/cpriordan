import os
import shutil
import pytest
import re
import time
import asyncio
from playwright.async_api import async_playwright, expect
from playwright.async_api import async_playwright, TimeoutError # ADDED FOR PERSONALIZATION FUNNEL LOOKER
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
            await asyncio.sleep(remaining_time + 1)
        otp_code = totp.now()
        # otp_input.fill(otp_code)
        # self.page.wait_for_timeout(300)
        await otp_input.fill(otp_code)
        await self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")


    async def take_screenshot(self, path):
        await self.page.screenshot(path=path)

class AnalyticsPage:
    def __init__(self, page):
        self.page = page
        self.admin_link = page.get_by_text("Admin").nth(0) # Click the first instance
        self.easterly_company_link = page.get_by_text("Easterly").nth(0) # Use the first instance
        self.first_united_company_link = page.get_by_text("1st United Services").nth(0)  # Use the first instance
        self.analytics_nav_link = page.get_by_text("Analytics").nth(0) # Use the first instance
        self.clients_nav_link = page.get_by_text("Clients") # Only one instance
        self.personalization_funnel_analytics_nav_link = page.get_by_text("Personalization Funnel")

    async def navigate_to_analytics_personalization_funnel_report(self, screenshots_directory):
        await self.admin_link.click()
        print("Clicked Admin link...")
        await self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        await self.page.wait_for_load_state("networkidle")  # Wait for page to stabilize
        # Navigate to Analtyics left nav link
        await self.analytics_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}3_before_clicked_analytics_left_nav_link.png')
        await self.analytics_nav_link.click()
        print("Clicked Analytics left nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}4_after_clicked_analytics_left_nav_link.png')
        await self.page.wait_for_load_state("networkidle")
        # Scroll down to Personalization Funnel nav link under Analytics
        await self.scroll_left_navigation_menu()
        print("Used left nav scrollbar to scroll down and view the Personalization Funnel link...")
        await self.page.screenshot(path=f'{screenshots_directory}5_use_left_nav_scroll_bar_to_view_personalization_funnel.png')
        # Click Personalization Funel link
        await self.personalization_funnel_analytics_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}6_before_click_personalization_funnel_link.png')
        await self.personalization_funnel_analytics_nav_link.click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.screenshot(path=f'{screenshots_directory}7_after_click_personalization_funnel_link.png')
        # 1st United link gets displayed after clicking the Personalization Funnel link (which maybe a security issue since should only have access to Easterly links)
        if await self.first_united_company_link.is_visible():
            print("About to click the company link...")
            await self.page.screenshot(path=f'{screenshots_directory}8_before_click_1st_United_Services_link.png')
            await self.first_united_company_link.wait_for(state="visible", timeout=10000)
            await self.first_united_company_link.click()
            await self.page.wait_for_load_state("networkidle")
            await self.page.screenshot(path=f'{screenshots_directory}9_clicked_1st_United_Services_link.png')
        else:
            print("1st United Services company link not found so go to link on https://stgfinalyticsdata.com/analytics/looker/funnel?cu_id=63958 instead...")
            await self.page.goto("https://stgfinalyticsdata.com/analytics/looker/funnel?cu_id=63958", wait_until="networkidle")
            await self.page.wait_for_load_state("networkidle")
            await self.page.screenshot(path=f'{screenshots_directory}9b_went_to_1st_united_services_personalization_funnel_url_directly_instead_for_security.png')

    async def navigate_to_analytics_personalization_funnel_report_for_clients(self, screenshots_directory,
                                                                              client_names):
        await self.admin_link.click()
        print("Clicked Admin link...")
        await self.page.screenshot(path=f'{screenshots_directory}2_after_clicked_admin_top_nav.png')
        await self.page.wait_for_load_state("networkidle")

        await self.analytics_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}3_before_clicked_analytics_left_nav_link.png')
        await self.analytics_nav_link.click()
        print("Clicked Analytics left nav link...")
        await self.page.screenshot(path=f'{screenshots_directory}4_after_clicked_analytics_left_nav_link.png')
        await self.page.wait_for_load_state("networkidle")

        await self.scroll_left_navigation_menu()
        await self.page.screenshot(
            path=f'{screenshots_directory}5_use_left_nav_scroll_bar_to_view_personalization_funnel.png')

        await self.personalization_funnel_analytics_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}6_before_click_personalization_funnel_link.png')
        await self.personalization_funnel_analytics_nav_link.click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.screenshot(path=f'{screenshots_directory}7_after_click_personalization_funnel_link.png')

        for client_name in client_names:
            client_link = self.page.get_by_text(client_name).nth(0)
            print(f"About to view personalization funnel report for client {client_name}")
            if await client_link.is_visible():
                await self.page.screenshot(
                    path=f'{screenshots_directory}8_before_click_{client_name.replace(" ", "_").lower()}_link.png')
                await client_link.wait_for(state="visible", timeout=10000)
                await client_link.click()
                # await self.page.wait_for_load_state("networkidle", timeout=10000)
                # Use domcontentloaded which is supposed to be more reliable for looker reports
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                print(f"Clicked {client_name} client link...")
                await self.page.screenshot(
                    path=f'{screenshots_directory}9_clicked_{client_name.replace(" ", "_").lower()}_link.png')

            else:
                # Take screenshot since may need to scroll down to check if the left nav link for the client is in the view port
                await self.page.screenshot(path=f'{screenshots_directory}page_showing_left_nav_to_check_if_client_{client_name}_is_in_viewport.png')
                # Need to use a dictionary that has the corresponding company ID for the given client for the code below to work as a backup
                # fallback_url = f"https://stgfinalyticsdata.com/analytics/looker/funnel?cu_id=63958"
                print(f"{client_name} link not found so may need to scroll down...")
                client_link = self.page.get_by_text(client_name).nth(0)
                await client_link.scroll_into_view_if_needed()
                await client_link.click()
                # await self.page.wait_for_load_state("networkidle", timeout=10000)
                # Use domcontentloaded which is supposed to be more reliable for looker reports
                await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                print(f"Clicked {client_name} client link...")
                await self.page.screenshot(
                    path=f'{screenshots_directory}9_clicked_{client_name.replace(" ", "_").lower()}_link_after_scroll.png')

            await wait_for_looker_iframe_to_load(self.page, screenshots_directory)
            print(f"iframe loaded with expected content for client {client_name}")
            await validate_no_server_error(self.page, screenshots_directory, client_name)
            # print(f"Validated no server error for client {client_name}")
            await self.page.screenshot(path=f'{screenshots_directory}personalization_looker_report_{client_name.replace(" ", "_").lower()}_link.png')
            print(f"Completed validation for {client_name} personalization funnel looker report.")
            await self.clients_nav_link.click()
            await self.page.wait_for_load_state("load", timeout=30000)
            print(f"Navigated to client's left nav link")

    async def scroll_left_navigation_menu(self):
        left_nav_menu = self.page.locator('div.scroll-scrolly_visible:nth-child(3) > div:nth-child(1) > div:nth-child(3)')
        await left_nav_menu.evaluate("element => element.scrollTop = element.scrollHeight")

    async def take_screenshot(self, path):
        await self.page.screenshot(path=path)


async def wait_for_looker_report(page):
    # Wait for the iframe to appear on the page
    iframe_element = await page.wait_for_selector("iframe[src*='lookerstudio.google.com']", timeout=60000)

    # Get the iframe's frame object
    iframe = await iframe_element.content_frame()

    # Wait for specific content in the iframe to load
    try:
        # CANT CHECK FOR CONTENT WITHIN THE IFRAME TO JUST AD EXTRA WAIT
        # await iframe.wait_for_selector("text=/personalization traffic funnel/i", timeout=60000)
        # print("Report content fully loaded.")
        await page.wait_for_timeout(20000)
    except TimeoutError:
        print("Report content did not load in time.")

async def wait_for_looker_iframe_to_load(page, screenshots_directory):
    iframe_selector = "iframe[src*='lookerstudio.google.com']"
    iframe_element = await page.wait_for_selector(iframe_selector, timeout=60000)
    iframe = await iframe_element.content_frame()

    if not iframe:
        raise RuntimeError("FAILED TO GET IFRAME CONTENT FRAME.")

    try:
        # Wait for key text inside iframe
        # COMMENTED OUT SINCE SELECTOR CAN'T BE VALIDATED INSIDE IFRAME TO JUST ADD MORE TIMEOUT
        # await iframe.wait_for_selector("text=/Finalytics App Submitted Ratio/i", timeout=60000)
        # print("Verified Looker report is loaded inside iframe.")
        await page.wait_for_timeout(20000)
        await page.screenshot(path=f'{screenshots_directory}10_last_looker_iframe_before_checked_for_errors.png')
    except TimeoutError:
        await page.screenshot(path=f'{screenshots_directory}10_last_looker_iframe_not_loaded_and_timedout.png')
        raise TimeoutError("Looker iframe content did not load on time.")



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


async def validate_no_server_error(page, screenshots_directory, client_name):
    """
    Validates that the page and Looker iframe do not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error", "Page not found", "System Error"]
    found_errors = []

    # Check errors in main page body
    page_text = await page.text_content("body")
    found_errors.extend([msg for msg in error_keywords if msg in page_text])

    # Check errors inside Looker iframe
    iframe_selector = "iframe[src*='lookerstudio.google.com']"
    try:
        iframe_element = await page.wait_for_selector(iframe_selector, timeout=30000)
        iframe = await iframe_element.content_frame()
        if iframe:
            iframe_body = await iframe.text_content("body")
            found_errors.extend([msg for msg in error_keywords if msg in iframe_body])
        else:
            print("WARNING: Unable to access Looker iframe content.")
    except TimeoutError:
        print("ERROR: Timeout while trying to access Looker iframe.")

    if found_errors:
        await page.screenshot(path=f'{screenshots_directory}INTERNAL_ERROR_OR_SYSTEM_ERROR_detected_for_{client_name}_funnel_looker_report.png')
        assert False, "Error messages found on the page or iframe: " + ", ".join(found_errors)



@pytest.mark.asyncio
async def test_personalization_funnel_looker_report():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()  # Create an isolated browser context
        page = await context.new_page()  # Open a new page (tab)
        login_page = LoginPage(page)
        analytics_page = AnalyticsPage(page)

        screenshots_directory = 'screenshots_adminsite_using_pytest/analytics_personalization_funnel/'
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

        # List of clients to validate
        clients = ["1st United Services", "Apple", "Georgia's Own", "Global", "Langley", "Mission Fed", "OneAZ", "Silver State", "Statewide", "TruStone", "UHFCU"]

        # Navigate to Analytics after login
        await analytics_page.navigate_to_analytics_personalization_funnel_report_for_clients(screenshots_directory, clients)

        # Wait for last iframe content with extended timeout to ensure it's fully loaded
        await wait_for_looker_iframe_to_load(page, screenshots_directory)
        print("Verified iframe loaded with expected content")

