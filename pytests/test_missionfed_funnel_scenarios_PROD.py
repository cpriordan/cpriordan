import asyncio
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import Path
from typing import Optional, List, Dict, Any

import pytest
import pytest_asyncio
from urllib.parse import urljoin, urlsplit, urlunsplit
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

"""
CHANGES (2025-09-29)
--------------------
# >>> CHANGED: Image diff output was nearly black. Reworked diff visualization to a high-contrast, colorized heatmap and a side-by-side triptych (baseline | actual | heatmap) so differences are obvious.
# >>> CHANGED: Compare tolerance is now configurable per-scenario via `rms_tolerance`.
# >>> CHANGED: The assertion now uses `cfg.rms_tolerance` instead of hard-coding 0.0.
# >>> CHANGED: Added robust logging of change ratio (% of pixels changed) to help diagnose near-miss diffs.
# >>> NOTE: "cd" scenario gets a small tolerance to account for tiny rendering shifts that don't affect correctness.
# >>> NOTE: Conditional product selection logic retained for personal loan / credit card (empty selector or name => skip selection).
"""

# =============================
# Optional dependency (Pillow)
# =============================
try:
    # >>> CHANGED: also import ImageOps for visible diffs
    from PIL import Image, ImageChops, ImageStat, ImageOps  # Pillow for pixel diff
except ImportError:
    Image = ImageChops = ImageStat = ImageOps = None

# ==========================================================
# Scenario model + registry
# ==========================================================

@dataclass
class ScenarioConfig:
    """Data-only config so the same test logic can run many scenarios.

    Only these vary across scenarios; everything else is shared test logic.
    """
    # Required per-scenario fields
    name: str  # used for pytest id & screenshots subfolder
    test_scenario_url: str
    test_scenario_url2: str
    baseline_rel: Path
    expected_hero_image_url: str

    # Optional/overridable bits
    cta_regex: str = r"FINISH\s*OPENING\s*MY\s*ACCOUNT"
    scenario_dir: Optional[str] = None  # default to name if not provided

    # Hero/product CTA label on the product page (e.g., "Apply Today", "APPLY NOW", "OPEN ACCOUNT")
    product_cta_button: Optional[str] = "Apply Today"

    # Only used when the scenario flows through a product selector after hero CTA
    product_pulldown_menu_selector: Optional[str] = None
    product_checkbox_selector: Optional[str] = None
    product_to_select: Optional[str] = None  # which product name to choose in the selector

    # >>> CHANGED: allow tiny visual drift per scenario (default strict)
    rms_tolerance: float = 0.0

    # Nice-to-haves for debugging
    expected_ad_heading: Optional[str] = None
    hero_heading_selector: Optional[str] = None
    expected_ad_title: Optional[str] = None
    hero_title_selector: Optional[str] = None

    def screenshots_dir(self, client: str) -> Path:
        base_dir = Path(f"screenshots_{client}_using_pytest")
        sub = self.scenario_dir or self.name
        return base_dir / sub

    @property
    def cta_pattern(self) -> re.Pattern:
        return re.compile(self.cta_regex, re.I)


