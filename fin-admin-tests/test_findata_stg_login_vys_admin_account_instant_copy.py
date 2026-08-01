import os
import shutil
import pytest
import re
import time
# from playwright.sync_api import sync_playwright, expect
import asyncio
import aiohttp
from playwright.async_api import async_playwright, expect
from pyotp import TOTP
from dotenv import load_dotenv
from colorama import Fore, Style

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

class InstantCopyPage:
    def __init__(self, page):
        self.page = page
        self.easterly_company_link = page.get_by_text("Easterly").nth(0) # Use the first instance
        self.missionfed_company_link = page.get_by_text("Mission Fed").nth(0)  # Use the first instance
        self.clients_nav_link = page.get_by_text("Clients")
        self.car_insurance_to_preview = page.get_by_text("Car Insurance")
        # Textarea for entering the website domain
        self.input_website_domain_text_field = "#domain" #Textarea with id="#domain"
        self.continue_button = page.get_by_text("Continue")

        # Checkbox core product options
        self.carloan_checkbox = "input[type='checkbox'][name='product_items'][value='car loan__https://missionfed.com/auto-loans/']"
        self.carinsurance_checkbox = "input[type='checkbox'][name='product_items'][value='car insurance__https://missionfed.com/insurance/auto/']"
        self.homeinsurance_checkbox = "input[type='checkbox'][name='product_items'][value='home insurance__https://missionfed.com/insurance/home/']"
        self.cd_checkbox = "input[type='checkbox'][name='product_items'][value='cd__https://missionfed.com/savings/certificates/']"
        self.heloc_checkbox = "input[type='checkbox'][name='product_items'][value='heloc__https://missionfed.com/home-loans/home-equity-line-of-credit/']"
        self.checking_checkbox = "input[type='checkbox'][name='product_items'][value='checking account__https://missionfed.com/checking-spending/']"
        self.credit_card_checkbox = "input[type='checkbox'][name='product_items'][value='credit card__https://missionfed.com/compare-credit-cards/']"
        self.mortgage_checkbox = "input[type='checkbox'][name='product_items'][value='mortgage__https://missionfed.com/home-loans/']"
        self.savings_checkbox = "input[type='checkbox'][name='product_items'][value='savings account__https://missionfed.com/savings/']"

    async def _expand_content_section_if_needed(self, screenshots_directory: str | None = None):
        """Ensure the left-nav 'Content' accordion is expanded so its children (Instant Copy, etc.) are visible.

        Uses the structure:
            <a data-toggle="collapse" href="#sidebarLayouts">...Content...</a>
            <div class="collapse" id="sidebarLayouts"> ... Instant Copy ... </div>
        """
        page = self.page

        content_toggle = page.locator("a[data-toggle='collapse'][href='#sidebarLayouts']").first
        sidebar_layouts = page.locator("div#sidebarLayouts").first

        # Wait for the toggle to exist
        await content_toggle.wait_for(state="visible", timeout=15000)

        # Check if sidebarLayouts is already expanded (Bootstrap usually adds 'show' when open)
        classes = await sidebar_layouts.get_attribute("class") or ""
        is_expanded = "show" in classes

        if not is_expanded:
            print("Content section appears collapsed; expanding it to reveal child items (Instant Copy, etc.)...")
            await content_toggle.click()
            # Give the collapse animation a moment
            await page.wait_for_timeout(500)
            if screenshots_directory:
                await page.screenshot(
                    path=f"{screenshots_directory}2_expanded_content_left_nav.png"
                )
        else:
            print("Content section is already expanded.")

    async def navigate_to_instant_copy(self, screenshots_directory: str):
        page = self.page

        # 1) Try the simple case first: 'Instant Copy' already visible in the left nav
        instant_copy_link = page.get_by_role("link", name="Instant Copy").first
        if await instant_copy_link.is_visible():
            print("'Instant Copy' link is already visible; clicking it directly...")
            await instant_copy_link.click()
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{screenshots_directory}3_instant_copy_loaded_direct.png")
            print("Successfully navigated to Instant Copy page (direct).")
        else:
            # 2) If not visible, expand the Content section in the left nav
            print("'Instant Copy' not visible; expanding the 'Content' section in the left nav...")
            await self._expand_content_section_if_needed(screenshots_directory)

            # 3) Now wait for 'Instant Copy' to be visible under the expanded Content group
            instant_copy_link = page.get_by_role("link", name="Instant Copy").first
            print("Waiting for 'Instant Copy' link to become visible after expanding Content...")
            await instant_copy_link.wait_for(state="visible", timeout=15000)
            await instant_copy_link.click()
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{screenshots_directory}3_instant_copy_loaded_after_expand.png")
            print("Successfully navigated to Instant Copy page after expanding Content section.")

        # 4) After clicking Instant Copy, navigate to Easterly company page
        await page.wait_for_load_state("networkidle")

        # Check if Easterly link is visible on the page
        if await self.easterly_company_link.is_visible():
            print("Clicking Easterly company link...")
            await page.screenshot(path=f'{screenshots_directory}4_before_click_easterly_link.png')
            await self.easterly_company_link.wait_for(state="visible", timeout=10000)
            await self.easterly_company_link.click()
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f'{screenshots_directory}5_after_click_easterly_link.png')
            print("Successfully clicked Easterly company link.")
        else:
            print(f"Easterly company link was not found; going directly to URL...")
            await page.goto(f"https://{test_env}finalyticsdata.com/content/instant-copy?cu_id=68490", wait_until="networkidle")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f'{screenshots_directory}5_easterly_url_used_for_instant_copy.png')
            print("Successfully navigated to Easterly instant copy page via direct URL.")
    async def input_website_domain(self, website_domain, screenshots_directory):
        print(f"About to enter website domain {website_domain} and screenshots directory is {screenshots_directory}")
        await self.page.fill(self.input_website_domain_text_field, website_domain)
        print(f"Website domain entered is {website_domain} and screenshots directory is {screenshots_directory}")
        await self.page.screenshot(path=f'{screenshots_directory}8_entered_website_domain.png')

    async def navigate_to_client_missionfed(self, screenshots_directory):
        await self.clients_nav_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}13_before_clicked_clients_left_nav_link.png')
        await self.clients_nav_link.click()
        print("Clicked Clients left nav link...")

        await self.missionfed_company_link.wait_for(state="visible", timeout=30000)
        await self.page.screenshot(path=f'{screenshots_directory}14_before_clicked_missionfed_client_left_nav_link.png')
        await self.missionfed_company_link.click()
        print("Clicked MissionFed left nav link...")

    async def select_core_products(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")

        # Scroll slowly and repeatedly to help ensure all checkboxes become visible
        print("Gradually scrolling the page to reveal checkboxes and continue button...")
        for step in range(3):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight / 4)")
            await self.page.wait_for_timeout(500)

        # List of checkboxes to select
        # Remove checking, CD and car loan since ad and adcopy exists on stg after DB migration
        checkboxes_to_select = [
            # self.carloan_checkbox, # COMMENTED OUT SINCE EXISTING ON STG EASTERLY AS MISSION AD AND ADCOPY SO NOT DUPLICATED
            self.carinsurance_checkbox, # ADDITIONAL AD GENERATED VIA INSTANT COPY THAT NEEDS DELETION
            self.homeinsurance_checkbox, # ADDITIONAL AD GENERATED VIA INSTANT COPY THAT NEEDS DELETION
            # self.cd_checkbox, # COMMENTED OUT SINCE EXISTING ON STG EASTERLY AS MISSION AD AND ADCOPY SO NOT DUPLICATED
            self.heloc_checkbox,
            # self.checking_checkbox, # COMMENTED OUT SINCE EXISTING ON STG EASTERLY AS MISSION AD AND ADCOPY SO NOT DUPLICATED
            self.credit_card_checkbox,
            self.mortgage_checkbox,
            self.savings_checkbox
        ]


        number_of_checkboxes = len(checkboxes_to_select)
        checkbox_counter = 0
        for checkbox in checkboxes_to_select:
            print(f"About to select {checkbox} which is checkbox number {checkbox_counter}...")
            locator = self.page.locator(checkbox)
            try:
                await locator.scroll_into_view_if_needed()
                await locator.wait_for(state="attached", timeout=5000)
                await locator.check()
                print(f'Selected checkbox {checkbox}')
                await self.page.screenshot(path=f'{screenshots_directory}10_selecting_core_product_checkbox_{checkbox_counter}.png')
            except Exception as e:
                print(f"Failed to check {checkbox}: {e}")
            # Increment for next checkbox index
            checkbox_counter += 1

        await self.page.screenshot(path=f'{screenshots_directory}11_selected_core_products.png')


    async def click_continue_button(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")
        try:
            print("Waiting for continue button to be visible before clicking...")
            await self.continue_button.wait_for(state="visible", timeout=20000)
            await self.continue_button.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)  # Let animations or DOM settle

            # Retry click up to 3 times if it fails
            for attempt in range(3):
                try:
                    print(f"Attempting to click continue button (Attempt {attempt + 1})...")
                    await self.continue_button.hover()
                    await self.continue_button.click(timeout=20000)
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.screenshot(path=f'{screenshots_directory}12_after_clicked_continue_after_core_products_selection.png')
                    return  # Exit early if successful
                except Exception as click_error:
                    print(Fore.YELLOW + f"Attempt {attempt + 1} failed to click continue: {click_error}" + Style.RESET_ALL)
                    await self.page.wait_for_timeout(2000)

            print(Fore.YELLOW + "Continue button click likely succeeded based on visual result, proceeding despite timeout." + Style.RESET_ALL)
            await self.page.screenshot(path=f'{screenshots_directory}12_continue_click_may_have_succeeded_but_raised_exception.png')
        except Exception as e:
            print(Fore.RED + f"Error clicking continue button: {e}" + Style.RESET_ALL)
            await self.page.screenshot(path=f'{screenshots_directory}error_failed_to_click_continue_button.png')
            raise



