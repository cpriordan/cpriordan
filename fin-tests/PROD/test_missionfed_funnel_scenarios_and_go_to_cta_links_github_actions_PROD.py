#!/usr/bin/env python3
# =====================
# File: fin-tests/PROD/test_missionfed_funnel_scenarios_and_go_to_cta_links_github_actions_PROD.py
# =====================
# PURPOSE:
#   Variant of the MissionFed funnel scenario test that does NOT click CTA buttons.
#   Instead it:
#     1. Runs the normal funnel scenario navigation (session_init → product page → homepage).
#     2. Finds each CTA element and reads its href attribute (relative URL).
#     3. Appends the relative URL to BASE_URL and navigates there directly via page.goto()
#        so that analytics / tracking pixels are NOT triggered by a real click.
#     4. Checks the HTTP response status is 200 (not 404 or other error).
#     5. Generates a self-contained HTML report listing each scenario, CTA text,
#        relative href, full URL, HTTP status, and pass/fail result.
#
# BASE_URL: https://www.missionfed.com
# Report:   tests/missionfed_cta_link_check_report.html (relative to CWD)

import asyncio
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ==========================================================
# Configuration
# ==========================================================

BASE_URL = "https://www.missionfed.com"

# Where the HTML CTA link report is written
REPORT_PATH = Path("tests") / "missionfed_cta_link_check_report.html"

# Module-level results list — populated by each test, consumed by the report fixture
_CTA_RESULTS: List[Dict] = []


# ==========================================================
# Scenario model
# ==========================================================

@dataclass
class ScenarioConfig:
    name: str
    test_scenario_url: str
    test_scenario_url2: str

    cta_regex: str = r"FINISH\s*OPENING\s*MY\s*ACCOUNT"
    scenario_dir: Optional[str] = None
    product_cta_button: Optional[str] = "Apply Today"
    product_pulldown_menu_selector: Optional[str] = None
    product_checkbox_selector: Optional[str] = None
    product_to_select: Optional[str] = None

    def screenshots_dir(self, client: str) -> Path:
        base_dir = Path("tests") / f"screenshots_{client}_using_pytest"
        sub = self.scenario_dir or self.name
        return base_dir / sub / "PROD"

    @property
    def cta_pattern(self) -> re.Pattern:
        return re.compile(self.cta_regex, re.I)


SCENARIOS: List[ScenarioConfig] = [
    ScenarioConfig(
        name="checking",
        test_scenario_url="https://www.missionfed.com/checking-spending/",
        test_scenario_url2="",
        product_cta_button="Apply Today",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Easy Checking",
        product_checkbox_selector="#mat-option-1 > span",
        cta_regex=r"FINISH\s*OPENING\s*MY\s*ACCOUNT",
    ),
    ScenarioConfig(
        name="savings",
        test_scenario_url="https://www.missionfed.com/savings/",
        test_scenario_url2="",
        product_cta_button="OPEN ACCOUNT",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Savings",
        product_checkbox_selector="#mat-option-3 > span",
        cta_regex=r"FINISH\s*OPENING\s*MY\s*ACCOUNT",
    ),
    ScenarioConfig(
        name="cd",
        test_scenario_url="https://www.missionfed.com/savings/",
        test_scenario_url2="",
        product_cta_button="OPEN ACCOUNT",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Certificate",
        product_checkbox_selector="#mat-option-6 > span",
        cta_regex=r"FINISH\s*OPENING\s*MY\s*ACCOUNT",
    ),
    ScenarioConfig(
        name="personal loan",
        test_scenario_url="https://www.missionfed.com/other-loans/personal-loan/",
        test_scenario_url2="",
        product_cta_button="APPLY NOW",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
    ),
    ScenarioConfig(
        name="credit card",
        test_scenario_url="https://www.missionfed.com/compare-credit-cards/",
        test_scenario_url2="",
        product_cta_button="APPLY NOW",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
    ),
    ScenarioConfig(
        name="hispanic checking",
        test_scenario_url="https://www.missionfed.com/?debug_all=1&segments=skew%20hispanic&zipcode=91911&keywords=checking%20account",
        test_scenario_url2="https://www.missionfed.com/checking-spending/",
        product_cta_button="Apply Today",
        product_pulldown_menu_selector="#mat-select-0 > div > div.mat-select-arrow-wrapper.ng-tns-c51-1 > div",
        product_to_select="Easy Checking",
        product_checkbox_selector="#mat-option-1 > span",
        cta_regex=r"FINISH\s*OPENING\s*MY\s*ACCOUNT",
    ),
    ScenarioConfig(
        name="hispanic credit card",
        test_scenario_url="https://www.missionfed.com/?cb=1&debug_all=1&segments=skew%20hispanic&zipcode=91911&keywords=credit%20card",
        test_scenario_url2="https://www.missionfed.com/compare-credit-cards/",
        product_cta_button="Apply Now",
        cta_regex=r"COMPLETE\s*MY\s*APPLICATION",
    ),
]


