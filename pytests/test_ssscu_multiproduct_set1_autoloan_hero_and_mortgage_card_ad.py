"""
Test SSSCU Multiproduct Set 1 - Auto Loan Hero and Mortgage Card Ad

Version History:
- 2025-11-23: Multiple fixes to make test pass
    - Added debug_all=1&session_init=1 to the homepage URL for personalization
    - Fixed missing commas in the card_ads_CTA_link_selectors list
    - Fixed missing closing quote in the has-text selector ('OPEN A CERTIFICATE')
    - Fixed missing commas in the expected_card_ads_CTA_links list
    - Fixed credential access issue by using browser.new_page() instead of
      trying to access non-existent browser.username and browser.password attributes
"""

import asyncio
from urllib.parse import urljoin

import pytest
import pytest_asyncio
import os
import time
import shutil
from pathlib import Path
from itertools import islice
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext

# Function to clear the directory before saving new screenshots

# Add parent directory to path for qa_tools import
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    detect_js_errors_from_specific_files_async,
    save_page_source_async,
    browser,
    DEFAULT_TIMEOUT)

async def validate_no_server_error(page):
    """
    Validates that the page does not contain server error messages.

    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error", "Page not found", "Not Found"]
    # page_text = page.inner_text("body")
    page_text = await page.inner_text("body")  # Properly await the coroutine
    found_errors = [msg for msg in error_keywords if msg in page_text]

    assert not found_errors, f"Error messages found on the page: {', '.join(found_errors)}"

async def scroll_until_visible(page, selector, timeout=10000):
    """
    Scrolls down until the given selector is visible or until timeout is reached.
    """
    try:
        print(f"Scrolling to make '{selector}' visible...")
        await page.locator(selector).scroll_into_view_if_needed()
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        print(f"Element '{selector}' is now visible.")
    except PlaywrightTimeoutError:
        pytest.fail(f"Timeout waiting for '{selector}' to be visible.")

# Fixture to set up Playwright and launch the browser
# @pytest_asyncio.fixture
# async def browser(request)-> BrowserContext:
#     """Fixture to launch the browser with HTTP credentials."""
#     username = request.param.get("username")
#     password = request.param.get("password")
#     async with async_playwright() as playwright:
#         # Changed headless=False for DEBUGGING
#         browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])
#         context = await browser.new_context(http_credentials={"username": username, "password": password})
#         context.set_default_timeout(40000)
#         yield context
#         await context.close()
#         await browser.close()
#

# @pytest_asyncio.fixture
# async def browser(request):
#     """Fixture to launch the browser with HTTP credentials."""
#     username = request.param.get("username")
#     password = request.param.get("password")
#     async with async_playwright() as playwright:
#         browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])
#         context = await browser.new_context(http_credentials={"username": username, "password": password})
#         context.set_default_timeout(40000)
#         yield context
#         await browser.close()

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True  # Treat the parameter as input for the 'browser' fixture
)
@pytest.mark.parametrize("product_urls", [
    {
        "auto_refi": "https://sscustage.wpenginepowered.com/loans-and-credit-cards/vehicle-loans/auto-loans/?api=stg",
    }
])
async def test_ssscu_multiproduct_and_js_errors(
        browser,
        product_urls,
        homepage_url="https://sscustage.wpenginepowered.com/?api=stg&debug_all=1&session_init=1", #USE STG DATA with debug_all for personalization
        homepage_url_stg_no_api_param = "https://sscustage.wpenginepowered.com/",
        auto_loan_expected_heading="DREAMING OF THAT PERFECT RIDE?",
        hero_heading_selector="#primary > section:nth-child(1) > div > div > div > div > div.col-12.col-md-6.order-md-2.order-1 > div > div > h2",
        hero_cta_selector='#primary > section:nth-child(1) > div > div > div > div > div.col-12.col-md-6.order-md-2.order-1 > div > div > div > div > a.btn.btn-primary',
        apply_today_hero_CTA_button_selector = "a.btn.btn-primary:has-text('APPLY NOW')",
        apply_today_card_cta_link_selector = "a:has-text('APPLY NOW)",
        client="ssscu"
):
    print(f"Starting {client} hero ad test..")

    # Save the screenshots in the tests folder and NOT in another tests folder under tests
    screenshots_directory = 'screenshots_' + client + '_using_pytest/multiproduct_set1/'
    clear_screenshots_directory(screenshots_directory)
    print(f"Cleared screenshot directory {screenshots_directory} so get new screenshots and timestamps for images or created it if it doesn't exist")

    # Define selectors and expected h2 headings for the card ads
    card_ad_selectors = [
        # ".layout.feature:first-of-type .feature-content b"
        "section#finalytics-feature div.feature-container.reverse b"
    ]

    expected_h2_headings = [
        # "DEBT CONSOLIDATION"  # Replace with actual expected heading for card 1
        "CERTIFICATE ACCOUNTS",  # Replace with actual expected heading for card 1 or another possible heading if expected card 1 times out
        "MONEY MARKET"
    ]

    # Define the card CTA link selectors and expected links
    card_ads_CTA_link_selectors = [
        "#\\36 7352a8226423 > div > div > div > div > div.feature-content.feature-content-side > div.d-grid.d-inline-flex.flex-wrap.align-items-center.gap-3.mt-4 > a.btn.btn-primary",
        # "div > div > div > div > div.feature-content.feature-content-side > div.d-grid.d-inline-flex.flex-wrap.align-items-center.gap-3.mt-4 > a.btn.btn-primary",
        # "# \36 7352a8226423 > div > div > div > div > div.feature-content.feature-content-side > div:nth-child(1) > b"
        "a.btn.btn-primary:has-text('OPEN A CERTIFICATE')"
    ]

    expected_card_ads_CTA_links = [
        "https://sscustage.wpenginepowered.com/why-choose-us",  # Replace with actual expected CTA link for card 1
        # "https://silverstatecu.mymortgage-online.com/loan-app/?siteId=9753643328&lar=officer&workFlowId=83309", # Replace with actual expected CTA link for card or another possible CTA link if expected card 1 times out
        "https://sscustage.wpenginepowered.com/why-choose-us"  # Certificate card CTA link
    ]

    # context = await browser.new_context()
    page = await browser.new_page()

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)
    # Initialize the screenshot index
    screenshot_index = 0

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        try:
            await page.wait_for_load_state('networkidle', timeout=90000)
        except PlaywrightTimeoutError:
            print("Network idle timed out, falling back to domcontentloaded")
            await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)
        screenshot_index += 1 # Increment the screenshot index
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_homepage_screenshot.png')

        # Loop through the product URLs and take screenshots
        print(f"About to visit the first x product URLs for multiproduct setup of the hero and card...")
        for product_name, product_url in islice(product_urls.items(), 1):  # Limit to first 1 items
            if not isinstance(product_url, str):
                pytest.fail(f"Unsupported value in 'product_urls': {product_name} -> {product_url}")
            print(f"Visiting product URL: {product_name} - {product_url}")
            await page.goto(product_url, timeout=DEFAULT_TIMEOUT)
            try:
                await page.wait_for_load_state('networkidle', timeout=90000)
            except PlaywrightTimeoutError:
                print("Network idle timed out, falling back to domcontentloaded")
                await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)

            # Increment the screenshot index
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, f"{screenshot_index}_{product_name}_screenshot.png")
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        try:
            await page.wait_for_load_state('networkidle', timeout=90000)
        except PlaywrightTimeoutError:
            print("Network idle timed out, falling back to domcontentloaded")
            await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)

        # Refresh homepage 3 times to get past "Best Credit Union 8 Years in a Row" ad to the standard personalization ad
        print("Refreshing homepage 3 times to ensure standard personalization ad displays...")
        for i in range(3):
            print(f"Refreshing homepage (refresh {i+1}/3)...")
            await page.reload()
            await page.wait_for_load_state('load')

        print("Homepage refreshes complete. Proceeding with ad validation...")

        print(f"Waiting for {hero_heading_selector} on the homepage...")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_homepage_before_heading_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=DEFAULT_TIMEOUT)

        # Strip any white space in the heading
        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert auto_loan_expected_heading == ad_on_hero_content_h1_normalized, (
        f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{auto_loan_expected_heading}'")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_ad1_screenshot_and_accept_cookie.png', timeout=DEFAULT_TIMEOUT)

        print(f"---> About to check if there is an accept cookie locator")
        # Handle cookie consent if the button is visible
        cookie_button_selector = "#onetrust-accept-btn-handler"
        if await page.is_visible(cookie_button_selector):
            print("Cookie consent button detected. Clicking 'Accept'...")
            await page.click(cookie_button_selector)
            try:
                await page.wait_for_load_state('networkidle', timeout=90000)
            except PlaywrightTimeoutError:
                print("Network idle timed out, falling back to domcontentloaded")
                await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)

            print("Cookie Accept consent button clicked and loading the page...")
        else:
            print("Cookie consent button not visible. Proceeding...")

        print("Sleep for a few seconds to see if page is not yet fully loaded before taking screenshot")
        time.sleep(5)

        # Screenshot after clicking the accept cookie button if visible
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_after_accept_cookie.png', timeout=DEFAULT_TIMEOUT)

        # Click the "Apply Today" button and handle the new tab
        if await page.is_visible(apply_today_hero_CTA_button_selector):
            print("Clicking the 'Apply Today' button...")
            await page.click(apply_today_hero_CTA_button_selector)
            # await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)
            try:
                await page.wait_for_load_state('networkidle', timeout=90000)
            except PlaywrightTimeoutError:
                print("Network idle timed out, falling back to domcontentloaded")
                await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)

            print("Waited for page to load after clicking the CTA link")

            # COMMENT OUT FOR NOW SO CAN TEST THE OTHER LINKS
            # Check that the page on the new tab  does not have any internal server error or any error message
            # await validate_no_server_error(new_tab)

            # Take a screenshot of the new tab
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, "CTA_page_screenshot.png")
            await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_clicked_hero_CTA_link.png',
                    timeout=DEFAULT_TIMEOUT)
            print(f"Screenshot of the opened page saved at {screenshot_path}")

        else:
            pytest.fail("'Apply Today' button was not found or visible on the page.")

         # Go back to the main page after clicking the CTA
        print(f"Go to the homepage after clicking the CTA link...")
        await page.goto(homepage_url, timeout=DEFAULT_TIMEOUT)
        try:
            await page.wait_for_load_state('networkidle', timeout=90000)
        except PlaywrightTimeoutError:
            print("Network idle timed out, falling back to domcontentloaded")
            await page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_TIMEOUT)

        # await page.wait_for_load_state('load', timeout=DEFAULT_TIMEOUT)

        # Screenshot after going back to the homepage
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_go_back_to_homepage.png',
                              timeout=DEFAULT_TIMEOUT)

        # Scroll down until the card ads are visible
        for selector in card_ad_selectors:
            print(f"Scrolling to first instance of '{selector}'...")
            first_instance = page.locator(selector).first
            await first_instance.scroll_into_view_if_needed()
            await first_instance.wait_for(state="visible", timeout=10000)
            screenshot_index += 1
            await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_page_scroll.png',
                    timeout=DEFAULT_TIMEOUT)
            print(f"Screenshot after scrolling to the card ad at {screenshot_path}")

        # Get the h2 headings of the card ads in class and compare against expected h2 heading
        for i, selector in enumerate(card_ad_selectors):
            print(f"Checking card ads heading {i + 1}")
            try:
                h2_text = await page.inner_text(selector)
                h2_text_normalized = h2_text.strip()
                print(f"Extracted card ad h2: {h2_text_normalized}")

                # expected_heading = expected_h2_headings[i]
                # Ensure expected headings are a list of possibilities
                expected_heading = expected_h2_headings
                # If expected_heading is a string, make it a list for uniform handling
                if isinstance(expected_heading, str):
                    expected_heading = [expected_heading]

                # assert h2_text_normalized in expected_heading, (
                #     f"Mismatch for heading {i + 1}: Expected one of {expected_heading}, got '{h2_text_normalized}'"
                # )
                # Comparing * one extracted heading * against * multiple acceptable options *
                assert any(h2_text_normalized == heading for heading in expected_heading), (
                    f"Mismatch for heading {i + 1}: Expected one of {expected_heading}, got '{h2_text_normalized}'"
                )

            except Exception as e:
                pytest.fail(f"Failed to validate heading {i + 1}: {e}")

        print("All h2 headings in the card ads were validated successfully.")

        base_url = "https://sscustage.wpenginepowered.com"

        # Get the CTA links of the 3 card ads in class and compare against expected links
        for j, link_selector in enumerate(card_ads_CTA_link_selectors):
            print(f"Checking card ads CTA links {j + 1} ...")
            try:
                # Check CTA links of card ads
                CTA_link_href = await page.get_attribute(link_selector, "href")
                print(f"Extracted card ad CTA link: {CTA_link_href}")
                # assert CTA_link_href == expected_card_ads_CTA_links[j], (
                #     f"Mismatch for CTA link {j + 1}: Expected '{expected_card_ads_CTA_links[j]}', got '{CTA_link_href}'"
                # )

                # Normalize to full URL if it's a relative link
                if CTA_link_href and CTA_link_href.startswith("/"):
                    CTA_link_href = urljoin(base_url, CTA_link_href)
                    print(f"Normalized relative URL to: {CTA_link_href}")

                # Ensure expected headings are a list of possibilities
                expected_card_ads_CTA_link = expected_card_ads_CTA_links
                # If expected_heading is a string, make it a list for uniform handling
                if isinstance(expected_card_ads_CTA_link, str):
                    expected_card_ads_CTA_link = [expected_card_ads_CTA_link]

                # Check for two possible card1 CTA link values in case card1 times out
                # if isinstance(expected_card_ads_CTA_links[j], list):
                #     assert CTA_link_href in expected_card_ads_CTA_links[j], (
                #         f"Mismatch for heading {i + 1}: Expected one of {expected_card_ads_CTA_links[j]}, got '{CTA_link_href}'"
                #     )
                # else:
                #     assert CTA_link_href == expected_card_ads_CTA_links[j], (
                #         f"Mismatch for heading {i + 1}: Expected '{expected_card_ads_CTA_links[j]}', got '{CTA_link_href}'"
                #     )

                # PREVIOUS
                # Comparing * one extracted heading * against * multiple acceptable options *
                # assert any(CTA_link_href == heading for heading in expected_card_ads_CTA_link), (
                #     f"Mismatch for card CTA link {i + 1}: Expected one of {expected_card_ads_CTA_link}, got '{CTA_link_href}'"
                # )

                # CHANGE
                CTA_link_href_normalized = CTA_link_href.replace("\n", "").strip()
                expected_card_ads_CTA_link_normalized = [link.replace("\n", "").strip() for link in
                                                         expected_card_ads_CTA_link]
                assert any(CTA_link_href_normalized == heading for heading in expected_card_ads_CTA_link_normalized), (
                    f"Mismatch for card CTA link {j + 1}: Expected one of {expected_card_ads_CTA_link_normalized}, got '{CTA_link_href_normalized}'"
                )

                # Open the card_CTA_link_full_url in a new tab and check that no error on the new tab, take screenshot and close the new tab
                card_CTA_link_full_url = CTA_link_href

                # Use the existing browser context to create a new page (inherits credentials)
                new_tab = await browser.new_page()
                print(f"Opening URL in new tab: {card_CTA_link_full_url}")
                # await new_tab.goto(card_CTA_link_full_url)
                # COMMENTED OUT SINCE CAUSING TIMEOUTS WAITING FOR FONTS TO LOAD
                # await new_tab.wait_for_load_state("networkidle")

                print(f"Opening URL in new tab: {card_CTA_link_full_url}")
                # await new_tab.goto(card_CTA_link_full_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT)
                await new_tab.goto(card_CTA_link_full_url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT)

                # COMMENT OUT FOR NOW TO CHECK THAT THE SCREENSHOTS ARE TAKEN
                # await validate_no_server_error(new_tab)
                screenshot_index += 1
                await new_tab.screenshot(
                    path=f'{screenshots_directory}{screenshot_index}_multiproduct_card_ad{j + 1}_CTA_link_page.png',
                    timeout=DEFAULT_TIMEOUT)

            except Exception as e:
                pytest.fail(f"Failed to validate card ad CTA link {j + 1}: {e}")

        print("All card ad CTA links in the card ads were validated successfully.")

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
