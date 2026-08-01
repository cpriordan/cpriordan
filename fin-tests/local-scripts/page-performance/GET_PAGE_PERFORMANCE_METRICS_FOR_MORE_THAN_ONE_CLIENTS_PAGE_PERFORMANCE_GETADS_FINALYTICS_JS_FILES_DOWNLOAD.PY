import csv
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import os
import json
import time
from urllib.parse import urlparse
import statistics

# ========== CONFIGURATION: Number of iterations ==========
NUM_ITERATIONS = 10
# Clients that often hit font-download stalls: capture as PDF by default
PDF_FIRST_CLIENTS = {"tru", "gocu"}
# ========== END CONFIGURATION ==========

# --- constants for key assets we want to track ---
KEY_ASSET_LABELS = {
    "settings_div.js": "settings_div.js",
    "finalytics.js": "finalytics.js",
    "finalytics-function_div.css": "finalytics-function_div.css",
    "finalytics.css": "finalytics.css",
}


def validate_and_sanitize_url(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return url


def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def login_if_redirected(page, username, password):
    login_url = "/util/Login"

    if login_url in page.url:
        print(f"Redirected to login page with page.url {page.url}. Attempting to log in.")

        try:
            page.wait_for_selector("#UserName", timeout=10000)
            page.wait_for_selector("#Password", timeout=10000)
            page.wait_for_selector("#Submit", timeout=10000)
        except Exception as e:
            print(f"Error: Required login fields are not available. {e}")
            return

        page.fill("#UserName", username)
        page.fill("#Password", password)
        page.click("#Submit")
        page.wait_for_load_state("domcontentloaded", timeout=30000)

        if not (login_url in page.url):
            print("Logged in successfully.")
        else:
            print("Login attempt failed. Still on the login page.")
    else:
        print(f"page.url {page.url} does NOT equal login_url {login_url} so skip login_if_redirected function")


def detect_js_errors_from_specific_files(page, specific_files):
    def handle_console_message(msg):
        if msg.type == 'error':
            location = msg.location
            file_name = location['url'].split('/')[-1]
            if file_name in specific_files:
                print(f"JS Error found in {file_name}: {msg.text}")

    page.on('console', handle_console_message)


# --- helper to build empty asset record ---
def _empty_asset_record():
    return {
        "url": "",
        "duration": 0.0,           # ms
        "transferSize": 0,         # bytes (fallbacks applied)
        "encodedBodySize": 0,      # bytes
        "decodedBodySize": 0,      # bytes
        "startTime": 0.0,          # ms
        "responseEnd": 0.0,        # ms
        "initiatorType": "",
        "fromCache": False,
        "found": False,
    }


def get_web_vitals_and_key_assets(page):
    """Extract Web Vitals, perf metrics, and key asset timings/sizes from the page.

    Also returns a dict keyed by asset label with timing/size info for:
      - finalytics-function_div.css
      - settings_div.js
      - finalytics.js
    """

    install_observer_script = """
    () => {
        if (!window.__lcpValue) {
            window.__lcpValue = 0;
            window.__clsValue = 0;

            try {
                const lcpObserver = new PerformanceObserver((entryList) => {
                    const entries = entryList.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    window.__lcpValue = lastEntry.startTime;
                });
                lcpObserver.observe({type: 'largest-contentful-paint', buffered: true});
            } catch (e) {
                console.log('LCP observer error:', e);
            }

            try {
                const clsObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        if (!entry.hadRecentInput) {
                            window.__clsValue += entry.value;
                        }
                    }
                });
                clsObserver.observe({type: 'layout-shift', buffered: true});
            } catch (e) {
                console.log('CLS observer error:', e);
            }
        }
    }
    """

    try:
        page.evaluate(install_observer_script)
        print("Performance observers installed")
    except Exception as e:
        print(f"Error installing performance observers: {e}")

    web_vitals_and_assets_script = f"""
    () => {{
        const perfData = performance.getEntriesByType('navigation')[0];
        const paintEntries = performance.getEntriesByType('paint');
        const resources = performance.getEntriesByType('resource');

        const metrics = {{
            navigationStart: perfData ? perfData.startTime : 0,
            domContentLoaded: perfData ? perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart : 0,
            loadComplete: perfData ? perfData.loadEventEnd - perfData.loadEventStart : 0,
            firstPaint: 0,
            firstContentfulPaint: 0,
            totalResources: resources.length,
            totalTransferSize: 0,
            domNodes: document.getElementsByTagName('*').length,
            domInteractive: perfData ? perfData.domInteractive : 0,
            domComplete: perfData ? perfData.domComplete : 0,
            loadEventEnd: perfData ? perfData.loadEventEnd : 0,
            largestContentfulPaint: 0,
            cumulativeLayoutShift: 0,
        }};

        paintEntries.forEach(entry => {{
            if (entry.name === 'first-paint') {{
                metrics.firstPaint = entry.startTime;
            }} else if (entry.name === 'first-contentful-paint') {{
                metrics.firstContentfulPaint = entry.startTime;
            }}
        }});

        metrics.totalTransferSize = resources.reduce((total, resource) => {{
            return total + (resource.transferSize || 0);
        }}, 0);

        if (window.__lcpValue > 0) {{
            metrics.largestContentfulPaint = window.__lcpValue;
        }} else {{
            try {{
                const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
                if (lcpEntries && lcpEntries.length > 0) {{
                    metrics.largestContentfulPaint = lcpEntries[lcpEntries.length - 1].startTime;
                }}
            }} catch (e) {{
                console.log('LCP fallback error:', e);
            }}
        }}

        if (window.__clsValue > 0) {{
            metrics.cumulativeLayoutShift = window.__clsValue;
        }} else {{
            try {{
                let clsValue = 0;
                const clsEntries = performance.getEntriesByType('layout-shift');
                if (clsEntries && clsEntries.length > 0) {{
                    clsEntries.forEach(entry => {{
                        if (!entry.hadRecentInput) {{
                            clsValue += entry.value;
                        }}
                    }});
                    metrics.cumulativeLayoutShift = clsValue;
                }}
            }} catch (e) {{
                console.log('CLS fallback error:', e);
            }}
        }}

        function isCacheHit(r) {{
            // Heuristic: transferSize===0 with encodedBodySize>0 or duration===0 suggests cache
            return (r.transferSize === 0) && ((r.encodedBodySize || 0) > 0 || r.duration === 0);
        }}

        function pick(name) {{
            const match = resources.find(r => r.name.includes(name));
            if (!match) return null;
            return {{
                url: match.name,
                duration: match.duration, // ms
                transferSize: match.transferSize || match.encodedBodySize || 0, // bytes
                encodedBodySize: match.encodedBodySize || 0,
                decodedBodySize: match.decodedBodySize || 0,
                startTime: match.startTime,
                responseEnd: match.responseEnd,
                initiatorType: match.initiatorType || '',
                fromCache: isCacheHit(match)
            }};
        }}

        const keyAssets = {{
            'finalytics-function_div.css': pick('finalytics-function_div.css'),
            'settings_div.js': pick('settings_div.js'),
            'finalytics.js': pick('finalytics.js'),
        }};

        return {{ metrics, keyAssets }};
    }}
    """

    try:
        result = page.evaluate(web_vitals_and_assets_script)
        metrics = result.get("metrics", {})
        key_assets = result.get("keyAssets", {})

        # normalize so each key exists with a uniform structure
        normalized = {}
        for k in KEY_ASSET_LABELS.keys():
            v = key_assets.get(k)
            if v:
                v["found"] = True
                normalized[k] = v
            else:
                normalized[k] = _empty_asset_record()
        metrics["keyAssets"] = normalized
        return metrics
    except Exception as e:
        print(f"Error extracting performance metrics & key assets: {e}")
        return None


def capture_getads_timing(page):
    """Capture the response time for the 'getads' network call"""

    getads_script = """
    () => {
        const resources = performance.getEntriesByType('resource');

        const getadsCall = resources.find(resource => 
            resource.name.includes('getads') || 
            resource.name.includes('getAds') ||
            resource.name.includes('GetAds')
        );

        if (getadsCall) {
            return {
                duration: getadsCall.duration,
                responseTime: getadsCall.responseEnd - getadsCall.requestStart,
                transferSize: getadsCall.transferSize || 0,
                url: getadsCall.name
            };
        }

        return null;
    }
    """

    try:
        getads_timing = page.evaluate(getads_script)
        if getads_timing:
            print(f"GetAds call found: {getads_timing['duration']:.0f} ms")
            return getads_timing
        else:
            print("GetAds call not found in performance entries")
            return None
    except Exception as e:
        print(f"Error capturing getads timing: {e}")
        return None


def calculate_aggregate_metrics(all_metrics):
    """Calculate average, min, max, and median for all metrics, including key assets.
       Also computes cache hit rates and first-vs-subsequent comparisons.
    """

    getads_times = [m.get('getadsResponseTime', 0) for m in all_metrics if m.get('getadsResponseTime', 0) > 0]

    aggregate = {
        'iterations': len(all_metrics),
        'avgFirstContentfulPaint': statistics.mean([m.get('firstContentfulPaint', 0) for m in all_metrics]),
        'minFirstContentfulPaint': min([m.get('firstContentfulPaint', 0) for m in all_metrics]),
        'maxFirstContentfulPaint': max([m.get('firstContentfulPaint', 0) for m in all_metrics]),
        'medianFirstContentfulPaint': statistics.median([m.get('firstContentfulPaint', 0) for m in all_metrics]),

        'avgLargestContentfulPaint': statistics.mean([m.get('largestContentfulPaint', 0) for m in all_metrics]),
        'minLargestContentfulPaint': min([m.get('largestContentfulPaint', 0) for m in all_metrics]),
        'maxLargestContentfulPaint': max([m.get('largestContentfulPaint', 0) for m in all_metrics]),
        'medianLargestContentfulPaint': statistics.median([m.get('largestContentfulPaint', 0) for m in all_metrics]),

        'avgCumulativeLayoutShift': statistics.mean([m.get('cumulativeLayoutShift', 0) for m in all_metrics]),
        'minCumulativeLayoutShift': min([m.get('cumulativeLayoutShift', 0) for m in all_metrics]),
        'maxCumulativeLayoutShift': max([m.get('cumulativeLayoutShift', 0) for m in all_metrics]),
        'medianCumulativeLayoutShift': statistics.median([m.get('cumulativeLayoutShift', 0) for m in all_metrics]),

        'avgDomInteractive': statistics.mean([m.get('domInteractive', 0) for m in all_metrics]),
        'avgDomComplete': statistics.mean([m.get('domComplete', 0) for m in all_metrics]),
        'avgTotalResources': statistics.mean([m.get('totalResources', 0) for m in all_metrics]),
        'avgTotalTransferSize': statistics.mean([m.get('totalTransferSize', 0) for m in all_metrics]),
    }

    if getads_times:
        aggregate['avgGetadsResponseTime'] = statistics.mean(getads_times)
        aggregate['minGetadsResponseTime'] = min(getads_times)
        aggregate['maxGetadsResponseTime'] = max(getads_times)
        aggregate['medianGetadsResponseTime'] = statistics.median(getads_times)
        aggregate['getadsCallsFound'] = len(getads_times)
    else:
        aggregate['avgGetadsResponseTime'] = 0
        aggregate['minGetadsResponseTime'] = 0
        aggregate['maxGetadsResponseTime'] = 0
        aggregate['medianGetadsResponseTime'] = 0
        aggregate['getadsCallsFound'] = 0

    # --- aggregate key asset metrics + cache hit rates and first vs subsequent ---
    assets_agg = {}
    first_vs_subseq = {}
    for key in KEY_ASSET_LABELS.keys():
        durations = []  # ms
        sizes = []      # bytes
        hits = 0
        found_count = 0

        # first run vs subsequent runs (by iteration index)
        first_run_vals = {"dur": [], "size": [], "hits": 0, "found": 0}
        subseq_vals = {"dur": [], "size": [], "hits": 0, "found": 0}

        for idx, m in enumerate(all_metrics, start=1):
            asset = m.get('keyAssets', {}).get(key)
            if asset and asset.get('found'):
                found_count += 1
                if asset.get('fromCache'):
                    hits += 1
                dur = asset.get('duration', 0) or 0
                sz = asset.get('transferSize', 0) or asset.get('encodedBodySize', 0) or 0
                if dur > 0:
                    durations.append(dur)
                if sz > 0:
                    sizes.append(sz)

                bucket = first_run_vals if idx == 1 else subseq_vals
                bucket["found"] += 1
                if asset.get('fromCache'):
                    bucket["hits"] += 1
                if dur > 0:
                    bucket["dur"].append(dur)
                if sz > 0:
                    bucket["size"].append(sz)

        if found_count == 0:
            assets_agg[key] = {
                'foundInRuns': 0,
                'avgDurationMs': 0.0,
                'minDurationMs': 0.0,
                'maxDurationMs': 0.0,
                'medianDurationMs': 0.0,
                'avgSizeBytes': 0,
                'minSizeBytes': 0,
                'maxSizeBytes': 0,
                'medianSizeBytes': 0,
                'cacheHitRatePct': 0.0,
            }
        else:
            assets_agg[key] = {
                'foundInRuns': found_count,
                'avgDurationMs': statistics.mean(durations) if durations else 0.0,
                'minDurationMs': min(durations) if durations else 0.0,
                'maxDurationMs': max(durations) if durations else 0.0,
                'medianDurationMs': statistics.median(durations) if durations else 0.0,
                'avgSizeBytes': int(statistics.mean(sizes)) if sizes else 0,
                'minSizeBytes': min(sizes) if sizes else 0,
                'maxSizeBytes': max(sizes) if sizes else 0,
                'medianSizeBytes': int(statistics.median(sizes)) if sizes else 0,
                'cacheHitRatePct': round((hits / found_count) * 100.0, 1) if found_count else 0.0,
            }

        def _bucket_summary(bucket):
            return {
                'avgDurationMs': statistics.mean(bucket['dur']) if bucket['dur'] else 0.0,
                'avgSizeBytes': int(statistics.mean(bucket['size'])) if bucket['size'] else 0,
                'cacheHitRatePct': round((bucket['hits'] / bucket['found']) * 100.0, 1) if bucket['found'] else 0.0,
                'foundInRuns': bucket['found'],
            }

        first_vs_subseq[key] = {
            'firstRun': _bucket_summary(first_run_vals),
            'subsequentRuns': _bucket_summary(subseq_vals),
        }

    aggregate['assets'] = assets_agg
    aggregate['assetsFirstVsSubsequent'] = first_vs_subseq

    return aggregate


def _fmt_kb(n_bytes):
    return f"{(n_bytes/1024):.2f} KB" if n_bytes else "N/A"


def _fmt_ms(n_ms):
    return f"{n_ms:.0f} ms" if n_ms else "N/A"


def _fmt_pct(p):
    return f"{p:.1f}%" if isinstance(p, (int, float)) else "N/A"


# --- NEW: robust capture that falls back to PDF if screenshot stalls on font loading ---
def _save_page_capture_with_pdf_fallback(page, client, company_setting, prefer_pdf_first=False):
    base = Path(f"./performance/{client}/{company_setting}/{client}_desktop_screenshot")
    ensure_directory_exists(base.parent)

    def _save_pdf():
        try:
            page.emulate_media(media="screen")
            pdf_path = str(base.with_suffix('.pdf'))
            page.pdf(path=pdf_path, print_background=True, prefer_css_page_size=True)
            print(f"Page PDF saved to {pdf_path}")
            return pdf_path
        except Exception as e:
            print(f"PDF capture failed: {e}")
            return None

    def _save_png():
        try:
            png_path = str(base.with_suffix('.png'))
            page.screenshot(path=png_path, timeout=60000, full_page=True)
            print(f"Final screenshot saved to {png_path}")
            return png_path
        except PlaywrightTimeoutError as e:
            print(f"Screenshot timed out (likely waiting for fonts). Details: {e}")
            return None
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return None

    if prefer_pdf_first:
        out = _save_pdf()
        if out:
            return out
        # fallback to PNG if PDF failed for some reason
        out = _save_png()
        return out
    else:
        out = _save_png()
        if out:
            return out
        print("Falling back to PDF (printToPDF) due to screenshot issue...")
        out = _save_pdf()
        return out


def generate_aggregate_performance_report(aggregate_metrics, all_metrics, client, company_setting, output_path):
    """Generate an HTML performance report with aggregate statistics + key asset sizes/timings + cache analysis."""

    ensure_directory_exists(output_path.parent)

    def score_fcp(fcp):
        if fcp < 1800: return 100
        if fcp < 3000: return 50
        return 0

    def score_lcp(lcp):
        if lcp < 2500: return 100
        if lcp < 4000: return 50
        return 0

    def score_cls(cls):
        if cls < 0.1: return 100
        if cls < 0.25: return 50
        return 0

    def score_getads(time_ms):
        if time_ms < 500: return 100
        if time_ms < 1000: return 50
        return 0

    avg_fcp = aggregate_metrics['avgFirstContentfulPaint']
    avg_lcp = aggregate_metrics['avgLargestContentfulPaint']
    avg_cls = aggregate_metrics['avgCumulativeLayoutShift']
    avg_getads = aggregate_metrics.get('avgGetadsResponseTime', 0)

    fcp_score = score_fcp(avg_fcp)
    lcp_score = score_lcp(avg_lcp)
    cls_score = score_cls(avg_cls)
    getads_score = score_getads(avg_getads)

    overall_score = int((fcp_score + lcp_score + cls_score) / 3)

    # Build per-run summary rows
    iteration_rows = ""
    for i, metrics in enumerate(all_metrics, 1):
        getads_time = metrics.get('getadsResponseTime', 0)
        getads_display = f"{getads_time:.0f} ms" if getads_time > 0 else "N/A"

        iteration_rows += f"""
        <tr>
            <td>Run {i}</td>
            <td>{metrics.get('firstContentfulPaint', 0):.0f} ms</td>
            <td>{metrics.get('largestContentfulPaint', 0):.0f} ms</td>
            <td>{metrics.get('cumulativeLayoutShift', 0):.3f}</td>
            <td>{getads_display}</td>
        </tr>
        """

    getads_metric_html = ""
    if aggregate_metrics.get('avgGetadsResponseTime', 0) > 0:
        getads_metric_html = f"""
        <div class=\"metric {'metric-good' if getads_score >= 90 else 'metric-average' if getads_score >= 50 else 'metric-poor'}\">
            <div class=\"metric-title\">GetAds Response Time - full client-side round-trip time (Average)</div>
            <div class=\"metric-value\">{avg_getads:.0f} <span class=\"metric-unit\">ms</span></div>
            <div class=\"metric-subtitle\">
                <div class=\"metric-range\">Min: {aggregate_metrics['minGetadsResponseTime']:.0f} ms</div>
                <div class=\"metric-range\">Max: {aggregate_metrics['maxGetadsResponseTime']:.0f} ms</div>
                <div class=\"metric-range\">Median: {aggregate_metrics['medianGetadsResponseTime']:.0f} ms</div>
                <div class=\"metric-range\">Found in: {aggregate_metrics['getadsCallsFound']} of {aggregate_metrics['iterations']} runs</div>
            </div>
        </div>
        """

    # --- Key assets aggregate table ---
    assets = aggregate_metrics.get('assets', {})
    def asset_row(label_key):
        a = assets.get(label_key, {})
        return f"""
        <tr>
            <td>{label_key}</td>
            <td>{_fmt_kb(a.get('avgSizeBytes', 0))}</td>
            <td>{_fmt_kb(a.get('medianSizeBytes', 0))}</td>
            <td>{_fmt_ms(a.get('avgDurationMs', 0))}</td>
            <td>{_fmt_ms(a.get('medianDurationMs', 0))}</td>
            <td>{_fmt_pct(a.get('cacheHitRatePct', 0.0))}</td>
            <td>{a.get('foundInRuns', 0)} / {aggregate_metrics['iterations']}</td>
        </tr>
        """

    assets_table_rows = "".join([asset_row(k) for k in KEY_ASSET_LABELS.keys()])

    # --- Per-run key assets table with Cache? ---
    per_run_assets_rows = ""
    for i, m in enumerate(all_metrics, 1):
        ka = m.get('keyAssets', {})
        def one_asset_cells(k):
            v = ka.get(k, {})
            size_b = (v.get('transferSize') or v.get('encodedBodySize') or 0)
            cache = 'Hit' if v.get('fromCache') else ('Miss' if v.get('found') else '—')
            return f"<td>{_fmt_kb(size_b)}</td><td>{_fmt_ms(v.get('duration', 0))}</td><td>{cache}</td>"
        per_run_assets_rows += f"""
        <tr>
            <td>Run {i}</td>
            {one_asset_cells('finalytics-function_div.css')}
            {one_asset_cells('settings_div.js')}
            {one_asset_cells('finalytics.js')}
        </tr>
        """

    # --- First vs subsequent comparison table ---
    fvs = aggregate_metrics.get('assetsFirstVsSubsequent', {})
    def fvs_row(label_key):
        s = fvs.get(label_key, {})
        first = s.get('firstRun', {})
        subsq = s.get('subsequentRuns', {})
        return f"""
        <tr>
            <td>{label_key}</td>
            <td>{_fmt_kb(first.get('avgSizeBytes', 0))}</td>
            <td>{_fmt_ms(first.get('avgDurationMs', 0))}</td>
            <td>{_fmt_pct(first.get('cacheHitRatePct', 0.0))}</td>
            <td>{first.get('foundInRuns', 0)}</td>
            <td>{_fmt_kb(subsq.get('avgSizeBytes', 0))}</td>
            <td>{_fmt_ms(subsq.get('avgDurationMs', 0))}</td>
            <td>{_fmt_pct(subsq.get('cacheHitRatePct', 0.0))}</td>
            <td>{subsq.get('foundInRuns', 0)}</td>
        </tr>
        """

    fvs_rows = "".join([fvs_row(k) for k in KEY_ASSET_LABELS.keys()])

    html_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{client} Page Performance Report </title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #202124; margin-bottom: 10px; }}
        .meta {{ color: #5f6368; margin-bottom: 30px; }}
        .score-circle {{ width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 48px; font-weight: bold; margin: 20px auto; color: white; }}
        .score-good {{ background: #0cce6b; }}
        .score-average {{ background: #ffa400; }}
        .score-poor {{ background: #ff4e42; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 30px; }}
        .metric {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; }}
        .metric-title {{ font-size: 14px; color: #5f6368; margin-bottom: 8px; font-weight: 600; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #202124; }}
        .metric-subtitle {{ font-size: 12px; color: #5f6368; margin-top: 10px; }}
        .metric-range {{ font-size: 11px; color: #80868b; }}
        .metric-unit {{ font-size: 14px; color: #5f6368; }}
        .metric-good {{ border-left: 4px solid #0cce6b; }}
        .metric-average {{ border-left: 4px solid #ffa400; }}
        .metric-poor {{ border-left: 4px solid #ff4e42; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 30px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; vertical-align: top; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .stat-label {{ font-weight: 600; background: #f8f9fa; }}
        h2 {{ color: #202124; margin-top: 40px; margin-bottom: 20px; }}
        .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <h1>{client} Page Performance Report</h1>
        <div class=\"meta\">Client: {client} | Setting: {company_setting} | Iterations: {aggregate_metrics['iterations']} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <div class=\"score-circle {'score-good' if overall_score >= 90 else 'score-average' if overall_score >= 50 else 'score-poor'}\">{overall_score}</div>
        <h2>Core Web Vitals - Averaged Across {aggregate_metrics['iterations']} Runs</h2>
        <div class=\"metrics\">
            <div class=\"metric {'metric-good' if fcp_score >= 90 else 'metric-average' if fcp_score >= 50 else 'metric-poor'}\">
                <div class=\"metric-title\">First Contentful Paint (Average)</div>
                <div class=\"metric-value\">{avg_fcp:.0f} <span class=\"metric-unit\">ms</span></div>
                <div class=\"metric-subtitle\">
                    <div class=\"metric-range\">Min: {aggregate_metrics['minFirstContentfulPaint']:.0f} ms</div>
                    <div class=\"metric-range\">Max: {aggregate_metrics['maxFirstContentfulPaint']:.0f} ms</div>
                    <div class=\"metric-range\">Median: {aggregate_metrics['medianFirstContentfulPaint']:.0f} ms</div>
                </div>
            </div>
            <div class=\"metric {'metric-good' if lcp_score >= 90 else 'metric-average' if lcp_score >= 50 else 'metric-poor'}\">
                <div class=\"metric-title\">Largest Contentful Paint (Average)</div>
                <div class=\"metric-value\">{avg_lcp:.0f} <span class=\"metric-unit\">ms</span></div>
                <div class=\"metric-subtitle\">
                    <div class=\"metric-range\">Min: {aggregate_metrics['minLargestContentfulPaint']:.0f} ms</div>
                    <div class=\"metric-range\">Max: {aggregate_metrics['maxLargestContentfulPaint']:.0f} ms</div>
                    <div class=\"metric-range\">Median: {aggregate_metrics['medianLargestContentfulPaint']:.0f} ms</div>
                </div>
            </div>
            <div class=\"metric {'metric-good' if cls_score >= 90 else 'metric-average' if cls_score >= 50 else 'metric-poor'}\">
                <div class=\"metric-title\">Cumulative Layout Shift (Average)</div>
                <div class=\"metric-value\">{avg_cls:.3f}</div>
                <div class=\"metric-subtitle\">
                    <div class=\"metric-range\">Min: {aggregate_metrics['minCumulativeLayoutShift']:.3f}</div>
                    <div class=\"metric-range\">Max: {aggregate_metrics['maxCumulativeLayoutShift']:.3f}</div>
                    <div class=\"metric-range\">Median: {aggregate_metrics['medianCumulativeLayoutShift']:.3f}</div>
                </div>
            </div>
            {getads_metric_html}
        </div>

        <h2>Key Asset Metrics (Averages)</h2>
        <table>
            <tr>
                <th>Asset</</th>
                <th>Avg Size</th>
                <th>Median Size</th>
                <th>Avg Download Time</th>
                <th>Median Download Time</th>
                <th>Cache Hit Rate</th>
                <th>Found In</th>
            </tr>
            {assets_table_rows}
        </table>

        <h2>Individual Test Runs</h2>
        <table>
            <tr><th>Iteration</th><th>FCP (ms)</th><th>LCP (ms)</th><th>CLS</th><th>GetAds Time</th></tr>
            {iteration_rows}
            <tr class=\"stat-label\"><td>Average</td><td>{avg_fcp:.0f} ms</td><td>{avg_lcp:.0f} ms</td><td>{avg_cls:.3f}</td><td>{avg_getads:.0f} ms</td></tr>
            <tr class=\"stat-label\"><td>Median</td><td>{aggregate_metrics['medianFirstContentfulPaint']:.0f} ms</td><td>{aggregate_metrics['medianLargestContentfulPaint']:.0f} ms</td><td>{aggregate_metrics['medianCumulativeLayoutShift']:.3f}</td><td>{aggregate_metrics.get('medianGetadsResponseTime', 0):.0f} ms</td></tr>
        </table>

        <h2>Per-Run Key Asset Sizes & Download Times</h2>
        <table>
            <tr>
                <th rowspan=\"2\">Iteration</th>
                <th colspan=\"3\" class=\"mono\">finalytics-function_div.css</th>
                <th colspan=\"3\" class=\"mono\">settings_div.js</th>
                <th colspan=\"3\" class=\"mono\">finalytics.js</th>
            </tr>
            <tr>
                <th>Size</th><th>Time</th><th>Cache?</th>
                <th>Size</th><th>Time</th><th>Cache?</th>
                <th>Size</th><th>Time</th><th>Cache?</th>
            </tr>
            {per_run_assets_rows}
        </table>

        <h2>First vs Subsequent Loads (by Iteration)</h2>
        <table>
            <tr>
                <th rowspan=\"2\">Asset</th>
                <th colspan=\"4\">First Run Only</th>
                <th colspan=\"4\">Subsequent Runs</th>
            </tr>
            <tr>
                <th>Avg Size</th><th>Avg Time</th><th>Cache Hit Rate</th><th># Runs</th>
                <th>Avg Size</th><th>Avg Time</th><th>Cache Hit Rate</th><th># Runs</th>
            </tr>
            {fvs_rows}
        </table>

        <h2>Additional Metrics (Averages)</h2>
        <table>
            <tr><th>Metric</th><th>Average Value</th></tr>
            <tr><td>DOM Interactive</td><td>{aggregate_metrics['avgDomInteractive']:.0f} ms</td></tr>
            <tr><td>DOM Complete</td><td>{aggregate_metrics['avgDomComplete']:.0f} ms</td></tr>
            <tr><td>Total Resources</td><td>{aggregate_metrics['avgTotalResources']:.0f}</td></tr>
            <tr><td>Total Transfer Size</td><td>{aggregate_metrics['avgTotalTransferSize'] / 1024:.2f} KB</td></tr>
        </table>

        <h2>Performance Thresholds</h2>
        <table>
            <tr><th>Metric</th><th>Good</th><th>Needs Improvement</th><th>Poor</th></tr>
            <tr><td>First Contentful Paint</td><td>&lt; 1.8s</td><td>1.8s - 3.0s</td><td>&gt; 3.0s</td></tr>
            <tr><td>Largest Contentful Paint</td><td>&lt; 2.5s</td><td>2.5s - 4.0s</td><td>&gt; 4.0s</td></tr>
            <tr><td>Cumulative Layout Shift</td><td>&lt; 0.1</td><td>0.1 - 0.25</td><td>&gt; 0.25</td></tr>
            <tr><td>GetAds Response Time</td><td>&lt; 500ms</td><td>500ms - 1s</td><td>&gt; 1s</td></tr>
        </table>
    </div>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"{client} page performance report generated at {output_path}")


def run_playwright_performance_test(url, scenario_url, client, company_setting, username, password, hero_selector,
                                    num_iterations=NUM_ITERATIONS):
    try:
        url = validate_and_sanitize_url(url)
        scenario_url = validate_and_sanitize_url(scenario_url)
    except ValueError as e:
        print(e)
        return

    all_metrics = []

    with sync_playwright() as p:
        # IMPORTANT: use headless=True so Chromium supports printToPDF reliably
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(http_credentials={"username": username, "password": password})
        page = context.new_page()

        specific_js_files = ['finalytics.js', 'finalytics-function.js', 'settings_div.js', 'settings.js',
                             'controlbar.js']

        try:
            for iteration in range(1, num_iterations + 1):
                print(f"{'=' * 60}")
                print(f"Starting Iteration {iteration} of {num_iterations}")
                print(f"{'=' * 60}")

                max_attempts = 2
                iteration_ok = False
                for attempt in range(max_attempts):
                    try:
                        page.goto(url, timeout=120000)

                        login_if_redirected(page, username, password)
                        print("Home Page loaded successfully.")

                        page.goto(scenario_url, timeout=90000)

                        if client not in ("glbl", "lfcu", "gocu", "u1st"):
                            print(f"Client is NOT {client} so use network idle for waiting for load state")
                            page.wait_for_load_state("networkidle", timeout=90000)
                        else:
                            print(f"Client is {client} so use domcontentloaded for waiting for load state")
                            page.wait_for_load_state("domcontentloaded", timeout=90000)
                        print("Scenario Page loaded successfully.")

                        print(f"About to go back to the homepage URL on {url} to see the ad")
                        if client not in ("glbl", "lfcu", "gocu", "u1st"):
                            page.goto(url, timeout=90000, wait_until="networkidle")
                        else:
                            page.goto(url, timeout=90000)
                            page.wait_for_load_state("domcontentloaded", timeout=90000)

                        print(f"Wait for HERO SELECTOR {hero_selector} to be visible for client {client}")
                        page.wait_for_selector(hero_selector, timeout=90000)

                        detect_js_errors_from_specific_files(page, specific_js_files)
                        print("Checked for JS errors only from specific JS files.")
                        iteration_ok = True
                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed: {e}")
                        if attempt < max_attempts - 1:
                            print("Retrying...")
                            time.sleep(5)
                        else:
                            print(f"WARNING: Iteration {iteration} failed after {max_attempts} attempts — skipping.")

                if not iteration_ok:
                    continue

                print(f"Collecting performance metrics for iteration {iteration}...")
                time.sleep(5)
                metrics = get_web_vitals_and_key_assets(page)

                getads_timing = capture_getads_timing(page)
                if getads_timing and metrics:
                    metrics['getadsResponseTime'] = getads_timing['duration']
                    metrics['getadsTransferSize'] = getads_timing['transferSize']
                    metrics['getadsUrl'] = getads_timing['url']

                if metrics:
                    all_metrics.append(metrics)
                    print(f"Iteration {iteration} Metrics:")
                    print(f"  FCP: {metrics.get('firstContentfulPaint', 0):.0f} ms")
                    print(f"  LCP: {metrics.get('largestContentfulPaint', 0):.0f} ms")
                    print(f"  CLS: {metrics.get('cumulativeLayoutShift', 0):.3f}")

                    # log key assets with cache info
                    ka = metrics.get('keyAssets', {})
                    for label in KEY_ASSET_LABELS.keys():
                        v = ka.get(label, {})
                        size_b = (v.get('transferSize') or v.get('encodedBodySize') or 0)
                        cache = 'cache-hit' if v.get('fromCache') else 'cache-miss'
                        print(f"  {label}: size={_fmt_kb(size_b)}, time={_fmt_ms(v.get('duration', 0))}, {cache}")

                    if 'getadsResponseTime' in metrics:
                        print(f"  GetAds Response Time (full client-side round-trip time): {metrics.get('getadsResponseTime', 0):.0f} ms")
                else:
                    print(f"Failed to collect metrics for iteration {iteration}")

                if iteration < num_iterations:
                    print(f"Waiting 3 seconds before next iteration...")
                    time.sleep(3)

            # --- NEW: robust screenshot with PDF fallback ---
            prefer_pdf = client in PDF_FIRST_CLIENTS
            capture_path = _save_page_capture_with_pdf_fallback(page, client, company_setting, prefer_pdf_first=prefer_pdf)
            if capture_path:
                print(f"Final page capture stored at {capture_path}")
            else:
                print("ERROR: Unable to capture page as PNG or PDF.")

            if all_metrics:
                if len(all_metrics) < num_iterations:
                    print(f"NOTE: Only {len(all_metrics)} of {num_iterations} iterations succeeded — "
                          f"averaging over {len(all_metrics)} runs.")
                print(f"{'=' * 60}")
                print(f"Calculating aggregate metrics from {len(all_metrics)} successful runs...")
                print(f"{'=' * 60}")

                aggregate_metrics = calculate_aggregate_metrics(all_metrics)

                print("=== Aggregate Performance Metrics ===")
                print(f"Average First Contentful Paint: {aggregate_metrics['avgFirstContentfulPaint']:.0f} ms")
                print(f"Average Largest Contentful Paint: {aggregate_metrics['avgLargestContentfulPaint']:.0f} ms")
                print(f"Average Cumulative Layout Shift: {aggregate_metrics['avgCumulativeLayoutShift']:.3f}")
                if aggregate_metrics.get('avgGetadsResponseTime', 0) > 0:
                    print(f"Average GetAds Response Time: {aggregate_metrics['avgGetadsResponseTime']:.0f} ms")
                    print(f"GetAds calls found in: {aggregate_metrics['getadsCallsFound']} of {aggregate_metrics['iterations']} iterations")

                # aggregate key asset summary with cache hit rates
                for label, summary in aggregate_metrics.get('assets', {}).items():
                    print(
                        f"{label}: avgSize={_fmt_kb(summary.get('avgSizeBytes', 0))}, "
                        f"avgTime={_fmt_ms(summary.get('avgDurationMs', 0))}, "
                        f"cacheHitRate={_fmt_pct(summary.get('cacheHitRatePct', 0.0))}, "
                        f"foundIn={summary.get('foundInRuns', 0)}/{aggregate_metrics['iterations']}"
                    )

                json_path = Path(f"./performance/{client}/{company_setting}/{client}_all_metrics.json")
                ensure_directory_exists(json_path.parent)
                with open(json_path, 'w') as f:
                    json.dump({
                        'aggregate': aggregate_metrics,
                        'individual_runs': all_metrics
                    }, f, indent=2)
                print(f"All metrics saved to {json_path}")

                html_path = Path(f"./performance/{client}/{company_setting}/{client}_page_performance_metrics.html")
                generate_aggregate_performance_report(aggregate_metrics, all_metrics, client, company_setting,
                                                      html_path)
            else:
                print("No metrics collected across all iterations")

        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()

        finally:
            context.close()
            browser.close()


def read_config_from_csv(csv_file_path):
    config_data_list = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                config_data_list.append(row)
        print(f"Successfully read {len(config_data_list)} configuration(s) from CSV")
    except FileNotFoundError:
        print(f"ERROR: CSV file not found: {csv_file_path}")
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        import traceback
        traceback.print_exc()
    return config_data_list


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Page performance test runner")
    parser.add_argument(
        "--env",
        choices=["STG", "PROD"],
        default="PROD",
        help="Target environment: STG or PROD (default: PROD)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    csv_map = {
        "STG": script_dir / "lighthouse_data_for_one_client_after_first_visit_with_selectors_most_clients_STG.csv",
        "PROD": script_dir / "lighthouse_data_for_MOST_clients_after_first_visit_with_selectors_PROD.csv",
    }
    csv_file_path = csv_map[args.env]

    print(f"Starting performance test script using ENV={args.env}, CSV={csv_file_path}...")
    config_data_list = read_config_from_csv(csv_file_path)

    if not config_data_list:
        print("No configurations found. Exiting.")
    else:
        for config_data in config_data_list:
            print("Processing configuration:", config_data)
            target_url = config_data["target_url"]
            scenario_url = config_data["scenario_url"]
            client = config_data["client"]
            company_setting = config_data["company_setting"]
            username = config_data["username"]
            password = config_data["password"]
            hero_selector = config_data["hero_selector"]

            run_playwright_performance_test(target_url, scenario_url, client, company_setting, username, password,
                                            hero_selector, num_iterations=NUM_ITERATIONS)

    print("Script completed.")