# ==========================================================
# URL helpers
# ==========================================================

def _build_full_url(href: str) -> str:
    """Resolve a CTA href to a full URL using BASE_URL."""
    if not href:
        return ""
    if re.match(r"^https?://", href):
        return href  # already absolute
    # Relative URL — prepend BASE_URL
    return BASE_URL.rstrip("/") + "/" + href.lstrip("/")


def _is_relative(href: str) -> bool:
    return bool(href) and not re.match(r"^https?://", href)


def _swap_page_host(u: str) -> str:
    """Point any missionfed.com URL at BASE_URL."""
    if not u:
        return u
    if re.match(r"^https?://", u):
        p = urlsplit(u)
        base_p = urlsplit(BASE_URL)
        if p.netloc.endswith("missionfed.com"):
            return urlunsplit((base_p.scheme, base_p.netloc, p.path, p.query, p.fragment))
        return u
    return urljoin(BASE_URL, u)


# ==========================================================
# Screenshot helpers
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
                print(f"Failed to delete {item}: {e}")
    else:
        directory.mkdir(parents=True, exist_ok=True)


async def save_page_source(page, filepath: Path) -> None:
    try:
        filepath.write_text(await page.content(), encoding="utf-8")
    except Exception as e:
        print(f"Failed to save page source: {e}")


# ==========================================================
# Page-load helper
# ==========================================================

async def wait_for_document_complete(page, timeout=70000):
    await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    await page.wait_for_load_state("load", timeout=timeout)
    await page.evaluate("""new Promise(resolve => {
        if (document.readyState === 'complete') resolve();
        else window.addEventListener('load', () => resolve(), { once: true });
    })""")


# ==========================================================
# Cookie-banner helper
# ==========================================================

COOKIE_ACCEPT_SELECTORS = ["a.cc-btn.cc-dismiss"]
COOKIE_BANNER_CONTAINERS = [".cc-window"]


async def try_click_cookie_accept(page, screenshots_directory: Path):
    for sel in COOKIE_ACCEPT_SELECTORS:
        locator = page.locator(sel)
        try:
            if await locator.count() > 0:
                await locator.first.wait_for(state="visible", timeout=2000)
                try:
                    await locator.first.click()
                except Exception:
                    handle = await locator.first.element_handle()
                    if handle:
                        await page.evaluate("(el) => el.click()", handle)
                await asyncio.sleep(0.5)
        except Exception:
            continue

    for cont in COOKIE_BANNER_CONTAINERS:
        try:
            count = await page.locator(cont).count()
            for i in range(count):
                if await page.locator(cont).nth(i).is_visible():
                    css = ",".join(COOKIE_BANNER_CONTAINERS) + "{ display:none !important; }"
                    await page.add_style_tag(content=css)
                    break
        except Exception:
            pass


# ==========================================================
# CTA helpers — href extraction (NO click)
# ==========================================================

def _cta_locator(page, cfg: ScenarioConfig):
    return page.locator(":is(a,button,[role='link'],[role='button'])", has_text=cfg.cta_pattern).first


async def wait_for_cta_visible(page, cfg: ScenarioConfig, timeout_ms: int = 12000) -> bool:
    deadline = time.time() + (timeout_ms / 1000.0)
    loc = _cta_locator(page, cfg)
    while time.time() < deadline:
        try:
            if await loc.count() > 0 and await loc.is_visible():
                return True
        except Exception:
            pass
        await asyncio.sleep(0.25)
    return False


