# Playwright timeout hardening for u1st multiproduct flow
# Highlights: NEW/CHANGED comments mark fixes. Network-quiet nav, font blocking, safe screenshots (CDP fallback).

import asyncio
import pytest
import pytest_asyncio
import os
import time
import shutil
import base64  # NEW
from pathlib import Path
from itertools import islice
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext


# =====================
# Utils
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


async def save_page_source(page, filepath):
    try:
        html_content = await page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")


def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
    async def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)
            screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
            await safe_page_screenshot(page, screenshot_path, full_page=True)  # CHANGED
            print(f"Screenshot of JS error saved at {screenshot_path}")
    page.on('console', lambda msg: asyncio.ensure_future(handle_console_message(msg)))


async def validate_no_server_error(page):
    error_keywords = ["Server Error", "(500)", "error", "Page not found", "Not Found"]
    page_text = await page.inner_text("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    assert not found_errors, f"Error messages found on the page: {', '.join(found_errors)}"


# =====================
# Navigation + Screenshot hardening
# =====================

async def navigate_and_settle(page, url, *, ready_selector: str | None = None, dom_timeout: int = 60000, idle_ms: int = 900, max_wait: int = 15000):
    """Go to URL without relying on Playwright's fragile 'networkidle'.
    Wait for DOMContentLoaded then for a brief network idle we compute ourselves.
    """
    loop = asyncio.get_event_loop()
    in_flight = {"count": 0}
    last_change = {"t": loop.time()}

    def _bump(d):
        in_flight["count"] += d
        last_change["t"] = loop.time()

    def on_req(_): _bump(+1)
    def on_done(_): _bump(-1)

    page.on("request", on_req)
    page.on("requestfinished", on_done)
    page.on("requestfailed", on_done)

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=dom_timeout)  # CHANGED
        if ready_selector:
            try:
                await page.wait_for_selector(ready_selector, state="attached", timeout=min(15000, dom_timeout))
            except PlaywrightTimeoutError:
                print(f"navigate_and_settle: '{ready_selector}' not attached before idle; continuing.")
        start = loop.time()
        while True:
            now = loop.time()
            if in_flight["count"] <= 0 and (now - last_change["t"]) * 1000 >= idle_ms:
                print("navigate_and_settle: network quiet.")
                return
            if (now - start) * 1000 >= max_wait:
                print("navigate_and_settle: max_wait reached, continuing.")
                return
            await asyncio.sleep(0.1)
    finally:
        try:
            page.remove_listener("request", on_req)
            page.remove_listener("requestfinished", on_done)
            page.remove_listener("requestfailed", on_done)
        except Exception:
            pass


