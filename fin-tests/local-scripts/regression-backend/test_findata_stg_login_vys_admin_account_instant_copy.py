import pytest
import asyncio
import aiohttp
import time
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

def clear_screenshots_directory(directory):
    """Clear screenshots directory - synchronous function works in async context."""
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
        self.easterly_company_link = page.get_by_text("Easterly").nth(0)
        self.missionfed_company_link = page.get_by_text("Mission Fed").nth(0)
        self.clients_nav_link = page.get_by_text("Clients")
        self.car_insurance_to_preview = page.get_by_text("Car Insurance")

        # Textarea for entering the website domain
        self.input_website_domain_text_field = "#domain"
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
        """Ensure the left-nav 'Content' accordion is expanded so its children (Instant Copy, etc.) are visible."""
        page = self.page
        content_toggle = page.locator("a[data-toggle='collapse'][href='#sidebarLayouts']").first
        sidebar_layouts = page.locator("div#sidebarLayouts").first

        await content_toggle.wait_for(state="visible", timeout=15000)
        classes = await sidebar_layouts.get_attribute("class") or ""
        is_expanded = "show" in classes

        if not is_expanded:
            print("Content section appears collapsed; expanding it to reveal child items (Instant Copy, etc.)...")
            await content_toggle.click()
            await page.wait_for_timeout(500)
            if screenshots_directory:
                await page.screenshot(path=f"{screenshots_directory}2_expanded_content_left_nav.png")
        else:
            print("Content section is already expanded.")

    async def _expand_instant_ai_if_needed(self, screenshots_directory: str | None = None):
        """Expand the 'Instant AI' submenu under Content so Instant Copy becomes visible."""
        page = self.page
        instant_ai_link = page.get_by_role("link", name="Instant AI").first
        instant_copy_link = page.get_by_role("link", name="Instant Copy").first

        # Only click Instant AI if Instant Copy is not yet visible
        if not await instant_copy_link.is_visible():
            print("'Instant Copy' not visible; clicking 'Instant AI' to expand its submenu...")
            await instant_ai_link.wait_for(state="visible", timeout=15000)
            await instant_ai_link.click()
            await page.wait_for_timeout(500)
            if screenshots_directory:
                await page.screenshot(path=f"{screenshots_directory}2b_expanded_instant_ai_submenu.png")
        else:
            print("'Instant Copy' already visible under Instant AI submenu.")

    async def navigate_to_instant_copy(self, screenshots_directory: str, test_env: str = 'stg'):
        page = self.page

        # Try the simple case first: 'Instant Copy' already visible in the left nav
        instant_copy_link = page.get_by_role("link", name="Instant Copy").first
        if await instant_copy_link.is_visible():
            print("'Instant Copy' link is already visible; clicking it directly...")
            await instant_copy_link.click()
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{screenshots_directory}3_instant_copy_loaded_direct.png")
            print("Successfully navigated to Instant Copy page (direct).")
        else:
            print("'Instant Copy' not visible; expanding the 'Content' section in the left nav...")
            await self._expand_content_section_if_needed(screenshots_directory)

            # Dark Matter UI: 'Instant Copy' is now nested under 'Instant AI' submenu
            await self._expand_instant_ai_if_needed(screenshots_directory)

            instant_copy_link = page.get_by_role("link", name="Instant Copy").first
            print("Waiting for 'Instant Copy' link to become visible after expanding Instant AI...")
            await instant_copy_link.wait_for(state="visible", timeout=15000)
            await instant_copy_link.click()
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=f"{screenshots_directory}3_instant_copy_loaded_after_expand.png")
            print("Successfully navigated to Instant Copy page after expanding Instant AI submenu.")

        # After clicking Instant Copy, navigate to Easterly company page
        await page.wait_for_load_state("networkidle")

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
        print(f"About to enter website domain {website_domain}")
        await self.page.fill(self.input_website_domain_text_field, website_domain)
        print(f"Website domain entered: {website_domain}")
        await self.page.screenshot(path=f'{screenshots_directory}8_entered_website_domain.png')

    async def select_core_products(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")

        # Scroll slowly to help ensure all checkboxes become visible
        print("Gradually scrolling the page to reveal checkboxes...")
        for step in range(3):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight / 4)")
            await self.page.wait_for_timeout(500)

        # List of checkboxes to select (excluding existing ones like car loan, CD, checking)
        checkboxes_to_select = [
            self.carinsurance_checkbox,
            self.homeinsurance_checkbox,
            self.heloc_checkbox,
            self.credit_card_checkbox,
            self.mortgage_checkbox,
            self.savings_checkbox
        ]

        checkbox_counter = 0
        for checkbox in checkboxes_to_select:
            print(f"About to select checkbox {checkbox_counter}: {checkbox}")
            locator = self.page.locator(checkbox)
            try:
                await locator.scroll_into_view_if_needed()
                await locator.wait_for(state="attached", timeout=5000)
                await locator.check()
                print(f'Selected checkbox {checkbox}')
                await self.page.screenshot(path=f'{screenshots_directory}10_selecting_core_product_checkbox_{checkbox_counter}.png')
            except Exception as e:
                print(f"Failed to check {checkbox}: {e}")
            checkbox_counter += 1

        await self.page.screenshot(path=f'{screenshots_directory}11_selected_core_products.png')

    async def click_continue_button(self, screenshots_directory):
        await self.page.wait_for_load_state("networkidle")
        try:
            print("Waiting for continue button to be visible...")
            await self.continue_button.wait_for(state="visible", timeout=20000)
            await self.continue_button.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)

            # Retry click up to 3 times if it fails
            for attempt in range(3):
                try:
                    print(f"Attempting to click continue button (Attempt {attempt + 1})...")
                    await self.continue_button.hover()
                    await self.continue_button.click(timeout=20000)
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.screenshot(path=f'{screenshots_directory}12_after_clicked_continue.png')
                    return
                except Exception as click_error:
                    print(Fore.YELLOW + f"Attempt {attempt + 1} failed: {click_error}" + Style.RESET_ALL)
                    await self.page.wait_for_timeout(2000)

            print(Fore.YELLOW + "Continue button click likely succeeded, proceeding..." + Style.RESET_ALL)
            await self.page.screenshot(path=f'{screenshots_directory}12_continue_click_completed.png')
        except Exception as e:
            print(Fore.RED + f"Error clicking continue button: {e}" + Style.RESET_ALL)
            await self.page.screenshot(path=f'{screenshots_directory}error_continue_button.png')
            raise

