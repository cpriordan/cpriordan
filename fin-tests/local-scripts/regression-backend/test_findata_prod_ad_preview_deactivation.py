#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
test_findata_prod_ad_preview_deactivation.py
────────────────────────────────────────────
Opens a headed browser at https://finalyticsdata.com/, waits for you to log in
manually (credentials + 2FA), then navigates to /qa/ad-expiration/, reads every
row in the "Full Results" section, and validates the deactivation Reason:

  1) AdCopy inactive          → checks /admin/app/adcopy/.../change/ is_active = False
  2) Ad expired (end_dt)      → checks that the end date column value is in the past
  3) All campaigns inactive   → checks every campaign linked to the ad is_active = False

Generates: test_ad_expiration_PROD.html  (in the script's directory)
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext, Page,
    TimeoutError as PWTimeout,
    async_playwright,
)

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_BASE  = "https://finalyticsdata.com"
THIS_DIR    = Path(__file__).resolve().parent
REPORT_PATH = THIS_DIR / "test_ad_expiration_PROD.html"
LOGIN_TIMEOUT_MS = 300_000   # 5 min for manual login

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def abs_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return ADMIN_BASE + ("" if path.startswith("/") else "/") + path


def parse_date(text: str) -> Optional[datetime]:
    """Parse 'Jan. 8, 2024' or 'Jan 8 2024' from reason text."""
    m = re.search(r"(\w+)\.?\s+(\d{1,2}),?\s+(\d{4})", text)
    if m:
        month = MONTH_MAP.get(m.group(1).lower()[:3])
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(2)))
            except ValueError:
                pass
    return None


async def safe_new_page(context: BrowserContext, url: str) -> Page:
    p = await context.new_page()
    await p.goto(url, timeout=30_000)
    await p.wait_for_load_state("networkidle", timeout=20_000)
    return p


def _icon_active(alt: str, src: str) -> Optional[bool]:
    """Return True/False/None from a Django admin icon img."""
    alt_l, src_l = alt.lower(), src.lower()
    if alt_l in ("true", "yes") or "icon-yes" in src_l:
        return True
    if alt_l in ("false", "no") or "icon-no" in src_l:
        return False
    return None


async def read_is_active_change_page(page: Page) -> Optional[bool]:
    """
    Read the is_active value from a Django admin *change* page.
    Returns True if active, False if inactive, None if not found.
    """
    # 1) Editable checkbox
    cb = page.locator("#id_is_active")
    if await cb.count():
        return await cb.is_checked()

    # 2) Read-only field with icon img
    field = page.locator(".field-is_active")
    if await field.count():
        imgs = await field.locator("img").all()
        for img in imgs:
            result = _icon_active(
                (await img.get_attribute("alt")) or "",
                (await img.get_attribute("src")) or "",
            )
            if result is not None:
                return result
        txt = (await field.inner_text()).strip()
        if "✓" in txt or txt.lower() in ("yes", "true"):
            return True
        if "✗" in txt or txt.lower() in ("no", "false"):
            return False

    return None


async def read_is_active_list_row(row) -> Optional[bool]:
    """Read is_active from a Django admin *list* page row."""
    imgs = await row.locator("img").all()
    for img in imgs:
        result = _icon_active(
            (await img.get_attribute("alt")) or "",
            (await img.get_attribute("src")) or "",
        )
        if result is not None:
            return result
    # Some themes render text inside a boolean field cell
    cells = await row.locator("td").all()
    for cell in cells:
        txt = (await cell.inner_text()).strip()
        if txt in ("✓", "Yes", "True"):
            return True
        if txt in ("✗", "No", "False", "×"):
            return False
    return None


# ── Validation functions ───────────────────────────────────────────────────────