async def safe_page_screenshot(page, path: str, *, clip: dict | None = None, full_page: bool = False, timeout: int = 20000):
    """Take a screenshot but fall back to CDP capture if Playwright waits on fonts.
    Also disables animations implicitly via emulate reduced motion.
    """
    try:
        await page.emulate_media(reduced_motion='reduce')  # NEW
        await page.add_style_tag(content="*{transition:none!important;animation:none!important}")  # NEW
        await page.screenshot(path=path, full_page=full_page, clip=clip, timeout=timeout)
        return
    except PlaywrightTimeoutError as e:
        print(f"Playwright screenshot timeout, falling back to CDP: {e}")  # NEW
        client = await page.context.new_cdp_session(page)
        await client.send("Page.enable")
        # Ensure layout is up-to-date
        await client.send("DOM.enable")
        await client.send("Overlay.disable")
        params = {"fromSurface": True, "captureBeyondViewport": True, "format": "png"}
        if clip:
            # CDP clip expects: x,y,width,height,scale
            params["clip"] = {"x": float(clip["x"]), "y": float(clip["y"]), "width": float(clip["width"]), "height": float(clip["height"]), "scale": 1}
        img_b64 = (await client.send("Page.captureScreenshot", params))['data']
        with open(path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        return


async def wait_for_js_and_element(page, hero_heading_selector, timeout=40000):
    try:
        print("Waiting for the document to be fully loaded...")
        await page.evaluate('''new Promise(resolve => {
            if (document.readyState === 'complete') { resolve(); }
            else { window.addEventListener('load', resolve); }
        });''')
        print(f"Waiting for the element '{hero_heading_selector}' to become visible...")
        await page.wait_for_function(
            f'document.querySelector("{hero_heading_selector}") !== null && '
            f'document.querySelector("{hero_heading_selector}").offsetHeight > 0',
            timeout=timeout
        )
        print(f"Element '{hero_heading_selector}' is now visible.")
    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout waiting for element '{hero_heading_selector}' to become visible: {e}")


# =====================
# Browser fixture with font hardening
# =====================

@pytest_asyncio.fixture
async def browser(request) -> BrowserContext:
    username = request.param.get("username")
    password = request.param.get("password")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-remote-fonts",  # NEW
                "--hide-scrollbars",
                "--disable-extensions",
                "--disable-background-timer-throttling",
                "--no-default-browser-check",
                "--no-first-run",
            ],
        )
        context = await browser.new_context(http_credentials={"username": username, "password": password})
        context.set_default_timeout(60000)  # CHANGED: more generous default

        # Patch FontFaceSet across all frames early  # NEW
        await context.add_init_script(
            """
            (() => {
              function patch(win){
                try{
                  const FFS = win.FontFaceSet && win.FontFaceSet.prototype;
                  if(FFS){
                    try{ Object.defineProperty(FFS, 'ready', { get(){ return Promise.resolve(this); } }); }catch(e){}
                    try{ FFS.load = async function(){ return []; }; }catch(e){}
                  }
                }catch(_){ }
              }
              patch(window);
              try{
                const mo = new MutationObserver((muts)=>{
                  for(const m of muts){
                    for(const n of m.addedNodes){
                      if(n && n.tagName === 'IFRAME' && n.contentWindow){ try{ patch(n.contentWindow); }catch(e){} }
                    }
                  }
                });
                mo.observe(document, {childList:true, subtree:true});
              }catch(_){ }
            })();
            """
        )

        # Block font resource type universally (covers most cases)  # NEW
        await context.route("**/*", lambda route: route.abort() if route.request.resource_type == 'font' else route.continue_())
        # Extra: also catch common font file extensions  # NEW
        await context.route("**/*.{woff,woff2,ttf,otf}", lambda route: route.abort())

        try:
            yield context
        finally:
            await context.close()
            await browser.close()


