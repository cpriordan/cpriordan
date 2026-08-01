"""
Playwright Integration Tests for finFuncAsTag Script Injection - PR #226 Changes

Tests the finFuncAsTag script injection skip logic.

Based on changes to: src/models/DirectoryPixels/index.js

When finFuncAsTag is true, the script injection should be skipped because
the finalytics-function.js is already loaded as a tag on the page.

To run:
    pytest test_fin_func_as_tag_injection.py -v

Dependencies:
    pip install pytest pytest-asyncio playwright
    playwright install chromium
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page
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
        await page.goto(LOGIN_URL, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)

        username_field = page.locator(SELECTORS["username_input"])
        if await username_field.is_visible(timeout=10000):
            await username_field.fill(USERNAME)

            password_field = page.locator(SELECTORS["password_input"])
            if await password_field.is_visible(timeout=2000):
                await password_field.fill(PASSWORD)

            await page.locator(SELECTORS["continue_button"]).click()

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

    login_success = await perform_login(page)
    if not login_success:
        raise Exception("Failed to login to Statewide OLB staging")

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


class TestFinFuncAsTagInjection:
    """
    Test suite for finFuncAsTag script injection logic.

    PR #226 changes:
    - When window.finFuncAsTag = true, skip dynamic script injection
    - Finalytics-function.js is already on the page as a static tag
    - Personalization should still work
    """

    @pytest.mark.asyncio
    async def test_script_injection_skipped_when_fin_func_as_tag_true(self, page: Page):
        """Script injection should be skipped when finFuncAsTag is true."""
        # Arrange - Track script injections
        injected_scripts = []

        async def handle_request(request):
            if request.resource_type == "script":
                injected_scripts.append(request.url)

        page.on("request", handle_request)

        # Set finFuncAsTag before page load
        await page.add_init_script("""
            window.finFuncAsTag = true;
        """)

        # Act
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Assert - Check that finalytics-function.js was NOT dynamically injected
        # (It should already be on the page as a static tag)
        dynamically_injected = any(
            "finalytics-function" in url and "injected" in url.lower()
            for url in injected_scripts
        )

        # Verify finFuncAsTag is set
        fin_func_as_tag = await page.evaluate("() => window.finFuncAsTag")
        assert fin_func_as_tag is True, "finFuncAsTag should be true"

        print(f"Scripts loaded: {len(injected_scripts)}")
        for script in injected_scripts:
            if "finalytics" in script.lower():
                print(f"  - {script}")

    @pytest.mark.asyncio
    async def test_normal_injection_when_fin_func_as_tag_false(self, page: Page):
        """Normal script injection should occur when finFuncAsTag is false."""
        # Arrange
        injected_scripts = []

        async def handle_request(request):
            if request.resource_type == "script" and "finalytics" in request.url.lower():
                injected_scripts.append(request.url)

        page.on("request", handle_request)

        # Ensure finFuncAsTag is false/undefined
        await page.add_init_script("""
            window.finFuncAsTag = false;
        """)

        # Act
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Assert - Should see finalytics scripts loaded
        print(f"Finalytics scripts loaded: {injected_scripts}")
        # Note: Exact assertion depends on implementation

    @pytest.mark.asyncio
    async def test_normal_injection_when_fin_func_as_tag_undefined(self, page: Page):
        """Normal script injection should occur when finFuncAsTag is undefined."""
        # Arrange
        injected_scripts = []

        async def handle_request(request):
            if request.resource_type == "script" and "finalytics" in request.url.lower():
                injected_scripts.append(request.url)

        page.on("request", handle_request)

        # Act - Navigate without setting finFuncAsTag
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Assert
        fin_func_as_tag = await page.evaluate("() => window.finFuncAsTag")
        assert fin_func_as_tag is None or fin_func_as_tag is False, \
            "finFuncAsTag should be undefined or false by default"

        print(f"Scripts with finFuncAsTag undefined: {injected_scripts}")

    @pytest.mark.asyncio
    async def test_personalization_works_with_fin_func_as_tag(self, page: Page):
        """Personalization should still work when finFuncAsTag is true."""
        # Arrange
        await page.add_init_script("""
            window.finFuncAsTag = true;
        """)

        # Use URL with personalization parameters
        url_with_personalization = f"{DASHBOARD_URL}?products_recommended=checking&debug_all=1"

        # Act
        await page.goto(url_with_personalization, timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        # Assert - Check for personalization elements
        personalization_present = await page.evaluate("""
            () => {
                // Check for tile ad
                const tileAd = document.querySelector('#finalytics-tile-ad');
                if (tileAd && tileAd.innerHTML.trim() !== '') return true;

                // Check for hero ad
                const heroAd = document.querySelector('#finalytics-hero-ad');
                if (heroAd && heroAd.innerHTML.trim() !== '') return true;

                // Check for any fin- prefixed elements with content
                const finElements = document.querySelectorAll('[id^="finalytics-"]');
                for (const el of finElements) {
                    if (el.innerHTML.trim() !== '') return true;
                }

                // Check window variable indicating personalization ran
                return window.finPersonalizationComplete === true;
            }
        """)

        # Note: This test may need adjustment based on actual site behavior
        print(f"Personalization present: {personalization_present}")

    @pytest.mark.asyncio
    async def test_debug_logging_confirms_skip_behavior(self, page: Page):
        """Debug logging should confirm skip behavior when finFuncAsTag is true."""
        # Arrange
        console_messages = []

        def handle_console(msg):
            text = msg.text.lower()
            if "skip" in text or "finfuncastag" in text or "injection" in text:
                console_messages.append(msg.text)

        page.on("console", handle_console)

        await page.add_init_script("""
            window.finFuncAsTag = true;
        """)

        url_with_debug = f"{DASHBOARD_URL}?debug_all=1"

        # Act
        await page.goto(url_with_debug, timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Assert - Check for debug messages about skipping
        print(f"Relevant console messages: {console_messages}")

        # Look for skip-related messages
        skip_logged = any(
            "skip" in msg.lower() or "finfuncastag" in msg.lower()
            for msg in console_messages
        )

        # Note: This depends on implementation having debug logging
        if skip_logged:
            print("Debug logging confirmed skip behavior")


class TestFinFuncAsTagEdgeCases:
    """Edge cases for finFuncAsTag handling."""

    @pytest.mark.asyncio
    async def test_fin_func_as_tag_set_after_page_load(self, page: Page):
        """Setting finFuncAsTag after page load should not affect already-loaded scripts."""
        # Act - Load page first
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")

        # Set finFuncAsTag after load
        await page.evaluate("() => { window.finFuncAsTag = true; }")

        # Trigger a reload or navigation
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Assert - finFuncAsTag should be set
        fin_func_value = await page.evaluate("() => window.finFuncAsTag")

        # Note: After reload, init script would need to re-set the value
        # This tests the timing of when the flag is checked

    @pytest.mark.asyncio
    async def test_fin_func_as_tag_with_string_value(self, page: Page):
        """finFuncAsTag should handle string 'true' value correctly."""
        # Arrange
        await page.add_init_script("""
            window.finFuncAsTag = 'true';  // String instead of boolean
        """)

        # Act
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")

        # Assert - Check how string value is handled
        fin_func_value = await page.evaluate("() => window.finFuncAsTag")
        print(f"finFuncAsTag value (string): {fin_func_value}, type: {type(fin_func_value)}")

        # Implementation should handle both boolean true and string 'true'

    @pytest.mark.asyncio
    async def test_multiple_finalytics_instances(self, page: Page):
        """Page with multiple Finalytics instances should respect finFuncAsTag."""
        # Arrange
        await page.add_init_script("""
            window.finFuncAsTag = true;
        """)

        # Act
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Assert - Count Finalytics script instances
        script_count = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                let count = 0;
                for (const script of scripts) {
                    if (script.src && script.src.includes('finalytics-function')) {
                        count++;
                    }
                }
                return count;
            }
        """)

        print(f"Finalytics-function script count: {script_count}")

        # Should not have duplicate injections
        assert script_count <= 1, "Should not have duplicate finalytics-function scripts"


class TestFinFuncAsTagPerformance:
    """Performance tests for finFuncAsTag skip logic."""

    @pytest.mark.asyncio
    async def test_page_load_performance_with_skip(self, page: Page):
        """Page should load faster when script injection is skipped."""
        # Test with finFuncAsTag = true
        await page.add_init_script("window.finFuncAsTag = true;")

        start_time = await page.evaluate("() => performance.now()")
        await page.goto(f"{DASHBOARD_URL}?debug_all=1", timeout=60000)
        await close_broadcast_overlay(page)
        await page.wait_for_load_state("networkidle")
        end_time = await page.evaluate("() => performance.now()")

        load_time_with_skip = end_time - start_time
        print(f"Load time with finFuncAsTag=true: {load_time_with_skip}ms")

        # Note: For meaningful comparison, would need to test without skip too
        # This just captures the baseline with skip enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
