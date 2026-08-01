"""
UHFCU OLB Pre-Login Car Loan Ad CTA Test — PROD

Runs against the real production site (https://uhfcu.bankjoy.com), so this
intentionally does NOT log in and does NOT click the CTA button (clicking the
anchor element would fire any onclick/analytics-tracking handlers bound to
the click event itself) -- it only checks the pre-login Finalytics banner ad
on the sign-in page for a single product (car loan), then reads the CTA
link's href attribute and navigates directly to that URL in a separate tab
to confirm the destination loads, without generating a real ad-click event.

This mirrors fin-tests/test_uhfcu__olb_login_core_products.py (the STG,
all-products, pre-login variant) but is intentionally scoped down to one
product for prod so a routine check doesn't touch every product's ad or
require real production account credentials.

For the single product it:
1. Navigates to the sign-in URL with products_recommended=car+loan
2. Checks that the pre-login overlay/banner is present
3. Validates that the CTA link text and href exist
4. Reads the CTA href and navigates to it directly in a new tab (no click)
5. Takes screenshots of both the banner and the CTA destination page

Screenshots are saved in: uhfcu/olb/login_PROD/car_loan/
"""

import pytest
import asyncio
import os
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Test configuration -- PROD
BASE_URL = "https://uhfcu.bankjoy.com/sign-in"
PRODUCT = "car loan"
LOGIN_URL_TEMPLATE = f"{BASE_URL}?cb=1&session_init=1&debug_all=1&products_recommended={{product}}"

# CSS Selectors for the pre-login banner/overlay
SELECTORS = {
    "pre_login_overlay": "#finalytics-information-wrapper-ad",
    "pre_login_cta":     "#finalytics-information-wrapper-ad > div > div:nth-child(3) > div > a",
    # Fallback selectors if the primary ones don't match UHFCU's DOM.
    # Scoped to div[id*=...] (not a bare [id*=...] attribute selector) so this
    # can't also match unrelated elements like the site's
    # <style id="__finalytics_mobile_css__"> tag, which caused a Playwright
    # "strict mode violation" (2 elements matched) when it did.
    "pre_login_overlay_fallback": "div[id*='finalytics']",
    "pre_login_cta_fallback":     "div[id*='finalytics'] a",
}

MAX_AD_RETRIES = 3
RETRY_SLEEP    = 5  # seconds between retries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Convert product name to a valid filename."""
    return name.replace(" ", "_").replace("/", "_").lower()


