"""
ESFCU High Yield Savings — Search Trigger Validation

Flow: session_init → search "high yield savings" → homepage → validate marquee ad

Usage:
    python test_esfcu_high_yield_savings_search.py           # defaults to stg
    python test_esfcu_high_yield_savings_search.py --env stg
    python test_esfcu_high_yield_savings_search.py --env prod
"""
import re
import sys
import os
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

ENV_CONFIG = {
    "stg": {
        "base_url":    "https://esfcu-dev.zagclients.net/?api=stg&debug_all=1&session_init=1&cb=1",
        "homepage":    "https://esfcu-dev.zagclients.net/",
        "search_base": "https://esfcu-dev.zagclients.net/search-results?SearchTerm=",
        "rewrite_domain": True,
    },
    "prod": {
        "base_url":    "https://www.esfcu.org/?session_init=1&debug_all=1&cb=1",
        "homepage":    "https://www.esfcu.org/",
        "search_base": "https://www.esfcu.org/search-results?SearchTerm=",
        "rewrite_domain": False,
    },
}

SCENARIO = {
    "label": "High Yield Savings",
    "search_term": "high+yield+savings",
    "expected_eyebrow": "HIGH YIELD SAVINGS ACCOUNTS",
    "expected_title": "Make your savings work harder",
    "expected_description": "Grow your savings faster with a high-yield account designed to work harder for you.",
    "expected_btn1_text": "Open an account",
    "expected_btn1_aria": "Open an account",
    "expected_btn1_url": "https://open.esfcu.org/products/highYieldSavings",
    "expected_btn2_text": "Learn more",
    "expected_btn2_aria": "Learn more",
    "expected_btn2_url": "https://www.esfcu.org/accounts/savings/high-yield-savings-accounts",
    "expected_image": "HighYieldSavings",
}

MARQUEE_SELECTORS = [
    ".marquee", "[class*='marquee']", ".hero", "[class*='hero']",
    ".slideshow", "#slideshow--main", ".banner", "main > section:first-of-type",
]


def inject_url_banner(page, url):
    page.evaluate(f"""() => {{
        const existing = document.getElementById('_fin_url_banner');
        if (existing) existing.remove();
        const banner = document.createElement('div');
        banner.id = '_fin_url_banner';
        banner.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; z-index: 999999;
            background: #1a1a2e; color: #ffffff; font-family: monospace;
            font-size: 13px; padding: 8px 16px; line-height: 1.4;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        `;
        banner.innerHTML = '<span style="color:#4fc3f7;">URL: </span>{url}';
        document.body.prepend(banner);
        document.body.style.paddingTop = '38px';
    }}""")