async def validate_adcopy_inactive(
    context: BrowserContext, ad_url: str
) -> Tuple[bool, str]:
    """Validate that the AdCopy linked to this ad has is_active = False."""
    page = await safe_new_page(context, ad_url)
    adcopy_url = None

    try:
        # Expand "Copy/Template/HTML" section if collapsed
        for toggle_text in ["Copy/Template/HTML", "Ad Copy", "Template"]:
            t = page.locator(f"text={toggle_text}").first
            if await t.count():
                try:
                    await t.click()
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
                break

        # Find the eye icon at #view_id_ad_copy > img:nth-child(1)
        eye = page.locator("#view_id_ad_copy > img:nth-child(1)")
        if not await eye.count():
            # Broader fallback
            eye = page.locator("[id*='view'][id*='ad_copy'] img").first

        if not await eye.count():
            return False, "Eye icon not found on ad page"

        # Try to get adcopy URL without clicking
        # 1) parent anchor
        parent_a = page.locator("#view_id_ad_copy a")
        if await parent_a.count():
            adcopy_url = await parent_a.first.get_attribute("href")

        # 2) onclick attribute of the img
        if not adcopy_url:
            onclick = (await eye.get_attribute("onclick")) or ""
            m = re.search(r"'([^']*adcopy[^']*)'", onclick, re.I)
            if m:
                adcopy_url = m.group(1)

        # 3) data- attribute
        if not adcopy_url:
            for attr in ("data-href", "data-url", "href"):
                v = await eye.get_attribute(attr)
                if v and "adcopy" in v.lower():
                    adcopy_url = v
                    break

        # 4) Click and capture new tab / navigation
        if not adcopy_url:
            prev_url = page.url
            try:
                async with context.expect_page(timeout=5_000) as pinfo:
                    await eye.click()
                new_tab = await pinfo.value
                await new_tab.wait_for_load_state("domcontentloaded", timeout=10_000)
                adcopy_url = new_tab.url
                await new_tab.close()
            except PWTimeout:
                await page.wait_for_load_state("domcontentloaded", timeout=10_000)
                if page.url != prev_url:
                    adcopy_url = page.url

        if not adcopy_url:
            return False, "Could not determine adcopy URL from eye icon"

        adcopy_url = abs_url(adcopy_url)
        adcopy_page = await safe_new_page(context, adcopy_url)
        try:
            is_active = await read_is_active_change_page(adcopy_page)
            if is_active is None:
                return False, f"is_active field not found on adcopy page ({adcopy_url})"
            if not is_active:
                return True, f"AdCopy is_active = False ✓  ({adcopy_url})"
            else:
                return False, f"AdCopy is_active = True ✗ (should be False)  ({adcopy_url})"
        finally:
            await adcopy_page.close()

    except Exception as e:
        return False, f"Error: {str(e)[:200]}"
    finally:
        await page.close()


async def validate_end_date_passed(reason: str, end_date: str = "") -> Tuple[bool, str]:
    """Validate that the end date (from the end_date column, or the reason text) is in the past."""
    # Prefer the dedicated end_date column value; fall back to parsing from reason text
    dt = parse_date(end_date) if end_date else None
    source = f"end date column ({end_date!r})" if end_date else ""
    if dt is None:
        dt = parse_date(reason)
        source = f"reason text ({reason!r})"
    if dt is None:
        return False, f"Could not parse date from end date column ({end_date!r}) or reason: {reason!r}"
    now = datetime.now()
    if dt < now:
        return True, f"End date {dt.strftime('%Y-%m-%d')} is in the past [from {source}]"
    return False, f"End date {dt.strftime('%Y-%m-%d')} is NOT yet in the past [from {source}]"