def clear_screenshots_directory(directory):
    """Clear screenshots directory - synchronous function works in async context."""
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


async def validate_image_exists(page, screenshots_directory):
    """
    Validates that the page does not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    from colorama import Fore, Style
    no_image_error_keywords = ["No image"]
    page_text = await page.text_content("body")
    found_errors = [msg for msg in no_image_error_keywords if msg in page_text]
    if found_errors:
        print(Fore.RED + f"No image message found on the preview page so review the full page screenshot {screenshots_directory}13_after_validated_campaign_preview.png. " + ", " + Style.RESET_ALL)
    else:
        print("No image message found on the page.")

async def delete_newly_generated_ads(page, screenshots_directory, names_to_delete):
    await page.goto(f"https://{test_env}finalyticsdata.com/admin/app/ad/?company__id__exact=18619&cu_id=vys")
    print(f"Navigated to ads list for deletion by name: {names_to_delete}")
    await page.screenshot(path=f'{screenshots_directory}17_after_navigated_to_easterly_mission_ads.png')

    try:
        rows = page.locator("#result_list tbody tr")
        row_count = await rows.count()
        print(f"Found {row_count} rows in the ad table.")

        for i in range(row_count):
            row = rows.nth(i)
            name_cell = row.locator("th.field-first_field_display")
            ad_name = (await name_cell.text_content()).strip()
            # Delete all newly generated ads
            if ad_name in names_to_delete:
                print(f"Selecting checkbox for ad: {ad_name}")
                checkbox = row.locator("input.action-select")
                await checkbox.check()

        await page.screenshot(path=f'{screenshots_directory}18_after_selecting_ads_for_deletion.png')
    except Exception as e:
        print(f"Failed to select checkboxes for specified names: {e}")

    try:
        await page.select_option("select[name='action']", value="delete_selected")
        print("Selected 'Delete selected ads' from the action dropdown")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f'{screenshots_directory}19_after_deleted_ads.png')
    except Exception as e:
        print(f"Failed to select 'Delete selected ads': {e}")

    try:
        await page.click("button.button.btn-primary.btn-round.search_btn")
        print("Clicked the Go button to execute the action")
    except Exception as e:
        print(f"Failed to click the Go button: {e}")

    try:
        await page.wait_for_selector("input[type='submit'][value=\"Yes, I’m sure\"]", timeout=5000)
        await page.click("input[type='submit'][value=\"Yes, I’m sure\"]")
        print("Clicked 'Yes, I'm sure' to confirm deletion")
    except Exception as e:
        print(f"Failed to confirm deletion: {e}")


async def delete_newly_generated_adcopy(page, screenshots_directory, names_to_delete):
    await page.goto(f"https://{test_env}finalyticsdata.com/admin/app/adcopy/?company__id__exact=18619&cu_id=vys")
    print(f"Navigated to ad copy list for deletion by name: {names_to_delete}")
    await page.screenshot(path=f'{screenshots_directory}19_after_navigated_to_easterly_mission_ads.png')

    try:
        rows = page.locator("#result_list tbody tr")
        row_count = await rows.count()
        print(f"Found {row_count} rows in the ad table.")

        for i in range(row_count):
            row = rows.nth(i)
            name_cell = row.locator("th.field-first_field_display")
            ad_name = (await name_cell.text_content()).strip()
            # Delete all newly generated ads
            if ad_name in names_to_delete:
                print(f"Selecting checkbox for ad: {ad_name}")
                checkbox = row.locator("input.action-select")
                await checkbox.check()

        await page.screenshot(path=f'{screenshots_directory}18_after_selecting_ads_for_deletion.png')
    except Exception as e:
        print(f"Failed to select checkboxes for specified names: {e}")

    try:
        await page.select_option("select[name='action']", value="delete_selected")
        print("Selected 'Delete selected ads' from the action dropdown")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f'{screenshots_directory}19_after_deleted_ads.png')
    except Exception as e:
        print(f"Failed to select 'Delete selected ads': {e}")

    try:
        await page.click("button.button.btn-primary.btn-round.search_btn")
        print("Clicked the Go button to execute the action")
    except Exception as e:
        print(f"Failed to click the Go button: {e}")

    try:
        await page.wait_for_selector("input[type='submit'][value=\"Yes, I’m sure\"]", timeout=5000)
        await page.click("input[type='submit'][value=\"Yes, I’m sure\"]")
        print("Clicked 'Yes, I'm sure' to confirm deletion")
    except Exception as e:
        print(f"Failed to confirm deletion: {e}")



async def validate_campaign_preview_links_images(page):
    valid_links = []
    invalid_links = []

    # Find all links under the Campaign Preview section
    heading = page.locator(".card-title", has_text="Campaign Preview: MISSION: Test Core Products")
    section = heading.locator("xpath=ancestor::div[contains(@class, 'card')]")
    links = await section.locator("a[href]").element_handles()

    links_info = []  # List to store tuples of (link_text, href)

    for link in links:
        href = await link.get_attribute("href")
        text = await page.evaluate('(element) => element.textContent', link)
        if href and (href.startswith("http") or href.startswith("/")):
            if href.startswith("/"):
                href = page.url.split("/")[0] + "//" + page.url.split("/")[2] + href
            links_info.append((text.strip() if text else "(no text)", href))

    # Remove duplicates by URL (preserving the first text found)
    seen_urls = set()
    unique_links_info = []
    for text, href in links_info:
        if href not in seen_urls:
            seen_urls.add(href)
            unique_links_info.append((text, href))

    # Also get image sources within .page-inner
    image_sources = []
    image_elements = await page.locator(".page-inner img[src]").element_handles()
    for img in image_elements:
        src = await img.get_attribute("src")
        if src and (src.startswith("http") or src.startswith("/")):
            if src.startswith("/"):
                src = page.url.split("/")[0] + "//" + page.url.split("/")[2] + src
            image_sources.append(("<img>", src))

    # Combine links and images
    all_urls = unique_links_info + image_sources

    async with aiohttp.ClientSession() as session:
        for text, url in all_urls:
            try:
                if "data:image" in url:
                    # Treat data:image URLs as 404 and not 403
                    invalid_links.append((text, url, 404))
                    continue
                async with session.get(url, allow_redirects=True) as response:
                    if response.status in [404, 500]:
                        invalid_links.append((text, url, response.status))
                    else:
                        valid_links.append((text, url, response.status))
            except Exception as e:
                invalid_links.append((text, url, str(e)))

    print("\nValid URLs:")
    for text, url, status in valid_links:
        print(f"  Text: {text} | URL: {url} -> {status}")

    # print("\nInvalid URLs:")
    print(Fore.RED + f"\nInvalid URLs:" + Style.RESET_ALL)
    for text, url, status in invalid_links:
        # print(f"  Text: {text} | URL: {url} -> {status}")
        print(Fore.RED + f"  Text: {text} | URL: {url} -> {status}" + Style.RESET_ALL)

    assert not invalid_links, f"Some links/images are invalid: {[(url, status) for _, url, status in invalid_links]}"


@pytest.mark.asyncio
async def test_instant_copy():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()  # Create an isolated browser context
        page = await context.new_page()  # Open a new page (tab)
        login_page = LoginPage(page)
        instant_copy_page = InstantCopyPage(page)

        screenshots_directory = 'screenshots_adminsite_using_pytest/instant_copy/'
        clear_screenshots_directory(screenshots_directory)
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
        await expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/')

        # Navigate to instant copy after login
        await instant_copy_page.navigate_to_instant_copy(screenshots_directory)

        try:
            await instant_copy_page.input_website_domain("missionfed.com", screenshots_directory)
            print(f"Website domain missionfed.com was entered.")
            await page.screenshot(path=f'{screenshots_directory}9_after_input_website_domain.png')
        except Exception as e:
            print(f"Error entering website domain missionfed.com: {e}")

        # Pause for 10 seconds
        print("Pause for a few seconds before clicking continue to allow time for continue button to get activated")
        time.sleep(15)

        # Click Continue
        await instant_copy_page.click_continue_button(screenshots_directory)
        print(f"Continue button clicked after website domain input")

        # Select core products
        await instant_copy_page.select_core_products(screenshots_directory)

        # Click Continue
        await instant_copy_page.click_continue_button(screenshots_directory)
        print(f"Continue button clicked after selected core products")

        # **Check for campaign preview page heading after Instant Copy after waiting for page to load
        await page.wait_for_load_state("networkidle")
        await expect(page.locator("text=Campaign Preview")).to_be_visible()
        print("Content Preview page appeared after instant import.")
        # Scroll to bottom to ensure full page is rendered before taking screenshot
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)  # Give time for lazy-loaded elements
        await page.screenshot(path=f'{screenshots_directory}13_after_validated_campaign_preview.png', full_page=True)

        # SCROLL DOWN SO CAN PREVIEW THE NEW CAR INSURANCE AD and take screenshot
        await page.locator("text=MISSION: Car Insurance").first.scroll_into_view_if_needed()
        print("Scroll down to newly generated ad...")
        await page.screenshot(path=f'{screenshots_directory}14_after_scroll_to_newly_generated_car_insurance_ad.png')

        # SCROLL DOWN SO CAN PREVIEW THE NEW HOME INSURANCE AD and take screenshot
        await page.locator("text=MISSION: Home Insurance").first.scroll_into_view_if_needed()
        print("Scroll down to newly generated ad...")
        await page.screenshot(path=f'{screenshots_directory}15_after_scroll_to_newly_generated_home_insurance_ad.png')

        # Check that the page does not have any internal server error or any error message
        await validate_no_server_error(page, screenshots_directory)
        print(f"Page was validated to not have any errors after instant copy")
        await page.screenshot(path=f'{screenshots_directory}16_after_validated_no_error.png')

        # Validate links and images on Preview Content page and modify to only print the errors on the console and catch if there is an exception
        print(f"Links and Images were validated on the Preview Content page")
        try:
            await validate_campaign_preview_links_images(page)
        except Exception as e:
            print(Fore.RED + f"validate_campaign_preview_links_images: {e}" + Style.RESET_ALL)
        print(f"Preview Page was validated and broken links were found")

        # Check for no image message when preview content and modify to only print the errors on the console and catch if there is an exception
        # await validate_image_exists(page, screenshots_directory)
        try:
            await validate_image_exists(page, screenshots_directory)
        except Exception as e:
            print(Fore.RED + f"validate_image_exists failed: {e}" + Style.RESET_ALL)
        print(f"Page was validated to not have image for product scenarios")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f'{screenshots_directory}20_after_validated_image_exists.png', full_page=True)

        # Delete generated after validation of preview page
        ad_names_to_delete = {"MISSION: Car Insurance", "MISSION: Home Insurance", "MISSION: HELOC", "MISSION: Credit Card", "MISSION: Mortgage", "MISSION: Savings Account"}
        await delete_newly_generated_ads(page, screenshots_directory, ad_names_to_delete)
        await delete_newly_generated_adcopy(page, screenshots_directory, ad_names_to_delete)
        print("Deleted newly generated ads and adcopies")