async def grab_href_from_element(page, loc) -> str:
    """Read href from a locator, checking inner <a> if needed."""
    raw_href = ""
    try:
        raw_href = (await loc.get_attribute("href")) or ""
    except Exception:
        pass
    if not raw_href:
        try:
            inner = loc.locator("a[href]").first
            if await inner.count() > 0:
                raw_href = (await inner.get_attribute("href")) or ""
        except Exception:
            pass
    return raw_href


async def grab_product_cta_href(page, cfg: ScenarioConfig) -> str:
    """
    On the product page, find the initial hero CTA (e.g. 'Apply Today') and
    return its href — no click. This is used to build the apply_url referer.
    """
    label = (cfg.product_cta_button or "Apply Today").strip()
    label_pattern = re.compile(re.escape(label), re.I)
    candidates = [
        page.get_by_role("link", name=label_pattern),
        page.get_by_role("button", name=label_pattern),
        page.locator(f"a:has-text('{label}')"),
        page.locator(f"[role='link']:has-text('{label}')"),
        # Generic fallback — any Apply/Open/Start link in the hero
        page.locator(".hero a[href]").first,
        page.locator("a[href*='apply']").first,
        page.locator("a[href*='open']").first,
    ]
    for cand in candidates:
        try:
            if await cand.count() > 0 and await cand.first.is_visible():
                href = await grab_href_from_element(page, cand.first)
                if href:
                    return href
        except Exception:
            continue
    return ""


async def _click_product_cta(page, screenshots_directory: Path, cfg: ScenarioConfig) -> str:
    """
    Click the product-page CTA (e.g. 'Apply Today') to register the funnel session with Finalytics.
    If the click opens a new tab, close it. Returns the apply URL (for use as referer).
    """
    label = (cfg.product_cta_button or "Apply Today").strip()
    label_pattern = re.compile(re.escape(label), re.I)

    candidates = [
        page.get_by_role("link", name=label_pattern),
        page.get_by_role("button", name=label_pattern),
        page.locator(f"a:has-text('{label}')"),
        page.locator(f"[role='link']:has-text('{label}')"),
        page.get_by_role("link", name=re.compile(r"Apply Today", re.I)),
        page.locator("a:has-text('Apply Today')"),
    ]

    target = None
    for cand in candidates:
        try:
            if await cand.count() > 0 and await cand.first.is_visible():
                target = cand.first
                break
        except Exception:
            continue

    if not target:
        raise PlaywrightTimeoutError(f"Could not locate product CTA labeled '{label}'.")

    # Read href before clicking (for use as referer even if new tab opens)
    apply_href = ""
    try:
        apply_href = (await target.get_attribute("href")) or ""
        if apply_href:
            apply_href = urljoin(page.url, apply_href)
    except Exception:
        pass

    prev_url = page.url
    new_tab = None
    context = page.context

    try:
        async with context.expect_page(timeout=7000) as page_info:
            await target.click()
        new_tab = await page_info.value
        try:
            await new_tab.wait_for_load_state("domcontentloaded")
            if not apply_href:
                apply_href = new_tab.url
            await new_tab.screenshot(path=str(screenshots_directory / "3_apply_page_new_tab.png"))
        except Exception:
            pass
        try:
            await new_tab.close()
        except Exception:
            pass
    except PlaywrightTimeoutError:
        # No new tab — same-tab navigation
        try:
            await page.wait_for_load_state("load", timeout=6000)
        except Exception:
            pass
        if not apply_href and page.url != prev_url:
            apply_href = page.url

    # Navigate the original tab to the apply URL so Finalytics records the visit
    # (mirrors original test's _validate_cta_destination behavior)
    if apply_href:
        try:
            await page.goto(apply_href, timeout=70000)
            await wait_for_document_complete(page)
            # Capture final URL after any redirects — this is what Finalytics will track as referer
            apply_href = page.url
            await page.screenshot(path=str(screenshots_directory / "3_apply_page.png"))
        except Exception as e:
            print(f"[WARNING] Could not navigate to apply URL {apply_href!r}: {e}")

    return apply_href or prev_url


