import pytest
import pytest_asyncio
import sys
import os
import asyncio

# Add parent directory to path for qa_tools import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import consolidated functions from qa_tools
from qa_tools import (
    clear_screenshots_directory,
    wait_for_js_and_element_async,
    browser_no_auth,
    DEFAULT_TIMEOUT,
    process_test_data_async)
from playwright.async_api import async_playwright

# Determine if running in headless mode - need extra wait time for personalization
IS_HEADLESS = os.environ.get("HEADLESS", "false").lower() in ["true", "1", "yes"]
# Extra wait time for Finalytics personalization scripts to complete in headless mode
PERSONALIZATION_WAIT = 5 if IS_HEADLESS else 2

MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries

# Test data configuration
data = [
    "https://www.stgfinalyticsdemo.com/?debug_all=1",  # Visit homepage with debug_all=1 first to establish debug session
    "https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans",
    5,  # Sleep for 5 seconds to allow page to fully load
    {
        'url': "https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire",
        'expected': {
            'h1': "Car Loan Ad 1 that uses aggressive expire",
            'h1__selector': '.col-md-8 > h1:nth-child(1)',
            'wait_type': 'element'
        }
    },
    {
        'url': "https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire?expire__aggressive=1&age__views=1&age__minutes=5",
        'expected': {
            'h1': "Banking with the Best",
            'h1__selector': '.col-md-8 > h1:nth-child(1)',
            'wait_type': 'element'
        }
    }
]


async def wait_for_finalytics_personalization(page, timeout=10000):
    """
    Wait for Finalytics personalization scripts to complete.
    Checks for window.finishedAdsReplacement flag or waits for timeout.
    """
    try:
        print("Waiting for Finalytics personalization to complete...")
        await page.wait_for_function(
            '''() => {
                // Check if Finalytics has finished replacing ads
                if (window.finishedAdsReplacement === true) return true;
                // Also check if personalization scripts have loaded
                if (window.finalyticsLoaded === true) return true;
                // Check for fin_session_data in localStorage as fallback
                try {
                    const hasSession = localStorage.getItem('fin_session_data') !== null;
                    if (hasSession && document.querySelector('.c-hero h1')) return true;
                } catch(e) {}
                return false;
            }''',
            timeout=timeout
        )
        print("Finalytics personalization completed.")
        return True
    except Exception as e:
        print(f"Finalytics personalization wait timed out (this may be normal): {e}")
        return False


async def check_hero_ad_with_retry(page, url, expected_h1, h1_selectors, screenshots_directory,
                                    screenshot_name, wait_personalization=True):
    """
    Navigate to url and assert one of h1_selectors shows expected_h1.
    Retries up to MAX_AD_RETRIES times (full reload between attempts) before raising,
    matching the reload-and-recheck pattern used for other clients' CI reliability fixes.
    """
    last_error = None

    for attempt in range(1, MAX_AD_RETRIES + 1):
        print(f"[Hero ad] Validation attempt {attempt}/{MAX_AD_RETRIES} for {url}")
        try:
            await page.goto(url)
            await page.wait_for_load_state('networkidle')

            if wait_personalization:
                await wait_for_finalytics_personalization(page, timeout=15000)

            await asyncio.sleep(PERSONALIZATION_WAIT)
            await page.screenshot(path=f'{screenshots_directory}{screenshot_name}.png')

            for selector in h1_selectors:
                try:
                    locator = page.locator(selector).first
                    await locator.wait_for(state='visible', timeout=5000)
                    actual_h1 = await locator.inner_text()
                    print(f"H1 content (using {selector}): '{actual_h1}'")

                    if expected_h1 in actual_h1 or actual_h1 in expected_h1:
                        print(f"[PASS] Found expected H1: '{actual_h1}'")
                        return actual_h1
                except Exception as e:
                    print(f"Selector {selector} failed: {str(e)[:100]}")
                    continue

            raise Exception(f"Expected H1 '{expected_h1}' not found with any selector.")
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            last_error = exc
            print(f"[Hero ad] Attempt {attempt} failed: {exc}")
            if attempt < MAX_AD_RETRIES:
                print(f"[Hero ad] Waiting {RETRY_SLEEP}s before retry...")
                await asyncio.sleep(RETRY_SLEEP)

    raise Exception(
        f"Expected H1 '{expected_h1}' not found after {MAX_AD_RETRIES} attempts. Last error: {last_error}"
    )


@pytest.mark.regression
@pytest.mark.asyncio
async def test_ad_expiration_by_aggressive_expiration_by_time(
    browser_no_auth
):
    print("Starting ad expiration testing...")
    print(sys.version)
    print(f"Running in {'HEADLESS' if IS_HEADLESS else 'HEADED'} mode")
    print(f"Personalization wait time: {PERSONALIZATION_WAIT} seconds")

    # Clear screenshots directory so timestamp of images get updated
    screenshots_directory = 'screenshots_aggressive_expiration_by_time_using_pytest/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser_no_auth.new_page()

    # Process navigation steps manually with extra wait for personalization
    # Step 1: Visit homepage with debug_all=1
    print("Step 1: Visiting homepage with debug_all=1...")
    await page.goto("https://www.stgfinalyticsdemo.com/?debug_all=1")
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}1_homepage.png')

    # Step 2: Visit auto loans page to establish session
    print("Step 2: Visiting auto loans page...")
    await page.goto("https://www.stgfinalyticsdemo.com/personal/borrow/auto-and-recreational-loans/auto-loans")
    await page.wait_for_load_state('networkidle')
    await page.screenshot(path=f'{screenshots_directory}2_auto_loans.png')

    # Step 3: Wait for session to be established
    print(f"Step 3: Waiting {5} seconds for session to be established...")
    await asyncio.sleep(5)

    # Step 4: Visit aggressive expire page - this is where personalization happens.
    # Retries up to MAX_AD_RETRIES times with a full reload between attempts (matching
    # the reliability pattern used for other clients' CI fixes), since a single-shot
    # check can't distinguish a genuinely slow personalization render from a real mismatch.
    print("Step 4: Visiting aggressive expire test page...")
    h1_selectors = ['.col-md-8 > h1:nth-child(1)', '.c-hero h1', '.col-md-8 h1']
    expected_h1 = "Car Loan Ad 1 that uses aggressive expire"

    await check_hero_ad_with_retry(
        page,
        "https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire",
        expected_h1, h1_selectors, screenshots_directory,
        "3_aggressive_expire_before",
    )

    # Step 5: Visit with expiration params - should show default content
    print("Step 5: Visiting aggressive expire page with expiration params...")
    expected_h1_after = "Banking with the Best"

    await check_hero_ad_with_retry(
        page,
        "https://www.stgfinalyticsdemo.com/qa/expire/aggressiveexpire?expire__aggressive=1&age__views=1&age__minutes=5",
        expected_h1_after, h1_selectors, screenshots_directory,
        "4_aggressive_expire_after",
    )

    print(f"Ad expiration testing completed successfully.")