def sanitize_text_for_print(text: str) -> str:
    """Remove or replace Unicode characters that can't be printed on Windows console."""
    if text is None:
        return ""
    replacements = {
        '↵': '',
        '\n': ' ',
        '\r': '',
        '\t': ' ',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('ascii', 'ignore').decode('ascii').strip()


def setup_screenshot_directory(base_dir: str = "uhfcu") -> str:
    """Create directory for the car loan login banner screenshot."""
    dir_path = f"{base_dir}/olb/login_PROD/car_loan"
    os.makedirs(dir_path, exist_ok=True)
    print(f"Created/verified directory: {dir_path}")
    return dir_path


async def set_browser_zoom(page, zoom_level: float = 0.8):
    """Set browser zoom level using CSS transform."""
    await page.evaluate(f"""
        document.body.style.transform = 'scale({zoom_level})';
        document.body.style.transformOrigin = '0 0';
        document.body.style.width = '{int(100 / zoom_level)}%';
    """)
    print(f"Browser zoom set to {int(zoom_level * 100)}%")


async def scroll_to_element(page, selector: str, timeout: int = 15000) -> bool:
    """Scroll until element is visible. Returns True if found."""
    try:
        await page.locator(selector).scroll_into_view_if_needed()
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        print(f"Element '{selector}' is visible")
        return True
    except PlaywrightTimeoutError:
        print(f"Timeout: '{selector}' not found")
        return False


async def navigate_to_cta_destination(context, href: str, page_origin: str, screenshot_path: str) -> dict:
    """
    Open the CTA's href directly in a new tab and confirm it loads --
    WITHOUT clicking the actual CTA element. Clicking the anchor would fire
    any onclick handlers / analytics click-tracking bound to the click event
    itself; navigating straight to the href visits the same destination
    without generating that ad-click event.

    If href is relative (starts with '/'), resolves it against page_origin.
    """
    result = {
        "href": href,
        "resolved_href": href,
        "valid": False,
        "status_code": None,
        "final_url": None,
        "screenshot": None,
        "error": None,
    }

    if not href or href == "#" or href.startswith("#"):
        result["error"] = "CTA href is empty or anchor-only"
        return result

    if href.startswith("/"):
        result["resolved_href"] = page_origin.rstrip("/") + href
    elif not href.startswith("http"):
        result["error"] = f"Cannot resolve href: {href}"
        return result

    resolved_href = result["resolved_href"]
    new_page = await context.new_page()
    try:
        print(f"Navigating directly to CTA href (no click): {resolved_href}")
        response = await new_page.goto(resolved_href, timeout=30000, wait_until="domcontentloaded")
        result["final_url"] = new_page.url
        if response is not None:
            result["status_code"] = response.status
            result["valid"] = response.status < 400
        else:
            # Some navigations (e.g. same-site client-side routing) return no
            # Response object even though the page loaded fine -- treat a
            # successful goto with no exception as valid in that case.
            result["valid"] = True

        await new_page.screenshot(path=screenshot_path, full_page=False)
        result["screenshot"] = screenshot_path
        print(f"CTA destination screenshot saved: {screenshot_path}")

        if result["valid"]:
            print(f"CTA destination: VALID (HTTP {result['status_code']})")
        else:
            print(f"CTA destination: INVALID (HTTP {result['status_code']})")
    except Exception as e:
        result["error"] = str(e)
        print(f"CTA destination navigation failed: {e}")
    finally:
        await new_page.close()

    return result


def get_page_origin(url: str) -> str:
    """Extract scheme + host from a full URL (e.g. 'https://example.com')."""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def find_overlay_and_cta(page) -> tuple[bool, str | None]:
    """
    Locate the pre-login overlay using primary then fallback selectors.
    Returns (overlay_found, cta_selector_used).
    """
    overlay_found = await scroll_to_element(page, SELECTORS["pre_login_overlay"])
    if overlay_found:
        return True, SELECTORS["pre_login_cta"]

    print("Primary overlay selector not found, trying fallback...")
    overlay_found = await scroll_to_element(page, SELECTORS["pre_login_overlay_fallback"], timeout=10000)
    if overlay_found:
        return True, SELECTORS["pre_login_cta_fallback"]

    return False, None


async def check_single_product(page, product: str, screenshot_dir: str, timestamp: str) -> dict:
    """
    Navigate to the product-specific login banner URL, validate the CTA,
    and capture a screenshot — without logging in.
    """
    product_filename = sanitize_filename(product)
    encoded_product = urllib.parse.quote(product)
    url = LOGIN_URL_TEMPLATE.format(product=encoded_product)

    result = {
        "product": product,
        "url": url,
        "overlay_found": False,
        "cta_text": None,
        "cta_href": None,
        "cta_href_valid": False,
        "cta_url_status": None,
        "cta_destination_screenshot": None,
        "screenshot": None,
        "error": None,
    }

    print(f"\n{'='*60}")
    print(f"TESTING (pre-login only, PROD): {product}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Refresh once (mirrors statewide behaviour — helps overlays render)
        print("Refreshing page...")
        await page.reload()
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Real production personalization can take noticeably longer to inject the ad
        # overlay than the STG/demo environment this test was modeled on -- networkidle
        # firing doesn't guarantee the ad-injection script has finished its own async
        # work yet. Give it a fixed head start before relying on the selector's timeout.
        print("Waiting for ad personalization to render...")
        await asyncio.sleep(8)

        await set_browser_zoom(page, 0.8)

        overlay_found, cta_selector = await find_overlay_and_cta(page)
        result["overlay_found"] = overlay_found

        if overlay_found:
            print(f"Overlay found. Checking CTA with selector: {cta_selector}")

            cta = page.locator(cta_selector)
            if await cta.count() > 0:
                result["cta_text"] = sanitize_text_for_print(await cta.first.inner_text())
                result["cta_href"] = await cta.first.get_attribute("href")

                print(f"CTA text : '{result['cta_text']}'")
                print(f"CTA href : {result['cta_href']}")

                page_origin = get_page_origin(page.url)
                cta_screenshot_path = f"{screenshot_dir}/{product_filename}_cta_destination_{timestamp}.png"
                nav_result = await navigate_to_cta_destination(
                    page.context, result["cta_href"], page_origin, cta_screenshot_path
                )
                result["cta_href_valid"] = nav_result["valid"]
                result["cta_url_status"] = nav_result["status_code"]
                result["cta_destination_screenshot"] = nav_result["screenshot"]

                if nav_result["resolved_href"] != result["cta_href"]:
                    print(f"CTA href (resolved): {nav_result['resolved_href']}")

                if not nav_result["valid"]:
                    err = nav_result.get("error") or f"HTTP {nav_result['status_code']}"
                    result["error"] = f"CTA destination invalid: {err}"

                if nav_result["final_url"] and nav_result["final_url"] != nav_result["resolved_href"]:
                    print(f"Redirects to: {nav_result['final_url']}")
            else:
                print("WARNING: CTA element not found inside overlay")
                result["error"] = "CTA element not found"
        else:
            print(f"WARNING: Pre-login overlay not found for '{product}'")
            result["error"] = "Overlay not found"

        suffix = "" if overlay_found else "_no_overlay"
        screenshot_path = f"{screenshot_dir}/{product_filename}{suffix}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        result["screenshot"] = screenshot_path
        print(f"Screenshot saved: {screenshot_path}")

    except Exception as e:
        error_msg = sanitize_text_for_print(str(e))
        print(f"ERROR testing '{product}': {error_msg}")
        result["error"] = error_msg
        try:
            screenshot_path = f"{screenshot_dir}/{product_filename}_error_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=False, timeout=5000)
            result["screenshot"] = screenshot_path
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Main pytest entry point — car loan only, PROD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_uhfcu_olb_car_loan_ad_cta_buttons_PROD():
    """
    Check the UHFCU Bankjoy pre-login banner ad for a single product (car loan)
    against the real production site.

    - Navigates to the car-loan sign-in URL
    - Verifies the pre-login overlay/banner is visible
    - Validates the CTA link text and href
    - Navigates directly to the CTA href in a new tab (no click) and confirms
      the destination loads
    - Captures screenshots of both the banner and the CTA destination page

    No login is performed and the CTA button itself is never clicked, since
    this runs against production and a real click would fire any analytics
    tracking bound to the click event.
    """
    print("\n" + "="*80)
    print("UHFCU OLB LOGIN BANNER - CAR LOAN ONLY (PROD, pre-login only)")
    print("="*80)

    screenshot_dir = setup_screenshot_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    headless = os.environ.get("HEADLESS", "false").lower() in ["true", "1", "yes"]

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=["--start-maximized"],
        )

        try:
            result = None
            for attempt in range(1, MAX_AD_RETRIES + 1):
                print(f"\n[Attempt {attempt}/{MAX_AD_RETRIES}]")
                # Use a brand-new browser context per attempt (fresh cookies/storage),
                # not just a page reload. Real production ad-serving can apply
                # frequency capping / de-dup based on session cookies, so retrying
                # within the same context can look like a false "ad missing" result
                # when it's really just "already shown to this session."
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                try:
                    result = await check_single_product(page, PRODUCT, screenshot_dir, timestamp)
                finally:
                    await page.close()
                    await context.close()

                if result["overlay_found"] and result["cta_href_valid"]:
                    break
                if attempt < MAX_AD_RETRIES:
                    print(f"Ad overlay/CTA not confirmed yet, waiting {RETRY_SLEEP}s before retry...")
                    await asyncio.sleep(RETRY_SLEEP)
        finally:
            await browser.close()

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    overlay_status = "FOUND" if result["overlay_found"] else "MISSING"
    cta_status = "VALID" if result["cta_href_valid"] else ("N/A" if not result["cta_href"] else "INVALID")
    http_code = str(result["cta_url_status"]) if result["cta_url_status"] else "—"
    print(f"Product            : {result['product']}")
    print(f"Overlay            : {overlay_status}")
    print(f"CTA destination    : {cta_status} (HTTP {http_code})")
    if result["error"]:
        print(f"Error              : {result['error']}")
    print(f"Banner screenshot  : {result['screenshot']}")
    print(f"CTA dest screenshot: {result['cta_destination_screenshot']}")

    assert result["overlay_found"], f"Pre-login overlay not found for '{PRODUCT}'"
    assert result["cta_href"], f"CTA href missing for '{PRODUCT}'"
    assert result["cta_href_valid"], (
        f"CTA destination invalid for '{PRODUCT}': "
        f"HTTP {result['cta_url_status']} — {result.get('error')}"
    )


if __name__ == "__main__":
    asyncio.run(test_uhfcu_olb_car_loan_ad_cta_buttons_PROD())