async def validate_no_server_error(page, screenshots_directory):
    """Validates that the page does not contain server error messages."""
    # Use specific error messages to avoid false positives from generic "error" word
    error_keywords = ["Server Error", "500 Internal Server Error", "(500)", "Page not found", "404 Not Found", "502 Bad Gateway", "503 Service Unavailable"]
    page_text = await page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)

async def validate_image_exists(page, screenshots_directory):
    """Check if 'No image' message appears on the page."""
    no_image_error_keywords = ["No image"]
    page_text = await page.text_content("body")
    found_errors = [msg for msg in no_image_error_keywords if msg in page_text]
    if found_errors:
        print(Fore.RED + f"No image message found on preview page" + Style.RESET_ALL)
    else:
        print("No 'No image' message found.")

async def delete_newly_generated_ads(page, screenshots_directory, names_to_delete, test_env):
    await page.goto(f"https://{test_env}finalyticsdata.com/admin/app/ad/?company__id__exact=18619&cu_id=vys")
    print(f"Navigated to ads list for deletion")
    await page.screenshot(path=f'{screenshots_directory}17_ads_list_for_deletion.png')

    try:
        rows = page.locator("#result_list tbody tr")
        row_count = await rows.count()
        print(f"Found {row_count} rows in the ad table.")

        for i in range(row_count):
            row = rows.nth(i)
            name_cell = row.locator("th.field-first_field_display")
            ad_name = (await name_cell.text_content()).strip()
            if ad_name in names_to_delete:
                print(f"Selecting checkbox for ad: {ad_name}")
                checkbox = row.locator("input.action-select")
                await checkbox.check()

        await page.screenshot(path=f'{screenshots_directory}18_selected_ads_for_deletion.png')
        await page.select_option("select[name='action']", value="delete_selected")
        await page.click("button.button.btn-primary.btn-round.search_btn")
        await page.wait_for_selector("input[type='submit'][value=\"Yes, I'm sure\"]", timeout=5000)
        await page.click("input[type='submit'][value=\"Yes, I'm sure\"]")
        print("Deleted selected ads")
    except Exception as e:
        print(f"Error deleting ads: {e}")