async def validate_campaigns_inactive(
    context: BrowserContext, ad_url: str
) -> Tuple[bool, str]:
    """
    For each campaign in #id_campaigns_to, navigate to its admin change page
    and confirm is_active = False.
    """
    page = await safe_new_page(context, ad_url)
    try:
        # Collect all campaign options from the "selected" list
        opts = await page.locator("#id_campaigns_to > option").all()
        if not opts:
            # Try the "from" (available) list as fallback
            opts = await page.locator("#id_campaigns_from > option").all()

        if not opts:
            return False, "No campaign options found on ad page"

        campaigns = []
        for opt in opts:
            name  = (await opt.inner_text()).strip()
            value = (await opt.get_attribute("value") or "").strip()
            if name or value:
                campaigns.append({"name": name, "id": value})

        print(f"  → Found {len(campaigns)} campaign(s): {[c['name'] for c in campaigns]}")

        results = []
        for camp in campaigns:
            camp_id   = camp["id"]
            camp_name = camp["name"]

            if not camp_id.isdigit():
                # Try searching via company admin approach
                result = await _search_campaign_on_admin(context, camp_name)
                results.append((camp_name, result))
                continue

            camp_url = f"{ADMIN_BASE}/admin/app/campaign/{camp_id}/change/"
            camp_page = await safe_new_page(context, camp_url)
            try:
                is_active = await read_is_active_change_page(camp_page)
            finally:
                await camp_page.close()

            if is_active is None:
                # Fall back to list search
                is_active_search = await _search_campaign_on_admin(context, camp_name)
                results.append((camp_name, is_active_search))
            else:
                results.append((camp_name, is_active))

        # All must be inactive (False)
        inactive = [(n, v) for n, v in results if v is False]
        active   = [(n, v) for n, v in results if v is True]
        unknown  = [(n, v) for n, v in results if v is None]

        details = "; ".join(
            f"'{n}' inactive ✓" for n, _ in inactive
        ) + (
            "  |  " + "; ".join(f"'{n}' ACTIVE ✗" for n, _ in active) if active else ""
        ) + (
            "  |  " + "; ".join(f"'{n}' unknown" for n, _ in unknown) if unknown else ""
        )

        if active:
            return False, f"Some campaigns still active: {details}"
        if unknown and not inactive:
            return False, f"Could not determine status: {details}"
        return True, f"All campaigns inactive ✓  {details}"

    except Exception as e:
        return False, f"Error: {str(e)[:200]}"
    finally:
        await page.close()


async def _search_campaign_on_admin(
    context: BrowserContext, campaign_name: str
) -> Optional[bool]:
    """
    Go to finalyticsdata.com main admin, find the matching company row, click
    Campaigns, search for the campaign, and read the Is Active icon.
    Returns True/False/None.
    """
    # Extract search key: first two words of campaign name
    words = campaign_name.split()
    search_key = " ".join(words[:2]).lower() if len(words) >= 2 else campaign_name.lower()

    main_page = await safe_new_page(context, ADMIN_BASE)
    try:
        # Find a "Campaigns" link whose row context matches our campaign name prefix
        camp_links = main_page.locator("a[href*='campaign']")
        cnt = await camp_links.count()

        campaigns_url = None
        for i in range(cnt):
            lnk  = camp_links.nth(i)
            href = (await lnk.get_attribute("href")) or ""
            # Skip non-company-specific links (e.g. top nav)
            if "company__id" not in href and "cu_id" not in href:
                continue
            # Check surrounding row text
            row_text = ""
            try:
                row = lnk.locator("xpath=ancestor::tr").first
                if await row.count():
                    row_text = (await row.inner_text()).lower()
            except Exception:
                pass
            if search_key[:6] in row_text or words[0].lower() in row_text:
                campaigns_url = abs_url(href)
                break

        if not campaigns_url:
            print(f"  → Could not find company row for campaign '{campaign_name}'")
            return None

        # Navigate to campaigns list and search
        list_page = await safe_new_page(context, campaigns_url)
        try:
            searchbar = list_page.locator("#searchbar")
            if await searchbar.count():
                await searchbar.fill(campaign_name)
                await list_page.keyboard.press("Enter")
                await list_page.wait_for_load_state("networkidle", timeout=15_000)

            rows = list_page.locator("#result_list tbody tr")
            row_cnt = await rows.count()
            for j in range(row_cnt):
                row_el   = rows.nth(j)
                row_text = (await row_el.inner_text()).lower()
                if campaign_name.lower()[:20] in row_text:
                    is_active = await read_is_active_list_row(row_el)
                    return is_active
            return None
        finally:
            await list_page.close()
    finally:
        await main_page.close()


# ── Page parser ───────────────────────────────────────────────────────────────