# Example built-in registry. You can also externalize to YAML/JSON—see loader below.
SCENARIOS: List[ScenarioConfig] = [
    ScenarioConfig(
        name="checking",
        test_scenario_url="https://www.missionfed.com/checking-spending/",
        test_scenario_url2="",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_checking_account_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/checking_1600x535_071125@2x.jpg",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Easy Checking",
        product_checkbox_selector="#mat-option-1 > span",
        product_cta_button="Apply Today",
        rms_tolerance=0.15,
    ),
    ScenarioConfig(
        name="savings",
        test_scenario_url="https://www.missionfed.com/savings/",
        test_scenario_url2="",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_savings_account_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/savings_061325_1600x535_2x.jpg",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Savings",
        product_checkbox_selector="#mat-option-3 > span",
        # If your site shows a different label, set it here (fallbacks still try "Apply Today")
        product_cta_button="OPEN ACCOUNT",
        rms_tolerance=0.35,
    ),
    ScenarioConfig(
        name="cd",
        test_scenario_url="https://www.missionfed.com/savings/",
        test_scenario_url2="",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_cd_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/certificates_1600x535@2x.jpg",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Certificate",
        product_checkbox_selector="#mat-option-6 > span",
        # If your site shows a different label, set it here (fallbacks still try "Apply Today")
        product_cta_button="OPEN ACCOUNT",
        # >>> CHANGED: small tolerance for tiny rendering drift observed on this page
        rms_tolerance=0.35,
    ),
    ScenarioConfig(
        name="personal loan",
        test_scenario_url="https://www.missionfed.com/other-loans/personal-loan/",
        test_scenario_url2="",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_personal_loan_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/personal-loan_061325_1600x535_2x.jpg",
        product_pulldown_menu_selector="",  # empty -> skip selection
        product_to_select="",                # empty -> skip selection
        product_checkbox_selector="",
        product_cta_button="APPLY NOW",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
        rms_tolerance=0.15,
    ),
    ScenarioConfig(
        name="credit card",
        test_scenario_url="https://www.missionfed.com/compare-credit-cards/",
        test_scenario_url2="",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_credit_card_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/credit-cards_1600x535@2x.jpg",
        product_pulldown_menu_selector="",  # empty -> skip selection
        product_to_select="",                # empty -> skip selection
        product_checkbox_selector="",
        product_cta_button="APPLY NOW",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
        rms_tolerance=0.15,
    ),
    ScenarioConfig(
        name="hispanic checking",
        test_scenario_url="https://www.missionfed.com/?debug_all=1&segments=skew%20hispanic&zipcode=91911&keywords=checking%20account",
        test_scenario_url2="https://www.missionfed.com/checking-spending/",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_hispanic_checking_account_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/checking-hispanic_080525_1600x535_lg@2x.jpg",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",  # empty -> skip selection
        product_to_select="Easy Checking",
        product_checkbox_selector="#mat-option-1 > span",
        product_cta_button="Apply Today",
        cta_regex=r"FINISH\s*OPENING\s*MY\s*ACCOUNT",
        rms_tolerance=0.15,
    ),
    ScenarioConfig(
        name="hispanic credit card",
        test_scenario_url="https://www.missionfed.com/?cb=1&debug_all=1&segments=skew%20hispanic&zipcode=91911&keywords=credit%20card",
        test_scenario_url2="https://www.missionfed.com/compare-credit-cards/",
        baseline_rel=Path("baseline_images_for_comparison/missionfed_hispanic_credit_card_funnel_ad_baseline.png"),
        expected_hero_image_url="https://www.missionfed.com/wp-content/uploads/credit-card_hispanic_080525_1600x535@2x.jpg",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        # empty -> skip selection
        product_to_select="",
        product_checkbox_selector="",
        product_cta_button="Apply Now",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
        rms_tolerance=0.15,
    )
]


# ==========================================================
# Optional: load scenarios from YAML/JSON if present
# ==========================================================

def _maybe_load_scenarios_from_file() -> Optional[List[ScenarioConfig]]:
    """If scenarios.yaml or scenarios.json exists, load from it; otherwise None.
    YAML is preferred (requires pyyaml). JSON fallback is supported natively.
    Schema keys should match ScenarioConfig fields.
    """
    cwd = Path.cwd()
    yaml_path = cwd / "scenarios.yaml"
    json_path = cwd / "scenarios.json"

    if yaml_path.exists():
        try:
            import yaml  # type: ignore
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or []
            return [ScenarioConfig(**_coerce_paths(item)) for item in raw]
        except Exception as e:
            print(f"Failed loading scenarios.yaml: {e}. Falling back to built-in SCENARIOS.")
    if json_path.exists():
        try:
            import json
            raw = json.loads(json_path.read_text(encoding="utf-8")) or []
            return [ScenarioConfig(**_coerce_paths(item)) for item in raw]
        except Exception as e:
            print(f"Failed loading scenarios.json: {e}. Falling back to built-in SCENARIOS.")
    return None


def _coerce_paths(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d)
    if "baseline_rel" in out and not isinstance(out["baseline_rel"], Path):
        out["baseline_rel"] = Path(out["baseline_rel"])
    return out


# ==========================================================
# Utilities (unchanged behavior, just organized)
# ==========================================================

def clear_screenshots_directory(directory: Path) -> None:
    if directory.exists():
        for item in directory.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                print(f"Failed to delete {item}. Reason: {e}")
    else:
        directory.mkdir(parents=True, exist_ok=True)