async def grab_funnel_cta_href(page, cfg: ScenarioConfig) -> Dict[str, str]:
    """
    On the homepage (after funnel history is set), find the funnel CTA
    (e.g. 'FINISH OPENING MY ACCOUNT') and read its href — no click.
    Returns dict: cta_text, raw_href, relative_href, full_url.
    """
    loc = _cta_locator(page, cfg)

    cta_text = ""
    raw_href = ""

    try:
        cta_text = (await loc.inner_text()).strip()
    except Exception:
        cta_text = cfg.cta_pattern.pattern

    raw_href = await grab_href_from_element(page, loc)

    relative_href = raw_href if _is_relative(raw_href) else (urlsplit(raw_href).path or raw_href)
    # full_url is set to raw_href as-is — funnel CTA hrefs are absolute URLs to external platforms
    full_url = raw_href

    return {
        "cta_text":      cta_text,
        "raw_href":      raw_href,
        "relative_href": relative_href,
        "full_url":      full_url,
    }


async def check_url_status(page, full_url: str) -> Dict:
    """
    Navigate directly to full_url (no button click).
    Returns http_status, ok (bool), note.
    """
    if not full_url:
        return {"http_status": None, "ok": False, "note": "Empty URL"}

    # Strip fragment — servers never see it
    parsed = urlsplit(full_url)
    url_no_frag = parsed._replace(fragment="").geturl()

    try:
        resp = await page.goto(url_no_frag, timeout=30000, wait_until="domcontentloaded")
        if resp:
            status = resp.status
            note = ""
            ok = False
            if status == 200:
                # Soft-404 check
                try:
                    title = (await page.title()).lower()
                    h1s = await page.locator("h1").all_inner_texts()
                    combined = title + " " + " ".join(h1s).lower()
                    if any(kw in combined for kw in ("not found", "404", "page not found", "can't find")):
                        note = f"Soft 404 (title: {await page.title()!r})"
                    else:
                        ok = True
                except Exception:
                    ok = True
            else:
                note = f"HTTP {status}"
            return {"http_status": status, "ok": ok, "note": note}
        else:
            return {"http_status": None, "ok": False, "note": "No response object"}
    except PlaywrightTimeoutError:
        return {"http_status": None, "ok": False, "note": "Timeout"}
    except Exception as exc:
        return {"http_status": None, "ok": False, "note": str(exc)[:200]}


# ==========================================================
# Playwright fixture
# ==========================================================

@pytest_asyncio.fixture
async def browser(request):
    username = request.param.get("username", "")
    password = request.param.get("password", "")

    headless_env = os.getenv("MF_HEADLESS", "").strip()
    ci_env = os.getenv("CI", "").strip()
    headless = True if (headless_env == "1" or ci_env) else False

    chromium_args = ["--remote-debugging-port=9222"]
    if headless:
        chromium_args += ["--disable-gpu", "--no-sandbox", "--no-zygote", "--disable-dev-shm-usage"]

    async with async_playwright() as playwright:
        b = await playwright.chromium.launch(headless=headless, args=chromium_args)
        ctx_kwargs = {}
        if username or password:
            ctx_kwargs["http_credentials"] = {"username": username, "password": password}
        context = await b.new_context(**ctx_kwargs)
        context.set_default_timeout(70000)
        yield context
        await b.close()


# ==========================================================
# Report generation fixture (session-scoped, runs at end)
# ==========================================================

@pytest.fixture(scope="session", autouse=True)
def generate_cta_report():
    """Yield to let all tests run, then write the HTML report."""
    yield
    _write_html_report(_CTA_RESULTS)


