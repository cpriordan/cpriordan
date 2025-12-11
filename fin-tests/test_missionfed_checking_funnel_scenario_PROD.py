import asyncio
import pytest
import pytest_asyncio
import os
import time
import shutil
import re  # used for CTA text matching
from urllib.parse import urljoin, urlsplit, urlunsplit  # used to resolve + normalize URLs
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# IMAGE DIFF: imports for baseline-vs-screenshot comparison
from pathlib import Path  # path-safe handling
try:
    from PIL import Image, ImageChops, ImageStat  # Pillow for pixel diff
except ImportError as _e:
    Image = ImageChops = ImageStat = None  # allow file to import even if Pillow missing

# ==========================================================
# Utilities
# ==========================================================

def clear_screenshots_directory(directory):
    if os.path.exists(directory):
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


async def save_page_source(page, filepath):
    try:
        html_content = await page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")


# ==========================================================
# Console error tracker (filters noisy network warnings)
# ==========================================================

def detect_js_errors_from_specific_files(client, page, specific_files, error_tracker):
    noisy_substrings = [
        # Treat these as warnings (do NOT fail the test)
        "No response received",
        "Failed to load resource",
        "net::ERR",
        "NS_ERROR",
        "TypeError: Failed to fetch",
    ]

    async def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
        if msg.type == 'error' and file_name.endswith('.js') and file_name in specific_files:
            text = msg.text or ""
            if any(s in text for s in noisy_substrings):
                print(f"[JS warning - ignored] {file_name}: {text} for client {client}")
                return
            error_message = f"JS Error found in {file_name}: {text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)
            screenshot_path = os.path.join(os.getcwd(), f"js_error_{client}.png")
            try:
                await page.screenshot(path=screenshot_path)
                print(f"Screenshot of JS error saved at {screenshot_path}")
            except Exception:
                pass

    page.on('console', lambda msg: asyncio.ensure_future(handle_console_message(msg)))


# ==========================================================
# Playwright fixtures
# ==========================================================

@pytest_asyncio.fixture
async def browser(request):
    username = request.param.get("username")
    password = request.param.get("password")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, args=["--remote-debugging-port=9222"])  # unchanged
        context = await browser.new_context(http_credentials={"username": username, "password": password})
        context.set_default_timeout(60000)
        # REMOVE NO CACHING SINCE ADS WON'T GET DISPLAYED
        # Keep a softer cache strategy to avoid local cache stickiness (URLs left untouched)
        # await context.set_extra_http_headers({
        #     "Cache-Control": "no-cache",
        #     "Pragma": "no-cache"
        # })
        yield context
        await browser.close()


# ==========================================================
# Robust wait helpers
# ==========================================================

async def wait_for_document_complete(page, timeout=60000):
    print("Waiting for the document to be fully loaded...")
    await page.wait_for_load_state('domcontentloaded', timeout=timeout)
    await page.wait_for_load_state('load', timeout=timeout)
    await page.evaluate('''new Promise(resolve => {
        if (document.readyState === 'complete') resolve();
        else window.addEventListener('load', () => resolve(), { once: true });
    })''')


# ==========================================================
# Helper: find product menu across frames + selector variants
# ==========================================================