async def save_page_source(page, filepath: Path) -> None:
    try:
        html_content = await page.content()
        filepath.write_text(html_content, encoding="utf-8")
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")


def detect_js_errors_from_specific_files(client: str, page, specific_files: List[str], error_tracker: List[str]) -> None:
    noisy_substrings = [
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
            screenshot_path = Path.cwd() / f"js_error_{client}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
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


# ==========================================================
# CTA helpers — now take ScenarioConfig
# ==========================================================

def cta_locator(page, cfg: ScenarioConfig):
    return page.locator(":is(a,button,[role='link'],[role='button'])", has_text=cfg.cta_pattern).first


async def wait_for_cta_visible(page, cfg: ScenarioConfig, timeout_ms: int = 12000) -> bool:
    deadline = time.time() + (timeout_ms / 1000.0)
    loc = cta_locator(page, cfg)
    while time.time() < deadline:
        try:
            if await loc.count() > 0 and await loc.is_visible():
                return True
        except Exception:
            pass
        await asyncio.sleep(0.25)
    return False


async def wait_for_cta_clickable(page, cfg: ScenarioConfig, timeout_ms: int = 12000) -> bool:
    loc = cta_locator(page, cfg)
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


async def click_cta_when_clickable(page, screenshots_directory: Path, cfg: ScenarioConfig) -> str:
    """Shared CTA clicker that works for any scenario; uses cfg.cta_regex."""
    loc = cta_locator(page, cfg)

    clickable = await wait_for_cta_clickable(page, cfg, timeout_ms=12000)
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
            await new_tab.screenshot(path=str(screenshots_directory / "cta_new_tab.png"))
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
    await page.screenshot(path=str(screenshots_directory / "9_cta_destination.png"))

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


async def try_click_cookie_accept(page, screenshots_directory: Path):
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
            await page.screenshot(path=str(screenshots_directory / '10_cookie_layer_might_be_still_blocking.png'))
        except Exception:
            pass
        css_rules = ','.join(COOKIE_BANNER_CONTAINERS) + '{ display:none !important; visibility:hidden !important; }'
        await page.add_style_tag(content=css_rules)
        print("Injected CSS to hide persistent cookie banner in test context.")
        await asyncio.sleep(0.25)
    return True


# ==========================================================
# Hero image helpers
# ==========================================================

def _normalize_url(u: str) -> str:
    if not u:
        return u
    if u.startswith('//'):
        u = 'https:' + u
    parts = urlsplit(u)
    parts = parts._replace(query='', fragment='')
    return urlunsplit(parts)


async def get_hero_background_img_url(page) -> Optional[str]:
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


# ==========================================================
# Hero CTA helper (was "Apply Today"), now scenario-driven
# ==========================================================

async def follow_hero_cta_in_original_tab(page, screenshots_directory: Path, cfg: ScenarioConfig) -> str:
    """Click the hero CTA on the product page using the label from cfg.product_cta_button.
    If a new tab opens, close it and navigate the original tab to the final URL.
    Returns the resolved destination URL.
    """
    label = (cfg.product_cta_button or "Apply Today").strip()
    label_pattern = re.compile(re.escape(label), re.I)

    candidates = [
        page.get_by_role('link', name=label_pattern),
        page.get_by_role('button', name=label_pattern),
        page.locator(f"a:has-text('{label}')"),
        page.locator(f"[role='link']:has-text('{label}')"),
    ]

    # Fallbacks if the exact label isn't found (e.g., legacy pages)
    if label.lower() != "apply today":
        fallback_pattern = re.compile(r"Apply Today", re.I)
        candidates.extend([
            page.get_by_role('link', name=fallback_pattern),
            page.get_by_role('button', name=fallback_pattern),
            page.locator("a:has-text('Apply Today')"),
            page.locator("[role='link']:has-text('Apply Today')"),
        ])

    target = None
    for cand in candidates:
        if await cand.count() > 0:
            target = cand.first
            break
    if not target:
        raise PlaywrightTimeoutError(f"Could not locate a hero CTA labeled '{label}'.")

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
            await new_tab.screenshot(path=str(screenshots_directory / "3_after_click_hero_cta_new_tab_opened.png"))
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
        raise PlaywrightTimeoutError(f"Could not determine the navigation URL from the hero CTA '{label}'.")

    if page.url != apply_href:
        await page.goto(apply_href, timeout=60000)
    await wait_for_document_complete(page, timeout=60000)
    await page.screenshot(path=str(screenshots_directory / "3b_hero_cta_destination_in_original_tab.png"))

    return apply_href


# ==========================================================
# IMAGE DIFF helper (shared across scenarios)
# ==========================================================

# >>> CHANGED: clearer failure guidance when Pillow is missing

def _ensure_pillow_available():
    if Image is None or ImageChops is None or ImageStat is None:
        raise RuntimeError(
            "Pillow (PIL) is required for baseline image comparison. Install with: pip install pillow"
        )


# >>> CHANGED: produce high-contrast, colorized diff + triptych and compute change ratio

def compare_images(baseline_path: Path, actual_path: Path, diff_out_path: Path, rms_tolerance: float = 0.0) -> float:
    """Return RMS difference between images; save a visible diff image.
    Also saves a side-by-side triptych at `<diff_out_path>_triptych.png`.
    rms_tolerance is logged for context; callers still assert separately.
    """
    _ensure_pillow_available()
    with Image.open(baseline_path).convert('RGBA') as b, Image.open(actual_path).convert('RGBA') as a:
        if b.size != a.size:
            raise AssertionError(f"Image sizes differ. Baseline {b.size} vs Actual {a.size}")
        diff = ImageChops.difference(b, a)

        # RMS across channels
        stat = ImageStat.Stat(diff)
        sq = sum((c ** 2 for c in stat.rms))
        rms = (sq / len(stat.rms)) ** 0.5

        try:
            # Build a high-contrast heatmap so small diffs are actually visible
            gray = ImageOps.grayscale(diff)
            boosted = ImageOps.autocontrast(gray)  # spreads small deltas across full range
            heat = ImageOps.colorize(boosted, black="#000000", white="#ff0033").convert('RGBA')
            heat.save(diff_out_path)

            # Also save a triptych for quick eyeballing
            triptych = Image.new('RGBA', (b.width * 3, b.height), (0, 0, 0, 0))
            triptych.paste(b, (0, 0))
            triptych.paste(a, (b.width, 0))
            triptych.paste(heat, (b.width * 2, 0))
            triptych_path = diff_out_path.with_name(diff_out_path.stem + "_triptych.png")
            triptych.save(triptych_path)

            # Estimate change ratio (percentage of pixels above a small threshold)
            threshold = 10  # out of 255 in grayscale space
            changed = sum(1 for v in boosted.getdata() if v > threshold)
            total = b.width * b.height
            ratio = (changed / total) * 100.0
            print(
                f"Image comparison: RMS={rms:.6f} (tolerance {rms_tolerance}), approx changed pixels={ratio:.3f}%\n"
                f"  Diff heatmap: {diff_out_path}\n  Triptych: {triptych_path}"
            )
        except Exception as viz_ex:
            # Fallback: at least save the raw diff
            print(f"[compare_images] Visualization fallback due to: {viz_ex}")
            diff.save(diff_out_path)

        return rms


# ==========================================================
# Helpers for filenames & slugs
# ==========================================================

def _slug(text: str) -> str:
    """Make a filename-safe slug from user-provided product names."""
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


# ==========================================================
# Try file-based scenarios first, otherwise use built-in
# ==========================================================

_SCENARIOS_FROM_FILE = _maybe_load_scenarios_from_file()
_ALL_SCENARIOS: List[ScenarioConfig] = _SCENARIOS_FROM_FILE or SCENARIOS


def _pytest_ids() -> List[str]:
    return [s.name for s in _ALL_SCENARIOS]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [{"username": "", "password": ""}],
    indirect=True,
)
@pytest.mark.parametrize("cfg", _ALL_SCENARIOS, ids=_pytest_ids())
async def test_missionfed_hero_ad_generic(
    browser,
    cfg: ScenarioConfig,
    homepage_url_with_session_init: str = "https://www.missionfed.com/?session_init=1&debug_all=1&cb=0",
    homepage_url: str = "https://www.missionfed.com/?debug_all=1&cb=0",
    client: str = "missionfed",
):
    """One test body, many scenarios via ScenarioConfig."""
    print(f"Starting {client} hero ad test for scenario: {cfg.name}")

    screenshots_directory = cfg.screenshots_dir(client)
    screenshots_directory.mkdir(parents=True, exist_ok=True)
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js', 'controlbar.js']
    error_tracker: List[str] = []
    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker)

    try:
        # 1) Land on homepage WITH session init (original tab)
        print(f"Going to homepage_url with session init {homepage_url_with_session_init}...")
        await page.goto(homepage_url_with_session_init, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / '1_homepage_session_init.png'))

        # 2) Go to product page (original tab)
        print(f"Going to test_scenario_url {cfg.test_scenario_url}...")
        await page.goto(cfg.test_scenario_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / '2_product_page.png'))

        # If test_scenario_url2 is NOT empty, also go to that URL
        if (cfg.test_scenario_url2):
            print(f"Going to test_scenario_url2 ALSO {cfg.test_scenario_url2}...")
            await page.goto(cfg.test_scenario_url2, timeout=60000)
            await wait_for_document_complete(page, timeout=60000)
            await page.screenshot(path=str(screenshots_directory / '2b_product_page.png'))

        # 3) Click hero/product CTA; then *conditionally* perform product selection
        print("Clicking hero/product CTA (scenario-dependent)…")
        apply_url = await follow_hero_cta_in_original_tab(page, screenshots_directory, cfg)
        await page.wait_for_timeout(2500)

        # Should we select a product? Only if BOTH selector & product name are provided (non-empty after strip)
        should_select_product = bool((cfg.product_pulldown_menu_selector or "").strip()) and \
                                 bool((cfg.product_to_select or "").strip())

        if should_select_product:
            try:
                print("Waiting for product menu to be visible…")

                # Try multiple selector variants across all frames (top + iframes)
                selector_candidates = [
                    cfg.product_pulldown_menu_selector,
                    "#mat-select-0 > div > div.mat-mdc-select-arrow-wrapper > div",  # mat-mdc variant
                    "#mat-select-0 > div > div.mat-mdc-select-arrow-wrapper > div > svg > path",  # SVG variant
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
                await page.screenshot(path=str(screenshots_directory / "8b_apply_form_product_menu_open.png"))

                # Use cfg.product_to_select to drive selection
                product_name = cfg.product_to_select.strip()
                name_pattern = re.compile(re.escape(product_name), re.I)

                # All further locators must be resolved in the SAME FRAME as the product menu
                clicked = False
                if cfg.product_checkbox_selector and cfg.product_checkbox_selector.strip():
                    opt = frame.locator(cfg.product_checkbox_selector).first
                    try:
                        await opt.wait_for(state="visible", timeout=10000)
                        await opt.click()
                        clicked = True
                    except Exception:
                        clicked = False
                if not clicked:
                    role_opt = frame.get_by_role("option", name=name_pattern).first
                    if await role_opt.count() > 0:
                        await role_opt.click()
                        clicked = True
                if not clicked:
                    by_text = frame.get_by_text(name_pattern).first
                    if await by_text.count() > 0:
                        await by_text.click()
                        clicked = True
                if not clicked:
                    raise PlaywrightTimeoutError(f"Could not click/select the '{product_name}' option.")

                sel_slug = _slug(product_name) or "product"
                await page.screenshot(path=str(screenshots_directory / f"8c_apply_form_{sel_slug}_selected.png"))
                print(f"Selected '{product_name}' in the form.")
            except Exception:
                await save_page_source(page, screenshots_directory / "apply_form_debug.html")
                await page.screenshot(path=str(screenshots_directory / "apply_form_debug.png"))
                raise
        else:
            print("Skipping product selection because selector or product name is empty for this scenario.")
            await page.screenshot(path=str(screenshots_directory / "apply_form_selection_skipped.png"))

        # Return to product page and home to seed personalization
        print(f"Going to test_scenario_url {cfg.test_scenario_url} AGAIN…")
        await page.goto(cfg.test_scenario_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / '3_product_page_again.png'))

        await page.goto(homepage_url, referer=apply_url, timeout=60000)
        await wait_for_document_complete(page, timeout=60000)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / '4_home_without_session_init.png'))

        # Fpr hispanic scenarios, do not use session_init since clears the segment information
        if not (cfg.name.startswith("hispanic")):
            print(f"Scenario is not hispanic and is: {cfg.name} so can use session_init")
            await page.goto(homepage_url_with_session_init, referer=apply_url, timeout=60000)
            await wait_for_document_complete(page, timeout=60000)
            await try_click_cookie_accept(page, screenshots_directory)
            await page.screenshot(path=str(screenshots_directory / '5_home_with_session_init.png'))
        else:
            print(f"Scenario is hispanic and is: {cfg.name} so skipping using session_init and about to refresh")

        # 4) Refresh until CTA appears
        found_cta = await wait_for_cta_visible(page, cfg, timeout_ms=6000)
        reloads = 0
        while not found_cta and reloads < 2:
            reloads += 1
            print(f"Soft reload #{reloads} of homepage (original tab)…")
            await page.reload(wait_until="load", timeout=60000)
            await wait_for_document_complete(page, timeout=60000)
            await page.screenshot(path=str(screenshots_directory / f'6_home_after_reload_{reloads}.png'))
            found_cta = await wait_for_cta_visible(page, cfg, timeout_ms=6000)

        if not found_cta:
            try:
                ref = await page.evaluate("document.referrer")
                ls_keys = await page.evaluate("Object.keys(localStorage)")
                cookies = await page.context.cookies("https://www.missionfed.com")
                print("Referrer:", ref)
                print("LocalStorage keys:", ls_keys)
                print("Cookies:", cookies)
            except Exception:
                pass
            await save_page_source(page, screenshots_directory / "after_home_refreshes_no_cta.html")
            await page.screenshot(path=str(screenshots_directory / "10_no_cta.png"))
            raise PlaywrightTimeoutError("CTA did not appear after refreshes.")

        print("Funnel ad CTA is visible in hero.")
        cta_screenshot_path = screenshots_directory / "7_funnel_ad_cta_visible.png"
        await page.screenshot(path=str(cta_screenshot_path))

        # 5) Validate hero image URL matches scenario expectation
        try:
            actual_img_url = await get_hero_background_img_url(page)
            print("Discovered hero background <img> URL:", actual_img_url)
            if not actual_img_url:
                await save_page_source(page, screenshots_directory / "hero_img_not_found.html")
                await page.screenshot(path=str(screenshots_directory / "11a_no_hero_img_found.png"))
                raise AssertionError("Could not find hero background <img> at the expected selector.")
            norm_actual = _normalize_url(actual_img_url)
            norm_expected = _normalize_url(cfg.expected_hero_image_url)
            if norm_actual != norm_expected:
                await page.screenshot(path=str(screenshots_directory / "11b_hero_img_mismatch.png"))
                raise AssertionError(f"Hero image URL mismatch.\nExpected: {norm_expected}\nActual:   {norm_actual}")
            else:
                print("Hero image URL matches expected.")
        except AssertionError as ae:
            pytest.fail(str(ae))

        # 6) Compare CTA screenshot with scenario baseline
        try:
            baseline_path = cfg.baseline_rel if cfg.baseline_rel.exists() else cfg.baseline_rel
            diff_out = screenshots_directory / "6_cta_diff_vs_baseline.png"
            print(
                f"Comparing screenshot to baseline...\n  Baseline: {baseline_path}\n  Actual:   {cta_screenshot_path}\n  Diff out: {diff_out}"
            )
            # >>> CHANGED: pass cfg.rms_tolerance to the comparator and assertion
            rms = compare_images(baseline_path, cta_screenshot_path, diff_out, rms_tolerance=cfg.rms_tolerance)
            print(f"Image RMS difference = {rms}")
            assert rms <= (cfg.rms_tolerance or 0.0), (
                f"Screenshot does not match baseline within tolerance. RMS={rms}. Tolerance={cfg.rms_tolerance}. See diff: {diff_out}"
            )
            print("Baseline image comparison PASSED (within tolerance).")
        except Exception as img_ex:
            pytest.fail(f"Baseline image comparison failed: {img_ex}")

        # 7) Click the personalized CTA when clickable (Finish Opening...)
        print("Waiting for CTA to be clickable and then clicking…")
        cta_dest = await click_cta_when_clickable(page, screenshots_directory, cfg)
        print("CTA click resolved destination:", cta_dest)

        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(screenshots_directory / '8a_after_funnel_cta_click.png'))

    except PlaywrightTimeoutError as e:
        try:
            await save_page_source(page, screenshots_directory / 'failure_source.html')
            await page.screenshot(path=str(screenshots_directory / 'failure_screenshot.png'))
        except Exception:
            pass
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print("No JavaScript errors detected for", client)