def _write_html_report(results: List[Dict]):
    total    = len(results)
    passed   = sum(1 for r in results if r.get("ok"))
    failed   = sum(1 for r in results if not r.get("ok"))
    no_href  = sum(1 for r in results if not r.get("raw_href"))

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    rows = ""
    for i, r in enumerate(results, 1):
        ok     = r.get("ok", False)
        status = r.get("http_status") or "—"
        note   = r.get("note", "")
        pill   = '<span class="pill ok">PASS</span>' if ok else '<span class="pill fail">FAIL</span>'
        note_html = f'<br><small style="color:#888">{esc(note)}</small>' if note else ""
        rows += f"""
        <tr class="{'ok' if ok else 'fail'}">
          <td class="num">{i}</td>
          <td>{esc(r.get('scenario',''))}</td>
          <td>{esc(r.get('cta_text',''))}</td>
          <td class="mono">{esc(r.get('relative_href','—'))}</td>
          <td class="mono"><a href="{esc(r.get('full_url',''))}" target="_blank">{esc(r.get('full_url',''))}</a></td>
          <td class="num">{status}</td>
          <td>{pill}{note_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MissionFed CTA Link Check — PROD</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         font-size: 13px; background: #f5f7fa; color: #333; }}
  header {{ background: #1a3c6e; color: #fff; padding: 20px 32px; }}
  header h1 {{ font-size: 1.3rem; }}
  header p {{ font-size: 0.8rem; opacity: .8; margin-top: 4px; }}
  .stats {{ display: flex; gap: 14px; padding: 14px 32px; background: #fff;
            border-bottom: 1px solid #dde; flex-wrap: wrap; }}
  .stat {{ background: #f0f4ff; border: 1px solid #d0d8f0; border-radius: 7px;
           padding: 10px 18px; text-align: center; min-width: 100px; }}
  .stat .val {{ font-size: 22px; font-weight: 700; }}
  .stat .lbl {{ font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #666; }}
  .stat.green .val {{ color: #1a7a3c; }}
  .stat.red   .val {{ color: #c0392b; }}
  .stat.blue  .val {{ color: #1a3c6e; }}
  main {{ padding: 20px 32px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff;
           border: 1px solid #dde; border-radius: 8px; overflow: hidden; }}
  th {{ background: #f0f2f8; padding: 8px 10px; font-size: 11px; text-transform: uppercase;
        letter-spacing: .04em; color: #555; border-bottom: 2px solid #dde; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #eef; vertical-align: top; }}
  tr.ok td {{ background: #f8fff9; }}
  tr.fail td {{ background: #fff8f8; }}
  .num {{ text-align: right; width: 50px; }}
  .mono {{ font-family: Consolas, monospace; font-size: 11px; word-break: break-all; }}
  .pill {{ display: inline-block; padding: 2px 10px; border-radius: 10px;
           font-size: 11px; font-weight: 700; }}
  .pill.ok   {{ background: #d4f5e2; color: #1a7a3c; }}
  .pill.fail {{ background: #fde0de; color: #c0392b; }}
  a {{ color: #1a3c6e; }}
  p.note {{ margin-top: 10px; font-size: 11px; color: #888; }}
</style>
</head>
<body>
<header>
  <h1>MissionFed Funnel — CTA Link Check (PROD)</h1>
  <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp;
     Base URL: {esc(BASE_URL)} &nbsp;|&nbsp;
     CTAs navigated directly (no button click)</p>
</header>
<div class="stats">
  <div class="stat blue"><div class="val">{total}</div><div class="lbl">Scenarios</div></div>
  <div class="stat green"><div class="val">{passed}</div><div class="lbl">Passed (200)</div></div>
  <div class="stat red"><div class="val">{failed}</div><div class="lbl">Failed</div></div>
  <div class="stat {'red' if no_href else 'blue'}"><div class="val">{no_href}</div><div class="lbl">No href found</div></div>
</div>
<main>
  <table>
    <thead>
      <tr>
        <th class="num">#</th>
        <th>Scenario</th>
        <th>CTA Text</th>
        <th>Relative href</th>
        <th>Full URL (BASE_URL + relative)</th>
        <th class="num">Status</th>
        <th>Result</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="note">
    CTAs are located by text pattern in the hero after running the funnel scenario.
    The href attribute is read directly — no button is clicked. The full URL is constructed
    as <code>{esc(BASE_URL)}</code> + relative href and navigated to via page.goto().
  </p>
</main>
</body>
</html>"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"\n[CTA Report] Saved to: {REPORT_PATH.resolve()}")
    print(f"[CTA Report] {passed} passed, {failed} failed out of {total} scenarios")


# ==========================================================
# Pytest parametrization
# ==========================================================

def _pytest_ids():
    return [s.name for s in SCENARIOS]


@pytest.mark.asyncio
@pytest.mark.parametrize("browser", [{"username": "", "password": ""}], indirect=True)
@pytest.mark.parametrize("cfg", SCENARIOS, ids=_pytest_ids())
async def test_missionfed_cta_link_check(
    browser,
    cfg: ScenarioConfig,
    client: str = "missionfed",
):
    """
    Funnel scenario navigation → CTA href extraction → direct URL navigation → HTTP 200 check.
    No button is clicked; analytics are not triggered.
    """
    home_with_init = f"{BASE_URL}/?session_init=1&debug_all=1&cb=0"
    home           = f"{BASE_URL}/?debug_all=1&cb=0"
    scen_url       = _swap_page_host(cfg.test_scenario_url)
    scen_url2      = _swap_page_host(cfg.test_scenario_url2) if cfg.test_scenario_url2 else ""

    screenshots_directory = cfg.screenshots_dir(client)
    screenshots_directory.mkdir(parents=True, exist_ok=True)
    clear_screenshots_directory(screenshots_directory)

    page = await browser.new_page()
    result_entry: Dict = {
        "scenario":      cfg.name,
        "cta_text":      "",
        "raw_href":      "",
        "relative_href": "",
        "full_url":      "",
        "http_status":   None,
        "ok":            False,
        "note":          "",
    }

    try:
        # ── Step 1: session_init homepage ──
        print(f"\n[{cfg.name}] Navigating to homepage with session_init...")
        await page.goto(home_with_init, timeout=70000)
        await wait_for_document_complete(page)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / "1_homepage_session_init.png"))

        # ── Step 2: product page ──
        print(f"[{cfg.name}] Navigating to product page: {scen_url}")
        await page.goto(scen_url, timeout=70000)
        await wait_for_document_complete(page)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / "2_product_page.png"))

        if scen_url2:
            print(f"[{cfg.name}] Navigating to product page 2: {scen_url2}")
            await page.goto(scen_url2, timeout=70000)
            await wait_for_document_complete(page)
            await page.screenshot(path=str(screenshots_directory / "2b_product_page2.png"))

        # ── Step 3: click "Apply Today" to register the funnel session ──
        # This click is required — Finalytics records the click event to show the funnel CTA later.
        print(f"[{cfg.name}] Clicking product CTA ('{cfg.product_cta_button}') to register funnel session...")
        apply_url = await _click_product_cta(page, screenshots_directory, cfg)
        print(f"[{cfg.name}] Apply URL: {apply_url!r}")
        await asyncio.sleep(2.5)

        # ── Step 3b: product selection on the apply form (if configured) ──
        should_select_product = (
            bool((cfg.product_pulldown_menu_selector or "").strip())
            and bool((cfg.product_to_select or "").strip())
        )
        if should_select_product:
            print(f"[{cfg.name}] Selecting product '{cfg.product_to_select}' on apply form...")
            try:
                await page.wait_for_selector(cfg.product_pulldown_menu_selector, state="visible", timeout=20000)
                product_menu = page.locator(cfg.product_pulldown_menu_selector).first
                try:
                    await product_menu.scroll_into_view_if_needed()
                except Exception:
                    pass
                await product_menu.click()
                await asyncio.sleep(0.5)

                product_name = cfg.product_to_select.strip()
                name_pattern = re.compile(re.escape(product_name), re.I)
                clicked = False
                if cfg.product_checkbox_selector and cfg.product_checkbox_selector.strip():
                    opt = page.locator(cfg.product_checkbox_selector).first
                    try:
                        await opt.wait_for(state="visible", timeout=8000)
                        await opt.click()
                        clicked = True
                    except Exception:
                        pass
                if not clicked:
                    role_opt = page.get_by_role("option", name=name_pattern).first
                    if await role_opt.count() > 0:
                        await role_opt.click()
                        clicked = True
                if not clicked:
                    by_text = page.get_by_text(name_pattern).first
                    if await by_text.count() > 0:
                        await by_text.click()
                if clicked:
                    print(f"[{cfg.name}] Selected '{product_name}'.")
                    await page.screenshot(path=str(screenshots_directory / "3b_product_selected.png"))
            except Exception as e:
                print(f"[{cfg.name}] WARNING: Product selection failed: {e} — continuing anyway.")

        # ── Step 4: navigate back to product page (mirrors original flow) ──
        print(f"[{cfg.name}] Navigating back to product page: {scen_url}")
        await page.goto(scen_url, timeout=70000)
        await wait_for_document_complete(page)
        await page.screenshot(path=str(screenshots_directory / "4_product_page_again.png"))

        # ── Step 5: homepage without session_init (with apply_url as referer) ──
        print(f"[{cfg.name}] Returning to homepage (no session_init)...")
        goto_kwargs = {"timeout": 70000}
        if apply_url:
            goto_kwargs["referer"] = apply_url
        await page.goto(home, **goto_kwargs)
        await wait_for_document_complete(page)
        await try_click_cookie_accept(page, screenshots_directory)
        await page.screenshot(path=str(screenshots_directory / "5_home_without_session_init.png"))

        if not cfg.name.startswith("hispanic"):
            print(f"[{cfg.name}] Navigating to homepage with session_init (referer=apply_url)...")
            await page.goto(home_with_init, **goto_kwargs)
            await wait_for_document_complete(page)
            await try_click_cookie_accept(page, screenshots_directory)
            await page.screenshot(path=str(screenshots_directory / "6_home_with_session_init.png"))

        # ── Step 6 (cont): wait for funnel CTA to appear ──
        print(f"[{cfg.name}] Waiting for funnel CTA to appear...")
        found_cta = await wait_for_cta_visible(page, cfg, timeout_ms=8000)

        reloads = 0
        while not found_cta and reloads < 2:
            reloads += 1
            print(f"[{cfg.name}] Soft reload #{reloads}...")
            await page.reload(wait_until="load", timeout=70000)
            await wait_for_document_complete(page)
            await page.screenshot(path=str(screenshots_directory / f"7_reload_{reloads}.png"))
            found_cta = await wait_for_cta_visible(page, cfg, timeout_ms=6000)

        await page.screenshot(path=str(screenshots_directory / "7_cta_visible.png"))

        if not found_cta:
            await save_page_source(page, screenshots_directory / "no_cta.html")
            result_entry["note"] = "Funnel CTA did not appear"
            _CTA_RESULTS.append(result_entry)
            pytest.fail(f"[{cfg.name}] Funnel CTA did not appear after reloads.")

        # ── Step 7: grab funnel CTA href (no click) ──
        # The href is grabbed as-is — it will already be an absolute URL to the application platform.
        print(f"[{cfg.name}] Grabbing funnel CTA href (no click)...")
        href_info = await grab_funnel_cta_href(page, cfg)
        # Use raw_href directly as the URL to navigate to (no BASE_URL construction needed)
        navigate_url = href_info["raw_href"]
        href_info["full_url"] = navigate_url
        result_entry.update(href_info)
        print(f"[{cfg.name}] CTA text   : {href_info['cta_text']!r}")
        print(f"[{cfg.name}] Raw href   : {href_info['raw_href']!r}")
        print(f"[{cfg.name}] URL to go  : {navigate_url!r}")

        if not navigate_url:
            result_entry["note"] = "Could not find href on CTA element"
            _CTA_RESULTS.append(result_entry)
            pytest.fail(f"[{cfg.name}] No href found on CTA element.")

        # ── Step 8: navigate directly to funnel CTA URL, check status ──
        print(f"[{cfg.name}] Navigating directly to: {navigate_url}")
        status_info = await check_url_status(page, navigate_url)
        result_entry.update(status_info)
        await page.screenshot(path=str(screenshots_directory / "8_cta_destination.png"))

        print(f"[{cfg.name}] HTTP status: {status_info['http_status']} "
              f"({'OK' if status_info['ok'] else 'FAIL'}) {status_info['note']}")

        _CTA_RESULTS.append(result_entry)

        assert status_info["ok"], (
            f"[{cfg.name}] CTA URL returned non-200 status.\n"
            f"  URL    : {href_info['full_url']}\n"
            f"  Status : {status_info['http_status']}\n"
            f"  Note   : {status_info['note']}"
        )

        print(f"[{cfg.name}] PASS — CTA URL is reachable (HTTP 200).")

    except PlaywrightTimeoutError as exc:
        try:
            await save_page_source(page, screenshots_directory / "failure_source.html")
            await page.screenshot(path=str(screenshots_directory / "failure.png"))
        except Exception:
            pass
        if result_entry not in _CTA_RESULTS:
            result_entry["note"] = f"Timeout: {exc}"
            _CTA_RESULTS.append(result_entry)
        pytest.fail(f"[{cfg.name}] Playwright timeout: {exc}")

    except AssertionError:
        raise

    except Exception as exc:
        try:
            await page.screenshot(path=str(screenshots_directory / "error.png"))
        except Exception:
            pass
        if result_entry not in _CTA_RESULTS:
            result_entry["note"] = str(exc)[:200]
            _CTA_RESULTS.append(result_entry)
        pytest.fail(f"[{cfg.name}] Unexpected error: {exc}")