# =====================
# The test (adapted to use hardened helpers)
# =====================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "user1", "password": "pass1"}],
    indirect=True
)
@pytest.mark.parametrize("product_urls", [
    {
        "checking_account": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/checking-accounts?api=stg",
        "credit_card": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/credit-cards?api=stg",
        "car_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/auto-loans?api=stg",
        "personal_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/personal-loans-and-lines?api=stg",
        "mortgage_loan": "https://1stunitedcu.cms.banno-staging.com/loans-and-credit/product/mortgage-loans?api=stg",
        "cd_loan": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/certificate-accounts?api=stg",
        "membership": "https://1stunitedcu.cms.banno-staging.com/more-for-you/about-us/join?api=stg",
        "auto_refi": "https://1stunitedcu.cms.banno-staging.com/search?q=auto+refinancing?api=stg",
        "savings_account": "https://1stunitedcu.cms.banno-staging.com/checking-and-savings/product/savings-accounts?api=stg",
        "mma_account": "https://1stunitedcu.cms.banno-staging.com/money-market-rates?api=stg",
    }
])
async def test_u1st_multiproducts_and_js_errors(
        browser,
        product_urls,
        homepage_url="https://1stunitedcu.cms.banno-staging.com/?api=stg",
        homepage_url_stg_no_api_param = "https://1stunitedcu.cms.banno-staging.com",
        personal_loan_expected_heading="Big Dreams, Small Payments",
        hero_heading_selector="#slideshow--main > div > div > div > div > div > div > div.hero__slider-content.d-flex.flex-row.align-content-center.justify-start.align-items-center > div > div > div > div > div > div > div > h2",
        hero_cta_selector='a.btn.btn-primary.external[href="/summer"]',
        apply_today_hero_CTA_button_selector = "a.btn.btn-primary.external:has-text('Apply Today')",
        apply_today_card_cta_link_selector = "a:has-text('Apply Today.')",
        client="u1st"
):
    print(f"Starting {client} hero ad test..")

    screenshots_directory = 'screenshots_' + client + '_using_pytest/multiproduct_set1/'
    clear_screenshots_directory(screenshots_directory)
    print(f"Cleared screenshot directory {screenshots_directory} so get new screenshots and timestamps for images or created it if it doesn't exist")

    card_ad_selectors = [
        "#main > div.container-fluid > div > div > div > div:nth-child(1) > div.icon-subad-text > div > div > h2",
        "#main > div.container-fluid > div > div > div > div:nth-child(2) > div.icon-subad-text > div > div > h2",
        "#main > div.container-fluid > div > div > div > div:nth-child(3) > div.icon-subad-text > div > div > h2"
    ]

    expected_h2_headings = [
        "Ready, Set, Drive",
        "Summer Spending Starts Here",
        "Checking Your Way"
    ]

    card_ads_CTA_link_selectors = [
        "#main > div.container-fluid > div > div > div > div:nth-child(1) > div.icon-subad-text > div > div > div > a",
        "#main > div.container-fluid > div > div > div > div:nth-child(2) > div.icon-subad-text > div > div > div > a",
        "#main > div.container-fluid > div > div > div > div:nth-child(3) > div.icon-subad-text > div > div > div > a",
    ]

    expected_card_ads_CTA_links = [
        "/loans-and-credit/product/auto-loans",
        "/summervisa",
        "/checking-and-savings/product/checking-accounts"
    ]

    page = await browser.new_page()

    # Force system fonts + reduced motion on every page (defense-in-depth)  # NEW
    await page.add_style_tag(content="*{font-family: Arial, Helvetica, sans-serif !important}")
    try:
        await page.emulate_media(reduced_motion='reduce')
    except Exception:
        pass

    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

    screenshot_index = 0

    try:
        print(f"Going to homepage_url {homepage_url}...")
        await navigate_and_settle(page, homepage_url, ready_selector="body", dom_timeout=60000, idle_ms=800, max_wait=8000)  # CHANGED
        screenshot_index += 1
        await safe_page_screenshot(page, f'{screenshots_directory}{screenshot_index}_homepage_screenshot.png', full_page=True)  # CHANGED

        print(f"About to visit the first 4 product URLs for multiproduct setup of the hero and 3 cards...")
        for product_name, product_url in islice(product_urls.items(), 4):
            if not isinstance(product_url, str):
                pytest.fail(f"Unsupported value in 'product_urls': {product_name} -> {product_url}")
            print(f"Visiting product URL: {product_name} - {product_url}")
            await navigate_and_settle(page, product_url, ready_selector="body", dom_timeout=90000, idle_ms=800, max_wait=8000)  # CHANGED
            screenshot_index += 1
            screenshot_path = os.path.join(screenshots_directory, f"{screenshot_index}_{product_name}_screenshot.png")
            await safe_page_screenshot(page, screenshot_path, full_page=True)  # CHANGED
            print(f"Screenshot saved: {screenshot_path}")

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await navigate_and_settle(page, homepage_url, ready_selector="body", dom_timeout=60000, idle_ms=800, max_wait=8000)  # CHANGED

        print(f"Waiting for {hero_heading_selector} on the homepage...")
        screenshot_index += 1
        await safe_page_screenshot(page, f'{screenshots_directory}{screenshot_index}_homepage_before_heading_selector_screenshot.png', full_page=True)  # CHANGED
        await wait_for_js_and_element(page, hero_heading_selector, timeout=60000)

        ad_on_hero_content_h1 = await page.locator(hero_heading_selector).inner_text()
        ad_on_hero_content_h1_normalized = ad_on_hero_content_h1.replace("\n", " ").strip()
        print(f"---> Heading of Ad is *** {ad_on_hero_content_h1_normalized} ***")
        assert personal_loan_expected_heading == ad_on_hero_content_h1_normalized, (
            f"Ad has heading '{ad_on_hero_content_h1_normalized}' but expected heading was '{personal_loan_expected_heading}'")

        screenshot_index += 1
        await safe_page_screenshot(page, f'{screenshots_directory}{screenshot_index}_multiproduct_hero_ad1_screenshot_and_accept_cookie.png', full_page=True)  # CHANGED

        print(f"---> About to check if there is an accept cookie locator")
        cookie_button_selector = "#onetrust-accept-btn-handler"
        if await page.is_visible(cookie_button_selector):
            print("Cookie consent button detected. Clicking 'Accept'...")
            await page.click(cookie_button_selector)
            # Replace networkidle with small settle  # CHANGED
            await page.wait_for_timeout(1200)
            print("Cookie Accept consent button clicked and loading the page...")
        else:
            print("Cookie consent button not visible. Proceeding...")

        print("Sleep briefly if page is still settling before taking screenshot")
        await page.wait_for_timeout(1500)  # CHANGED (no time.sleep)

        screenshot_index += 1
        await safe_page_screenshot(page, f'{screenshots_directory}{screenshot_index}_multiproduct_hero_after_accept_cookie.png', full_page=True)  # CHANGED

        # Click the "Apply Today" button and handle the new tab
        if await page.is_visible(apply_today_hero_CTA_button_selector):
            print("Clicking the 'Apply Today' button...")
            async with page.expect_popup() as popup_info:
                await page.click(apply_today_hero_CTA_button_selector)
            new_tab = await popup_info.value
            # Harden new tab wait  # CHANGED
            await navigate_and_settle(new_tab, new_tab.url, ready_selector="body", dom_timeout=60000, idle_ms=800, max_wait=8000)
            screenshot_index += 1
            await safe_page_screenshot(new_tab, f'{screenshots_directory}{screenshot_index}_multiproduct_after_clicked_hero_CTA_link.png', full_page=True)
            await new_tab.close()
        else:
            pytest.fail("'Apply Today' button was not found or visible on the page.")

        print(f"Go to the homepage after clicking the CTA link...")
        await navigate_and_settle(page, homepage_url, ready_selector="body", dom_timeout=60000, idle_ms=800, max_wait=8000)

        screenshot_index += 1
        await safe_page_screenshot(page, f'{screenshots_directory}{screenshot_index}_multiproduct_after_go_back_to_homepage.png', full_page=True)

        # Validate headings
        for i, selector in enumerate(card_ad_selectors):
            print(f"Checking card ads heading {i + 1}")
            try:
                h2_text = await page.inner_text(selector)
                h2_text_normalized = h2_text.strip()
                print(f"Extracted card ad h2: {h2_text_normalized}")
                assert h2_text_normalized == expected_h2_headings[i], (
                    f"Mismatch for heading {i + 1}: Expected '{expected_h2_headings[i]}', got '{h2_text_normalized}'"
                )
            except Exception as e:
                pytest.fail(f"Failed to validate heading {i + 1}: {e}")

        print("All h2 headings in the card ads were validated successfully.")

        # Validate CTA links
        for j, link_selector in enumerate(card_ads_CTA_link_selectors):
            print(f"Checking card ads CTA links {j + 1} ...")
            try:
                CTA_link_href = await page.get_attribute(link_selector, "href")
                print(f"Extracted card ad CTA link: {CTA_link_href}")
                assert CTA_link_href == expected_card_ads_CTA_links[j], (
                    f"Mismatch for CTA link {j + 1}: Expected '{expected_card_ads_CTA_links[j]}', got '{CTA_link_href}'"
                )
                card_CTA_link_full_url = homepage_url_stg_no_api_param + CTA_link_href
                new_tab = await browser.new_page()
                print(f"Opening URL in new tab: {card_CTA_link_full_url}")
                await navigate_and_settle(new_tab, card_CTA_link_full_url, ready_selector="body", dom_timeout=60000, idle_ms=800, max_wait=8000)  # CHANGED
                screenshot_index += 1
                await safe_page_screenshot(new_tab, f'{screenshots_directory}{screenshot_index}_multiproduct_card_ad{j + 1}_CTA_link_page.png', full_page=True)
                await new_tab.close()
                print("New tab closed to check the other card ad links on the homepage.")
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
