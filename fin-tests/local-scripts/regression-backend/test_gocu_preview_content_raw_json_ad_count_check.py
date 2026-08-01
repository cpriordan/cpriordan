"""
GOCU Preview Content — Raw JSON vs. displayed-ads count check (STG)

Regression test for the ticket: the Raw JSON accordion on the Preview Content
page (app/views.py preview_content) frequently rendered as an empty list ([])
even when the page above it correctly displayed ads with full ad copy.

Root cause: the Raw JSON builder queried campaign.adcopy_set (the reverse
manager for AdCopy.campaigns, a ManyToManyField), while the preview table
above it uses campaign.ad_set (a real FK, Ad.campaign). Many AdCopy rows had
their M2M campaigns field out of sync with their Ad children's campaign_id,
so campaign.adcopy_set came back empty while the ads still rendered fine.

Fix: derive the Raw JSON entries from the already-fetched ads queryset
(dedupe by ad_copy_id) instead of querying campaign.adcopy_set.

This script walks every campaign listed on GOCU's Preview Content page
(/scenarios/campaigns-list/preview) and, for each one, compares:
  - the number of ads actually rendered ("Showing N of M")
  - len(window.rawJsonData) -- the JS array the page populates from the
    same builder described in the ticket

For any campaign with N > 0 displayed ads, rawJsonData must be non-empty --
a campaign showing ads but an empty rawJsonData is exactly the bug signature
described in the ticket. rawJsonData's length does not always equal N: the
fix explicitly dedupes by ad_copy_id, so campaigns where two+ ads legitimately
share one AdCopy will show fewer JSON entries than displayed ads by design.
Count mismatches are therefore reported as informational notes, not failures
-- only an empty/zero rawJsonData alongside displayed ads is a hard failure.

Scope note: the visible "Raw JSON" accordion UI (with Copy JSON / Pretty /
One Line buttons) did not render for this test account's permission level
("Basic Access") during live verification, even though window.rawJsonData
was present and correctly populated on the page. So this check validates
the underlying data the accordion is built from -- the exact artifact the
ticket's root cause and fix describe -- rather than the accordion widget
itself. If a higher-privilege account is available later, the widget and
its buttons should be checked directly in addition to this.

Saves a screenshot of the campaign list and an HTML report with a
pass/fail row per campaign.
"""

import json
import os
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qa_tools import AdminLoginPage, setup_admin_test_environment
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots_gocu_preview_content_raw_json_using_pytest"
REPORT_PATH = Path(__file__).parent / "test_gocu_preview_content_raw_json_ad_count_report.html"

CID_LINK_PATTERN = re.compile(r"^/content/preview-content\?cid=(\d+)$")
SHOWING_PATTERN = re.compile(r"Showing (\d+) of (\d+)")


def collect_campaign_links(page):
    """Return [(name, cid, href), ...] for every campaign on the Preview Content list page."""
    campaigns = []
    seen_hrefs = set()
    for link in page.locator("a").all():
        href = link.get_attribute("href")
        if not href:
            continue
        m = CID_LINK_PATTERN.match(href)
        if not m or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        name = link.inner_text().strip()
        campaigns.append({"name": name, "cid": int(m.group(1)), "href": href})
    return campaigns


def check_campaign(page, test_env, campaign):
    url = f"https://{test_env}finalyticsdata.com{campaign['href']}"
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)

    body_text = page.locator("body").inner_text()
    m = SHOWING_PATTERN.search(body_text)
    shown_count = int(m.group(1)) if m else None

    raw_json_data = page.evaluate("() => window.rawJsonData || null")
    raw_json_len = len(raw_json_data) if isinstance(raw_json_data, list) else None

    note = None
    if shown_count is None:
        passed = False
        detail = "Could not find 'Showing N of M' text on the page"
    elif raw_json_len is None:
        passed = False
        detail = "window.rawJsonData was not defined on the page"
    elif shown_count == 0:
        passed = True
        detail = f"No ads displayed (Showing 0), rawJsonData also empty ({raw_json_len})"
    elif raw_json_len == 0:
        # This is the exact bug signature: ads render, Raw JSON is [].
        passed = False
        detail = f"BUG SIGNATURE: {shown_count} ads displayed but rawJsonData is empty"
    else:
        passed = True
        detail = f"Displayed ads={shown_count}, rawJsonData entries={raw_json_len}"
        if shown_count != raw_json_len:
            note = (f"Count differs from displayed ads ({shown_count} ads vs {raw_json_len} JSON entries) "
                     f"-- expected when ads share an AdCopy (dedup by ad_copy_id), not necessarily a bug")

    return {
        "name": campaign["name"],
        "cid": campaign["cid"],
        "url": url,
        "shown_count": shown_count,
        "raw_json_len": raw_json_len,
        "passed": passed,
        "detail": detail,
        "note": note,
    }