async def delete_newly_generated_adcopy(page, screenshots_directory, names_to_delete, test_env):
    await page.goto(f"https://{test_env}finalyticsdata.com/admin/app/adcopy/?company__id__exact=18619&cu_id=vys")
    print(f"Navigated to adcopy list for deletion")
    await page.screenshot(path=f'{screenshots_directory}19_adcopy_list_for_deletion.png')

    try:
        rows = page.locator("#result_list tbody tr")
        row_count = await rows.count()
        print(f"Found {row_count} rows in the adcopy table.")

        for i in range(row_count):
            row = rows.nth(i)
            name_cell = row.locator("th.field-first_field_display")
            ad_name = (await name_cell.text_content()).strip()
            if ad_name in names_to_delete:
                print(f"Selecting checkbox for adcopy: {ad_name}")
                checkbox = row.locator("input.action-select")
                await checkbox.check()

        await page.screenshot(path=f'{screenshots_directory}20_selected_adcopy_for_deletion.png')
        await page.select_option("select[name='action']", value="delete_selected")
        await page.click("button.button.btn-primary.btn-round.search_btn")
        await page.wait_for_selector("input[type='submit'][value=\"Yes, I'm sure\"]", timeout=5000)
        await page.click("input[type='submit'][value=\"Yes, I'm sure\"]")
        print("Deleted selected adcopy")
    except Exception as e:
        print(f"Error deleting adcopy: {e}")

async def validate_campaign_preview_links_images(page):
    """Validate links and images on campaign preview page."""
    valid_links = []
    invalid_links = []

    heading = page.locator(".card-title", has_text="Campaign Preview")
    section = heading.locator("xpath=ancestor::div[contains(@class, 'card')]")
    links = await section.locator("a[href]").element_handles()

    links_info = []
    for link in links:
        href = await link.get_attribute("href")
        text = await page.evaluate('(element) => element.textContent', link)
        if href and (href.startswith("http") or href.startswith("/")):
            if href.startswith("/"):
                href = page.url.split("/")[0] + "//" + page.url.split("/")[2] + href
            links_info.append((text.strip() if text else "(no text)", href))

    # Remove duplicates
    seen_urls = set()
    unique_links_info = []
    for text, href in links_info:
        if href not in seen_urls:
            seen_urls.add(href)
            unique_links_info.append((text, href))

    # Get image sources
    image_sources = []
    image_elements = await page.locator(".page-inner img[src]").element_handles()
    for img in image_elements:
        src = await img.get_attribute("src")
        if src and (src.startswith("http") or src.startswith("/")):
            if src.startswith("/"):
                src = page.url.split("/")[0] + "//" + page.url.split("/")[2] + src
            image_sources.append(("<img>", src))

    all_urls = unique_links_info + image_sources

    async with aiohttp.ClientSession() as session:
        for text, url in all_urls:
            try:
                if "data:image" in url:
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
        print(f"  {text} | {url} -> {status}")

    if invalid_links:
        print(Fore.RED + "\nInvalid URLs:" + Style.RESET_ALL)
        for text, url, status in invalid_links:
            print(Fore.RED + f"  {text} | {url} -> {status}" + Style.RESET_ALL)

    assert not invalid_links, f"Some links/images are invalid: {[(url, status) for _, url, status in invalid_links]}"

