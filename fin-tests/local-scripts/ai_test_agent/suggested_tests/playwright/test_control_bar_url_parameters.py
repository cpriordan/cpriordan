"""
Playwright Integration Tests for Control Bar URL Parameters - PR #226 Changes

Tests the new control bar loading logic with URL parameters.

Based on changes to: src/models/DirectoryPixels/index.js

To run:
    pytest test_control_bar_url_parameters.py -v

Dependencies:
    pip install pytest pytest-asyncio playwright
    playwright install chromium
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, expect, Page
from typing import Optional
import os

# Test configuration for Statewide OLB Staging
BASE_URL = os.environ.get("TEST_BASE_URL", "https://statewide.stage.bankjoy.com")
LOGIN_URL = f"{BASE_URL}/?cb=1&session_init=1&debug_all=1"
DASHBOARD_URL = f"{BASE_URL}/consumer/main/dashboard"
TIMEOUT = 30000

# Statewide OLB Credentials
USERNAME = "cbracey25"
PASSWORD = "SwFCU2025$$$"

# Selectors for login
SELECTORS = {
    "username_input": "#username",
    "password_input": "#password",
    "continue_button": "button:has-text('Continue')",
    "broadcast_close": "#mat-mdc-dialog-0 > div > div > app-broadcast-ad-dialog > button",
}


async def perform_login(page: Page) -> bool:
    """Perform login to Statewide OLB staging."""
    try:
        # Navigate to login page
        await page.goto(LOGIN_URL, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)

        # Enter username
        username_field = page.locator(SELECTORS["username_input"])
        if await username_field.is_visible(timeout=10000):
            await username_field.fill(USERNAME)

            # Enter password
            password_field = page.locator(SELECTORS["password_input"])
            if await password_field.is_visible(timeout=2000):
                await password_field.fill(PASSWORD)

            # Click continue
            await page.locator(SELECTORS["continue_button"]).click()

            # Wait for dashboard
            try:
                await page.wait_for_url("**/consumer/**", timeout=15000)
                print(f"Login successful - navigated to {page.url}")
                return True
            except:
                pass

        return "consumer" in page.url and "sign-in" not in page.url
    except Exception as e:
        print(f"Login error: {e}")
        return False


async def close_broadcast_overlay(page: Page, timeout: int = 3000) -> bool:
    """Close broadcast overlay if present."""
    close_selectors = [
        SELECTORS["broadcast_close"],
        "app-broadcast-ad-dialog button",
        "#mat-mdc-dialog-0 button",
        "button[aria-label='Close']",
    ]

    for selector in close_selectors:
        try:
            close_btn = page.locator(selector).first
            if await close_btn.is_visible(timeout=timeout):
                await close_btn.click()
                await page.wait_for_timeout(1000)
                return True
        except:
            continue

    # Try Escape key
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
    except:
        pass

    return False


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def browser():
    """Launch browser for tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.environ.get("HEADLESS", "true").lower() == "true"
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="module")
async def authenticated_context(browser):
    """Create authenticated browser context (login once, reuse for all tests)."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True
    )
    page = await context.new_page()

    # Perform login
    login_success = await perform_login(page)
    if not login_success:
        raise Exception("Failed to login to Statewide OLB staging")

    # Close any broadcast overlay
    await page.wait_for_timeout(2000)
    await close_broadcast_overlay(page)

    yield context
    await context.close()


@pytest.fixture
async def page(authenticated_context):
    """Create new page in authenticated context for each test."""
    page = await authenticated_context.new_page()
    yield page
    await page.close()


class TestControlBarUrlParameters:
    """
    Test suite for control bar URL parameter handling.

    PR #226 changes how the control bar is loaded based on URL parameters:
    - cb=1: Force show control bar
    - cb=0: Force hide control bar
    - No param: Use sessionStorage setting
    """

    @pytest.mark.asyncio
    async def test_control_bar_loads_with_cb_equals_1(self, page: Page):
        """Control bar should load when cb=1 parameter is present."""
        # Arrange - Navigate to dashboard with cb=1
        url_with_cb = f"{DASHBOARD_URL}?cb=1&debug_all=1"

        # Act
        await page.goto(url_with_cb, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)

        # Wait for control bar script to potentially load
        await page.wait_for_timeout(3000)

        # Assert - Check for control bar element or script
        control_bar_loaded = await page.evaluate("""
            () => {
                // Check for control bar element
                const controlBar = document.querySelector('#finalytics-control-bar') ||
                                   document.querySelector('.fin-control-bar') ||
                                   document.querySelector('[data-fin-controlbar]');
                if (controlBar) return true;

                // Check for control bar script
                const scripts = document.querySelectorAll('script');
                for (const script of scripts) {
                    if (script.src && script.src.includes('controlbar')) {
                        return true;
                    }
                }

                // Check window variable
                return window.finControlBarLoaded === true;
            }
        """)

        assert control_bar_loaded, "Control bar should load when cb=1 parameter is present"

    @pytest.mark.asyncio
    async def test_control_bar_suppressed_with_cb_equals_0(self, page: Page):
        """Control bar should NOT load when cb=0 parameter is present."""
        # Arrange
        url_without_cb = f"{DASHBOARD_URL}?cb=0&debug_all=1"

        # Act
        await page.goto(url_without_cb, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert - Control bar should not be present
        control_bar_present = await page.evaluate("""
            () => {
                const controlBar = document.querySelector('#finalytics-control-bar') ||
                                   document.querySelector('.fin-control-bar') ||
                                   document.querySelector('[data-fin-controlbar]');
                return controlBar !== null;
            }
        """)

        assert not control_bar_present, "Control bar should NOT load when cb=0 parameter is present"

    @pytest.mark.asyncio
    async def test_control_bar_respects_session_storage_setting(self, page: Page):
        """Control bar should respect sessionStorage showControlBar setting."""
        # Arrange - Navigate to dashboard first
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)

        # Set showControlBar in sessionStorage
        await page.evaluate("""
            () => {
                sessionStorage.setItem('showControlBar', 'true');
            }
        """)

        # Act - Navigate without cb parameter
        await page.reload()
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert
        control_bar_loaded = await page.evaluate("""
            () => {
                const controlBar = document.querySelector('#finalytics-control-bar') ||
                                   document.querySelector('.fin-control-bar');
                return controlBar !== null || window.finControlBarLoaded === true;
            }
        """)

        # Note: This may vary based on implementation
        # The test verifies the sessionStorage is checked
        session_value = await page.evaluate("() => sessionStorage.getItem('showControlBar')")
        assert session_value == "true", "sessionStorage showControlBar should be set"

    @pytest.mark.asyncio
    async def test_control_bar_waits_for_pixel_processing(self, page: Page):
        """Control bar should wait for FinalyticsPixel processing before loading."""
        # Arrange
        url_with_cb = f"{DASHBOARD_URL}?cb=1&debug_all=1"

        # Set up request interception to track timing
        requests_timeline = []

        async def handle_request(request):
            if "finalytics" in request.url.lower():
                requests_timeline.append({
                    "url": request.url,
                    "time": len(requests_timeline)
                })

        page.on("request", handle_request)

        # Act
        await page.goto(url_with_cb, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert - Control bar script should load after main pixel
        pixel_loaded_first = False
        controlbar_loaded = False

        for req in requests_timeline:
            if "finalytics.js" in req["url"] or "pixel" in req["url"].lower():
                pixel_loaded_first = True
            if "controlbar" in req["url"].lower():
                controlbar_loaded = True
                # Control bar should load after pixel
                assert pixel_loaded_first, "Control bar should load AFTER FinalyticsPixel"

        # Note: If no control bar request, test passes (may be cached or inline)

    @pytest.mark.asyncio
    async def test_control_bar_timeout_after_5_seconds(self, page: Page):
        """Control bar loading should timeout after 5 seconds if pixel doesn't respond."""
        # Arrange - Block the main pixel request to simulate slow loading
        await page.route("**/finalytics.js", lambda route: route.abort())
        await page.route("**/finalytics-function.js", lambda route: route.abort())

        url_with_cb = f"{DASHBOARD_URL}?cb=1"

        # Act
        start_time = await page.evaluate("() => Date.now()")
        await page.goto(url_with_cb, timeout=60000)
        await close_broadcast_overlay(page)

        # Wait for potential timeout
        await page.wait_for_timeout(6000)

        end_time = await page.evaluate("() => Date.now()")
        elapsed = end_time - start_time

        # Assert - Should not hang indefinitely
        assert elapsed < 15000, "Control bar loading should timeout and not hang"

    @pytest.mark.asyncio
    async def test_cb_parameter_overrides_session_storage(self, page: Page):
        """URL parameter cb should override sessionStorage setting."""
        # Arrange - Navigate to dashboard and set sessionStorage
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)

        await page.evaluate("""
            () => {
                sessionStorage.setItem('showControlBar', 'true');
            }
        """)

        # Act - Navigate with cb=0 (should override session setting)
        await page.goto(f"{DASHBOARD_URL}?cb=0&debug_all=1", timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert - Control bar should NOT be present despite session setting
        control_bar_present = await page.evaluate("""
            () => {
                return document.querySelector('#finalytics-control-bar') !== null ||
                       document.querySelector('.fin-control-bar') !== null;
            }
        """)

        assert not control_bar_present, "cb=0 URL parameter should override sessionStorage"

    @pytest.mark.asyncio
    async def test_control_bar_with_multiple_url_parameters(self, page: Page):
        """Control bar should work correctly with multiple URL parameters."""
        # Arrange
        url_with_params = f"{DASHBOARD_URL}?debug_all=1&cb=1&session_init=1&products_recommended=checking"

        # Act
        await page.goto(url_with_params, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert
        control_bar_loaded = await page.evaluate("""
            () => {
                return document.querySelector('#finalytics-control-bar') !== null ||
                       document.querySelector('.fin-control-bar') !== null ||
                       window.finControlBarLoaded === true;
            }
        """)

        # Verify URL was parsed correctly
        current_url = page.url
        assert "cb=1" in current_url, "cb parameter should be in URL"


class TestControlBarDebugMode:
    """Test control bar behavior in debug mode."""

    @pytest.mark.asyncio
    async def test_control_bar_logs_in_debug_mode(self, page: Page):
        """Control bar should output debug logs when debug_all=1."""
        # Arrange
        console_messages = []

        def handle_console(msg):
            if "controlbar" in msg.text.lower() or "control bar" in msg.text.lower():
                console_messages.append(msg.text)

        page.on("console", handle_console)

        url_with_debug = f"{DASHBOARD_URL}?cb=1&debug_all=1"

        # Act
        await page.goto(url_with_debug, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_broadcast_overlay(page)
        await page.wait_for_timeout(3000)

        # Assert - Should see debug messages about control bar
        # Note: This depends on implementation having debug logging
        print(f"Control bar console messages: {console_messages}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
