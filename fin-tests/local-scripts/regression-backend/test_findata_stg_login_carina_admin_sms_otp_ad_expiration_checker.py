from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import os


def check_ad_expiration():
    """Check ads on staging site for expiration status.

    1. Navigate to https://stgfinalyticsdata.com/qa/ad-expiration/
    2. Scroll to "Full Results" section
    3. Click each link in the "Ad Name" column of table.table-striped.table-hover
    4. On each ad detail page:
       - Read campaign name from #id_campaigns_to > option
       - Click "Start/End/Expire" collapse to reveal dates
       - Read end date from #id_end_dt_0
    5. Flag as NOT Expired or Expired and generate report
    """

    base_url = "https://stgfinalyticsdata.com/qa/ad-expiration/"
    current_date = datetime.now().date()

    # Store results
    ads_data = []

    with sync_playwright() as p:
        # Launch browser in non-headless mode so you can interact with it
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context()
        page = context.new_page()

        # Navigate to the ad expiration page
        print(f"Navigating to {base_url}")
        page.goto(base_url, timeout=60000)

        # Check if we need to login (if redirected to login page)
        current_url = page.url
        if "login" in current_url.lower() or page.locator('input[type="password"]').count() > 0:
            print("\n" + "=" * 60)
            print("LOGIN REQUIRED")
            print("=" * 60)
            print("Please complete the login process manually:")
            print("1. Enter your username and password")
            print("2. Wait for SMS OTP code on your phone")
            print("3. Enter the SMS code when prompted")
            print("4. Click submit/login")
            print("\nThe script will wait up to 5 minutes for you to complete login...")
            print("=" * 60 + "\n")

            # Wait for successful login (redirected away from login page)
            try:
                page.wait_for_url(
                    lambda url: "login" not in url.lower(), timeout=300000
                )
                print("Login successful! Continuing with ad checks...\n")
                time.sleep(2)

                # Navigate to ad expiration page after login
                page.goto(base_url, wait_until="networkidle")
                time.sleep(2)

            except Exception:
                print("\nLogin timeout or failed. Please try again.")
                browser.close()
                return
        else:
            print("Already logged in!\n")
            time.sleep(2)

        # -----------------------------------------------------------------
        # Collect ad links from the "Ad Name" column in the Full Results table
        # -----------------------------------------------------------------
        print("Waiting for Full Results table to load...")

        # Wait for the table to appear on the page
        try:
            page.wait_for_selector(
                "table.table-striped, table.table-hover", timeout=30000
            )
        except Exception:
            print("Table not found with class selectors, waiting for any table...")
            try:
                page.wait_for_selector("table", timeout=10000)
            except Exception:
                pass

        time.sleep(2)

        # Debug: report what tables exist on the page
        table_info = page.evaluate("""() => {
            const tables = document.querySelectorAll('table');
            return Array.from(tables).map((t, i) => ({
                index: i,
                className: t.className,
                rowCount: t.querySelectorAll('tr').length,
                hasLinks: t.querySelectorAll('a[href]').length
            }));
        }""")
        print(f"  Tables found on page: {len(table_info)}")
        for t in table_info:
            print(f"    Table {t['index']}: class='{t['className']}', "
                  f"rows={t['rowCount']}, links={t['hasLinks']}")

        # Scroll to the Full Results section
        page.evaluate("""() => {
            const headings = document.querySelectorAll('h1, h2, h3, h4, h5');
            for (const h of headings) {
                if (h.textContent.trim().includes('Full Results')) {
                    h.scrollIntoView({ block: 'start', behavior: 'instant' });
                    return true;
                }
            }
            return false;
        }""")
        time.sleep(1)

        # Extract all Ad Name links from the FIRST column of the Full Results table
        # The table has columns: Ad Name | Company | Reason | End Date | Campaigns
        # We need to find the specific table that has "Ad Name" as a header,
        # since there are multiple tables on the page with the same CSS classes.
        ad_entries = page.evaluate("""() => {
            // Find the table that has an "Ad Name" column header
            let table = null;
            let reasonColIndex = -1;
            const allTables = document.querySelectorAll('table');
            for (const t of allTables) {
                const headers = t.querySelectorAll('th');
                let headerIndex = 0;
                for (const th of headers) {
                    if (th.textContent.trim() === 'Ad Name') {
                        table = t;
                    }
                    if (th.textContent.trim() === 'Reason') {
                        reasonColIndex = headerIndex;
                    }
                    headerIndex++;
                }
                if (table) break;
            }

            if (!table) return [];

            // Get all rows (both tbody tr and direct tr), skip header rows
            const rows = table.querySelectorAll('tr');
            const results = [];
            for (const row of rows) {
                const firstTd = row.querySelector('td:first-child');
                if (!firstTd) continue;  // skip header rows (th only)
                const link = firstTd.querySelector('a[href]');
                if (!link) continue;
                const href = link.getAttribute('href');
                const text = link.textContent.trim();
                // Get the Reason column value
                const cells = row.querySelectorAll('td');
                let reason = '';
                if (reasonColIndex >= 0 && reasonColIndex < cells.length) {
                    reason = cells[reasonColIndex].textContent.trim();
                }
                if (href) {
                    results.push({ href: href, ad_name: text, reason: reason });
                }
            }
            return results;
        }""")

        # Debug: if no entries found, inspect the table structure
        if not ad_entries:
            debug_info = page.evaluate("""() => {
                const tables = document.querySelectorAll('table.table-striped.table-hover');
                const results = [];
                for (let t = 0; t < tables.length; t++) {
                    const table = tables[t];
                    // Get headers
                    const headers = Array.from(table.querySelectorAll('th'))
                        .map(th => th.textContent.trim());
                    // Get first 3 rows
                    const rows = table.querySelectorAll('tr');
                    const sampleRows = [];
                    for (let r = 0; r < Math.min(4, rows.length); r++) {
                        const cells = rows[r].querySelectorAll('td, th');
                        const cellData = Array.from(cells).map(c => ({
                            tag: c.tagName,
                            text: c.textContent.trim().substring(0, 60),
                            hasLink: c.querySelector('a') !== null,
                            linkHref: c.querySelector('a') ? c.querySelector('a').getAttribute('href') : null
                        }));
                        sampleRows.push(cellData);
                    }
                    results.push({ tableIndex: t, headers, sampleRows, totalRows: rows.length });
                }
                return results;
            }""")
            for tbl in debug_info:
                print(f"\n  DEBUG Table {tbl['tableIndex']} ({tbl['totalRows']} rows):")
                print(f"    Headers: {tbl['headers']}")
                for i, row in enumerate(tbl['sampleRows']):
                    print(f"    Row {i}: {row}")

        print(f"\nFound {len(ad_entries)} ad links in the Ad Name column\n")

        if not ad_entries:
            print("ERROR: No ad links found in the Full Results table!")
            print("Make sure the page loaded correctly and has a table.table-striped.table-hover")
            browser.close()
            return

        # Create screenshots directory
        screenshots_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ad_screenshots"
        )
        os.makedirs(screenshots_dir, exist_ok=True)

        for idx, entry in enumerate(ad_entries, 1):
            ad_url = entry["href"]
            ad_name = entry["ad_name"]
            ad_reason = entry.get("reason", "")

            print(f"Checking ad {idx}/{len(ad_entries)}: {ad_name}")
            print(f"  URL: {ad_url}")
            print(f"  Reason from table: {ad_reason or '(none)'}")

            # If the reason is "All campaigns inactive 30+ days", skip detailed check
            if ad_reason == "All campaigns inactive 30+ days":
                print(f"  >> Skipping detailed check - reason: {ad_reason}")
                print(f"  Status: In-active campaigns (should be de-activated/expired)")

                if not ad_url.startswith("http"):
                    ad_url = f"https://stgfinalyticsdata.com{ad_url}"

                ads_data.append({
                    "ad_number": idx,
                    "ad_name": ad_name,
                    "ad_url": ad_url,
                    "campaign_name": "",
                    "is_test_campaign": False,
                    "end_date": "",
                    "is_expired": True,
                    "status": "In-active campaigns",
                    "screenshot": "",
                    "adcopy_is_active": None,
                    "adcopy_url": "",
                    "expiration_reasons": ["All campaigns inactive 30+ days"],
                    "adcopy_screenshot": "",
                    "reason_from_table": ad_reason,
                })
                print()
                continue

            try:
                # Build full URL if relative
                if not ad_url.startswith("http"):
                    ad_url = f"https://stgfinalyticsdata.com{ad_url}"

                page.goto(ad_url, wait_until="networkidle", timeout=30000)
                time.sleep(1)

                # Get campaign name from the "Chosen campaigns" box (#id_campaigns_to)
                campaign_name = ""
                try:
                    campaigns_select = page.locator("#id_campaigns_to")
                    if campaigns_select.count() > 0:
                        # Get all options in the chosen campaigns select
                        options = page.locator("#id_campaigns_to > option").all()
                        campaign_names = []
                        for opt in options:
                            text = opt.inner_text().strip()
                            if text:
                                campaign_names.append(text)
                        campaign_name = ", ".join(campaign_names)
                except Exception as e:
                    print(f"  Could not find campaign name: {e}")

                # Check if this is a "test campaign only" scenario:
                # Only true when there is exactly 1 chosen campaign and it contains "test"
                # If there are multiple campaigns and at least one is NOT a test campaign,
                # then it's NOT a test-only campaign (it has a real production campaign too)
                is_test_campaign_only = (
                    len(campaign_names) == 1
                    and "test" in campaign_names[0].lower()
                ) if campaign_names else False

                # Click "Start/End/Expire" collapse menu to reveal end date
                collapse_clicked = False
                try:
                    # The collapse header is inside a dark gray fieldset area
                    # It shows as a clickable text like "Start/End/Expire"
                    # with a triangle indicator (collapsed = right arrow, expanded = down arrow)
                    collapse = page.locator("fieldset :text('Start/End/Expire')").first
                    if collapse.is_visible(timeout=3000):
                        collapse.click()
                        collapse_clicked = True
                        time.sleep(1)
                except Exception:
                    pass

                if not collapse_clicked:
                    # Try alternative selectors
                    for selector in [
                        "text=Start/End/Expire",
                        "a:has-text('Start/End/Expire')",
                        "h2:has-text('Start/End/Expire')",
                        "h3:has-text('Start/End/Expire')",
                        "summary:has-text('Start/End/Expire')",
                    ]:
                        try:
                            el = page.locator(selector).first
                            if el.is_visible(timeout=1000):
                                el.click()
                                collapse_clicked = True
                                time.sleep(1)
                                break
                        except Exception:
                            continue

                if not collapse_clicked:
                    # JS fallback: find the element containing "Start/End/Expire" and click it
                    try:
                        page.evaluate("""() => {
                            const allElements = document.querySelectorAll('a, h2, h3, h4, summary, div, span');
                            for (const el of allElements) {
                                if (el.textContent.trim() === 'Start/End/Expire'
                                    || el.textContent.trim() === '\\u25b6 Start/End/Expire'
                                    || el.textContent.trim() === '\\u25bc Start/End/Expire') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        time.sleep(1)
                        collapse_clicked = True
                    except Exception:
                        pass

                if not collapse_clicked:
                    print("  Warning: Could not click Start/End/Expire collapse menu")

                # Get end date from #id_end_dt_0
                end_date_str = ""
                is_expired = False
                try:
                    end_date_input = page.locator("#id_end_dt_0")
                    # Wait for it to become visible after the collapse opens
                    end_date_input.wait_for(state="visible", timeout=5000)
                    end_date_str = end_date_input.input_value().strip()

                    if end_date_str:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                        is_expired = end_date < current_date
                        print(f"  End date: {end_date_str}, Expired: {is_expired}")
                    else:
                        print("  End date field is empty (no end date set)")
                except Exception as e:
                    print(f"  Could not get end date: {e}")

                # Take screenshot of ad page before navigating away
                screenshot_filename = f"ad_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"  Screenshot: {screenshot_filename}")

                # --- Check adcopy "Is active" status ---
                adcopy_is_active = None
                adcopy_url = ""
                adcopy_screenshot_filename = ""
                try:
                    # Get the adcopy link from the collapsed "Ad copy" section
                    adcopy_link = page.locator("#view_id_ad_copy")
                    if adcopy_link.count() > 0:
                        adcopy_href = adcopy_link.get_attribute("href")
                        if adcopy_href:
                            if not adcopy_href.startswith("http"):
                                adcopy_url = f"https://stgfinalyticsdata.com{adcopy_href}"
                            else:
                                adcopy_url = adcopy_href
                            print(f"  Adcopy URL: {adcopy_url}")

                            # Navigate to the adcopy page
                            page.goto(adcopy_url, wait_until="networkidle", timeout=30000)
                            time.sleep(1)

                            # Check #id_is_active checkbox
                            is_active_checkbox = page.locator("#id_is_active")
                            if is_active_checkbox.count() > 0:
                                adcopy_is_active = is_active_checkbox.is_checked()
                                print(f"  Adcopy Is Active: {adcopy_is_active}")
                            else:
                                print("  Warning: #id_is_active checkbox not found on adcopy page")

                            # Take adcopy page screenshot
                            adcopy_screenshot_filename = f"adcopy_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            adcopy_screenshot_path = os.path.join(screenshots_dir, adcopy_screenshot_filename)
                            page.screenshot(path=adcopy_screenshot_path, full_page=True)
                            print(f"  Adcopy Screenshot: {adcopy_screenshot_filename}")
                        else:
                            print("  No href on adcopy link")
                    else:
                        print("  No adcopy link (#view_id_ad_copy) found")
                except Exception as e:
                    print(f"  Could not check adcopy active status: {e}")

                # Determine status:
                # Expired (CAN DE-ACTIVATE) if: end date is in the past OR adcopy is inactive
                adcopy_inactive = adcopy_is_active is False  # False specifically, not None
                date_expired = is_expired
                status = "Expired" if (date_expired or adcopy_inactive) else "NOT Expired"

                # Build expiration reasons list
                expiration_reasons = []
                if date_expired:
                    expiration_reasons.append("End date has passed")
                if is_test_campaign_only:
                    expiration_reasons.append("Test campaign only")
                if adcopy_inactive:
                    expiration_reasons.append("Adcopy is inactive")

                print(f"  Campaign: {campaign_name or '(none)'}")
                print(f"  Is Test Campaign Only: {is_test_campaign_only}")
                print(f"  End Date: {end_date_str or '(empty)'}")
                print(f"  Status: {status}")
                if expiration_reasons:
                    print(f"  Reasons: {', '.join(expiration_reasons)}")

                # Store ad data
                ads_data.append({
                    "ad_number": idx,
                    "ad_name": ad_name,
                    "ad_url": ad_url,
                    "campaign_name": campaign_name,
                    "is_test_campaign_only": is_test_campaign_only,
                    "end_date": end_date_str,
                    "is_expired": is_expired,
                    "status": status,
                    "screenshot": screenshot_filename,
                    "adcopy_is_active": adcopy_is_active,
                    "adcopy_url": adcopy_url,
                    "expiration_reasons": expiration_reasons,
                    "adcopy_screenshot": adcopy_screenshot_filename,
                })

                print()

            except Exception as e:
                print(f"  Error checking ad: {e}\n")
                ads_data.append({
                    "ad_number": idx,
                    "ad_name": ad_name,
                    "ad_url": ad_url,
                    "campaign_name": "ERROR",
                    "is_test_campaign_only": False,
                    "end_date": "",
                    "is_expired": False,
                    "status": "Error",
                    "screenshot": "",
                    "adcopy_is_active": None,
                    "adcopy_url": "",
                    "expiration_reasons": [],
                    "adcopy_screenshot": "",
                    "error": str(e),
                })

        browser.close()

    # Generate HTML report
    report_path = generate_html_report(ads_data, screenshots_dir)
    print(f"\nReport generated: {report_path}")
    print(f"Screenshots saved in: {screenshots_dir}")


def generate_html_report(ads_data, screenshots_dir):
    """Generate HTML report of ad expiration check results."""

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count statistics
    total_ads = len(ads_data)
    not_expired_ads = [ad for ad in ads_data if ad.get("status") == "NOT Expired"]
    expired_ads = [ad for ad in ads_data if ad.get("status") == "Expired"]
    inactive_campaign_ads = [ad for ad in ads_data if ad.get("status") == "In-active campaigns"]
    can_deactivate_ads = [ad for ad in ads_data if ad.get("status") in ("Expired", "In-active campaigns")]
    test_campaign_only_ads = [ad for ad in ads_data if ad.get("is_test_campaign_only")]
    error_ads = [ad for ad in ads_data if ad.get("status") == "Error"]
    adcopy_inactive_ads = [ad for ad in ads_data if ad.get("adcopy_is_active") is False]

    # Build table rows
    table_rows = ""
    for ad in ads_data:
        # Status badge
        status = ad.get("status", "Unknown")
        if status == "NOT Expired":
            badge = '<span class="badge badge-dont-deactivate">DON\'T DE-ACTIVATE</span>'
        elif status == "Expired":
            badge = '<span class="badge badge-deactivate">CAN DE-ACTIVATE</span>'
        elif status == "In-active campaigns":
            badge = ('<span class="badge badge-inactive-campaigns">IN-ACTIVE CAMPAIGNS</span>'
                     ' <span class="badge badge-deactivate">CAN DE-ACTIVATE</span>')
        else:
            badge = '<span class="badge badge-info">ERROR</span>'

        # Extra badges
        extra = ""
        if ad.get("is_test_campaign_only"):
            extra += ' <span class="badge badge-warning">TEST CAMPAIGN ONLY</span>'
        if not ad.get("end_date"):
            extra += ' <span class="badge badge-muted">NO END DATE</span>'
        if ad.get("adcopy_is_active") is False:
            extra += ' <span class="badge badge-adcopy-inactive">ADCOPY INACTIVE</span>'

        # Adcopy active status cell
        adcopy_active_val = ad.get("adcopy_is_active")
        if adcopy_active_val is True:
            adcopy_cell = '<span class="badge badge-success">Active</span>'
        elif adcopy_active_val is False:
            adcopy_cell = '<span class="badge badge-adcopy-inactive">Inactive</span>'
        else:
            adcopy_cell = '<span class="badge badge-muted">Unknown</span>'

        # Expiration reasons cell
        reasons = ad.get("expiration_reasons", [])
        reasons_cell = "<br>".join(reasons) if reasons else "--"

        # Screenshot thumbnail
        screenshot_cell = ""
        if ad.get("screenshot"):
            screenshot_cell = (
                f'<a href="ad_screenshots/{ad["screenshot"]}" target="_blank">'
                f'<img src="ad_screenshots/{ad["screenshot"]}" class="thumb" '
                f'title="Click to view full size"></a>'
            )
        # Adcopy screenshot thumbnail
        if ad.get("adcopy_screenshot"):
            screenshot_cell += (
                f' <a href="ad_screenshots/{ad["adcopy_screenshot"]}" target="_blank">'
                f'<img src="ad_screenshots/{ad["adcopy_screenshot"]}" class="thumb" '
                f'title="Adcopy page - click to view full size"></a>'
            )

        campaign_display = ad.get("campaign_name") or "(none)"
        end_date_display = ad.get("end_date") or "--"

        adcopy_inactive_str = "True" if ad.get("adcopy_is_active") is False else "False"
        data_attrs = (
            f'data-status="{status}" '
            f'data-test-only="{ad.get("is_test_campaign_only", False)}" '
            f'data-expired="{ad.get("is_expired", False)}" '
            f'data-adcopy-inactive="{adcopy_inactive_str}"'
        )

        row_class = "row-expired" if status in ("Expired", "In-active campaigns") else ""

        table_rows += f"""
            <tr class="{row_class}" {data_attrs}>
                <td>{ad["ad_number"]}</td>
                <td><strong>{ad.get("ad_name", "")}</strong></td>
                <td>{campaign_display}</td>
                <td>{badge}{extra}</td>
                <td>{end_date_display}</td>
                <td>{adcopy_cell}</td>
                <td>{reasons_cell}</td>
                <td>{screenshot_cell}</td>
                <td><a href="{ad["ad_url"]}" target="_blank" class="link">Open</a></td>
            </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ad Expiration Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header p {{ margin: 4px 0; opacity: 0.9; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-card h3 {{
            margin: 0 0 8px 0;
            color: #666;
            font-size: 13px;
            text-transform: uppercase;
        }}
        .stat-card .number {{
            font-size: 32px;
            font-weight: bold;
        }}
        .color-total {{ color: #333; }}
        .color-not-expired {{ color: #ef4444; }}
        .color-expired {{ color: #10b981; }}
        .color-test {{ color: #f59e0b; }}
        .color-error {{ color: #6b7280; }}
        .color-adcopy-inactive {{ color: #ea580c; }}
        .color-inactive-campaigns {{ color: #b91c1c; }}

        .filter-section {{
            background: white;
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filter-btn {{
            padding: 8px 16px;
            margin-right: 8px;
            margin-bottom: 4px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
        }}
        .filter-btn.active {{
            background: #667eea;
            color: white;
        }}

        table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: top;
        }}
        tr:hover {{ background-color: #f9fafb; }}
        .row-expired {{ background-color: #fef2f2; }}
        .row-expired:hover {{ background-color: #fee2e2; }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-info {{ background: #dbeafe; color: #1e40af; }}
        .badge-muted {{ background: #f3f4f6; color: #6b7280; }}
        .badge-adcopy-inactive {{ background: #fed7aa; color: #9a3412; }}
        .badge-inactive-campaigns {{ background: #fecaca; color: #7f1d1d; }}
        .badge-deactivate {{ background: #d1fae5; color: #065f46; }}
        .badge-dont-deactivate {{ background: #fee2e2; color: #991b1b; font-weight: 800; }}

        .link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{ text-decoration: underline; }}

        .thumb {{
            max-width: 120px;
            max-height: 80px;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        }}
        .thumb:hover {{
            border-color: #667eea;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Ad Expiration Check Report</h1>
        <p>Generated: {current_time}</p>
        <p>Source: <a href="https://stgfinalyticsdata.com/qa/ad-expiration/"
           style="color: white;">https://stgfinalyticsdata.com/qa/ad-expiration/</a></p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>Total Ads</h3>
            <div class="number color-total">{total_ads}</div>
        </div>
        <div class="stat-card">
            <h3>Don't De-activate</h3>
            <div class="number color-not-expired">{len(not_expired_ads)}</div>
        </div>
        <div class="stat-card">
            <h3>Can De-activate</h3>
            <div class="number color-expired">{len(can_deactivate_ads)}</div>
        </div>
        <div class="stat-card">
            <h3>Test Campaign Only</h3>
            <div class="number color-test">{len(test_campaign_only_ads)}</div>
        </div>
        <div class="stat-card">
            <h3>In-active Campaigns</h3>
            <div class="number color-inactive-campaigns">{len(inactive_campaign_ads)}</div>
        </div>
        <div class="stat-card">
            <h3>Adcopy Inactive</h3>
            <div class="number color-adcopy-inactive">{len(adcopy_inactive_ads)}</div>
        </div>
        <div class="stat-card">
            <h3>Errors</h3>
            <div class="number color-error">{len(error_ads)}</div>
        </div>
    </div>

    <div class="filter-section">
        <strong>Filter:</strong>
        <button class="filter-btn active" onclick="filterTable('all')">All ({total_ads})</button>
        <button class="filter-btn" onclick="filterTable('not-expired')">Don't De-activate ({len(not_expired_ads)})</button>
        <button class="filter-btn" onclick="filterTable('can-deactivate')">Can De-activate ({len(can_deactivate_ads)})</button>
        <button class="filter-btn" onclick="filterTable('test-only')">Test Campaign Only ({len(test_campaign_only_ads)})</button>
        <button class="filter-btn" onclick="filterTable('inactive-campaigns')">In-active Campaigns ({len(inactive_campaign_ads)})</button>
        <button class="filter-btn" onclick="filterTable('adcopy-inactive')">Adcopy Inactive ({len(adcopy_inactive_ads)})</button>
    </div>

    <table id="adsTable">
        <thead>
            <tr>
                <th>#</th>
                <th>Ad Name</th>
                <th>Campaign</th>
                <th>Status</th>
                <th>End Date</th>
                <th>Adcopy Active</th>
                <th>Reasons</th>
                <th>Screenshots</th>
                <th>Link</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>

    <script>
        function filterTable(filter) {{
            const rows = document.querySelectorAll('#adsTable tbody tr');
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            rows.forEach(row => {{
                const status = row.getAttribute('data-status');
                const isTestOnly = row.getAttribute('data-test-only') === 'True';
                const isAdcopyInactive = row.getAttribute('data-adcopy-inactive') === 'True';
                let show = false;
                if (filter === 'all') show = true;
                else if (filter === 'not-expired') show = status === 'NOT Expired';
                else if (filter === 'can-deactivate') show = status === 'Expired' || status === 'In-active campaigns';
                else if (filter === 'inactive-campaigns') show = status === 'In-active campaigns';
                else if (filter === 'test-only') show = isTestOnly;
                else if (filter === 'adcopy-inactive') show = isAdcopyInactive;
                row.style.display = show ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_ad_expiration_report.html"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return report_path


if __name__ == "__main__":
    print("=" * 60)
    print("Ad Expiration Checker")
    print("=" * 60)
    print()
    check_ad_expiration()