async def find_product_menu_across_frames(page, selector_candidates, timeout_ms=30000):
    """Locate the product pulldown menu, searching all frames and multiple selectors.

    Returns (frame, locator) so that subsequent locators for options/checkboxes
    are resolved in the same frame as the <mat-select>.
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    last_error = None

    # Clean up selectors (strip empties / Nones)
    selector_candidates = [s.strip() for s in selector_candidates if s]

    while time.time() < deadline:
        try:
            for frame in page.frames:
                for sel in selector_candidates:
                    try:
                        loc = frame.locator(sel)
                        if await loc.count() > 0:
                            try:
                                await loc.first.wait_for(state="visible", timeout=2000)
                                print(f"Found product menu using selector '{sel}' in frame URL: {frame.url}")
                                return frame, loc.first
                            except Exception as e:
                                last_error = e
                                continue
                    except Exception as e:
                        last_error = e
                        continue
        except Exception as e:
            last_error = e

        await asyncio.sleep(0.5)

    raise PlaywrightTimeoutError(
        f"Timed out after {timeout_ms}ms waiting for product menu to be visible. "
        f"Selectors tried: {selector_candidates}. Last error: {last_error}"
    )


# === CTA helpers ===

# CHANGE CTA FOR CHECKING
CTA_REGEX = re.compile(r"FINISH\s*OPENING\s*MY\s*ACCOUNT", re.I)


def cta_locator(page):
    return page.locator(":is(a,button,[role='link'],[role='button'])", has_text=CTA_REGEX).first


async def wait_for_cta_visible(page, timeout_ms=12000):
    deadline = time.time() + (timeout_ms / 1000.0)
    loc = cta_locator(page)
    while time.time() < deadline:
        try:
            if await loc.count() > 0 and await loc.is_visible():
                return True
        except Exception:
            pass
        await asyncio.sleep(0.25)
    return False


# wait for CTA to be CLICKABLE (visible + enabled + attached + has size)
async def wait_for_cta_clickable(page, timeout_ms=12000):
    loc = cta_locator(page)
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        try:
            if await loc.count() == 0:
                await asyncio.sleep(0.2)
                continue
            if await loc.is_visible():
                if await loc.is_enabled():
                    try:
                        await loc.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    box = await loc.bounding_box()
                    if box and box.get('width', 0) > 2 and box.get('height', 0) > 2:
                        return True
        except Exception:
            pass
        await asyncio.sleep(0.2)
    return False


# robust click for the CTA that mirrors the Apply-Now flow
async def click_cta_when_clickable(page, screenshots_directory):
    """Wait for the CTA to be clickable, then click it.
    If a new tab opens, capture its URL, close it, and navigate the ORIGINAL tab to that URL.
    If no new tab opens, honor same-tab navigation.
    Returns the resolved destination URL.
    """
    loc = cta_locator(page)

    clickable = await wait_for_cta_clickable(page, timeout_ms=12000)
    if not clickable:
        raise PlaywrightTimeoutError("CTA visible but not clickable within timeout.")

    dest_href = None
    try:
        dest_href = await loc.get_attribute("href")
        if not dest_href:
            inner_anchor = loc.locator("a[href]").first
            if await inner_anchor.count() > 0:
                dest_href = await inner_anchor.get_attribute("href")
        if dest_href:
            dest_href = urljoin(page.url, dest_href)
    except Exception:
        pass

    context = page.context
    prev_url = page.url

    new_tab = None
    try:
        async with context.expect_page(timeout=6000) as page_info:
            await loc.click(force=False)
        new_tab = await page_info.value
        try:
            await new_tab.wait_for_load_state('domcontentloaded')
            await new_tab.wait_for_load_state('load')
            await try_click_cookie_accept(new_tab, screenshots_directory)
            await new_tab.screenshot(path=f"{screenshots_directory}/cta_new_tab.png")
        except Exception:
            pass
    except PlaywrightTimeoutError:
        try:
            await page.wait_for_load_state('load', timeout=6000)
        except Exception:
            pass

    if not dest_href:
        if new_tab is not None:
            try:
                dest_href = new_tab.url
            except Exception:
                pass
        elif page.url != prev_url:
            dest_href = page.url

    if not dest_href:
        try:
            dest_href = await loc.get_attribute("href")
            if dest_href:
                dest_href = urljoin(page.url, dest_href)
        except Exception:
            pass

    if new_tab is not None:
        try:
            await new_tab.close()
        except Exception:
            pass

    if not dest_href:
        raise PlaywrightTimeoutError("Could not determine destination URL after clicking CTA.")

    if page.url != dest_href:
        await page.goto(dest_href, timeout=60000)
    await wait_for_document_complete(page, timeout=60000)
    await page.screenshot(path=f"{screenshots_directory}/8_cta_destination.png")

    return dest_href


# ==========================================================
# Cookie banner handling
# ==========================================================

COOKIE_ACCEPT_SELECTORS = [
    'a.cc-btn.cc-dismiss',
]

COOKIE_BANNER_CONTAINERS = [
    '.cc-window',
]


async def try_click_cookie_accept(page, screenshots_directory):
    for sel in COOKIE_ACCEPT_SELECTORS:
        locator = page.locator(sel)
        try:
            if await locator.count() > 0:
                await locator.first.wait_for(state="visible", timeout=2000)
                try:
                    await locator.first.click()
                    print(f"Clicked cookie accept button via selector: {sel}")
                except Exception:
                    handle = await locator.first.element_handle()
                    if handle:
                        await page.evaluate('(el)=>el.click()', handle)
                        print(f"Clicked cookie accept via JS: {sel}")
                await asyncio.sleep(0.5)
        except Exception:
            continue

    banner_still_present = False
    for cont in COOKIE_BANNER_CONTAINERS:
        try:
            count = await page.locator(cont).count()
            if count > 0:
                for i in range(count):
                    if await page.locator(cont).nth(i).is_visible():
                        banner_still_present = True
                        print(f"Cookie banner container still visible: {cont}")
                        break
        except Exception:
            pass

    if banner_still_present:
        try:
            await page.screenshot(path=f'{screenshots_directory}/9_cookie_layer_might_be_still_blocking.png')
        except Exception:
            pass
        css_rules = ','.join(COOKIE_BANNER_CONTAINERS) + '{ display:none !important; visibility:hidden !important; }'
        await page.add_style_tag(content=css_rules)
        print("Injected CSS to hide persistent cookie banner in test context.")
        await asyncio.sleep(0.25)
    return True


# ==========================================================
# Hero image helpers — target the exact selector you requested
# ==========================================================

def _normalize_url(u: str) -> str:
    if not u:
        return u
    if u.startswith('//'):
        u = 'https:' + u
    parts = urlsplit(u)
    parts = parts._replace(query='', fragment='')
    return urlunsplit(parts)


async def get_hero_background_img_url(page) -> str:
    """Return the hero background image URL.

    MissionFed updated the hero markup so the primary <img> is now
    `.hero__background > img:nth-child(1)`. We try this first, but
    also keep the older selector as a fallback in case markup changes
    again or on other pages.
    """
    selectors = [
        ".hero__background > img:nth-child(1)",                 # new primary selector
        "#main .hero__background > img:nth-child(1)",           # slightly more specific
        "#main > div.hero > div.hero__background > img",        # legacy selector
    ]

    for sel in selectors:
        img = page.locator(sel).first
        try:
            await img.wait_for(state="visible", timeout=6000)
        except Exception:
            # If this selector doesn't resolve to a visible <img>, try the next one
            continue

        srcset = await img.get_attribute('srcset')
        if srcset:
            first = srcset.split(',')[0].strip().split(' ')[0]
            if first:
                return urljoin(page.url, first)

        src = await img.get_attribute('src')
        if src:
            return urljoin(page.url, src)

    # If none of the selectors produced a visible <img> with src/srcset
    return None
    srcset = await img.get_attribute('srcset')
    if srcset:
        first = srcset.split(',')[0].strip().split(' ')[0]
        if first:
            return urljoin(page.url, first)
    src = await img.get_attribute('src')
    if src:
        return urljoin(page.url, src)
    return None


EXPECTED_HERO_IMAGE_URL = "https://www.missionfed.com/wp-content/uploads/checking_1600x535_071125@2x.jpg"


# ==========================================================
# Click "Apply Today" helper
# ==========================================================

async def follow_apply_today_in_original_tab(page, screenshots_directory):
    """1) Locate and click the visible "Apply Today" control.
    2) Capture its href (if any) for canonical apply URL.
    3) If a new tab opens, close it immediately.
    4) Navigate the ORIGINAL tab to the apply URL.
    5) Return the resolved apply URL actually used.
    """
    candidates = [
        page.get_by_role('link', name=re.compile(r'Apply Today', re.I)),
        page.get_by_role('button', name=re.compile(r'Apply Today', re.I)),
        page.locator("a:has-text('Apply Today')"),
        page.locator("[role='link']:has-text('Apply Today')"),
    ]
    target = None
    for cand in candidates:
        if await cand.count() > 0:
            target = cand.first
            break
    if not target:
        raise PlaywrightTimeoutError("Could not locate an 'Apply Today' control on the page.")

    apply_href = None
    try:
        apply_href = await target.get_attribute("href")
        if not apply_href:
            inner_anchor = target.locator("a[href]").first
            if await inner_anchor.count() > 0:
                apply_href = await inner_anchor.get_attribute("href")
        if apply_href:
            apply_href = urljoin(page.url, apply_href)
    except Exception:
        pass

    context = page.context
    prev_url = page.url

    new_tab = None
    try:
        async with context.expect_page(timeout=7000) as page_info:
            await target.click()
        new_tab = await page_info.value
        try:
            await new_tab.wait_for_load_state('domcontentloaded')
            await new_tab.wait_for_load_state('load')
            await try_click_cookie_accept(new_tab, screenshots_directory)
            await new_tab.screenshot(path=f"{screenshots_directory}/3_after_click_apply_today_new_tab_opened.png")
        except Exception:
            pass
        try:
            await new_tab.close()
        except Exception:
            pass
    except PlaywrightTimeoutError:
        pass

    if not apply_href:
        if page.url != prev_url:
            apply_href = page.url
        elif new_tab is not None:
            try:
                apply_href = new_tab.url
            except Exception:
                pass

    if not apply_href:
        raise PlaywrightTimeoutError("Could not determine the Apply URL from the 'Apply Today' control.")

    if page.url != apply_href:
        await page.goto(apply_href, timeout=60000)
    await wait_for_document_complete(page, timeout=60000)
    await page.screenshot(path=f"{screenshots_directory}/3b_apply_today_destination_in_original_tab.png")

    return apply_href


# ==========================================================
# IMAGE DIFF helper
# ==========================================================


def _ensure_pillow_available():
    if Image is None or ImageChops is None or ImageStat is None:
        raise RuntimeError(
            "Pillow (PIL) is required for baseline image comparison. Install with: pip install pillow"
        )


def compare_images(baseline_path: Path, actual_path: Path, diff_out_path: Path, rms_tolerance: float = 0.0) -> float:
    """Return RMS difference between images. Save a diff image. Raise if dimensions differ.
    rms_tolerance=0 requires exact pixel match.
    """
    _ensure_pillow_available()
    with Image.open(baseline_path).convert('RGBA') as b, Image.open(actual_path).convert('RGBA') as a:
        if b.size != a.size:
            raise AssertionError(f"Image sizes differ. Baseline {b.size} vs Actual {a.size}")
        diff = ImageChops.difference(b, a)
        diff_out_path.parent.mkdir(parents=True, exist_ok=True)
        amplified = ImageChops.multiply(diff, Image.new('RGBA', diff.size, (255, 255, 255, 255)))
        amplified.save(diff_out_path)
        stat = ImageStat.Stat(diff)
        sq = sum((c ** 2 for c in stat.rms))
        rms = (sq / len(stat.rms)) ** 0.5
        return rms


# ==========================================================
# Test
# ==========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "", "password": ""}],
    indirect=True,
)
async def test_missionfeb_checking_funnel_ad_PROD(
    browser,
    homepage_url_with_session_init="https://www.missionfed.com/?session_init=1&debug_all=1&cb=0",
    homepage_url="https://www.missionfed.com/?debug_all=1&cb=0",
    scenario_dir="checking",
    # UPDATED selector to mat-mdc variant; we still try legacy + simpler ones in the helper
    product_pulldown_menu_selector="#mat-select-0 > div > div.mat-mdc-select-arrow-wrapper > div",
    easy_checking_account_checkbox_selector="#mat-option-1 > span",
    test_scenario_url="https://www.missionfed.com/checking-spending/",
    expected_ad_heading="DRIVE AWAY WITH BETTER RATES.",
    hero_heading_selector="#main > div.hero > div.hero__content > div > div > div",
    expected_ad_title="Your Next Car, No Guesswork.",
    hero_title_selector="#main > div.hero > div.hero__content > div > div > h1",
    client="missionfed",
):
    print(f"Starting {client} hero ad test..")

    # Ensure base screenshots dir + scenario subdir exist and use them
    base_dir = 'screenshots_' + client + '_using_pytest'
    screenshots_directory = os.path.join(base_dir, scenario_dir)  # e.g., screenshots_missionfed_using_pytest/checking
    os.makedirs(screenshots_directory, exist_ok=True)

    # Optional: clear any previous contents in that scenario directory
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

    try:
        # 1) Land on homepage WITH session init (original tab)
        print(f"Going to homepage_url with session init {homepage_url_with_session_init}...")
        await page.goto(homepage_url_with_session_init, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=f'{screenshots_directory}/1_homepage_session_init.png')

        # 2) Go to Product page (original tab)
        print(f"Going to test_scenario_url {test_scenario_url}...")
        await page.goto(test_scenario_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=f'{screenshots_directory}/2_checking_account_page.png')

        # 3) CLICK the APPLY TODAY control -> copy href -> close NEW TAB -> navigate ORIGINAL TAB to apply URL
        print("Clicking 'Apply Today', copying href, closing the new tab, and using the ORIGINAL tab to visit Apply URL…")
        apply_url = await follow_apply_today_in_original_tab(page, screenshots_directory)
        await page.wait_for_timeout(2500)  # brief dwell so analytics/personalization records the visit

        # After clicking Apply Today -> open product menu -> select Easy Checking
        try:
            print("Waiting for the 'Apply Today' form to be fully loaded (product menu visible)…")

            # Try multiple selector variants across all frames (top + iframes)
            selector_candidates = [
                product_pulldown_menu_selector,
                "#mat-select-0 > div > div.mat-mdc-select-arrow-wrapper > div > svg > path",  # as seen in DevTools
                "#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",       # legacy Angular variant
                "#mat-select-0",  # fallback: whole mat-select root
            ]

            frame, product_menu = await find_product_menu_across_frames(
                page,
                selector_candidates=selector_candidates,
                timeout_ms=35000,
            )

            try:
                await product_menu.scroll_into_view_if_needed()
            except Exception:
                pass

            await product_menu.click()
            await page.screenshot(path=f"{screenshots_directory}/apply_form_product_menu_open.png")

            # All further locators must be resolved in the SAME FRAME as the product menu
            option_locator = frame.locator(easy_checking_account_checkbox_selector).first
            try:
                await option_locator.wait_for(state="visible", timeout=10000)
                clicked = False
                try:
                    await option_locator.click()
                    clicked = True
                except Exception:
                    clicked = False

                if not clicked:
                    role_opt = frame.get_by_role("option", name=re.compile(r"Easy Checking", re.I)).first
                    if await role_opt.count() > 0:
                        await role_opt.click()
                        clicked = True

                if not clicked:
                    by_text = frame.get_by_text(re.compile(r"Easy Checking", re.I)).first
                    if await by_text.count() > 0:
                        await by_text.click()
                        clicked = True

                if not clicked:
                    raise PlaywrightTimeoutError("Could not click/select the 'Easy Checking' option.")

            except Exception:
                await page.screenshot(path=f"{screenshots_directory}/apply_form_easy_checking_not_found.png")
                raise

            await page.screenshot(path=f"{screenshots_directory}/apply_form_easy_checking_selected.png")
            print("Selected 'Easy Checking' in the Apply Today form.")
        except Exception:
            await save_page_source(page, f"{screenshots_directory}/apply_form_debug.html")
            await page.screenshot(path=f"{screenshots_directory}/apply_form_debug.png")
            raise

        # 4) From the ORIGINAL TAB, go to the homepage WITH session_init exactly as given
        print(f"Returning to homepage with session_init from original tab: {homepage_url_with_session_init}")
        try:
            print("Referrer before navigating back (original tab):", await page.evaluate("document.referrer"))
        except Exception:
            pass

        # Go to product page AGAIN using original tab
        print(f"Going to test_scenario_url {test_scenario_url} AGAIN...")
        await page.goto(test_scenario_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=f'{screenshots_directory}/3_checking_account_page_again.png')

        # Go to homepage without session_init
        await page.goto(homepage_url, referer=apply_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=f'{screenshots_directory}/4_back_home_without_session_init_from_original_tab_after_checking_account_and_apply_now.png')

        # Go to homepage WITH session_init
        await page.goto(homepage_url_with_session_init, referer=apply_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=f'{screenshots_directory}/5_back_home_with_session_init_from_original_tab_after_checking_account_and_apply_now.png')

        # Refresh until the CTA appears (max 2 soft reloads)
        found_cta = await wait_for_cta_visible(page, timeout_ms=6000)
        reloads = 0
        while not found_cta and reloads < 2:
            reloads += 1
            print(f"Soft reload #{reloads} of homepage (original tab)…")
            await page.reload(wait_until="load", timeout=60000)
            await wait_for_document_complete(page, timeout=60000)
            await page.screenshot(path=f'{screenshots_directory}/6_home_after_reload_{reloads}_original_tab.png')
            found_cta = await wait_for_cta_visible(page, timeout_ms=6000)

        if not found_cta:
            try:
                ref = await page.evaluate("document.referrer")
                ls_keys = await page.evaluate("Object.keys(localStorage)")
                cookies = await page.context.cookies("https://www.missionfed.com")
                print("Referrer seen by page (original tab):", ref)
                print("LocalStorage keys (original tab):", ls_keys)
                print("First-party cookies on missionfed.com (original tab):", cookies)
            except Exception:
                pass
            await save_page_source(page, f"{screenshots_directory}/after_home_refreshes_no_cta_original_tab.html")
            await page.screenshot(path=f"{screenshots_directory}/10_after_home_reloads_no_cta_original_tab.png")
            raise PlaywrightTimeoutError("CTA 'Finish Opening My Account' did not appear after refreshes (including cookie injection retry path).")

        print("CTA 'Finish Opening My Account' is visible in hero.")
        cta_screenshot_path = Path(f"{screenshots_directory}/6_cta_complete_my_application_visible.png")
        await page.screenshot(path=str(cta_screenshot_path))

        # Validate hero image
        try:
            actual_img_url = await get_hero_background_img_url(page)
            print("Discovered hero background <img> URL:", actual_img_url)
            if not actual_img_url:
                await save_page_source(page, f"{screenshots_directory}/hero_img_not_found.html")
                await page.screenshot(path=f"{screenshots_directory}/11a_no_hero_img_found.png")
                raise AssertionError("Could not find hero background <img> at the expected selector.")
            norm_actual = _normalize_url(actual_img_url)
            norm_expected = _normalize_url(EXPECTED_HERO_IMAGE_URL)
            if norm_actual != norm_expected:
                await page.screenshot(path=f"{screenshots_directory}/11b_hero_img_mismatch.png")
                raise AssertionError(f"Hero image URL mismatch.Expected: {norm_expected} Actual:   {norm_actual}")
            else:
                print("Hero image URL matches expected.")
        except AssertionError as ae:
            pytest.fail(str(ae))

        # Compare CTA screenshot with baseline image
        try:
            baseline_rel = Path("baseline_images_for_comparison") / "missionfed_checking_account_funnel_ad_baseline.png"
            baseline_path = baseline_rel.resolve() if baseline_rel.exists() else baseline_rel
            diff_out = Path(screenshots_directory) / "6_cta_diff_vs_baseline_black_or_empty_means_no_difference.png"
            print(f"Comparing screenshot to baseline...\n  Baseline: {baseline_path}\n  Actual:   {cta_screenshot_path}\n  Diff out: {diff_out}")
            rms = compare_images(baseline_path, cta_screenshot_path, diff_out, rms_tolerance=0.0)
            print(f"Image RMS difference = {rms}")
            assert rms <= 0.0, (
                f"Screenshot does not match baseline. RMS={rms}. See diff: {diff_out}"
            )
            print("Baseline image comparison PASSED (exact match).")
        except Exception as img_ex:
            pytest.fail(f"Baseline image comparison failed: {img_ex}")

        # Click the CTA when clickable
        print("Waiting for CTA to be clickable and then clicking…")
        cta_dest = await click_cta_when_clickable(page, screenshots_directory)
        print("CTA click resolved destination:", cta_dest)

        # Final proof
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f'{screenshots_directory}/7_final_checking_account_funnel_after_cta_click.png')

    except PlaywrightTimeoutError as e:
        try:
            await save_page_source(page, f'{screenshots_directory}/failure_source.html')
            await page.screenshot(path=f'{screenshots_directory}/failure_screenshot.png')
        except Exception:
            pass
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
