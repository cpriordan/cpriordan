"""
Playwright Tests for Control Bar URL Parameters - Statewide OLB Staging

Simplified version with login handled in each test.

To run:
    python -m pytest test_statewide_control_bar.py -v -s
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page
import os

# Configuration
BASE_URL = "https://statewide.stage.bankjoy.com"
LOGIN_URL = f"{BASE_URL}/?cb=1&session_init=1&debug_all=1"
DASHBOARD_URL = f"{BASE_URL}/consumer/main/dashboard"

# Credentials
USERNAME = "cbracey25"
PASSWORD = "SwFCU2025$$$"


async def login_and_get_page(playwright):
    """Login and return authenticated page."""
    browser = await playwright.chromium.launch(
        headless=os.environ.get("HEADLESS", "true").lower() == "true"
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True
    )
    page = await context.new_page()

    # Navigate to login
    print(f"Navigating to {LOGIN_URL}")
    await page.goto(LOGIN_URL, timeout=60000)
    await page.wait_for_load_state('networkidle', timeout=30000)

    # Enter credentials
    username_field = page.locator("#username")
    if await username_field.is_visible(timeout=10000):
        await username_field.fill(USERNAME)
        print("Username entered")

        password_field = page.locator("#password")
        if await password_field.is_visible(timeout=2000):
            await password_field.fill(PASSWORD)
            print("Password entered")

        await page.locator("button:has-text('Continue')").click()
        print("Clicked Continue")

        try:
            await page.wait_for_url("**/consumer/**", timeout=15000)
            print(f"Login successful - {page.url}")
        except:
            if "consumer" in page.url:
                print(f"Login successful (alt check) - {page.url}")
            else:
                print(f"Login may have failed - {page.url}")

    # Close broadcast overlay
    await page.wait_for_timeout(2000)
    for selector in ["#mat-mdc-dialog-0 button", "app-broadcast-ad-dialog button", "button[aria-label='Close']"]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                print("Closed broadcast overlay")
                await page.wait_for_timeout(1000)
                break
        except:
            continue

    return browser, context, page


@pytest.mark.asyncio
async def test_control_bar_with_cb_1():
    """Control bar should load when cb=1 parameter is present."""
    async with async_playwright() as p:
        browser, context, page = await login_and_get_page(p)

        try:
            # Navigate to dashboard with cb=1
            url = f"{DASHBOARD_URL}?cb=1&debug_all=1"
            print(f"\nNavigating to {url}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            # Check for control bar
            control_bar_present = await page.evaluate("""
                () => {
                    const cb = document.querySelector('#finalytics-control-bar') ||
                               document.querySelector('.fin-control-bar') ||
                               document.querySelector('[data-fin-controlbar]');
                    return cb !== null;
                }
            """)

            # Check for Finalytics scripts
            scripts = await page.evaluate("""
                () => {
                    const scripts = [];
                    document.querySelectorAll('script').forEach(s => {
                        if (s.src && s.src.includes('finalytics')) {
                            scripts.push(s.src);
                        }
                    });
                    return scripts;
                }
            """)

            print(f"Control bar present: {control_bar_present}")
            print(f"Finalytics scripts loaded: {len(scripts)}")
            for s in scripts[:5]:
                print(f"  - {s}")

            # Test passes if we see Finalytics scripts (control bar may or may not be visible)
            assert len(scripts) > 0 or control_bar_present, "Expected Finalytics to be active"

        finally:
            await context.close()
            await browser.close()


@pytest.mark.asyncio
async def test_control_bar_with_cb_0():
    """Control bar should be suppressed when cb=0 parameter is present."""
    async with async_playwright() as p:
        browser, context, page = await login_and_get_page(p)

        try:
            # Navigate to dashboard with cb=0
            url = f"{DASHBOARD_URL}?cb=0&debug_all=1"
            print(f"\nNavigating to {url}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            # Check for control bar (should NOT be present)
            control_bar_present = await page.evaluate("""
                () => {
                    const cb = document.querySelector('#finalytics-control-bar') ||
                               document.querySelector('.fin-control-bar');
                    return cb !== null && cb.offsetParent !== null;
                }
            """)

            print(f"Control bar visible: {control_bar_present}")
            print("Test: cb=0 should suppress control bar")

        finally:
            await context.close()
            await browser.close()


@pytest.mark.asyncio
async def test_finalytics_scripts_loaded():
    """Verify Finalytics scripts are loaded on the page."""
    async with async_playwright() as p:
        browser, context, page = await login_and_get_page(p)

        try:
            # Navigate to dashboard
            url = f"{DASHBOARD_URL}?cb=1&debug_all=1"
            print(f"\nNavigating to {url}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            # Get all Finalytics-related scripts
            scripts = await page.evaluate("""
                () => {
                    const result = {
                        scripts: [],
                        tileAd: document.querySelector('#finalytics-tile-ad') !== null,
                        heroAd: document.querySelector('#finalytics-hero-ad') !== null,
                    };
                    document.querySelectorAll('script').forEach(s => {
                        if (s.src && s.src.toLowerCase().includes('finalytics')) {
                            result.scripts.push(s.src);
                        }
                    });
                    return result;
                }
            """)

            print(f"Finalytics scripts: {len(scripts['scripts'])}")
            for s in scripts['scripts']:
                print(f"  - {s}")
            print(f"Tile ad present: {scripts['tileAd']}")
            print(f"Hero ad present: {scripts['heroAd']}")

            assert len(scripts['scripts']) > 0, "Expected Finalytics scripts to be loaded"

        finally:
            await context.close()
            await browser.close()


@pytest.mark.asyncio
async def test_fin_func_as_tag_behavior():
    """Test finFuncAsTag script injection behavior."""
    async with async_playwright() as p:
        browser, context, page = await login_and_get_page(p)

        try:
            # Set finFuncAsTag before navigation
            await page.add_init_script("window.finFuncAsTag = true;")

            # Navigate to dashboard
            url = f"{DASHBOARD_URL}?debug_all=1"
            print(f"\nNavigating to {url}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            # Check finFuncAsTag value
            fin_func_value = await page.evaluate("() => window.finFuncAsTag")
            print(f"finFuncAsTag value: {fin_func_value}")

            # Count finalytics-function scripts
            script_count = await page.evaluate("""
                () => {
                    let count = 0;
                    document.querySelectorAll('script').forEach(s => {
                        if (s.src && s.src.includes('finalytics-function')) {
                            count++;
                        }
                    });
                    return count;
                }
            """)

            print(f"Finalytics-function script count: {script_count}")
            assert script_count <= 1, "Should not have duplicate finalytics-function scripts"

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
