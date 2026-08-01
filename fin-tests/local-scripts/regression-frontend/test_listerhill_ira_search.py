"""
Listerhill Credit Union — IRA Search Trigger Validation

Flow: session_init → search "ira" → homepage → validate fin-hero ad

Usage (pytest):
    pytest fin-ui-tests/test_listerhill_ira_search.py -v -s

Usage (standalone):
    python fin-ui-tests/test_listerhill_ira_search.py
"""

import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL    = "https://listerhill.com/?cb=1&debug_all=1&session_init=1"
HOMEPAGE    = "https://listerhill.com/"
SEARCH_BASE = "https://listerhill.com/search?query="

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots_listerhill"

SCENARIO = {
    "name":       "IRA",
    "search_term": "ira",
    "title":       "Your Retirement, on Your Terms",
    "subhead":     "Whether you're just starting out or catching up, we have IRA options designed to help you save smarter and retire with confidence.",
    "cta1_text":   "Open an Account",
    "cta1_url":    None,
    "cta2_text":   "Explore IRA Options",
    "cta2_url":    "https://listerhill.com/everyday-banking/savings/ira",
    "image_path":  "/uploads/Hero_IRA_1440x830.webp",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[–—―−—–−]", "-", text)
    return " ".join(text.split())


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _inject_url_banner(page, url: str) -> None:
    escaped = url.replace("'", "\\'")
    page.evaluate(f"""() => {{
        const e = document.getElementById('__url_banner__');
        if (e) e.remove();
        const d = document.createElement('div');
        d.id = '__url_banner__';
        d.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#0d1b2a;'
            + 'color:#e8f4f8;font-family:monospace;font-size:13px;padding:6px 12px;'
            + 'z-index:999999;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'
            + 'box-shadow:0 2px 6px rgba(0,0,0,.5)';
        d.textContent = '{escaped}';
        document.body.appendChild(d);
    }}""")


def _get_fin_hero_data(page) -> dict:
    return page.evaluate("""() => {
        const hero = document.querySelector('.fin-hero');
        if (!hero) return { found: false, title: '', subhead: '', buttons: [], bgImage: '' };

        const imgEl = hero.querySelector('[role="img"]');
        let bgImage = '';
        if (imgEl) {
            bgImage = imgEl.style.backgroundImage
                   || window.getComputedStyle(imgEl).backgroundImage || '';
        }

        const titleEl = hero.querySelector('h1, h2, h3');
        const title   = titleEl ? titleEl.innerText.trim() : '';

        const pEl    = hero.querySelector('p');
        const subhead = pEl ? pEl.innerText.trim() : '';

        const seen = new Set();
        const buttons = [];
        hero.querySelectorAll('a[href]').forEach(a => {
            const text = (a.innerText || a.textContent || '').trim();
            const href = a.href || '';
            const aria = a.getAttribute('aria-label') || '';
            const key  = text + '|' + href;
            if (text && href && !seen.has(key)) {
                seen.add(key);
                buttons.push({ text, href, aria });
            }
        });

        return { found: true, title, subhead, buttons, bgImage };
    }""")


def _find_hero_element(page):
    for sel in [".fin-hero", ".js-slider-wrapper", ".slider-wrapper"]:
        try:
            el = page.query_selector(sel)
            if el:
                box = el.bounding_box()
                if box and box["width"] > 400 and box["height"] > 200:
                    return el, sel
        except Exception:
            pass
    return None, None


def _image_matches(expected_path: str, bg_image: str) -> bool:
    if not expected_path:
        return False
    filename = expected_path.split("/")[-1]
    return expected_path in bg_image or filename in bg_image


def _find_btn(match_text: str, buttons: list) -> dict | None:
    for b in buttons:
        if match_text.upper() in b["text"].upper():
            return b
    return None


def _text_matches(expected: str, found: str) -> bool:
    exp = _normalize(expected).lower()
    fnd = _normalize(found).lower()
    return bool(exp) and bool(fnd) and (exp in fnd or fnd in exp)


# ---------------------------------------------------------------------------
# Pytest test
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_listerhill_ira_search():
    """Session init → search 'ira' → homepage → validate IRA fin-hero ad."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    sc      = SCENARIO
    sc_slug = _slug(sc["name"])
    search_url = SEARCH_BASE + quote_plus(sc["search_term"])

    print(f"\n{'='*60}")
    print(f"  Listerhill — {sc['name']} Search Trigger")
    print(f"{'='*60}")
    print(f"  Session init : {BASE_URL}")
    print(f"  Search URL   : {search_url}")
    print(f"  Homepage     : {HOMEPAGE}")

    with sync_playwright() as pw:
        headless = not (
            "--headed" in sys.argv
            or str(False) == str(__import__("os").environ.get("HEADLESS", "true")).lower()
        )
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1440, "height": 830})
        page    = context.new_page()

        print("\n  Step 1: Session init...")
        page.goto(BASE_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        print(f"  Step 2: Search trigger...")
        page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        print("  Step 3: Homepage...")
        page.goto(HOMEPAGE, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        fin_present = page.evaluate("() => !!document.querySelector('.fin-hero')")
        if not fin_present:
            print("  [retry] fin-hero not yet visible, waiting 3 more seconds...")
            page.wait_for_timeout(3000)

        hero_el, hero_sel = _find_hero_element(page)
        if hero_el:
            print(f"  Hero found via: {hero_sel}")
        else:
            print("  [warn] No hero element found")

        _inject_url_banner(page, HOMEPAGE)
        page.wait_for_timeout(300)

        fp_path = SCREENSHOTS_DIR / f"listerhill_{sc_slug}_fullpage.png"
        page.screenshot(path=str(fp_path), full_page=True)
        print(f"  Full-page screenshot: {fp_path.name}")

        if hero_el:
            try:
                hero_path = SCREENSHOTS_DIR / f"listerhill_{sc_slug}_hero.png"
                hero_el.screenshot(path=str(hero_path))
                print(f"  Hero crop: {hero_path.name}")
            except Exception as e:
                print(f"  [warn] Hero crop failed: {e}")

        data     = _get_fin_hero_data(page)
        title    = data.get("title",   "")
        subhead  = data.get("subhead", "")
        buttons  = data.get("buttons", [])
        bg_image = data.get("bgImage", "")

        context.close()
        browser.close()

    failures = []

    if not _text_matches(sc["title"], title):
        failures.append(f"Title — expected: '{sc['title']}' | found: '{title}'")
    else:
        print(f"  PASS  Title: {title!r}")

    if not _text_matches(sc["subhead"], subhead):
        failures.append(f"Subhead — expected: '{sc['subhead']}' | found: '{subhead}'")
    else:
        print(f"  PASS  Subhead")

    btn2 = _find_btn(sc["cta2_text"], buttons)
    if btn2 is None:
        failures.append(f"Button 2 text — expected: '{sc['cta2_text']}' | not found in buttons")
    else:
        print(f"  PASS  Button 2 text: {btn2['text']!r}")
        if not _text_matches(sc["cta2_url"], btn2.get("href", "")):
            failures.append(
                f"Button 2 URL — expected: '{sc['cta2_url']}' | found: '{btn2.get('href', '')}'"
            )
        else:
            print(f"  PASS  Button 2 URL: {btn2['href']!r}")

    if sc["image_path"] and not _image_matches(sc["image_path"], bg_image):
        failures.append(f"Image — expected path containing '{sc['image_path']}' | found: '{bg_image[:120]}'")
    elif sc["image_path"]:
        print(f"  PASS  Image contains '{sc['image_path']}'")

    if failures:
        msg = "\n  ".join([""] + failures)
        pytest.fail(f"Listerhill IRA scenario failed:{msg}")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Listerhill IRA search trigger test")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()
    if args.headed:
        import os
        os.environ["HEADLESS"] = "false"
    test_listerhill_ira_search()