def get_marquee_content(page):
    content = {}
    marquee_el = None
    marquee_sel = None
    for sel in MARQUEE_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                marquee_el = el
                marquee_sel = sel
                break
        except Exception:
            pass

    if marquee_el:
        content["marquee_selector"] = marquee_sel
        try:
            content["marquee_text"] = marquee_el.inner_text().strip()
        except Exception:
            content["marquee_text"] = ""

    for sel in [".eyebrow", "[class*='eyebrow']", ".overline", "p.eyebrow",
                "span.eyebrow", ".kicker", "[class*='kicker']"]:
        try:
            for el in page.query_selector_all(sel):
                t = el.inner_text().strip()
                if t:
                    content["eyebrow"] = t
                    break
        except Exception:
            pass
        if "eyebrow" in content:
            break

    for sel in ["h1", ".marquee h1", ".marquee h2", "[class*='marquee'] h1",
                "[class*='marquee'] h2", ".hero h1", ".hero h2", "[class*='hero'] h1"]:
        try:
            for el in page.query_selector_all(sel):
                t = el.inner_text().strip()
                if t and len(t) > 3:
                    content["title"] = t
                    break
        except Exception:
            pass
        if "title" in content:
            break

    for sel in [".marquee p", "[class*='marquee'] p", ".hero p", "[class*='hero'] p",
                ".description", "[class*='description']"]:
        try:
            for el in page.query_selector_all(sel):
                t = el.inner_text().strip()
                if t and len(t) > 20:
                    content["description"] = t
                    break
        except Exception:
            pass
        if "description" in content:
            break

    try:
        content["buttons"] = page.evaluate("""() => {
            const seen = new Set();
            const results = [];
            document.querySelectorAll('.marquee, [class*="marquee"], .hero, [class*="hero"], .slideshow, .banner')
                .forEach(container => {
                    container.querySelectorAll('a[href], button').forEach(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        const href = el.href || el.getAttribute('href') || '';
                        const aria = el.getAttribute('aria-label') || '';
                        if (text && !seen.has(text)) { seen.add(text); results.push({ text, href, aria }); }
                    });
                });
            return results;
        }""")
    except Exception:
        content["buttons"] = []

    try:
        bg = page.evaluate("""() => {
            const containers = document.querySelectorAll(
                '.marquee, [class*="marquee"], .hero, [class*="hero"], .slideshow, .banner, main > section'
            );
            for (const el of containers) {
                const bg = window.getComputedStyle(el).backgroundImage;
                if (bg && bg !== 'none' && bg.includes('url(')) return bg;
                for (const child of el.querySelectorAll('*')) {
                    const cbg = window.getComputedStyle(child).backgroundImage;
                    if (cbg && cbg !== 'none' && cbg.includes('url(')) return cbg;
                }
            }
            return '';
        }""")
        if bg:
            content["image_bg"] = bg
    except Exception:
        pass

    try:
        imgs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('.marquee img, [class*="marquee"] img, .hero img, [class*="hero"] img')
                .forEach(img => {
                    const src = img.src || img.getAttribute('data-src') || '';
                    if (src && !src.includes('.svg') && !src.includes('icon') && !src.includes('logo'))
                        results.push(src);
                });
            return results;
        }""")
        if imgs:
            content["image_src"] = imgs[0]
    except Exception:
        pass

    return content, marquee_el


def check_scenario(scenario, content, cfg):
    results = {"label": scenario["label"], "passed": True, "checks": []}
    full_text = (content.get("marquee_text", "") + " " +
                 content.get("eyebrow", "") + " " +
                 content.get("title", "")).upper()

    def check(name, expected, found, search_in=None):
        si = search_in if search_in is not None else full_text
        ok = expected.upper() in si.upper()
        results["checks"].append({"check": name, "expected": expected, "found": found, "passed": ok})
        if not ok:
            results["passed"] = False

    check("Eyebrow", scenario["expected_eyebrow"], content.get("eyebrow", "(not found)"))
    check("Title",   scenario["expected_title"],   content.get("title", "(not found)"))
    check("Description", scenario["expected_description"],
          content.get("description", ""),
          search_in=content.get("marquee_text", ""))

    buttons    = content.get("buttons", [])
    btn_hrefs  = [b["href"] for b in buttons]
    all_text   = " | ".join(b["text"] for b in buttons)
    all_href   = " | ".join(b["href"] for b in buttons)

    def url_matches(expected, found_list):
        exp_parsed = urlparse(expected)
        for found in found_list:
            if expected in found:
                return True
            if cfg["rewrite_domain"] and "esfcu.org" in expected:
                if exp_parsed.path == urlparse(found).path:
                    return True
        return False

    def find_btn(match_text):
        for b in buttons:
            if match_text.upper() in b["text"].upper():
                return b
        return None

    for i, (txt_key, aria_key, url_key) in enumerate([
        ("expected_btn1_text", "expected_btn1_aria", "expected_btn1_url"),
        ("expected_btn2_text", "expected_btn2_aria", "expected_btn2_url"),
    ], start=1):
        btn = find_btn(scenario[txt_key])
        btn_aria = btn["aria"] if btn else "(button not found)"

        results["checks"].append({
            "check": f"Button {i} text: '{scenario[txt_key]}'",
            "expected": scenario[txt_key], "found": all_text or "(none)",
            "passed": btn is not None,
        })
        if btn is None:
            results["passed"] = False

        aria_ok = scenario[aria_key].lower() == btn_aria.lower() if btn else False
        results["checks"].append({
            "check": f"Button {i} aria: '{scenario[aria_key]}'",
            "expected": scenario[aria_key], "found": btn_aria, "passed": aria_ok,
        })
        if not aria_ok:
            results["passed"] = False

        url_ok = url_matches(scenario[url_key], btn_hrefs)
        results["checks"].append({
            "check": f"Button {i} URL: '{scenario[url_key]}'",
            "expected": scenario[url_key], "found": all_href or "(none)", "passed": url_ok,
        })
        if not url_ok:
            results["passed"] = False

    img_combined = (content.get("image_bg", "") + " " + content.get("image_src", "")).lower()
    img_ok = scenario["expected_image"].lower() in img_combined
    results["checks"].append({
        "check": f"Image contains: '{scenario['expected_image']}'",
        "expected": scenario["expected_image"],
        "found": content.get("image_bg") or content.get("image_src") or "(not found)",
        "passed": img_ok,
    })
    if not img_ok:
        results["passed"] = False

    return results


def safe_name(text):
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_').lower()


MAX_RETRIES = 3
RETRY_SLEEP = 10  # seconds between retries


def main(env="stg", headed=False):
    cfg          = ENV_CONFIG[env]
    base_url     = cfg["base_url"]
    homepage_url = cfg["homepage"]
    search_url   = cfg["search_base"] + SCENARIO["search_term"]

    screenshots_dir = Path(__file__).parent / "screenshots_esfcu_using_pytest"
    screenshots_dir.mkdir(exist_ok=True)

    slug = safe_name(SCENARIO["label"])

    print(f"\n{'='*60}")
    print(f"  ESFCU High Yield Savings — Search Trigger [{env.upper()}]")
    print(f"{'='*60}")
    print(f"  Session init : {base_url}")
    print(f"  Search URL   : {search_url}")
    print(f"  Homepage     : {homepage_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page    = context.new_page()

        result     = None
        content    = {}
        marquee_el = None

        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\n  Attempt {attempt}/{MAX_RETRIES}")

            print("  Step 1: Session init...")
            page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)

            print("  Step 2: Search trigger...")
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)

            print("  Step 3: Homepage...")
            page.goto(homepage_url, wait_until="domcontentloaded", timeout=60000)

            for sel in MARQUEE_SELECTORS:
                try:
                    page.wait_for_selector(sel, timeout=10000, state="visible")
                    print(f"  Marquee found: {sel}")
                    break
                except Exception:
                    pass
            page.wait_for_timeout(4000)

            content, marquee_el = get_marquee_content(page)
            result = check_scenario(SCENARIO, content, cfg)

            if result["passed"]:
                print(f"  Correct ad found on attempt {attempt}.")
                break

            title_found = content.get("title", "")
            if "error" in title_found.lower():
                print(f"  Server error detected on attempt {attempt} (title: '{title_found}').")
            else:
                print(f"  Ad not found on attempt {attempt}.")

            if attempt < MAX_RETRIES:
                print(f"  Waiting {RETRY_SLEEP}s before retry...")
                time.sleep(RETRY_SLEEP)

        inject_url_banner(page, homepage_url)
        full_path = screenshots_dir / f"esfcu_{slug}_fullpage_{env}.png"
        page.screenshot(path=str(full_path), full_page=True)
        print(f"  Screenshot  : {full_path.name}")

        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n  Result: {status}")
        for chk in result["checks"]:
            icon = "PASS" if chk["passed"] else "FAIL"
            print(f"    {icon}  {chk['check']}")
            if not chk["passed"]:
                print(f"           Expected : {chk['expected']}")
                print(f"           Found    : {str(chk['found'])[:120]}")

        if marquee_el:
            try:
                crop_path = screenshots_dir / f"esfcu_{slug}_marquee_{env}.png"
                marquee_el.screenshot(path=str(crop_path))
                print(f"  Marquee crop: {crop_path.name}")
            except Exception as e:
                print(f"  Marquee crop failed: {e}")

        context.close()
        browser.close()

    return result


# ---------------------------------------------------------------------------
# Pytest test
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_esfcu_high_yield_savings_search(request):
    """Session init → search 'high yield savings' → homepage → validate marquee ad."""
    env = request.config.getoption("--env", default="stg")
    result = main(env=env, headed=False)
    if not result["passed"]:
        failures = [
            f"{c['check']}\n      Expected : {c['expected']}\n      Found    : {str(c['found'])[:120]}"
            for c in result["checks"] if not c["passed"]
        ]
        pytest.fail("ESFCU High Yield Savings scenario failed:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ESFCU High Yield Savings search trigger test")
    parser.add_argument("--env", choices=["stg", "prod"], default="stg")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    result = main(env=args.env, headed=args.headed)
    sys.exit(0 if result["passed"] else 1)
