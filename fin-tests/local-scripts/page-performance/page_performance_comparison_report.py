"""
Page Performance Comparison Report Generator

Analyzes page performance metrics from a sprint folder and generates a comparative
HTML report with charts for all clients.

Usage:
    # Single folder report (existing behavior)
    python page_performance_comparison_report.py <folder_path>

    # Before vs After comparison report
    python page_performance_comparison_report.py <before_folder> --compare <after_folder>

Metrics Analyzed:
    - First Contentful Paint (FCP)
    - Largest Contentful Paint (LCP)
    - Cumulative Layout Shift (CLS)
    - GetAds Response Time

Examples:
    python page_performance_comparison_report.py "C:\\path\\to\\sprint\\results"

    python page_performance_comparison_report.py "C:\\path\\to\\before" --compare "C:\\path\\to\\after" \\
        --before-label "Before Release" --after-label "After Release" \\
        --title "Prod Performance: Before vs After Release"
"""

import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("BeautifulSoup not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4'])
    from bs4 import BeautifulSoup


def parse_performance_html(html_path):
    """Parse a client's page performance HTML report and extract key metrics."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    metrics = {}
    client_name = Path(html_path).stem.replace('_page_performance_metrics', '')
    metrics['client'] = client_name

    # Extract the 4 key metrics
    metric_divs = soup.find_all('div', class_='metric')
    for div in metric_divs:
        title_elem = div.find('div', class_='metric-title')
        value_elem = div.find('div', class_='metric-value')

        if title_elem and value_elem:
            title = title_elem.get_text(strip=True)
            value_text = value_elem.get_text(strip=True)

            # Parse the numeric value
            match = re.search(r'([\d.]+)', value_text)
            if match:
                value = float(match.group(1))

                if 'First Contentful Paint' in title:
                    metrics['fcp'] = value
                elif 'Largest Contentful Paint' in title:
                    metrics['lcp'] = value
                elif 'Cumulative Layout Shift' in title:
                    metrics['cls'] = value
                elif 'GetAds Response Time' in title:
                    metrics['getads'] = value

    return metrics


def find_performance_reports(folder_path):
    """Find all client performance HTML reports in the folder structure."""
    reports = []
    folder = Path(folder_path)

    for html_file in folder.rglob('*_page_performance_metrics.html'):
        reports.append(html_file)

    return reports


def get_metric_class(metric_name, value):
    """Determine if metric is good, average, or poor."""
    thresholds = {
        'fcp': (1800, 3000),      # ms
        'lcp': (2500, 4000),      # ms
        'cls': (0.1, 0.25),       # score
        'getads': (500, 1000),    # ms
    }

    if metric_name not in thresholds:
        return 'neutral'

    good, poor = thresholds[metric_name]
    if value < good:
        return 'good'
    elif value < poor:
        return 'average'
    else:
        return 'poor'


def detect_environment(folder_path):
    """Detect if the folder path contains 'prod' or 'stg' to determine environment and additional context.
    Returns a tuple: (environment_prefix, suffix) for title construction.
    """
    path_lower = str(folder_path).lower()
    env = None
    suffix = ""

    # Detect base environment
    if 'prod' in path_lower:
        env = 'Prod'
    elif 'stg' in path_lower or 'staging' in path_lower:
        env = 'Stg'

    # Detect additional context from path (suffix goes after "Page Performance Report")
    if 'with_load_balancing' in path_lower or 'with-load-balancing' in path_lower:
        suffix = " with Load Balancing"
    elif 'before_load_balancing' in path_lower or 'no_load_balance' in path_lower:
        suffix = " before Load Balancing"

    return (env, suffix) if env else (None, "")


def generate_comparison_report(metrics_data, output_path, folder_name, environment=None, suffix="", custom_title=None):
    """Generate an HTML comparison report with charts."""

    # Determine report title based on custom_title, environment and suffix
    # Format: "{Env} Page Performance Report{suffix}"
    if custom_title:
        report_title = custom_title
    elif environment:
        report_title = f"{environment} Page Performance Report{suffix}"
    else:
        report_title = f"Page Performance Report{suffix}"

    clients = [m['client'] for m in metrics_data]
    fcp_values = [m.get('fcp', 0) for m in metrics_data]
    lcp_values = [m.get('lcp', 0) for m in metrics_data]
    cls_values = [m.get('cls', 0) for m in metrics_data]
    getads_values = [m.get('getads', 0) for m in metrics_data]

    # Calculate averages safely
    avg_fcp = sum(fcp_values) / len(fcp_values) if fcp_values else 0
    avg_lcp = sum(lcp_values) / len(lcp_values) if lcp_values else 0
    avg_cls = sum(cls_values) / len(cls_values) if cls_values else 0
    avg_getads = sum(getads_values) / len(getads_values) if getads_values else 0

    sorted_metrics = sorted(metrics_data, key=lambda x: x['client'])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #202124; margin-bottom: 10px; }}
        h2 {{ color: #202124; margin-top: 40px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
        .meta {{ color: #5f6368; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .good {{ color: #0cce6b; font-weight: bold; }}
        .average {{ color: #ffa400; font-weight: bold; }}
        .poor {{ color: #ff4e42; font-weight: bold; }}
        .chart-container {{ width: 100%; max-width: 800px; margin: 30px auto; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 30px; margin-top: 30px; }}
        @media (max-width: 1000px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
        .legend {{ display: flex; gap: 20px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 3px; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .summary-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; }}
        .summary-card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #5f6368; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; color: #202124; }}
        .summary-card .unit {{ font-size: 14px; color: #5f6368; }}
        @media (max-width: 800px) {{ .summary-cards {{ grid-template-columns: repeat(2, 1fr); }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        <div class="meta">
            <strong>Sprint Folder:</strong> {folder_name}<br>
            <strong>Clients Analyzed:</strong> {len(clients)}<br>
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>

        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background: #0cce6b;"></div> Good</div>
            <div class="legend-item"><div class="legend-color" style="background: #ffa400;"></div> Needs Improvement</div>
            <div class="legend-item"><div class="legend-color" style="background: #ff4e42;"></div> Poor</div>
        </div>

        <h2>Summary Statistics</h2>
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Avg First Contentful Paint</h3>
                <div class="value">{avg_fcp:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="summary-card">
                <h3>Avg Largest Contentful Paint</h3>
                <div class="value">{avg_lcp:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="summary-card">
                <h3>Avg Cumulative Layout Shift</h3>
                <div class="value">{avg_cls:.3f}</div>
                <div class="unit">score</div>
            </div>
            <div class="summary-card">
                <h3>Avg GetAds Response Time</h3>
                <div class="value">{avg_getads:.0f}</div>
                <div class="unit">ms</div>
            </div>
        </div>

        <h2>Detailed Comparison Table</h2>
        <table>
            <tr>
                <th>Client</th>
                <th>FCP (ms)</th>
                <th>LCP (ms)</th>
                <th>CLS</th>
                <th>GetAds (ms)</th>
            </tr>'''

    for m in sorted_metrics:
        fcp_class = get_metric_class('fcp', m.get('fcp', 0))
        lcp_class = get_metric_class('lcp', m.get('lcp', 0))
        cls_class = get_metric_class('cls', m.get('cls', 0))
        getads_class = get_metric_class('getads', m.get('getads', 0))

        html += f'''
            <tr>
                <td><strong>{m['client'].upper()}</strong></td>
                <td class="{fcp_class}">{m.get('fcp', 'N/A')}</td>
                <td class="{lcp_class}">{m.get('lcp', 'N/A')}</td>
                <td class="{cls_class}">{m.get('cls', 'N/A')}</td>
                <td class="{getads_class}">{m.get('getads', 'N/A')}</td>
            </tr>'''

    # Prepare chart data
    chart_clients = json.dumps([m['client'].upper() for m in sorted_metrics])
    chart_fcp = json.dumps([m.get('fcp', 0) for m in sorted_metrics])
    chart_lcp = json.dumps([m.get('lcp', 0) for m in sorted_metrics])
    chart_cls = json.dumps([m.get('cls', 0) for m in sorted_metrics])
    chart_getads = json.dumps([m.get('getads', 0) for m in sorted_metrics])

    html += f'''
        </table>

        <h2>Performance Charts</h2>
        <div class="charts-grid">
            <div class="chart-container">
                <canvas id="fcpChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="lcpChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="clsChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="getadsChart"></canvas>
            </div>
        </div>

        <h2>Performance Thresholds Reference</h2>
        <table>
            <tr><th>Metric</th><th>Good</th><th>Needs Improvement</th><th>Poor</th></tr>
            <tr><td>First Contentful Paint</td><td class="good">&lt; 1.8s</td><td class="average">1.8s - 3.0s</td><td class="poor">&gt; 3.0s</td></tr>
            <tr><td>Largest Contentful Paint</td><td class="good">&lt; 2.5s</td><td class="average">2.5s - 4.0s</td><td class="poor">&gt; 4.0s</td></tr>
            <tr><td>Cumulative Layout Shift</td><td class="good">&lt; 0.1</td><td class="average">0.1 - 0.25</td><td class="poor">&gt; 0.25</td></tr>
            <tr><td>GetAds Response Time</td><td class="good">&lt; 500ms</td><td class="average">500ms - 1s</td><td class="poor">&gt; 1s</td></tr>
        </table>
    </div>

    <script>
        const clients = {chart_clients};

        function getBarColors(values, thresholds) {{
            return values.map(v => {{
                if (v < thresholds[0]) return '#0cce6b';
                if (v < thresholds[1]) return '#ffa400';
                return '#ff4e42';
            }});
        }}

        // FCP Chart
        new Chart(document.getElementById('fcpChart'), {{
            type: 'bar',
            data: {{
                labels: clients,
                datasets: [{{
                    label: 'First Contentful Paint (ms)',
                    data: {chart_fcp},
                    backgroundColor: getBarColors({chart_fcp}, [1800, 3000])
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'First Contentful Paint (ms)' }} }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});

        // LCP Chart
        new Chart(document.getElementById('lcpChart'), {{
            type: 'bar',
            data: {{
                labels: clients,
                datasets: [{{
                    label: 'Largest Contentful Paint (ms)',
                    data: {chart_lcp},
                    backgroundColor: getBarColors({chart_lcp}, [2500, 4000])
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'Largest Contentful Paint (ms)' }} }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});

        // CLS Chart
        new Chart(document.getElementById('clsChart'), {{
            type: 'bar',
            data: {{
                labels: clients,
                datasets: [{{
                    label: 'Cumulative Layout Shift',
                    data: {chart_cls},
                    backgroundColor: getBarColors({chart_cls}, [0.1, 0.25])
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'Cumulative Layout Shift' }} }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});

        // GetAds Chart
        new Chart(document.getElementById('getadsChart'), {{
            type: 'bar',
            data: {{
                labels: clients,
                datasets: [{{
                    label: 'GetAds Response Time (ms)',
                    data: {chart_getads},
                    backgroundColor: getBarColors({chart_getads}, [500, 1000])
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'GetAds Response Time (ms)' }} }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});
    </script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def generate_before_after_comparison_report(before_data, after_data, output_path,
                                             before_label="Before", after_label="After",
                                             custom_title=None):
    """Generate a before-vs-after comparison HTML report with grouped bar charts and delta analysis.

    Args:
        before_data: List of parsed metric dicts from the "before" folder
        after_data: List of parsed metric dicts from the "after" folder
        output_path: Path to write the HTML report
        before_label: Label for the "before" dataset in charts/legends
        after_label: Label for the "after" dataset in charts/legends
        custom_title: Optional custom report title
    """
    report_title = custom_title or f"Page Performance Comparison: {before_label} vs {after_label}"

    # Build lookup by client name (lowercase for matching)
    before_map = {m['client'].lower(): m for m in before_data}
    after_map = {m['client'].lower(): m for m in after_data}

    # Find matched clients (present in both folders)
    all_clients = sorted(set(before_map.keys()) | set(after_map.keys()))
    matched_clients = sorted(set(before_map.keys()) & set(after_map.keys()))
    before_only = sorted(set(before_map.keys()) - set(after_map.keys()))
    after_only = sorted(set(after_map.keys()) - set(before_map.keys()))

    metrics_list = ['fcp', 'lcp', 'cls', 'getads']
    metric_labels = {
        'fcp': 'First Contentful Paint',
        'lcp': 'Largest Contentful Paint',
        'cls': 'Cumulative Layout Shift',
        'getads': 'GetAds Response Time',
    }
    metric_units = {'fcp': 'ms', 'lcp': 'ms', 'cls': 'score', 'getads': 'ms'}
    # For all metrics, lower is better
    lower_is_better = {'fcp': True, 'lcp': True, 'cls': True, 'getads': True}

    # Build comparison data for matched clients
    comparison = []
    for client_key in matched_clients:
        b = before_map[client_key]
        a = after_map[client_key]
        row = {'client': b['client'], 'metrics': {}}
        for m in metrics_list:
            bv = b.get(m)
            av = a.get(m)
            delta = None
            delta_pct = None
            improved = None
            if bv is not None and av is not None and bv != 0:
                delta = av - bv
                delta_pct = (delta / bv) * 100
                improved = delta < 0 if lower_is_better[m] else delta > 0
            row['metrics'][m] = {
                'before': bv, 'after': av,
                'delta': delta, 'delta_pct': delta_pct,
                'improved': improved
            }
        comparison.append(row)

    # Calculate average deltas per metric
    avg_deltas = {}
    for m in metrics_list:
        pcts = [r['metrics'][m]['delta_pct'] for r in comparison
                if r['metrics'][m]['delta_pct'] is not None]
        avg_deltas[m] = sum(pcts) / len(pcts) if pcts else 0

    # Prepare JSON data for charts
    chart_clients = json.dumps([r['client'].upper() for r in comparison])
    chart_data = {}
    for m in metrics_list:
        chart_data[f'{m}_before'] = json.dumps([r['metrics'][m]['before'] or 0 for r in comparison])
        chart_data[f'{m}_after'] = json.dumps([r['metrics'][m]['after'] or 0 for r in comparison])
        chart_data[f'{m}_delta_pct'] = json.dumps([
            round(r['metrics'][m]['delta_pct'], 1) if r['metrics'][m]['delta_pct'] is not None else 0
            for r in comparison
        ])

    # Build summary cards HTML
    summary_cards_html = ''
    for m in metrics_list:
        avg_d = avg_deltas[m]
        # For lower-is-better metrics, negative delta = improved
        is_improved = avg_d < 0 if lower_is_better[m] else avg_d > 0
        color = '#0cce6b' if is_improved else '#ff4e42'
        arrow = 'v' if avg_d < 0 else '^' if avg_d > 0 else '-'
        sign = '+' if avg_d > 0 else ''
        fmt = '.3f' if m == 'cls' else '.1f'
        summary_cards_html += f'''
            <div class="summary-card">
                <h3>Avg {metric_labels[m]}</h3>
                <div class="value" style="color: {color};">{sign}{avg_d:{fmt}}%</div>
                <div class="unit">{"Improved" if is_improved else "Degraded"}</div>
            </div>'''

    # Build detailed comparison table rows
    table_rows = ''
    for r in comparison:
        table_rows += f'\n            <tr><td><strong>{r["client"].upper()}</strong></td>'
        for m in metrics_list:
            md = r['metrics'][m]
            bv = md['before']
            av = md['after']
            dp = md['delta_pct']
            improved = md['improved']

            fmt = '.3f' if m == 'cls' else '.0f'
            b_str = f'{bv:{fmt}}' if bv is not None else 'N/A'
            a_str = f'{av:{fmt}}' if av is not None else 'N/A'
            a_class = get_metric_class(m, av) if av is not None else 'neutral'

            if dp is not None:
                sign = '+' if dp > 0 else ''
                d_color = '#0cce6b' if improved else '#ff4e42'
                d_str = f'<span style="color:{d_color}">{sign}{dp:.1f}%</span>'
            else:
                d_str = 'N/A'

            table_rows += f'<td>{b_str}</td><td class="{a_class}">{a_str}</td><td>{d_str}</td>'
        table_rows += '</tr>'

    # Build per-client summary cards
    client_cards_html = ''
    for r in comparison:
        improved_count = sum(1 for m in metrics_list if r['metrics'][m]['improved'] is True)
        degraded_count = sum(1 for m in metrics_list if r['metrics'][m]['improved'] is False)
        total = sum(1 for m in metrics_list if r['metrics'][m]['improved'] is not None)
        if total > 0 and improved_count > degraded_count:
            verdict = 'Improved'
            verdict_color = '#0cce6b'
        elif total > 0 and degraded_count > improved_count:
            verdict = 'Degraded'
            verdict_color = '#ff4e42'
        else:
            verdict = 'Mixed'
            verdict_color = '#ffa400'

        metrics_html = ''
        for m in metrics_list:
            md = r['metrics'][m]
            dp = md['delta_pct']
            if dp is not None:
                sign = '+' if dp > 0 else ''
                color = '#0cce6b' if md['improved'] else '#ff4e42'
                metrics_html += f'<div class="client-metric"><span>{metric_labels[m]}</span><span style="color:{color};font-weight:bold">{sign}{dp:.1f}%</span></div>'

        client_cards_html += f'''
            <div class="client-card">
                <div class="client-name">{r["client"].upper()}</div>
                <div class="verdict" style="color:{verdict_color}">{verdict}</div>
                {metrics_html}
            </div>'''

    # Unmatched clients warning
    unmatched_html = ''
    if before_only or after_only:
        unmatched_html = '<div class="unmatched-warning"><h3>Unmatched Clients</h3>'
        if before_only:
            unmatched_html += f'<p><strong>Only in {before_label}:</strong> {", ".join(c.upper() for c in before_only)}</p>'
        if after_only:
            unmatched_html += f'<p><strong>Only in {after_label}:</strong> {", ".join(c.upper() for c in after_only)}</p>'
        unmatched_html += '</div>'

    before_label_js = json.dumps(before_label)
    after_label_js = json.dumps(after_label)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #202124; margin-bottom: 10px; }}
        h2 {{ color: #202124; margin-top: 40px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
        .meta {{ color: #5f6368; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #e0e0e0; font-size: 14px; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .good {{ color: #0cce6b; font-weight: bold; }}
        .average {{ color: #ffa400; font-weight: bold; }}
        .poor {{ color: #ff4e42; font-weight: bold; }}
        .chart-container {{ width: 100%; max-width: 800px; margin: 30px auto; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 30px; margin-top: 30px; }}
        @media (max-width: 1000px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .summary-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; }}
        .summary-card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #5f6368; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; }}
        .summary-card .unit {{ font-size: 14px; color: #5f6368; }}
        @media (max-width: 800px) {{ .summary-cards {{ grid-template-columns: repeat(2, 1fr); }} }}
        .client-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin: 30px 0; }}
        .client-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; }}
        .client-name {{ font-size: 16px; font-weight: bold; color: #202124; margin-bottom: 8px; }}
        .verdict {{ font-size: 20px; font-weight: bold; margin-bottom: 12px; }}
        .client-metric {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }}
        .unmatched-warning {{ background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0; }}
        .unmatched-warning h3 {{ margin: 0 0 8px 0; color: #856404; }}
        .unmatched-warning p {{ margin: 4px 0; color: #856404; }}
        .legend {{ display: flex; gap: 20px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        <div class="meta">
            <strong>Matched Clients:</strong> {len(matched_clients)}<br>
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>

        {unmatched_html}

        <h2>Average Change Summary</h2>
        <div class="summary-cards">{summary_cards_html}
        </div>

        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background: #4285f4;"></div> {before_label}</div>
            <div class="legend-item"><div class="legend-color" style="background: #34a853;"></div> {after_label}</div>
        </div>

        <h2>Side-by-Side Comparison Charts</h2>
        <div class="charts-grid">
            <div class="chart-container"><canvas id="fcpChart"></canvas></div>
            <div class="chart-container"><canvas id="lcpChart"></canvas></div>
            <div class="chart-container"><canvas id="clsChart"></canvas></div>
            <div class="chart-container"><canvas id="getadsChart"></canvas></div>
        </div>

        <h2>Delta Percentage Charts</h2>
        <div class="charts-grid">
            <div class="chart-container"><canvas id="fcpDeltaChart"></canvas></div>
            <div class="chart-container"><canvas id="lcpDeltaChart"></canvas></div>
            <div class="chart-container"><canvas id="clsDeltaChart"></canvas></div>
            <div class="chart-container"><canvas id="getadsDeltaChart"></canvas></div>
        </div>

        <h2>Detailed Comparison Table</h2>
        <table>
            <tr>
                <th rowspan="2">Client</th>
                <th colspan="3" style="text-align:center">FCP (ms)</th>
                <th colspan="3" style="text-align:center">LCP (ms)</th>
                <th colspan="3" style="text-align:center">CLS</th>
                <th colspan="3" style="text-align:center">GetAds (ms)</th>
            </tr>
            <tr>
                <th>{before_label}</th><th>{after_label}</th><th>Change</th>
                <th>{before_label}</th><th>{after_label}</th><th>Change</th>
                <th>{before_label}</th><th>{after_label}</th><th>Change</th>
                <th>{before_label}</th><th>{after_label}</th><th>Change</th>
            </tr>{table_rows}
        </table>

        <h2>Per-Client Summary</h2>
        <div class="client-cards">{client_cards_html}
        </div>

        <h2>Performance Thresholds Reference</h2>
        <table>
            <tr><th>Metric</th><th>Good</th><th>Needs Improvement</th><th>Poor</th></tr>
            <tr><td>First Contentful Paint</td><td class="good">&lt; 1.8s</td><td class="average">1.8s - 3.0s</td><td class="poor">&gt; 3.0s</td></tr>
            <tr><td>Largest Contentful Paint</td><td class="good">&lt; 2.5s</td><td class="average">2.5s - 4.0s</td><td class="poor">&gt; 4.0s</td></tr>
            <tr><td>Cumulative Layout Shift</td><td class="good">&lt; 0.1</td><td class="average">0.1 - 0.25</td><td class="poor">&gt; 0.25</td></tr>
            <tr><td>GetAds Response Time</td><td class="good">&lt; 500ms</td><td class="average">500ms - 1s</td><td class="poor">&gt; 1s</td></tr>
        </table>
    </div>

    <script>
        const clients = {chart_clients};
        const beforeLabel = {before_label_js};
        const afterLabel = {after_label_js};

        function createGroupedBarChart(canvasId, title, beforeData, afterData) {{
            new Chart(document.getElementById(canvasId), {{
                type: 'bar',
                data: {{
                    labels: clients,
                    datasets: [
                        {{ label: beforeLabel, data: beforeData, backgroundColor: '#4285f4' }},
                        {{ label: afterLabel, data: afterData, backgroundColor: '#34a853' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ title: {{ display: true, text: title }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        }}

        function createDeltaChart(canvasId, title, deltaData) {{
            const colors = deltaData.map(v => v <= 0 ? '#0cce6b' : '#ff4e42');
            new Chart(document.getElementById(canvasId), {{
                type: 'bar',
                data: {{
                    labels: clients,
                    datasets: [{{
                        label: 'Change %',
                        data: deltaData,
                        backgroundColor: colors
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: title }},
                        tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y.toFixed(1) + '%' }} }}
                    }},
                    scales: {{ y: {{ ticks: {{ callback: v => v + '%' }} }} }}
                }}
            }});
        }}

        // Side-by-side charts
        createGroupedBarChart('fcpChart', 'First Contentful Paint (ms)',
            {chart_data['fcp_before']}, {chart_data['fcp_after']});
        createGroupedBarChart('lcpChart', 'Largest Contentful Paint (ms)',
            {chart_data['lcp_before']}, {chart_data['lcp_after']});
        createGroupedBarChart('clsChart', 'Cumulative Layout Shift',
            {chart_data['cls_before']}, {chart_data['cls_after']});
        createGroupedBarChart('getadsChart', 'GetAds Response Time (ms)',
            {chart_data['getads_before']}, {chart_data['getads_after']});

        // Delta charts
        createDeltaChart('fcpDeltaChart', 'FCP Change %', {chart_data['fcp_delta_pct']});
        createDeltaChart('lcpDeltaChart', 'LCP Change %', {chart_data['lcp_delta_pct']});
        createDeltaChart('clsDeltaChart', 'CLS Change %', {chart_data['cls_delta_pct']});
        createDeltaChart('getadsDeltaChart', 'GetAds Change %', {chart_data['getads_delta_pct']});
    </script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def main(folder_path, output_filename='page_performance_comparison_report.html', custom_title=None, output_dir=None,
         compare_folder=None, before_label="Before", after_label="After"):
    """Main function to analyze page performance and generate report.

    Args:
        folder_path: Path to folder containing performance report HTML files
        output_filename: Name of the output HTML file
        custom_title: Optional custom title for the report (overrides auto-detection)
        output_dir: Optional directory to save the report (defaults to folder_path)
        compare_folder: Optional second folder for before/after comparison mode
        before_label: Label for the "before" dataset (default: "Before")
        after_label: Label for the "after" dataset (default: "After")
    """

    def _parse_folder(folder_path, label=""):
        """Parse all performance reports in a folder and return metrics list."""
        prefix = f"[{label}] " if label else ""
        print(f"{prefix}Analyzing: {folder_path}")
        reports = find_performance_reports(folder_path)
        print(f"{prefix}Found {len(reports)} client reports")
        if not reports:
            print(f"{prefix}ERROR: No page performance reports found!")
            print(f"{prefix}Looking for files matching: *_page_performance_metrics.html")
            return []
        metrics_data = []
        for report in reports:
            try:
                metrics = parse_performance_html(report)
                metrics_data.append(metrics)
                print(f"  {prefix}{report.name}: FCP={metrics.get('fcp', 'N/A')} LCP={metrics.get('lcp', 'N/A')} "
                      f"CLS={metrics.get('cls', 'N/A')} GetAds={metrics.get('getads', 'N/A')}")
            except Exception as e:
                print(f"  {prefix}Error parsing {report.name}: {e}")
        return metrics_data

    print("=" * 60)

    # --- Comparison mode ---
    if compare_folder:
        before_data = _parse_folder(folder_path, before_label)
        print()
        after_data = _parse_folder(compare_folder, after_label)
        print("\n" + "=" * 60)

        if not before_data or not after_data:
            print("ERROR: Both folders must contain performance reports for comparison.")
            return None, []

        # Determine output directory
        if output_dir:
            output_folder = Path(output_dir)
            output_folder.mkdir(parents=True, exist_ok=True)
        else:
            output_folder = Path(folder_path).parent

        output_path = output_folder / output_filename
        generate_before_after_comparison_report(
            before_data, after_data, output_path,
            before_label=before_label, after_label=after_label,
            custom_title=custom_title
        )

        # Print summary
        before_map = {m['client'].lower(): m for m in before_data}
        after_map = {m['client'].lower(): m for m in after_data}
        matched = set(before_map.keys()) & set(after_map.keys())
        print(f"\nComparison report generated: {output_path}")
        print(f"\nSummary:")
        print(f"  {before_label} clients: {len(before_data)}")
        print(f"  {after_label} clients: {len(after_data)}")
        print(f"  Matched clients: {len(matched)}")

        return str(output_path), (before_data, after_data)

    # --- Single folder mode (existing behavior) ---
    metrics_data = _parse_folder(folder_path)
    print("\n" + "=" * 60)

    if not metrics_data:
        return None, []

    # Use custom title if provided, otherwise auto-detect
    if custom_title:
        environment = None
        suffix = ""
        print(f"Using custom title: {custom_title}")
    else:
        # Detect environment (Prod/Staging) and suffix from folder path
        environment, suffix = detect_environment(folder_path)
        if environment:
            print(f"Environment detected: {environment}{suffix}")

    # Determine output directory
    if output_dir:
        output_folder = Path(output_dir)
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_folder}")
    else:
        output_folder = Path(folder_path)

    # Generate comparison report
    output_path = output_folder / output_filename
    generate_comparison_report(metrics_data, output_path, Path(folder_path).name, environment, suffix, custom_title)

    print(f"\nReport generated: {output_path}")
    print(f"\nSummary:")
    print(f"  Clients analyzed: {len(metrics_data)}")

    if metrics_data:
        fcp_values = [m.get('fcp', 0) for m in metrics_data]
        lcp_values = [m.get('lcp', 0) for m in metrics_data]
        cls_values = [m.get('cls', 0) for m in metrics_data]
        getads_values = [m.get('getads', 0) for m in metrics_data]

        print(f"  Avg FCP: {sum(fcp_values)/len(fcp_values):.0f} ms")
        print(f"  Avg LCP: {sum(lcp_values)/len(lcp_values):.0f} ms")
        print(f"  Avg CLS: {sum(cls_values)/len(cls_values):.3f}")
        print(f"  Avg GetAds: {sum(getads_values)/len(getads_values):.0f} ms")

    return str(output_path), metrics_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate page performance comparison report from client HTML reports.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Single folder report
  python page_performance_comparison_report.py "C:\\path\\to\\sprint\\results"
  python page_performance_comparison_report.py "C:\\path\\to\\data" --title "Custom Report Title"

  # Before vs After comparison
  python page_performance_comparison_report.py "C:\\path\\to\\before" --compare "C:\\path\\to\\after"
  python page_performance_comparison_report.py "C:\\path\\to\\before" --compare "C:\\path\\to\\after" \\
      --before-label "Before Release" --after-label "After Release" \\
      --title "Prod Performance: Before vs After Release"
        '''
    )
    parser.add_argument('folder_path', help='Path to folder containing performance report HTML files (or "before" folder in comparison mode)')
    parser.add_argument('--output', '-o', default='page_performance_comparison_report.html',
                        help='Output filename (default: page_performance_comparison_report.html)')
    parser.add_argument('--title', '-t', help='Custom title for the report (overrides auto-detection)')
    parser.add_argument('--output-dir', '-d', help='Directory to save the report (defaults to folder_path)')
    parser.add_argument('--compare', '-c', metavar='AFTER_FOLDER',
                        help='Path to "after" folder for before/after comparison mode')
    parser.add_argument('--before-label', default='Before',
                        help='Label for the "before" dataset in comparison mode (default: Before)')
    parser.add_argument('--after-label', default='After',
                        help='Label for the "after" dataset in comparison mode (default: After)')

    args = parser.parse_args()

    if not os.path.exists(args.folder_path):
        print(f"ERROR: Folder not found: {args.folder_path}")
        sys.exit(1)

    if args.compare and not os.path.exists(args.compare):
        print(f"ERROR: Comparison folder not found: {args.compare}")
        sys.exit(1)

    main(args.folder_path, args.output, args.title, args.output_dir,
         compare_folder=args.compare, before_label=args.before_label, after_label=args.after_label)