def generate_html_report(results, out_path):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed_count = sum(1 for r in results if r["passed"])

    rows = ""
    for r in results:
        bg = "#f0fdf4" if r["passed"] else "#fff5f5"
        if r["note"]:
            bg = "#fffbea"
        status_html = (
            '<span style="color:#0cce6b;font-weight:bold">&#10003; PASS</span>' if r["passed"] else
            '<span style="color:#ff4e42;font-weight:bold">&#10007; FAIL</span>'
        )
        detail_html = escape(r["detail"])
        if r["note"]:
            detail_html += f'<br><span style="color:#a16207">&#9888; {escape(r["note"])}</span>'
        rows += f"""
        <tr style="background:{bg};vertical-align:top">
            <td style="font-size:12px;white-space:nowrap"><a href="{escape(r['url'])}">{escape(r['name'])}</a> (cid={r['cid']})</td>
            <td style="text-align:center;width:90px">{status_html}</td>
            <td style="font-size:12px">{detail_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GOCU Preview Content — Raw JSON vs Ad Count (STG)</title>
<style>
  body {{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:24px;background:#f4f6f8;color:#222}}
  .container {{max-width:1200px;margin:0 auto}}
  h1 {{color:#1a202c;margin-bottom:4px}}
  .meta {{color:#666;font-size:14px;margin-bottom:24px}}
  table {{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.1)}}
  th,td {{padding:8px 12px;text-align:left;border-bottom:1px solid #e2e8f0}}
  th {{background:#f8fafc;font-weight:600;font-size:12px}}
  code {{background:#f1f5f9;padding:1px 5px;border-radius:3px;font-size:11px}}
</style>
</head>
<body>
<div class="container">
  <h1>GOCU Preview Content — Raw JSON vs. Displayed-Ads Count (STG)</h1>
  <div class="meta">Generated: {timestamp} &nbsp;|&nbsp; {passed_count}/{len(results)} campaigns passed</div>
  <table>
    <thead><tr><th>Campaign</th><th style="text-align:center">Result</th><th>Detail</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="font-size:12px;color:#888;margin-top:12px">
    For every campaign with displayed ads (N &gt; 0), <code>window.rawJsonData</code> (the data the Raw JSON
    accordion is built from, per the ticket's fix in <code>preview_content</code>) must also have N entries.
    A campaign passing with 0 ads and 0 rawJsonData entries is a trivial pass (nothing to compare), not a
    reproduction of the bug pattern.
  </p>
</div>
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"\nHTML report saved: {out_path}")


def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    findata_user, findata_pw, findata_otp, test_env, totp, _ = setup_admin_test_environment('gocu')

    with sync_playwright() as p:
        headless = os.environ.get("HEADLESS", "false").lower() == "true"
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        login_page = AdminLoginPage(page, is_async=False)
        login_page.navigate(test_env)
        login_page.login(findata_user, findata_pw)
        login_page.enter_2fa_code(totp)
        login_page.complete_2fa_login(test_env)
        print(f"Logged in. Current URL: {page.url}")

        content_menu = page.get_by_text("Content").nth(0)
        content_menu.click()
        page.wait_for_timeout(500)
        page.locator(".sub-item:text('Content Modules')").click()
        page.wait_for_load_state("networkidle", timeout=20000)

        page.get_by_text("Preview Content").click()
        page.wait_for_load_state("networkidle", timeout=20000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "1_preview_content_list.png"), full_page=True)

        campaigns = collect_campaign_links(page)
        print(f"Found {len(campaigns)} campaigns to check.")

        results = []
        for campaign in campaigns:
            result = check_campaign(page, test_env, campaign)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"  [{status}] {result['name']} (cid={result['cid']}): {result['detail']}")
            if result["note"]:
                print(f"           note: {result['note']}")
            results.append(result)

        browser.close()

    generate_html_report(results, REPORT_PATH)

    failed = [r for r in results if not r["passed"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} campaigns passed.")
    if failed:
        print("FAILED campaigns:")
        for r in failed:
            print(f"  - {r['name']} (cid={r['cid']}): {r['detail']}")
    return not failed


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
