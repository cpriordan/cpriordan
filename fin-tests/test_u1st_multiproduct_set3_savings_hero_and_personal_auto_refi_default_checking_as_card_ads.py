import asyncio
import pytest
import pytest_asyncio
import os
import time
import shutil
from itertools import islice
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext

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

def scroll_until_visible(page, selector):
    # Wait until the selector is visible
    page.locator(selector).scroll_into_view_if_needed()
    print(f"Scrolled to element: {selector}")

# Fixture to set up Playwright and launch the browser

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "user1", "password": "pass1"}],
    indirect=True  # Treat the parameter as input for the 'browser' fixture
)
@pytest.mark.parametrize("product_urls", [
    {
        # FIRST SET OF MULTIPRUDCT
        # "checking_account": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/checking-accounts",
        # "credit_card": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/credit-cards",
        # "car_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/auto-loans",
        # "personal_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/personal-loans-and-lines",
        # SECOND SET OF MULTIPRUDCT
        # "mortgage_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/mortgage-loans",
        # "cd_loan": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/certificate-accounts",
        # "membership": "https://1stunitedcu.cms.banno-staging.com/more-for-you/about-us/join",
        # "auto_refi": "https://1stunitedcu.cms.banno-staging.com/search?q=auto+refinancing",
        # THIRD SET OF MULTIPRUDCT
        "auto_refi": "https://1stunitedcu.cms.banno-staging.com/search?q=auto+refinancing&api=stg",
        "personal_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/personal-loans-and-lines?api=stg",
        "savings_account": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/savings-accounts?api=stg",
        "mma_account": "https://1stunitedcu.cms.banno-staging.com/money-market-rates?api=stg",
    }
])
async def test_u1st_multiproducts_and_js_errors(
        browser,
        product_urls,
        homepage_url="https://1stunitedcu.cms.banno-staging.com/?api=stg", #USE STG DATA
        homepage_url_stg_no_api_param="https://1stunitedcu.cms.banno-staging.com",
        hero_expected_heading="High Yield Savings - Tiered Rates as High as 3.50% APY",
        hero_heading_selector="#slideshow--main > div > div > div > div > div > div > div.hero__slider-content.d-flex.flex-row.align-content-center.justify-start.align-items-center > div > div > div > div > div > div > div > h2",
        hero_cta_selector='a.btn.btn-primary.external[href="/summer"]',
        hero_CTA_button_selector = "a.btn.btn-primary.external:has-text('View Savings Accounts')",
        apply_today_card_cta_link_selector = "a:has-text('Apply Today.')",
        client="u1st"
):
    print(f"Starting {client} hero ad test..")

    # SCREENSHOT DIRECTORY IS DIFFERENT FOR EACH SET
    screenshots_directory = 'screenshots_' + client + '_using_pytest/multiproduct_set3/'
    clear_screenshots_directory(screenshots_directory)
    print(f"Cleared screenshot direction{screenshots_directory} so get new screenshots and timestamps for images")

    # Define selectors and expected h2 headings for the card ads
    card_ad_selectors = [
        "#main > div.container-fluid > div > div > div > div:nth-child(1) > div.icon-subad-text > div > div > h2",
        "#main > div.container-fluid > div > div > div > div:nth-child(2) > div.icon-subad-text > div > div > h2",
        "#main > div.container-fluid > div > div > div > div:nth-child(3) > div.icon-subad-text > div > div > h2"
    ]

    # EXPECTED HEADINGS ARE DIFFERENT FOR EACH SET
    expected_h2_headings = [
        "Big Dreams, Small Payments",  # Replace with actual expected heading for card 1
        "Shift into Savings",  # Replace with actual expected heading for card 2
        "Checking Your Way"   # Replace with actual expected heading for card 3
    ]

    # Define the card CTA link selectors and expected links
    card_ads_CTA_link_selectors = [
        "#main > div.container-fluid > div > div > div > div:nth-child(1) > div.icon-subad-text > div > div > div > a",
        "#main > div.container-fluid > div > div > div > div:nth-child(2) > div.icon-subad-text > div > div > div > a",
        "#main > div.container-fluid > div > div > div > div:nth-child(3) > div.icon-subad-text > div > div > div > a",
    ]

    # EXPECTED CTA links ARE DIFFERENT FOR EACH SET
    expected_card_ads_CTA_links = [
        "/loans-and-credit/product/personal-loans-and-lines",  # Replace with actual expected CTA link for card 1
        "/cruise",  # Replace with actual expected heading for card 2
        "/checking-and-savings/product/checking-accounts"   # Replace with actual expected heading for card 3
    ]

    page = await browser.new_page()

    specific_js_files = get_common_js_files()
    error_tracker = []
    await detect_js_errors_from_specific_files_async(client, page, specific_js_files, error_tracker, screenshots_directory)
    # Initialize the screenshot index
    screenshot_index = 0

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await page.goto(homepage_url, timeout=90000)
        # await page.wait_for_load_state('networkidle', timeout=90000)
        await page.wait_for_load_state('load', timeout=90000)
        screenshot_index += 1  # Increment the screenshot index
        await page.screenshot(path=f'{screenshots_directory}{screenshot_index}_homepage_screenshot.png')

        # Loop through the product URLs and take screenshots
        print(f"About to visit the first 4 product URLs for multiproduct setup of the hero and 3 cards...")
        for product_name, product_url in islice(product_urls.items(), 4):  # Limit to first 4 items
            if not isinstance(product_url, str):
                pytest.fail(f"Unsupported value in 'product_urls': {product_name} -> {product_url}")
            print(f"Visiting product URL: {product_name} - {product_url}")
            await page.goto(product_url, timeout=90000)
            await page.wait_for_load_state('networkidle', timeout=90000)
            # Increment the screenshot index
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, f"{screenshot_index}_{product_name}_screenshot.png")
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await page.goto(homepage_url, timeout=90000)
        await page.wait_for_load_state('networkidle', timeout=90000)

        print(f"Waiting for {hero_heading_selector} on the homepage...")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(
            path=f'{screenshots_directory}{screenshot_index}_homepage_before_heading_selector_screenshot.png')
        await wait_for_js_and_element_async(page, hero_heading_selector, timeout=90000)

        # Strip any white space in the heading
        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert hero_expected_heading == ad_on_hero_content_h1_normalized, (
            f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{hero_expected_heading}'")
        # Increment the screenshot index
        screenshot_index += 1
        await page.screenshot(
            path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_ad1_screenshot_and_accept_cookie.png',
            timeout=90000)

        print(f"---> About to check if there is an accept cookie locator")
        # Handle cookie consent if the button is visible
        cookie_button_selector = "#onetrust-accept-btn-handler"
        if await page.is_visible(cookie_button_selector):
            print("Cookie consent button detected. Clicking 'Accept'...")
            await page.click(cookie_button_selector)
            await page.wait_for_load_state('networkidle', timeout=90000)
            print("Cookie Accept consent button clicked and loading the page...")
        else:
            print("Cookie consent button not visible. Proceeding...")

        print("Sleep for a few seconds to see if page is not yet fully loaded before taking screenshot")
        time.sleep(5)

        # Screenshot after clicking the accept cookie button if visible
        screenshot_index += 1
        await page.screenshot(
            path=f'{screenshots_directory}{screenshot_index}_multiproduct_hero_after_accept_cookie.png', timeout=90000)

        # Click the Hero "CTA" button and handle the new tab
        if await page.is_visible(hero_CTA_button_selector):
            print("Clicking the 'View Savings Account' button...")
            async with page.expect_popup() as popup_info:
                await page.click(hero_CTA_button_selector)

            # Get the new tab
            new_tab = await popup_info.value
            await new_tab.wait_for_load_state("networkidle")

            # COMMENT OUT FOR NOW SO CAN TEST THE OTHER LINKS
            # Check that the page on the new tab  does not have any internal server error or any error message
            # await validate_no_server_error(new_tab)

            # Take a screenshot of the new tab
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, "new_tab_screenshot.png")
            await new_tab.screenshot(
                path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_clicked_hero_CTA_link.png',
                timeout=90000)
            print(f"Screenshot of the new tab saved at {screenshot_path}")

        else:
            pytest.fail("'View Savings Account' button was not found or visible on the page.")

        # Go back to the main page after clicking the CTA
        print(f"Go to the homepage after clicking the CTA link...")
        await page.goto(homepage_url, timeout=90000)
        await page.wait_for_load_state('networkidle', timeout=90000)

        # Screenshot after going back to the homepage
        screenshot_index += 1
        await page.screenshot(
            path=f'{screenshots_directory}{screenshot_index}_multiproduct_after_go_back_to_homepage.png',
            timeout=60000)

        # Get the h2 headings of the 3 card ads in class and compare against expected h2 heading
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
            print(f"Checking card ads CTA links {j + 1} and scrolling down if needed to make the card CTA links visible so can check the card CTA links...")
            # Scroll down until the Apply Today CTA button is visible since there was a failure adn the screenshot showed it was not visible
            scroll_until_visible(page, card_ads_CTA_link_selectors[j])
            try:
                # Check CTA links of card ads
                CTA_link_href = await page.get_attribute(link_selector, "href")
                print(f"Extracted card ad CTA link: {CTA_link_href}")
                # If the href does not contain "mortgage?", check the entire link
                if not CTA_link_href.__contains__('mortgage-rates'):
                    assert CTA_link_href == expected_card_ads_CTA_links[j], (
                        f"Mismatch for CTA link {j + 1}: Expected '{expected_card_ads_CTA_links[j]}', got '{CTA_link_href}'"
                    )
                else:
                    print(f"Skip validating exact link since uses mortgage parameters in the URL")
                # Open the card_CTA_link_full_url in a new tab and check that no error on the new tab, take screenshot and close the new tab
                card_CTA_link_full_url = homepage_url_stg_no_api_param + CTA_link_href
                new_tab = await browser.new_page()
                print(f"Opening URL in new tab: {card_CTA_link_full_url} if it is not for mortgage")
                # If the href does not contain "mortgage>", go to the page to validate
                if not CTA_link_href.__contains__('mortgage-rates'):
                    await new_tab.goto(card_CTA_link_full_url)
                    # await new_tab.wait_for_load_state("networkidle")
                    # Use loadstate instead of networkidle to avoid timeouts when loadiing fonts
                    await new_tab.wait_for_load_state("load")
                    # COMMENT OUT FOR NOW TO CHECK THAT THE SCREENSHOTS ARE TAKEN
                    # await validate_no_server_error(new_tab)
                    screenshot_index += 1
                    await new_tab.screenshot(
                        path=f'{screenshots_directory}{screenshot_index}_multiproduct_card_ad{j + 1}_CTA_link_page.png',
                        timeout=60000)
                    # Close the new tab so can find the card ads
                    await new_tab.close()
                    print("New tab closed to check the other card ad links on the homepage.")
                else:
                    print(f"Skip validating the CTA link page since uses mortgage parameters in the URL")

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