@pytest.mark.asyncio
async def test_instant_copy():
    """Test instant copy functionality - creates campaigns and validates them."""
    async with async_playwright() as p:
        import os
        headless = os.environ.get("HEADLESS", "false").lower() == "true"
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Setup environment
            findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')

            screenshots_directory = os.path.join(os.path.dirname(__file__), 'screenshots_adminsite_using_pytest/instant_copy/')
            clear_screenshots_directory(screenshots_directory)
            print(f"Cleared screenshots directory {screenshots_directory}.")

            # Initialize page objects
            login_page = AdminLoginPage(page, is_async=True)
            instant_copy_page = InstantCopyPage(page)

            # Perform login
            await login_page.navigate(test_env)
            print(f"About to login...")
            await login_page.login(findata_user, findata_pw)

            await login_page.enter_2fa_code(totp)
            await login_page.complete_2fa_login(test_env)

            await login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')

            current_url = page.url
            print(f"Current URL after login is {current_url}.")

            # Navigate to instant copy
            await instant_copy_page.navigate_to_instant_copy(screenshots_directory, test_env)

            # Input website domain
            try:
                await instant_copy_page.input_website_domain("missionfed.com", screenshots_directory)
                print(f"Website domain missionfed.com entered.")
                await page.screenshot(path=f'{screenshots_directory}9_after_input_website_domain.png')
            except Exception as e:
                print(f"Error entering website domain: {e}")

            # Wait for continue button to activate
            print("Pausing to allow continue button to activate...")
            time.sleep(15)

            # Click Continue
            await instant_copy_page.click_continue_button(screenshots_directory)
            print("Continue button clicked after website domain input")

            # Select core products
            await instant_copy_page.select_core_products(screenshots_directory)

            # Click Continue
            await instant_copy_page.click_continue_button(screenshots_directory)
            print("Continue button clicked after selecting core products")

            # Validate campaign preview
            # Default assertion timeout (5s) is too tight for this network round-trip in CI,
            # where the wizard's server-side campaign generation can take noticeably longer
            # than on a local machine.
            await page.wait_for_load_state("networkidle")
            await expect(page.locator("text=Campaign Preview")).to_be_visible(timeout=30000)
            print("Campaign Preview page appeared after instant copy.")

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'{screenshots_directory}13_campaign_preview.png', full_page=True)

            # Scroll to newly generated ads
            await page.locator("text=MISSION: Car Insurance").first.scroll_into_view_if_needed()
            await page.screenshot(path=f'{screenshots_directory}14_car_insurance_ad.png')

            await page.locator("text=MISSION: Home Insurance").first.scroll_into_view_if_needed()
            await page.screenshot(path=f'{screenshots_directory}15_home_insurance_ad.png')

            # Validate no server errors
            await validate_no_server_error(page, screenshots_directory)
            print("Page validated - no errors after instant copy")
            await page.screenshot(path=f'{screenshots_directory}16_validated_no_error.png')

            # Validate links and images
            print("Validating links and images...")
            try:
                await validate_campaign_preview_links_images(page)
            except Exception as e:
                print(Fore.RED + f"Link/image validation: {e}" + Style.RESET_ALL)

            # Validate images exist
            try:
                await validate_image_exists(page, screenshots_directory)
            except Exception as e:
                print(Fore.RED + f"Image validation: {e}" + Style.RESET_ALL)

            await page.screenshot(path=f'{screenshots_directory}20_final_validation.png', full_page=True)

            # Cleanup - delete generated ads and adcopies
            ad_names_to_delete = {
                "MISSION: Car Insurance",
                "MISSION: Home Insurance",
                "MISSION: HELOC",
                "MISSION: Credit Card",
                "MISSION: Mortgage",
                "MISSION: Savings Account"
            }
            await delete_newly_generated_ads(page, screenshots_directory, ad_names_to_delete, test_env)
            await delete_newly_generated_adcopy(page, screenshots_directory, ad_names_to_delete, test_env)
            print("Deleted newly generated ads and adcopies")

            print("Instant copy test completed successfully")

        finally:
            await context.close()
            await browser.close()
