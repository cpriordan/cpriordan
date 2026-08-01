"""
Statewide OLB Card Ad CTA Links Test - STAGING (GitHub Actions)

CI-compatible test targeting the Statewide SWFCU staging environment.

Changes from the PROD version:
- BASE_URL  → https://statewide.stage.bankjoy.com
- Default credentials are the SWFCU staging test account
- Report filename: statewide_cta_links_report_STG.html
- Screenshots saved under statewide/olb_STG/cta_links/

Required GitHub Secrets (override the hardcoded defaults):
    STATEWIDE_STG_USERNAME      OLB staging login username
    STATEWIDE_STG_PASSWORD      OLB staging login password
    STATEWIDE_STG_OTP_SECRET    Base-32 TOTP secret (if account uses authenticator-app 2FA)
                                Leave unset if no 2FA is required in the staging environment.

Optional environment variables:
    STATEWIDE_STG_BASE_URL      Default: https://statewide.stage.bankjoy.com
    STATEWIDE_STG_SKIP_2FA      Set to "true" to skip OTP handling entirely
"""

import asyncio
import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

# =============================================================================
# CONFIGURATION — env vars take precedence; hardcoded values are STG defaults
# =============================================================================
BASE_URL   = os.environ.get("STATEWIDE_STG_BASE_URL", "https://statewide.stage.bankjoy.com")
USERNAME   = os.environ.get("STATEWIDE_STG_USERNAME", "cbracey25")
PASSWORD   = os.environ.get("STATEWIDE_STG_PASSWORD", "SwFCU2025$$$")
OTP_SECRET = os.environ.get("STATEWIDE_STG_OTP_SECRET", "")
SKIP_2FA   = os.environ.get("STATEWIDE_STG_SKIP_2FA", "false").lower() == "true"

LOGIN_URL     = f"{BASE_URL}/?cb=1&session_init=1&debug_all=1"
DASHBOARD_URL = f"{BASE_URL}/consumer/main/dashboard"

REPORT_PATH     = Path("statewide_cta_links_report_STG.html")
SCREENSHOT_ROOT = Path("statewide/olb_STG/cta_links")

# =============================================================================

CORE_PRODUCTS = [
    "checking account",
    "cd",
    "equipment loan",
    "personal loan",
    "rv loan",
    "ira",
    "credit card",
    "boat loan",
    "car loan",
    "savings account",
]

SELECTORS = {
    "username_input":        "#username",
    "password_input":        "#password",
    "continue_button":       "button:has-text('Continue')",
    "otp_input":             "input[type='text'][maxlength='6'], input[name*='otp'], input[name*='code'], input[placeholder*='code'], input[placeholder*='OTP'], input[id*='otp'], input[id*='code']",
    "tile_ad":               "#finalytics-tile-ad",
    "tile_ad_primary_btn":   "#finalytics-tile-ad > div > div > div > a.btn-primary",
    "tile_ad_secondary_btn": "#finalytics-tile-ad > div > div > div > a.btn-secondary",
    "broadcast_close":       "#mat-mdc-dialog-0 > div > div > app-broadcast-ad-dialog > button",
}

NOT_FOUND_PATTERNS = ["404", "page not found", "not found", "error"]


# =============================================================================
# Helpers
# =============================================================================

