import asyncio
import pytest
import pytest_asyncio
import os
import shutil
import time  # ⟵ NEW: used by polling loop
from itertools import islice
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext

# =====================
# FS helpers
# =====================

def clear_screenshots_directory(directory):
    if os.path.exists(directory):
        print(f"Directory {directory} exists so remove all files in the directory")
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
        print(f"Created directory {directory} since it doesn't exist")

# =====================
# Network quiet helper
# =====================

async def wait_for_network_quiet(page, idle_ms: int = 1200, max_wait: int = 15000):
    loop = asyncio.get_event_loop()
    in_flight = {"count": 0}
    last_change = {"t": loop.time()}

    def _bump(delta: int):
        in_flight["count"] += delta
        last_change["t"] = loop.time()

    def on_req(_):
        _bump(+1)

    def on_done(_):
        _bump(-1)

    page.on("request", on_req)
    page.on("requestfinished", on_done)
    page.on("requestfailed", on_done)

    try:
        start = loop.time()
        while True:
            now = loop.time()
            if in_flight["count"] <= 0 and (now - last_change["t"]) * 1000 >= idle_ms:
                return
            if (now - start) * 1000 >= max_wait:
                print("wait_for_network_quiet: max_wait reached, continuing.")
                return
            await asyncio.sleep(0.1)
    finally:
        try:
            page.remove_listener("request", on_req)
            page.remove_listener("requestfinished", on_done)
            page.remove_listener("requestfailed", on_done)
        except Exception:
            pass

# =====================
# Robust element wait + text extraction
# =====================

async def _wait_for_nonempty_text(loc, timeout_ms: int = 60000):  # ⟵ NEW: replaces wait_for_function arg issue
    """Polls locator until it has non-empty text or times out."""
    deadline = time.time() + (timeout_ms / 1000)
    last_err = None
    while time.time() < deadline:
        try:
            txt = (await loc.inner_text()).strip()
            if txt:
                return txt
        except Exception as e:
            last_err = e
        await asyncio.sleep(0.1)
    raise PlaywrightTimeoutError(f"Non-empty text not found within {timeout_ms}ms. Last error: {last_err}")

async def wait_for_attached_and_nonempty(page, selector: str, timeout: int = 60000):  # ⟵ CHANGED
    loc = page.locator(selector).first
    await loc.wait_for(state="attached", timeout=timeout)
    # ⟵ CHANGED: use our polling helper instead of page.wait_for_function(..., loc)
    await _wait_for_nonempty_text(loc, timeout)

async def extract_text_like(page, selector: str) -> str:
    loc = page.locator(selector).first
    try:
        direct = (await loc.inner_text()).strip()
    except Exception:
        direct = ""
    if direct:
        return direct
    for attr in ("aria-label", "title", "data-title", "data-text"):
        try:
            val = await loc.get_attribute(attr)
            if val and val.strip():
                return val.strip()
        except Exception:
            pass
    child = loc.locator("h1, h2, h3, .eyebrow, [role=heading]").first
    try:
        return (await child.inner_text()).strip()
    except Exception:
        return ""

# =====================
# PDF helper (replaces flaky PNG screenshots)
# =====================

async def save_pdf(page, path: str):  # ⟵ still used
    """Reliable PDF capture that avoids screenshot font-wait stalls."""
    try:
        await page.emulate_media(media="screen")
        await page.pdf(
            path=path,
            print_background=True,
            prefer_css_page_size=True,
        )
        print(f"[PDF] saved: {path}")
    except Exception as e:
        print(f"[PDF] capture failed for {path}: {e}")

# =====================
# Browser fixture (PDF-friendly + font-stall proof)
# =====================

# =====================
# The test (captures PDFs; fixed nonempty wait)
# =====================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "trustonestage", "password": "TruStone2024!!"}],
    indirect=True,
)
@pytest.mark.parametrize("product_urls", [
    {
        "checking_account": "https://trustonestage.wpenginepowered.com/checking-and-savings/checking-accounts/?api=stg",
    }
])
async def test_tru_multiproduct_two_card_ads_no_js_errors(
    browser,
    product_urls,
    homepage_url="https://trustonestage.wpenginepowered.com/?api=stg&session_init=1",
    checking_loan_expected_heading="CHECKING ACCOUNTS",
    hero_heading_selector="#primary > section:nth-child(1) > div > div > div.container > div > div > div > div > div.eyebrow",
    client="tru",
):
    print(f"Starting {client} hero ad test..")
    screenshots_directory = 'screenshots_' + client + '_using_pytest/multiproduct_two_cards/'
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()

    # Force system fonts and kill animations pre-render (kept)
    await page.add_style_tag(content="*{font-family: Arial, Helvetica, sans-serif !important} html,body{scroll-behavior:auto!important}")
    await page.add_style_tag(content="*{animation:none!important;transition:none!important}")

    screenshot_index = 0

    try:
        for product_name, product_url in islice(product_urls.items(), 1):
            print(f"Visiting product URL: {product_name} - {product_url}")
            await page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
            await wait_for_network_quiet(page)
            screenshot_index += 1
            await save_pdf(page, f"{screenshots_directory}{screenshot_index}_{product_name}.pdf")

        # Validate hero heading text robustly (now using polling-based wait)  ⟵ CHANGED
        await wait_for_attached_and_nonempty(page, hero_heading_selector, timeout=60000)
        raw_text = await extract_text_like(page, hero_heading_selector)
        norm = raw_text.replace("\n", " ").strip().upper()
        print(f"---> Heading of Ad is *** {norm} ***")
        assert checking_loan_expected_heading.upper() == norm, (
            f"Ad has heading '{norm}' but expected heading was '{checking_loan_expected_heading}'")

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        print("Test finished.")