async def parse_full_results(page: Page) -> List[Dict]:
    """
    Parse every row in the Full Results section of /qa/ad-expiration/.
    Reads column headers first to locate the correct Ad Name and Reason columns.
    Returns list of dicts with keys: ad_name, ad_url, reason, end_date.
    """
    await page.wait_for_load_state("networkidle", timeout=30_000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(1)

    # ── Locate the correct table ──────────────────────────────────────────────
    # We want the DETAILED table (one row per ad), not the summary table.
    # Strategy: pick the table with the most <tbody tr> rows.
    table = None
    best_count = 0
    all_tables = await page.locator("table").all()
    for t_candidate in all_tables:
        cnt = await t_candidate.locator("tbody tr").count()
        if cnt == 0:
            cnt = await t_candidate.locator("tr").count() - 1  # subtract header row
        if cnt > best_count:
            best_count = cnt
            table = t_candidate

    print(f"Selected table has {best_count} rows.")

    if not table:
        print("WARNING: No table found on ad-expiration page.")
        await page.screenshot(path=str(THIS_DIR / "debug_expiration_page.png"))
        print(f"Screenshot saved: {THIS_DIR / 'debug_expiration_page.png'}")
        return []

    # ── Identify columns by header text, or by scanning first data rows ──────
    header_texts = [h.strip().lower() for h in await table.locator("th").all_inner_texts()]
    print(f"Table headers: {header_texts}")

    REASON_KEYWORDS = ["adcopy", "ad copy", "expired", "campaign", "end_dt", "inactive"]

    def header_col(keywords: List[str]) -> int:
        for kw in keywords:
            for j, h in enumerate(header_texts):
                if kw in h:
                    return j
        return -1

    ad_name_col_hint  = header_col(["ad name", "ad", "name"])
    reason_col_hint   = header_col(["reason", "deactivat", "status"])
    end_date_col_hint = header_col(["end date", "end_date", "end dt", "end_dt"])

    # Probe first few rows to detect the ad-link column and reason column
    probe_rows = await table.locator("tbody tr").all()
    probe_rows = probe_rows[:min(5, len(probe_rows))]

    ad_name_col  = ad_name_col_hint  if ad_name_col_hint  >= 0 else -1
    reason_col   = reason_col_hint   if reason_col_hint   >= 0 else -1
    end_date_col = end_date_col_hint if end_date_col_hint >= 0 else -1

    for prow in probe_rows:
        pcells = await prow.locator("td").all()
        for ci, pc in enumerate(pcells):
            txt = (await pc.inner_text()).strip().lower()
            href_text = ""
            lnk = pc.locator("a").first
            if await lnk.count():
                href_text = (await lnk.get_attribute("href")) or ""

            # Ad-link column: has a link to /app/ad/
            if ad_name_col < 0 and "/app/ad/" in href_text:
                ad_name_col = ci

            # Reason column: cell text contains a known reason keyword
            if reason_col < 0 and any(k in txt for k in REASON_KEYWORDS):
                reason_col = ci

        if ad_name_col >= 0 and reason_col >= 0:
            break

    if ad_name_col < 0:
        ad_name_col = 0
    if reason_col < 0:
        reason_col = max(1, len(header_texts) - 1) if header_texts else 1

    print(f"Using col {ad_name_col} for Ad Name, col {reason_col} for Reason, col {end_date_col} for End Date.")

    # ── Parse rows ────────────────────────────────────────────────────────────
    rows = table.locator("tbody tr")
    row_count = await rows.count()
    if row_count == 0:
        # Some tables don't use <tbody>
        rows = table.locator("tr:not(:first-child)")
        row_count = await rows.count()

    print(f"Full Results table: {row_count} data rows found.")

    ads = []
    for i in range(row_count):
        row   = rows.nth(i)
        cells = await row.locator("td").all()
        if not cells:
            continue

        # --- Ad Name + URL ---
        ad_name = ad_url = ""
        name_cell = cells[ad_name_col] if ad_name_col < len(cells) else cells[0]
        lnk = name_cell.locator("a").first
        if await lnk.count():
            ad_name = (await lnk.inner_text()).strip()
            href    = (await lnk.get_attribute("href")) or ""
            ad_url  = abs_url(href)
        else:
            # Try any cell with a link to /admin/app/ad/
            for cell in cells:
                lnk2 = cell.locator("a[href*='/app/ad/']").first
                if await lnk2.count():
                    ad_name = (await lnk2.inner_text()).strip()
                    href    = (await lnk2.get_attribute("href")) or ""
                    ad_url  = abs_url(href)
                    break
        if not ad_name:
            ad_name = (await cells[0].inner_text()).strip()

        # --- Reason ---
        reason = ""
        if reason_col < len(cells):
            reason = (await cells[reason_col].inner_text()).strip()
        if not reason:
            # Scan all cells for known reason keywords
            for cell in cells:
                txt = (await cell.inner_text()).strip()
                txt_l = txt.lower()
                if any(k in txt_l for k in ["adcopy", "ad copy", "expired", "campaign", "end_dt"]):
                    reason = txt
                    break

        # --- End Date ---
        end_date = ""
        if end_date_col >= 0 and end_date_col < len(cells):
            end_date = (await cells[end_date_col].inner_text()).strip()

        if not ad_name:
            continue

        ads.append({"ad_name": ad_name, "ad_url": ad_url, "reason": reason, "end_date": end_date})

    return ads


# ── HTML report ───────────────────────────────────────────────────────────────

def build_report(results: List[Dict]) -> str:
    total       = len(results)
    validated   = sum(1 for r in results if r.get("validated"))
    not_val     = total - validated
    now_str     = datetime.now().strftime("%Y-%m-%d %H:%M")

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    rows_html = ""
    for i, r in enumerate(results, 1):
        ok      = r.get("validated", False)
        pill    = (
            '<span class="pill ok">Validated</span>'
            if ok else
            '<span class="pill fail">Not Validated</span>'
        )
        ad_cell = (
            f'<a href="{esc(r["ad_url"])}" target="_blank">{esc(r["ad_name"])}</a>'
            if r.get("ad_url") else esc(r.get("ad_name", ""))
        )
        detail_html = f'<br><small class="detail">{esc(r.get("detail",""))}</small>'
        rows_html += f"""
        <tr class="{'ok' if ok else 'fail'}">
          <td class="num">{i}</td>
          <td>{ad_cell}</td>
          <td class="reason">{esc(r.get('reason',''))}</td>
          <td>{pill}{detail_html}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ad Expiration Validation Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
        font-size:13px;background:#f5f7fa;color:#333}}
  header{{background:#1a3c6e;color:#fff;padding:20px 32px}}
  header h1{{font-size:1.3rem}}
  header p{{font-size:.8rem;opacity:.8;margin-top:4px}}
  .stats{{display:flex;gap:14px;padding:14px 32px;background:#fff;
          border-bottom:1px solid #dde;flex-wrap:wrap}}
  .stat{{background:#f0f4ff;border:1px solid #d0d8f0;border-radius:7px;
         padding:10px 18px;text-align:center;min-width:100px}}
  .stat .val{{font-size:22px;font-weight:700}}
  .stat .lbl{{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:#666}}
  .stat.green .val{{color:#1a7a3c}}
  .stat.red   .val{{color:#c0392b}}
  .stat.blue  .val{{color:#1a3c6e}}
  main{{padding:20px 32px}}
  table{{width:100%;border-collapse:collapse;background:#fff;
         border:1px solid #dde;border-radius:8px;overflow:hidden}}
  th{{background:#f0f2f8;padding:8px 10px;font-size:11px;
      text-transform:uppercase;letter-spacing:.04em;color:#555;
      border-bottom:2px solid #dde;text-align:left}}
  td{{padding:8px 10px;border-bottom:1px solid #eef;vertical-align:top}}
  tr.ok td{{background:#f8fff9}}
  tr.fail td{{background:#fff8f8}}
  .num{{text-align:right;width:40px}}
  .reason{{font-size:12px;color:#555;max-width:320px}}
  .pill{{display:inline-block;padding:2px 10px;border-radius:10px;
         font-size:11px;font-weight:700}}
  .pill.ok  {{background:#d4f5e2;color:#1a7a3c}}
  .pill.fail{{background:#fde0de;color:#c0392b}}
  .detail{{color:#888;font-size:11px;line-height:1.4}}
  a{{color:#1a3c6e}}
</style>
</head>
<body>
<header>
  <h1>Ad Expiration — Deactivation Reason Validation</h1>
  <p>Generated: {now_str} &nbsp;|&nbsp; Source: {ADMIN_BASE}/qa/ad-expiration/</p>
</header>
<div class="stats">
  <div class="stat blue"><div class="val">{total}</div><div class="lbl">Total Ads</div></div>
  <div class="stat green"><div class="val">{validated}</div><div class="lbl">Validated</div></div>
  <div class="stat {'red' if not_val else 'blue'}">
    <div class="val">{not_val}</div><div class="lbl">Not Validated</div></div>
</div>
<main>
  <table>
    <thead><tr>
      <th class="num">#</th>
      <th>Ad Name</th>
      <th>Reason</th>
      <th>Validation Result</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</main>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    results: List[Dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--start-maximized", "--remote-debugging-port=9222"],
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page    = await context.new_page()

        # ── 1. Navigate and wait for manual login ──────────────────────────────
        print(f"\nOpening {ADMIN_BASE} …")
        await page.goto(ADMIN_BASE, timeout=30_000)

        print("\n" + "=" * 60)
        print("  Please log in manually (username, password, 2FA).")
        print("  Waiting up to 5 minutes for successful login …")
        print("=" * 60 + "\n")

        try:
            await page.wait_for_function(
                """() => {
                    const u = window.location.href;
                    return !u.includes('/login') &&
                           !u.includes('/accounts/') &&
                           (document.querySelector('table') !== null ||
                            document.querySelector('#content')  !== null ||
                            document.querySelector('.module')   !== null);
                }""",
                timeout=LOGIN_TIMEOUT_MS,
            )
            print("Login detected.\n")
        except PWTimeout:
            print("Login timeout — proceeding anyway.\n")

        # ── 2. Navigate to ad-expiration page ─────────────────────────────────
        target = f"{ADMIN_BASE}/qa/ad-expiration/"
        print(f"Navigating to {target} …")
        await page.goto(target, timeout=30_000)

        # ── 3. Parse Full Results ──────────────────────────────────────────────
        ads = await parse_full_results(page)
        if not ads:
            print("No ads found. Exiting.")
            await browser.close()
            return

        print(f"\nFound {len(ads)} ads to validate.\n")

        # ── 4. Validate each ad ────────────────────────────────────────────────
        for idx, ad in enumerate(ads, 1):
            name   = ad["ad_name"]
            reason = ad["reason"]
            url    = ad["ad_url"]

            print(f"[{idx}/{len(ads)}] {name!r}")
            print(f"       Reason : {reason!r}")

            reason_l = reason.lower()

            if "adcopy inactive" in reason_l or "ad copy inactive" in reason_l:
                validated, detail = await validate_adcopy_inactive(context, url)

            elif "end_dt" in reason_l or "ad expired" in reason_l:
                validated, detail = await validate_end_date_passed(reason, ad.get("end_date", ""))

            elif "campaigns inactive" in reason_l or "all campaign" in reason_l:
                validated, detail = await validate_campaigns_inactive(context, url)

            else:
                validated = False
                detail    = f"Unrecognised reason type — skipped"

            status = "✓ VALIDATED" if validated else "✗ NOT VALIDATED"
            print(f"       Result  : {status} — {detail}\n")

            results.append({
                "ad_name":   name,
                "ad_url":    url,
                "reason":    reason,
                "validated": validated,
                "detail":    detail,
            })

        await browser.close()

    # ── 5. Write report ────────────────────────────────────────────────────────
    html = build_report(results)
    REPORT_PATH.write_text(html, encoding="utf-8")
    val = sum(1 for r in results if r.get("validated"))
    print("=" * 60)
    print(f"Report saved : {REPORT_PATH}")
    print(f"Results      : {val} validated, {len(results) - val} not validated / {len(results)} total")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