def sanitize_filename(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_").lower()


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def setup_screenshot_dirs() -> dict:
    dirs = {
        "primary":   SCREENSHOT_ROOT / "primary",
        "secondary": SCREENSHOT_ROOT / "secondary",
        "card":      SCREENSHOT_ROOT / "card_ads",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


async def scroll_to_element(page, selector: str, timeout: int = 15000) -> bool:
    try:
        await page.locator(selector).scroll_into_view_if_needed(timeout=timeout)
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        return True
    except Exception:
        return False


async def set_browser_zoom(page, zoom: float = 0.8):
    await page.evaluate(
        f"document.body.style.cssText = 'transform:scale({zoom});transform-origin:0 0;width:{int(100/zoom)}%'"
    )


async def close_broadcast_overlay(page, timeout: int = 4000) -> bool:
    selectors = [
        SELECTORS["broadcast_close"],
        "app-broadcast-ad-dialog button",
        "#mat-mdc-dialog-0 button",
        "mat-dialog-container button",
        "[mat-dialog-close]",
        "button[aria-label='Close']",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=timeout):
                await btn.click()
                await page.wait_for_timeout(800)
                return True
        except Exception:
            continue
    try:
        dialog = page.locator("mat-dialog-container, .mat-mdc-dialog-container")
        if await dialog.count() > 0 and await dialog.first.is_visible(timeout=1000):
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(800)
            return True
    except Exception:
        pass
    return False


async def click_submit(page) -> bool:
    selectors = [
        SELECTORS["continue_button"],
        "button[type='submit']",
        "button:has-text('Sign In')",
        "button:has-text('Login')",
        "button.bj-btn-primary",
        ".btn-primary",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(800)
                return True
        except Exception:
            continue
    await page.keyboard.press("Enter")
    return True


async def handle_otp(page) -> bool:
    """
    Attempt to fill the OTP field if one appears after credentials.
    Uses pyotp with STATEWIDE_STG_OTP_SECRET if available.
    Returns True if OTP was handled (or not needed), False on unrecoverable failure.
    """
    if SKIP_2FA:
        print("[CI] STATEWIDE_STG_SKIP_2FA=true — skipping OTP handling")
        return True

    otp_locator = page.locator(SELECTORS["otp_input"])
    try:
        await otp_locator.first.wait_for(state="visible", timeout=8000)
    except PlaywrightTimeoutError:
        print("[CI] No OTP input detected — assuming 2FA not required in STG")
        return True

    if not PYOTP_AVAILABLE:
        print("[CI] ERROR: pyotp not installed but OTP prompt appeared")
        return False

    if not OTP_SECRET:
        print("[CI] ERROR: STATEWIDE_STG_OTP_SECRET is not set but OTP prompt appeared")
        return False

    try:
        totp = pyotp.TOTP(OTP_SECRET)
        code = totp.now()
        print(f"[CI] Generated TOTP code: {code}")
        await otp_locator.first.fill(code)
        await page.wait_for_timeout(500)
        await click_submit(page)
        print("[CI] OTP submitted")
        return True
    except Exception as e:
        print(f"[CI] OTP submission error: {e}")
        return False


async def perform_login(page) -> bool:
    print(f"[CI] Navigating to: {LOGIN_URL}")
    await page.goto(LOGIN_URL, timeout=60000)
    await page.wait_for_load_state("networkidle", timeout=30000)

    username_field = page.locator(SELECTORS["username_input"])
    if not await username_field.is_visible(timeout=10000):
        print("[CI] Username field not visible")
        return False

    await username_field.fill(USERNAME)
    await page.wait_for_timeout(300)

    password_field = page.locator(SELECTORS["password_input"])
    if await password_field.is_visible(timeout=3000):
        await password_field.fill(PASSWORD)
        await page.wait_for_timeout(300)

    await click_submit(page)
    await page.wait_for_timeout(2000)

    # Check if already on dashboard (no 2FA)
    if "consumer/main" in page.url and "sign-in" not in page.url:
        print("[CI] Logged in without 2FA")
        return True

    otp_ok = await handle_otp(page)
    if not otp_ok:
        return False

    try:
        await page.wait_for_url("**/consumer/**", timeout=30000)
        print(f"[CI] Login complete — {page.url}")
        return True
    except PlaywrightTimeoutError:
        pass

    logged_in = "consumer" in page.url and "sign-in" not in page.url
    print(f"[CI] Login status: {'success' if logged_in else 'failed'} — {page.url}")
    return logged_in


async def is_valid_page(page) -> tuple:
    try:
        title = await page.title()
        broken = any(p in title.lower() for p in NOT_FOUND_PATTERNS)
        return not broken, title
    except Exception as e:
        return False, f"Error: {e}"


async def test_card_ad_cta_links(page, screenshot_dirs: dict, timestamp: str, product_name: str = None) -> dict:
    result = {
        "product":                   product_name or "unknown",
        "primary_btn_text":          None,
        "primary_href":              None,
        "primary_destination_url":   None,
        "primary_valid":             False,
        "primary_title":             None,
        "primary_screenshot":        None,
        "secondary_exists":          False,
        "secondary_btn_text":        None,
        "secondary_href":            None,
        "secondary_destination_url": None,
        "secondary_valid":           False,
        "secondary_title":           None,
        "secondary_screenshot":      None,
    }

    product_fn = sanitize_filename(result["product"])
    print(f"\n{'='*60}\nTesting CTA links for: {result['product']}\n{'='*60}")

    card_found = await scroll_to_element(page, SELECTORS["tile_ad"])
    if card_found:
        card_ss = screenshot_dirs["card"] / f"{product_fn}_{timestamp}.png"
        try:
            await page.screenshot(path=str(card_ss), full_page=False, timeout=10000)
            result["card_screenshot"] = str(card_ss)
        except Exception:
            pass

    dashboard_url = page.url

    # ── Primary ───────────────────────────────────────────────────────────────
    print("\n--- Primary CTA ---")
    primary_btn = page.locator(SELECTORS["tile_ad_primary_btn"])
    if await primary_btn.count() > 0 and await primary_btn.first.is_visible(timeout=5000):
        try:
            btn_text = await primary_btn.first.inner_text()
            btn_href = await primary_btn.first.get_attribute("href")
            result["primary_btn_text"] = btn_text.strip()
            result["primary_href"]     = btn_href
            print(f"Text : {btn_text.strip()!r}")
            print(f"Href : {btn_href}")

            if btn_href:
                await page.goto(btn_href, timeout=30000)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1000)

                result["primary_destination_url"] = page.url
                valid, title = await is_valid_page(page)
                result["primary_valid"] = valid
                result["primary_title"] = title
                print(f"Dest  : {page.url}")
                print(f"Title : {title}")
                print(f"Valid : {'PASS' if valid else 'FAIL'}")

                ss_path = screenshot_dirs["primary"] / f"{product_fn}_primary_{timestamp}.png"
                try:
                    await page.screenshot(path=str(ss_path), full_page=False, timeout=10000)
                    result["primary_screenshot"] = str(ss_path)
                except Exception:
                    pass

                await page.goto(dashboard_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(800)
                await close_broadcast_overlay(page)
        except Exception as e:
            print(f"Primary error: {e}")
    else:
        print("No primary button found")

    # ── Secondary ─────────────────────────────────────────────────────────────
    print("\n--- Secondary CTA ---")
    await scroll_to_element(page, SELECTORS["tile_ad"], timeout=8000)
    await page.wait_for_timeout(400)

    secondary_btn = page.locator(SELECTORS["tile_ad_secondary_btn"])
    if await secondary_btn.count() > 0 and await secondary_btn.first.is_visible(timeout=5000):
        result["secondary_exists"] = True
        try:
            btn_text = await secondary_btn.first.inner_text()
            btn_href = await secondary_btn.first.get_attribute("href")
            result["secondary_btn_text"] = btn_text.strip()
            result["secondary_href"]     = btn_href
            print(f"Text : {btn_text.strip()!r}")
            print(f"Href : {btn_href}")

            if btn_href:
                await page.goto(btn_href, timeout=30000)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1000)

                result["secondary_destination_url"] = page.url
                valid, title = await is_valid_page(page)
                result["secondary_valid"] = valid
                result["secondary_title"] = title
                print(f"Dest  : {page.url}")
                print(f"Title : {title}")
                print(f"Valid : {'PASS' if valid else 'FAIL'}")

                ss_path = screenshot_dirs["secondary"] / f"{product_fn}_secondary_{timestamp}.png"
                try:
                    await page.screenshot(path=str(ss_path), full_page=False, timeout=10000)
                    result["secondary_screenshot"] = str(ss_path)
                except Exception:
                    pass

                await page.goto(dashboard_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(800)
                await close_broadcast_overlay(page)
        except Exception as e:
            print(f"Secondary error: {e}")
    else:
        print("No secondary button found")

    return result


# =============================================================================
# HTML report
# =============================================================================

def _row_html(r: dict, idx: int) -> str:
    p_status = "PASS" if r["primary_valid"]  else ("N/A" if not r["primary_href"]            else "FAIL")
    s_status = "PASS" if r["secondary_valid"] else ("N/A" if not r["secondary_exists"]        else "FAIL")
    p_cls    = {"PASS": "pass", "FAIL": "fail", "N/A": "na"}[p_status]
    s_cls    = {"PASS": "pass", "FAIL": "fail", "N/A": "na"}[s_status]

    def ss_link(path):
        if not path:
            return "—"
        return f'<a href="{esc(str(Path(path)))}" target="_blank">screenshot</a>'

    return f"""
    <tr>
      <td class="num">{idx}</td>
      <td><strong>{esc(r['product'])}</strong></td>
      <td class="url"><a href="{esc(r['primary_href'] or '')}" target="_blank">{esc(r['primary_href'] or '—')}</a></td>
      <td class="url"><a href="{esc(r['primary_destination_url'] or '')}" target="_blank">{esc(r['primary_destination_url'] or '—')}</a></td>
      <td>{esc(r['primary_title'] or '—')}</td>
      <td><span class="pill {p_cls}">{p_status}</span></td>
      <td>{ss_link(r.get('primary_screenshot'))}</td>
      <td class="url"><a href="{esc(r['secondary_href'] or '')}" target="_blank">{esc(r['secondary_href'] or '—')}</a></td>
      <td class="url"><a href="{esc(r['secondary_destination_url'] or '')}" target="_blank">{esc(r['secondary_destination_url'] or '—')}</a></td>
      <td>{esc(r['secondary_title'] or '—')}</td>
      <td><span class="pill {s_cls}">{s_status}</span></td>
      <td>{ss_link(r.get('secondary_screenshot'))}</td>
    </tr>"""


def build_html_report(results: list, timestamp: str) -> str:
    pass_count = sum(
        (1 if r["primary_valid"] else 0) + (1 if r["secondary_valid"] else 0)
        for r in results
    )
    fail_count = sum(
        (1 if r["primary_href"] and not r["primary_valid"] else 0) +
        (1 if r["secondary_exists"] and r["secondary_href"] and not r["secondary_valid"] else 0)
        for r in results
    )
    total = pass_count + fail_count
    rows  = "".join(_row_html(r, i + 1) for i, r in enumerate(results))
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Statewide OLB CTA Links Report — STG</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;background:#f5f7fa;color:#333}}
header{{background:#2d6a4f;color:#fff;padding:20px 32px}}
header h1{{font-size:1.3rem;margin-bottom:4px}}
header p{{font-size:.8rem;opacity:.8}}
.env-badge{{display:inline-block;background:#52b788;color:#fff;border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;margin-left:10px;letter-spacing:.06em}}
.stats{{display:flex;gap:12px;padding:14px 32px;background:#fff;border-bottom:1px solid #dde;flex-wrap:wrap}}
.stat{{background:#f0f4ff;border:1px solid #d0d8f0;border-radius:7px;padding:10px 18px;text-align:center;min-width:100px}}
.stat .val{{font-size:24px;font-weight:700}}
.stat .lbl{{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#666;margin-top:3px}}
.stat.green .val{{color:#1a7a3c}} .stat.red .val{{color:#c0392b}} .stat.blue .val{{color:#1a3c6e}}
main{{padding:20px 32px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dde;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
th{{background:#f0f2f8;padding:8px 8px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#555;border-bottom:2px solid #dde;text-align:left;white-space:nowrap}}
td{{padding:6px 8px;border-bottom:1px solid #eef;vertical-align:middle}}
.num{{text-align:right;width:30px;color:#aaa;font-size:11px}}
.url{{font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pill{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700}}
.pill.pass{{background:#d4f5e2;color:#1a7a3c}}
.pill.fail{{background:#fde0de;color:#c0392b}}
.pill.na{{background:#f0f2f8;color:#888}}
</style>
</head>
<body>
<header>
  <h1>Statewide OLB — Card Ad CTA Links Report <span class="env-badge">STG</span></h1>
  <p>Generated: {now} &nbsp;|&nbsp; Environment: {BASE_URL} &nbsp;|&nbsp; Links navigated directly (no click) to avoid analytics</p>
</header>
<div class="stats">
  <div class="stat blue"><div class="val">{len(results)}</div><div class="lbl">Products Tested</div></div>
  <div class="stat blue"><div class="val">{total}</div><div class="lbl">Links Checked</div></div>
  <div class="stat green"><div class="val">{pass_count}</div><div class="lbl">Pass</div></div>
  <div class="stat {'red' if fail_count else 'blue'}"><div class="val">{fail_count}</div><div class="lbl">Fail</div></div>
</div>
<main>
<table>
  <thead><tr>
    <th class="num">#</th>
    <th>Product</th>
    <th>Primary Href</th>
    <th>Primary Dest URL</th>
    <th>Primary Title</th>
    <th>Primary</th>
    <th>Screenshot</th>
    <th>Secondary Href</th>
    <th>Secondary Dest URL</th>
    <th>Secondary Title</th>
    <th>Secondary</th>
    <th>Screenshot</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</main>
</body>
</html>"""


# =============================================================================
# Pytest entry point
# =============================================================================

@pytest.mark.asyncio
async def test_statewide_olb_card_ad_go_to_cta_links_github_actions_STG():
    """
    CI version: validates card ad CTA link URLs on the Statewide OLB STAGING dashboard.
    Runs headless; credentials come from environment variables (with STG defaults built in).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dirs = setup_screenshot_dirs()
    results = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        try:
            login_ok = await perform_login(page)
            assert login_ok, (
                f"Login failed — check credentials for {BASE_URL} "
                f"(user: {USERNAME})"
            )

            print(f"\n[CI] Navigating to dashboard: {DASHBOARD_URL}")
            await page.goto(DASHBOARD_URL, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            await close_broadcast_overlay(page)

            for i in range(1, 3):
                print(f"[CI] Dashboard refresh {i}/2")
                await page.reload()
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(2000)
                await close_broadcast_overlay(page)

            await set_browser_zoom(page, 0.8)

            result = await test_card_ad_cta_links(page, screenshot_dirs, timestamp)
            results.append(result)

            visited = {result["product"]}

            for product in CORE_PRODUCTS:
                if product in visited:
                    continue

                encoded = urllib.parse.quote(product)
                product_url = (
                    f"{DASHBOARD_URL}?products_recommended={encoded}"
                    f"&cb=1&session_init=1&debug_all=1"
                )
                print(f"\n[CI] Loading card ad for: {product}")
                await page.goto(product_url, timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                await page.wait_for_timeout(2000)
                await close_broadcast_overlay(page)

                for i in range(1, 3):
                    print(f"[CI] Refresh {i}/2 for {product}")
                    await page.reload()
                    await page.wait_for_load_state("networkidle", timeout=60000)
                    await page.wait_for_timeout(2000)
                    await close_broadcast_overlay(page)

                await set_browser_zoom(page, 0.8)

                tile_ad = page.locator(SELECTORS["tile_ad"])
                if await tile_ad.count() == 0:
                    print(f"[CI] No card ad found for {product} — skipping")
                    continue

                result = await test_card_ad_cta_links(page, screenshot_dirs, timestamp, product)
                results.append(result)
                visited.add(product)
                await page.wait_for_timeout(800)

        except Exception as e:
            try:
                err_path = SCREENSHOT_ROOT / f"error_{timestamp}.png"
                await page.screenshot(path=str(err_path), full_page=False, timeout=5000)
                print(f"[CI] Error screenshot: {err_path}")
            except Exception:
                pass
            raise
        finally:
            await context.close()
            await browser.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    pass_count = sum(
        (1 if r["primary_valid"] else 0) + (1 if r["secondary_valid"] else 0)
        for r in results
    )
    fail_count = sum(
        (1 if r["primary_href"] and not r["primary_valid"] else 0) +
        (1 if r["secondary_exists"] and r["secondary_href"] and not r["secondary_valid"] else 0)
        for r in results
    )

    print(f"\n{'='*80}")
    print("TEST SUMMARY — STAGING (CI)")
    print(f"{'='*80}")
    print(f"Environment     : {BASE_URL}")
    print(f"Products tested : {len(results)}")
    print(f"Links checked   : {pass_count + fail_count}")
    print(f"PASS            : {pass_count}")
    print(f"FAIL            : {fail_count}")

    for r in results:
        p = "PASS" if r["primary_valid"]  else ("N/A" if not r["primary_href"]  else "FAIL")
        s = "PASS" if r["secondary_valid"] else ("N/A" if not r["secondary_exists"] else "FAIL")
        print(f"  {r['product']:25s}  primary={p}  secondary={s}")

    html = build_html_report(results, timestamp)
    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"\n[CI] HTML report saved: {REPORT_PATH}")

    assert fail_count == 0, (
        f"{fail_count} CTA link(s) failed validation — see {REPORT_PATH} for details"
    )
