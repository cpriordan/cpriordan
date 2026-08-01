#!/usr/bin/env python3
"""
Run all UI regression tests marked with @pytest.mark.regression against STG.

Discovers every test file under fin-ui-tests/ and runs only the tests
decorated with @pytest.mark.regression.  Generates a timestamped pytest
HTML report and a combined report with inline failure screenshots.

Usage:
    python run_ui_regression_tests_stg.py                  # all regression tests
    python run_ui_regression_tests_stg.py --client gocu    # one client only
    python run_ui_regression_tests_stg.py --headed         # show browser window
    python run_ui_regression_tests_stg.py --report-dir ./my_reports
    python run_ui_regression_tests_stg.py --verbose
"""

import argparse
import base64
import glob
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR  = BASE_DIR
PYTEST_CMD = [sys.executable, "-m", "pytest"]
ENV        = "stg"

SCREENSHOT_DIRS = [
    "fin-ui-tests/screenshots_listerhill",
    "screenshots_esfcu_using_pytest",
    "screenshots_gocu_using_pytest",
    "screenshots_glbl_using_pytest",
    "screenshots_u1st_using_pytest",
    "screenshots_tru_using_pytest",
    "screenshots_ssscu_using_pytest",
    "screenshots_oneaz_using_pytest",
    "screenshots_swfcu_using_pytest",
    "screenshots_ad_expiration_by_time_using_pytest",
    "screenshots_ad_expiration_by_views_using_pytest",
    "screenshots_ad_expiration_by_aggressive_expiration_by_time_using_pytest",
]


def collect_test_files(client_filter=None):
    pattern = os.path.join(TESTS_DIR, "test_*.py")
    files = sorted(glob.glob(pattern))
    if client_filter:
        files = [f for f in files if client_filter.lower() in os.path.basename(f).lower()]
    return files


def _img_to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


def _find_screenshots_for_client(client_keyword: str) -> list:
    matches = []
    for rel_dir in SCREENSHOT_DIRS:
        abs_dir = os.path.join(BASE_DIR, rel_dir)
        if not os.path.isdir(abs_dir):
            continue
        for f in sorted(Path(abs_dir).glob("*.png")):
            if client_keyword.lower() in f.name.lower():
                matches.append(str(f))
    return matches


def _client_keyword_from_test_name(test_name: str) -> str:
    name = test_name.lower()
    for kw in ["gocu", "swfcu", "tru", "u1st", "ssscu", "oneaz", "glbl", "global",
               "esfcu", "listerhill", "mma", "expiration"]:
        if kw in name:
            return kw
    return name.split("[")[0].split("_")[2] if name.count("_") >= 2 else name


def generate_combined_report(junit_xml: str, output_html: str) -> None:
    try:
        tree = ET.parse(junit_xml)
        root = tree.getroot()
    except Exception as e:
        print(f"  [warn] Could not parse JUnit XML: {e}")
        return

    testcases = root.findall(".//testcase")
    passed = failed = skipped = 0
    rows_html = []

    for tc in testcases:
        name      = tc.get("name", "")
        classname = tc.get("classname", "")
        time_s    = tc.get("time", "")

        failure_el = tc.find("failure")
        error_el   = tc.find("error")
        skipped_el = tc.find("skipped")

        if failure_el is not None or error_el is not None:
            status    = "FAIL"
            detail_el = failure_el if failure_el is not None else error_el
            detail    = (detail_el.get("message", "") + "\n" + (detail_el.text or "")).strip()
            failed   += 1
        elif skipped_el is not None:
            status  = "SKIP"
            detail  = skipped_el.get("message", "")
            skipped += 1
        else:
            status  = "PASS"
            detail  = ""
            passed += 1

        status_color = {"PASS": "#1a7a1a", "FAIL": "#b00020", "SKIP": "#888"}.get(status, "#333")
        status_bg    = {"PASS": "#f0fff0", "FAIL": "#fff0f0", "SKIP": "#fafafa"}.get(status, "#fff")

        detail_html = ""
        if detail:
            escaped = detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            detail_html = f'<pre style="margin:6px 0 0;font-size:12px;white-space:pre-wrap;color:#555">{escaped}</pre>'

        screenshots_html = ""
        if status == "FAIL":
            kw    = _client_keyword_from_test_name(name + " " + classname)
            shots = _find_screenshots_for_client(kw)
            if shots:
                imgs = []
                for shot in shots[:6]:
                    try:
                        uri   = _img_to_data_uri(shot)
                        fname = os.path.basename(shot)
                        imgs.append(
                            f'<div style="display:inline-block;margin:4px;vertical-align:top">'
                            f'<div style="font-size:11px;color:#666;margin-bottom:2px">{fname}</div>'
                            f'<img src="{uri}" style="max-width:320px;max-height:220px;'
                            f'border:1px solid #ddd;border-radius:3px" />'
                            f'</div>'
                        )
                    except Exception:
                        pass
                if imgs:
                    screenshots_html = (
                        '<div style="margin-top:8px">'
                        '<div style="font-size:12px;font-weight:bold;color:#555;margin-bottom:4px">'
                        'Screenshots:</div>'
                        + "".join(imgs)
                        + '</div>'
                    )

        display_name = name.replace("[browser0]", "").strip()
        rows_html.append(f"""
        <tr style="background:{status_bg}">
          <td style="padding:8px 12px;font-weight:bold;color:{status_color};white-space:nowrap">{status}</td>
          <td style="padding:8px 12px">
            <div style="font-weight:bold">{display_name}</div>
            <div style="font-size:12px;color:#888">{classname}</div>
            {detail_html}
            {screenshots_html}
          </td>
          <td style="padding:8px 12px;white-space:nowrap;color:#888;font-size:12px">{time_s}s</td>
        </tr>""")

    total         = passed + failed + skipped
    now_str       = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_color = "#1a7a1a" if failed == 0 else "#b00020"
    summary_label = "ALL PASSED" if failed == 0 else f"{failed} FAILED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>UI Regression — STG — {now_str}</title>
