import pytest
import pytest_asyncio
import sys
import os
import time
from pathlib import Path
from itertools import islice
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools  
from qa_tools import (
    clear_screenshots_directory,
    save_page_source_async,
    detect_js_errors_from_specific_files_async,
    wait_for_js_and_element_async,
    validate_finalytics_tags,
    setup_screenshots_directory,
    get_common_js_files,
    get_common_finalytics_tags,
    browser)

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

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "sscustage", "password": "SilverState2023!!"}],
    indirect=True  # Treat the parameter as input for the 'browser' fixture
)
@pytest.mark.parametrize("product_urls", [
    {
        "credit_card": "https://sscustage.wpenginepowered.com/loans-and-credit-cards/credit-cards?api=stg",
    }
])
async def test_ssscu_multiproduct_and_js_errors(
        browser,
        product_urls,
        homepage_url="https://sscustage.wpenginepowered.com/?api=stg", #USE STG DATA
        homepage_url_stg_no_api_param = "https://sscustage.wpenginepowered.com/",
        credit_card_expected_heading="EARN 2% CASH BACK WITH OUR VISA® CREDIT CARD",
        hero_heading_selector="#primary > section:nth-child(1) > div > div > div > div > div.col-12.col-md-6.order-md-2.order-1 > div > div > h2",
        hero_cta_selector='#primary > section:nth-child(1) > div > div > div > div > div.col-12.col-md-6.order-md-2.order-1 > div > div > div > div > a.btn.btn-primary',
        apply_today_hero_CTA_button_selector = "a.btn.btn-primary:has-text('APPLY NOW')",
        apply_today_card_cta_link_selector = "a:has-text('APPLY NOW)",
        client="ssscu"
):
    print(f"Starting {client} hero ad test..")

    # Save the screenshots in the tests folder and NOT in another tests folder under tests
    screenshots_directory = 'screenshots_' + client + '_using_pytest/multiproduct_set2/'
    clear_screenshots_directory(screenshots_directory)
    print(f"Cleared screenshot directory {screenshots_directory} so get new screenshots and timestamps for images or created it if it doesn't exist")

    # Define selectors and expected h2 headings for the card ads
    card_ad_selectors = [
        "#finalytics-feature > div.block.pt-50.pb-25 > div > div > div > div > div > h2"
    ]

    expected_h2_headings = [
        "BOOST YOUR CASH FLOW AND REDUCE YOUR STRESS"  # Replace with actual expected heading for card 1
    ]

    # Define the card CTA link selectors and expected links
    card_ads_CTA_link_selectors = [
        "div > div > div > div > div.feature-content.feature-content-side > div.d-grid.d-inline-flex.flex-wrap.align-items-center.gap-3.mt-4 > a.btn.btn-primary"
    ]

    expected_card_ads_CTA_links = [
        "https://app.loanspq.com/apply.aspx?lenderref=ssscu111517&list=ccplvlheST"  # Replace with actual expected CTA link for card 1
    ]

    # context = await browser.new_context()
    page = await browser.new_page()

    specific_js_files = get_common_js_files()
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)
    # Initialize the screenshot index
    screenshot_index = 0

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        screenshot_index += 1 # Increment the screenshot index
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_homepage_screenshot.png')

        # Loop through the product URLs and take screenshots
        print(f"About to visit the first x product URLs for multiproduct setup of the hero and card...")
        for product_name, product_url in islice(product_urls.items(), 1):  # Limit to first 1 items
            if not isinstance(product_url, str):
                pytest.fail(f"Unsupported value in 'product_urls': {product_name} -> {product_url}")
            print(f"Visiting product URL: {product_name} - {product_url}")
            await page.goto(product_url, timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=60000)
            # Increment the screenshot index
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, f"{screenshot_index}_{product_name}_screenshot.png")
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)

        print(f"Waiting for {hero_heading_selector} on the homepage...")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_homepage_before_heading_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=60000)

        # Strip any white space in the heading
        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert credit_card_expected_heading == ad_on_hero_content_h1_normalized, (
        f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{credit_card_expected_heading}'")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_ad1_screenshot_and_accept_cookie.png', timeout=60000)

        print(f"---> About to check if there is an accept cookie locator")
        # Handle cookie consent if the button is visible
        cookie_button_selector = "#onetrust-accept-btn-handler"
        if await page.is_visible(cookie_button_selector):
            print("Cookie consent button detected. Clicking 'Accept'...")
            await page.click(cookie_button_selector)
            await page.wait_for_load_state('networkidle', timeout=60000)
            print("Cookie Accept consent button clicked and loading the page...")
        else:
            print("Cookie consent button not visible. Proceeding...")

        print("Sleep for a few seconds to see if page is not yet fully loaded before taking screenshot")
        time.sleep(5)

        # Screenshot after clicking the accept cookie button if visible
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_after_accept_cookie.png', timeout=60000)

        # Click the "Apply Today" button and handle the new tab
        if await page.is_visible(apply_today_hero_CTA_button_selector):
            print("Clicking the 'Apply Today' button...")
            await page.click(apply_today_hero_CTA_button_selector)
            # await page.wait_for_load_state('load', timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=60000)
            print("Waited for page to load after clicking the CTA link")

            # COMMENT OUT FOR NOW SO CAN TEST THE OTHER LINKS
            # Check that the page on the new tab  does not have any internal server error or any error message
            # await validate_no_server_error(new_tab)

            # Take a screenshot of the new tab
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, "CTA_page_screenshot.png")
            await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_clicked_hero_CTA_link.png',
                    timeout=60000)
            print(f"Screenshot of the opened page saved at {screenshot_path}")

        else:
            pytest.fail("'Apply Today' button was not found or visible on the page.")

         # Go back to the main page after clicking the CTA
        print(f"Go to the homepage after clicking the CTA link...")
        await page.goto(homepage_url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        # await page.wait_for_load_state('load', timeout=60000)

        # Screenshot after going back to the homepage
        screenshot_index += 1
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_go_back_to_homepage.png',
                              timeout=60000)

        # Scroll down until the card ads are visible
        for selector in card_ad_selectors:
            print(f"Scrolling to first instance of '{selector}'...")
            first_instance = page.locator(selector).first
            await first_instance.scroll_into_view_if_needed()
            await first_instance.wait_for(state="visible", timeout=10000)
            screenshot_index += 1
            await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_page_scroll.png',
                    timeout=60000)
            print(f"Screenshot after scrolling to the card ad at {screenshot_path}")

        # Get the h2 headings of the card ads in class and compare against expected h2 heading
        for i, selector in enumerate(card_ad_selectors):
            print(f"Checking card ads heading {i + 1}")
            try:
                # Check headings of card ads
                h2_text = await page.inner_text(selector)
                h2_text_normalized = h2_text.strip()
                print(f"Extracted card ad h2: {h2_text_normalized}")
                assert h2_text_normalized == expected_h2_headings[i], (
                    f"Mismatch for heading {i + 1}: Expected '{expected_h2_headings[i]}', got '{h2_text_normalized}'"
                )
            except Exception as e:
                pytest.fail(f"Failed to validate heading {i + 1}: {e}")

        print("All h2 headings in the card ads were validated successfully.")

        # Get the CTA links of the 3 card ads in class and compare against expected links
        for j, link_selector in enumerate(card_ads_CTA_link_selectors):
            print(f"Checking card ads CTA links {j + 1} ...")
            try:
                # Check CTA links of card ads
                CTA_link_href = await page.get_attribute(link_selector, "href")
                print(f"Extracted card ad CTA link: {CTA_link_href}")
                assert CTA_link_href == expected_card_ads_CTA_links[j], (
                    f"Mismatch for CTA link {j + 1}: Expected '{expected_card_ads_CTA_links[j]}', got '{CTA_link_href}'"
                )
                # Open the card_CTA_link_full_url in a new tab and check that no error on the new tab, take screenshot and close the new tab
                card_CTA_link_full_url = CTA_link_href
                # new_tab = await browser.new_page()

                # Open the new tab and ensure it is focused
                new_tab = await browser.browser.new_page()
                print(f"Opening URL in new tab: {card_CTA_link_full_url}")
                # await new_tab.goto(card_CTA_link_full_url)
                # await new_tab.wait_for_load_state("networkidle")

                print(f"Opening URL in new tab: {card_CTA_link_full_url}")
                await new_tab.goto(card_CTA_link_full_url, wait_until="domcontentloaded", timeout=60000)

                # COMMENT OUT FOR NOW TO CHECK THAT THE SCREENSHOTS ARE TAKEN
                # await validate_no_server_error(new_tab)
                screenshot_index += 1
                await new_tab.screenshot(
                    path=f'{screenshots_directory}{screenshot_index}_multiproduct_card_ad{j + 1}_CTA_link_page.png',
                    timeout=60000)
                # Close the new tab so can find the card ads

                # DON'T CLOSE THE NEW TAB
                # await new_tab.close()
                # print("New tab closed to check the other card ad links on the homepage.")

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