<style>
  body  {{ font-family: system-ui, sans-serif; margin: 32px; color: #111; }}
  h1    {{ font-size: 22px; margin-bottom: 6px; }}
  .meta {{ font-size: 14px; color: #555; margin-bottom: 24px; }}
  .summary {{ font-size: 16px; font-weight: bold; margin-bottom: 20px; color: {summary_color}; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td    {{ border: 1px solid #e0e0e0; vertical-align: top; }}
  thead td {{ background: #f0f4f8; font-weight: bold; padding: 8px 12px; }}
</style>
</head>
<body>
<h1>UI Regression Tests — STG</h1>
<div class="meta">Generated: {now_str} &nbsp;|&nbsp; Marker: <code>@pytest.mark.regression</code></div>
<div class="summary">{summary_label} &nbsp;|&nbsp; {passed}/{total} passed
  {f'&nbsp;|&nbsp; {skipped} skipped' if skipped else ''}
</div>
<table>
  <thead>
    <tr>
      <td style="width:60px">Result</td>
      <td>Test</td>
      <td style="width:70px">Time</td>
    </tr>
  </thead>
  <tbody>
    {''.join(rows_html)}
  </tbody>
</table>
</body>
</html>"""

    Path(output_html).write_text(html, encoding="utf-8")
    print(f"  Combined report  : {output_html}")


def main():
    parser = argparse.ArgumentParser(
        description="Run all @pytest.mark.regression UI tests against STG"
    )
    parser.add_argument("--client", "-c", type=str, default=None,
                        help="Filter to a single client (e.g. gocu, u1st, esfcu)")
    parser.add_argument("--headed", action="store_true",
                        help="Run browser in headed mode")
    parser.add_argument("--report-dir", "-o", type=str,
                        default=os.path.join(BASE_DIR, "regression_reports"),
                        help="Directory for reports (default: ./regression_reports)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose pytest output")
    args = parser.parse_args()

    files = collect_test_files(args.client)
    if not files:
        print("No test_*.py files found" + (f" matching '{args.client}'" if args.client else ""))
        sys.exit(0)

    os.makedirs(args.report_dir, exist_ok=True)
    timestamp     = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    label         = args.client or "all"
    pytest_html   = os.path.join(args.report_dir, f"ui_regression_stg_{label}_{timestamp}.html")
    junit_xml     = os.path.join(args.report_dir, f"ui_regression_stg_{label}_{timestamp}.xml")
    combined_html = os.path.join(args.report_dir, f"ui_regression_stg_{label}_{timestamp}_combined.html")

    print("=" * 60)
    print(f"  UI Regression Tests — STG")
    print(f"  Marker  : @pytest.mark.regression")
    print(f"  Filter  : {label}")
    print(f"  {len(files)} file(s) scanned | {timestamp}")
    print("=" * 60)

    if not args.headed:
        os.environ.setdefault("HEADLESS", "true")

    cmd = PYTEST_CMD + files + [
        "-m", "regression",
        f"--env={ENV}",
        "-v" if args.verbose else "-q",
        "-s",
        "--tb=short",
        f"--html={pytest_html}",
        "--self-contained-html",
        f"--junitxml={junit_xml}",
        "-p", "no:warnings",
    ]

    result = subprocess.run(cmd, cwd=BASE_DIR)

    generate_combined_report(junit_xml, combined_html)

    print()
    print("=" * 60)
    print("  ALL REGRESSION TESTS PASSED" if result.returncode == 0 else "  SOME REGRESSION TESTS FAILED")
    print(f"  Pytest report    : {pytest_html}")
    print("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
