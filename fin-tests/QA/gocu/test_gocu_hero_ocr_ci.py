# QA version of test_gocu_hero_ocr_ci with resilient #main hero handling only (updated links for GOCU and more fixes for font waits)

import asyncio
import pytest
import pytest_asyncio
import sys
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from PIL import Image, ImageChops, ImageStat, ImageFilter
import pytesseract
from pytesseract import TesseractNotFoundError

# NEW: auto-headless in CI; override with HEADLESS env
HEADLESS = (os.getenv("CI", "").lower() in {"true", "1", "yes"}) or (os.getenv("HEADLESS", "").lower() in {"true", "1", "yes"})
print(f"[CI] HEADLESS={HEADLESS}")

# =====================
# Tesseract configuration
# =====================

def _configure_tesseract() -> bool:
    try:
        _ = pytesseract.get_tesseract_version()
        return True
    except Exception:
        pass
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for exe in possible_paths:
        if os.path.exists(exe):
            pytesseract.pytesseract.tesseract_cmd = exe
            try:
                _ = pytesseract.get_tesseract_version()
                print(f"Using Tesseract at: {exe}")
                return True
            except Exception:
                continue
    return False

TESSERACT_OK = _configure_tesseract()

# =====================
# File helpers
# =====================

def clear_screenshots_directory(directory: str | Path):
    directory = Path(directory)
    if directory.exists():
        for p in directory.iterdir():
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
            except Exception as e:
                print(f"Failed to delete {p}. Reason: {e}")
    else:
        directory.mkdir(parents=True, exist_ok=True)


async def save_page_source(page, filepath: str | Path):
    try:
        html_content = await page.content()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

# =====================
# GitHub baseline download / resolve
# =====================

def _github_tree_to_raw(tree_url: str, filename: str) -> str:
    parsed = urlparse(tree_url)
    parts = [p for p in parsed.path.strip('/').split('/') if p]
    if len(parts) < 4 or parts[2] != 'tree':
        raise ValueError(f"Not a GitHub tree URL: {tree_url}")
    owner, repo, _, branch, *path_parts = parts
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    dir_path = '/'.join(path_parts)
    raw_url = f"{raw_base}/{dir_path}/{filename}" if dir_path else f"{raw_base}/{filename}"
    return raw_url


def download_baseline_from_github(tree_url: str, filename: str, dest_path: Path) -> Path:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    raw_url = _github_tree_to_raw(tree_url, filename)
    print(f"[BASELINE] Resolving GitHub raw URL: {raw_url}")
    try:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        headers = {"User-Agent": "hero-ocr-ci"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = Request(raw_url, headers=headers)
        with urlopen(req) as resp:
            status = getattr(resp, 'status', 200)
            if status != 200:
                raise RuntimeError(f"HTTP {status} while fetching baseline from {raw_url}")
            data = resp.read()
        with open(dest_path, 'wb') as f:
            f.write(data)
        print(f"[BASELINE] Downloaded to: {dest_path} ({len(data)} bytes)")
        return dest_path
    except Exception as e:
        raise RuntimeError(f"Failed to download baseline from GitHub: {e}")


def resolve_baseline_image(*, baseline_filename: str, test_dir: Path, baseline_rel_dir: str,
                           github_tree_dir: str, download_dest: Path) -> Path:
    local1 = Path(test_dir) / baseline_rel_dir / baseline_filename
    if local1.exists():
        print(f"[BASELINE] Using local file: {local1}")
        return local1

    ws = os.getenv("GITHUB_WORKSPACE")
    if ws:
        local2 = Path(ws) / "fin-tests" / "QA" / baseline_rel_dir / baseline_filename
        if local2.exists():
            print(f"[BASELINE] Using workspace file: {local2}")
            return local2

    print("[BASELINE] Local file not found; attempting download...")
    return download_baseline_from_github(github_tree_dir, baseline_filename, download_dest)

# =====================
# Network-quiet helpers
# =====================

async def wait_for_network_quiet(page, idle_ms: int = 1200, max_wait: int = 15000):
    loop = asyncio.get_event_loop()
    in_flight = {"count": 0}
    last_change = {"t": loop.time()}

    def _bump(delta: int):
        in_flight["count"] += delta
        last_change["t"] = loop.time()

    def on_req(_):
        _bump(+1)

    def on_done(_):
        _bump(-1)

    page.on("request", on_req)
    page.on("requestfinished", on_done)
    page.on("requestfailed", on_done)

    try:
        start = loop.time()
        while True:
            now = loop.time()
            if in_flight["count"] <= 0 and (now - last_change["t"]) * 1000 >= idle_ms:
                return
            if (now - start) * 1000 >= max_wait:
                print("wait_for_network_quiet: max_wait reached, continuing.")
                return
            await asyncio.sleep(0.1)
    finally:
        try:
            page.remove_listener("request", on_req)
            page.remove_listener("requestfinished", on_done)
            page.remove_listener("requestfailed", on_done)
        except Exception:
            pass


async def navigate_and_settle(page, url: str, ready_selector: str | None = None,
                              wait_until: str = "domcontentloaded", nav_timeout: int = 45000,
                              idle_ms: int = 900, max_wait: int = 12000):
    loop = asyncio.get_event_loop()
    in_flight = {"count": 0}
    last_change = {"t": loop.time()}

    def _bump(delta: int):
        in_flight["count"] += delta
        last_change["t"] = loop.time()

    def on_req(_):
        _bump(+1)

    def on_done(_):
        _bump(-1)

    page.on("request", on_req)
    page.on("requestfinished", on_done)
    page.on("requestfailed", on_done)

    try:
        await page.goto(url, wait_until=wait_until, timeout=nav_timeout)
        if ready_selector:
            try:
                await page.wait_for_selector(ready_selector, state="visible", timeout=min(15000, nav_timeout))
                print(f"navigate_and_settle: '{ready_selector}' is visible.")
            except PlaywrightTimeoutError:
                print(f"navigate_and_settle: '{ready_selector}' not visible before quiet; continuing.")
        start = asyncio.get_event_loop().time()
        while True:
            now = asyncio.get_event_loop().time()
            if in_flight["count"] <= 0 and (now - last_change["t"]) * 1000 >= idle_ms:
                print("navigate_and_settle: network quiet.")
                return
            if (now - start) * 1000 >= max_wait:
                print("navigate_and_settle: max_wait reached, continuing.")
                return
            await asyncio.sleep(0.1)
    finally:
        try:
            page.remove_listener("request", on_req)
            page.remove_listener("requestfinished", on_done)
            page.remove_listener("requestfailed", on_done)
        except Exception:
            pass

# =====================
# DOM helpers / visual stability
# =====================

async def wait_for_js_and_element(page, selector, timeout=45000):
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=timeout)
        print("DOM content loaded.")
    except PlaywrightTimeoutError:
        print("Timeout while waiting for DOM content loaded.")
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        print(f"Element {selector} is visible.")
    except PlaywrightTimeoutError:
        print(f"Timeout waiting for element: {selector}")


async def freeze_visual_changes(page):
    # Support both legacy #homeSlider and gocu's .hero under #main  ⟵ FIXED
    await page.add_style_tag(content="""
      * { transition: none !important; animation: none !important; }
      #homeSlider .slick-track, #main .hero .slick-track { transform: none !important; }
      #homeSlider .slick-slide,  #main .hero .slick-slide  { opacity: 1 !important; }
      #homeSlider video, #homeSlider .bg, #homeSlider picture img, #homeSlider .slide img,
      #main .hero video, #main .hero .bg, #main .hero picture img, #main .hero .slide img {
        opacity: 0 !important; /* keep copy visible, hide background */
      }
    """)
    await page.evaluate("""
        for (const v of document.querySelectorAll('video')) {
            try { v.pause(); v.currentTime = 0; } catch (e) {}
        }
        try { window.stop && window.stop(); } catch(e) {}
    """)
    await page.wait_for_timeout(50)


async def align_viewport_to_baseline(page, baseline_img_path: Path, extra_height: int = 400) -> Tuple[int, int]:
    img = Image.open(baseline_img_path)
    bw, bh = img.size
    await page.set_viewport_size({"width": bw, "height": max(bh + extra_height, 700)})
    await page.add_style_tag(content="html,body{overflow-y:hidden!important}")
    await page.wait_for_timeout(50)
    return bw, bh

# =====================
# OCR + PIXEL comparison (enhanced)
# =====================

def _normalize_text(txt: str) -> str:
    return " ".join(txt.split()).strip().lower()


def _apply_preprocess(img: Image.Image, blur_radius: int = 0) -> Image.Image:
    out = img.convert('RGB')
    if blur_radius > 0:
        out = out.filter(ImageFilter.GaussianBlur(blur_radius))
    return out


def _compute_pixel_diff_metrics(base_img: Image.Image, curr_img: Image.Image) -> Tuple[float, float]:
    w = min(base_img.width, curr_img.width)
    h = min(base_img.height, curr_img.height)
    if base_img.size != (w, h):
        base_img = base_img.crop((0, 0, w, h))
    if curr_img.size != (w, h):
        curr_img = curr_img.crop((0, 0, w, h))

    diff = ImageChops.difference(base_img, curr_img)
    stat = ImageStat.Stat(diff)
    overall_rms = sum(stat.rms) / len(stat.rms)

    g = diff.convert("L")
    hist = g.histogram()
    total = sum(hist)
    changed = total - hist[0]
    percent_changed = (changed / total * 100.0) if total else 0.0
    return overall_rms, percent_changed


def compare_images_ocr_and_pixels(
    baseline_path: str | Path,
    current_path: str | Path,
    rms_threshold: float = 3.0,
    change_threshold: float = 2.0,
    blur_radius: int = 0,
) -> Tuple[bool, bool, str]:
    baseline_path = Path(baseline_path)
    current_path = Path(current_path)
    print(f"baseline_path is {baseline_path} and current_path is {current_path}")

    if not baseline_path.exists():
        return False, False, f"Baseline image not found: {baseline_path}"
    if not current_path.exists():
        return False, False, f"Current image not found: {current_path}"

    base_img_raw = Image.open(baseline_path)
    curr_img_raw = Image.open(current_path)
    base_img = _apply_preprocess(base_img_raw, blur_radius)
    curr_img = _apply_preprocess(curr_img_raw, blur_radius)

    if not TESSERACT_OK:
        ocr_match = False
        ocr_msg = "OCR unavailable on this machine."
    else:
        try:
            base_txt = _normalize_text(pytesseract.image_to_string(base_img))
            curr_txt = _normalize_text(pytesseract.image_to_string(curr_img))
            print(f"[OCR] baseline: '{base_txt}'")
            print(f"[OCR] current : '{curr_txt}'")
            ocr_match = bool(base_txt and curr_txt and base_txt == curr_txt)
            ocr_msg = (
                "OCR text matches." if ocr_match else
                f"""OCR text differs.
Baseline: '{base_txt}'
Current : '{curr_txt}'"""
            )
        except (TesseractNotFoundError, FileNotFoundError) as e:
            ocr_match = False
            ocr_msg = f"OCR failed: {e}"

    overall_rms, pct_changed = _compute_pixel_diff_metrics(base_img, curr_img)
    pixels_ok = (overall_rms <= rms_threshold) and (pct_changed <= change_threshold)
    px_msg = (
        f"Pixel diff RMS={overall_rms:.2f} (≤ {rms_threshold}) and changed={pct_changed:.2f}% (≤ {change_threshold:.0f}%) → "
        f"{'OK' if pixels_ok else 'DIFF'}"
    )

    details = f"{ocr_msg} {px_msg}"
    return ocr_match, pixels_ok, details

# =====================
# Browser fixture (CI-ready)
# =====================

@pytest_asyncio.fixture
async def browser(request):
    param_user = request.param.get("username") if hasattr(request, 'param') and request.param else None
    param_pass = request.param.get("password") if hasattr(request, 'param') and request.param else None
    username = os.getenv("BASIC_AUTH_USER") or param_user or "gocu"
    password = os.getenv("BASIC_AUTH_PASS") or param_pass or "gocu"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=HEADLESS,
            args=[
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--disable-extensions",
                "--disable-background-timer-throttling",
                "--no-default-browser-check",
                "--no-first-run",
            ],
        )
        context = await browser.new_context(
            http_credentials={"username": username, "password": password},
            device_scale_factor=1,
            viewport={"width": 1280, "height": 900},
        )

        # NEW ✨: Override FontFaceSet across ALL frames (including iframes) *before* any page scripts run
        await context.add_init_script(
            """
            (() => {
              function patch(win){
                try{
                  const FFS = win.FontFaceSet && win.FontFaceSet.prototype;
                  if(FFS){
                    try{ Object.defineProperty(FFS, 'ready', { get(){ return Promise.resolve(this); } }); }catch(e){}
                    try{ FFS.load = async function(){ return []; }; }catch(e){}
                  }
                }catch(_){ }
              }
              patch(window);
              // Some pages create/attach iframes dynamically; hook to patch them too
              try{
                const mo = new MutationObserver((muts)=>{
                  for(const m of muts){
                    for(const n of m.addedNodes){
                      if(n && n.tagName === 'IFRAME' && n.contentWindow){
                        try{ patch(n.contentWindow); }catch(e){}
                      }
                    }
                  }
                });
                mo.observe(document, {childList:true, subtree:true});
              }catch(_){ }
            })();
            """
        )  # ⟵ NEW (stronger)

        # NEW: Block *font* resource_type everywhere (covers no-extension font URLs too)
        await context.route("**/*", lambda route: route.abort() if route.request.resource_type == 'font' else route.continue_())  # ⟵ NEW

        # (kept) optional global switch via env to also block font file extensions from odd CDNs
        if os.getenv("BLOCK_FONT_EXT", "1").lower() in {"1", "true", "yes"}:  # ⟵ NEW
            await context.route("**/*.{woff,woff2,ttf,otf}", lambda route: route.abort())  # ⟵ NEW

        context.set_default_timeout(45000)
        context.set_default_navigation_timeout(45000)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()

# =====================
# The test (with DOM assertion) + baseline resolve
# =====================

@pytest.mark.asyncio
@pytest.mark.parametrize("browser", [{"username": "OneAZ", "password": "pugs r potatoes!3"}], indirect=True)
async def test_gocu_hero_ocr_ci(
    browser,
    homepage_url="https://georgiasownstg.wpengine.com/?api=stg",
    test_scenario_url="https://georgiasownstg.wpengine.com/checking/student-access",
    expected_heading="Level up your financial game",
    hero_heading_selector="#main > section:nth-child(1) > div > div",
    client="gocu",
    html_finalytics_prod_cloudfront="//d1v4vw9mwf7wyh.cloudfront.net",
    html_finalytics_prod_cloudfront2="https://d1v4vw9mwf7wyh.cloudfront.net",
    finalytics_css_tag="finalytics-function_div.css",
    finalytics_js_tag="finalytics.js",
    finalytics_function_js_tag="finalytics-function.js",
    finalytics_settings_div_js_tag="settings_div.js",
    unexpected_in_hero_selectors: Optional[list[str]] = None,
    baseline_github_tree_dir: str = "https://github.com/carina-finai/tests/tree/tests/fin-tests/QA/gocu/baseline",
    baseline_filename: str = "hero_ad_only_baseline.png",
):
    print(f"Starting {client} hero ad test (CI-ready)...")
    print(sys.version)

    test_dir = Path(__file__).resolve().parent
    screenshots_root = test_dir / f"screenshots_{client}_using_pytest"
    current_dir = screenshots_root / "current"
    clear_screenshots_directory(current_dir)

    print(f"Resolved test_dir: {test_dir}")
    print(f"Resolved screenshots_root: {screenshots_root}")
    print(f"Resolved current_dir: {current_dir}")

    downloaded_baseline_path = current_dir / baseline_filename
    try:
        baseline_hero_path = resolve_baseline_image(
            baseline_filename=baseline_filename,
            test_dir=test_dir,
            baseline_rel_dir="gocu/baseline",
            github_tree_dir=baseline_github_tree_dir,
            download_dest=downloaded_baseline_path,
        )
    except Exception as e:
        pytest.fail(f"Failed to prepare baseline: {e}")

    page = await browser.new_page()

    # EXTRA: also inject patches on this page specifically (defense-in-depth)  ⟵ NEW
    await page.add_init_script(
        """
        (() => {
          try{
            const FFS = window.FontFaceSet && window.FontFaceSet.prototype;
            if(FFS){
              try{ Object.defineProperty(FFS, 'ready', { get(){ return Promise.resolve(this); } }); }catch(e){}
              try{ FFS.load = async function(){ return []; }; }catch(e){}
            }
          }catch(_){ }
        })();
        """
    )  # ⟵ NEW

    # EXTRA: force system fonts (prevents layout shift even with fonts blocked)
    await page.add_style_tag(content="*{font-family: Arial, Helvetica, sans-serif !important}")  # ⟵ CHANGED

    # Reduce motion globally to limit any animation work during screenshots  ⟵ NEW
    try:
        await page.emulate_media(reduced_motion='reduce')  # ⟵ NEW
    except Exception:
        pass

    specific_js_files = [
        'finalytics.js',
        'finalytics-function.js',
        'settings_div.js',
        'settings.js',
        'controlbar.js',
        'settings.js?code=gocu',
        'settings.js?code=gocu:80',
    ]
    error_tracker = []

    def detect_js_errors_from_specific_files(client: str, page, specific_files: list[str], error_tracker: list[str], screenshots_directory: str | Path):
        screenshots_directory = Path(screenshots_directory)
        async def handle_console_message(msg):
            try:
                location = msg.location
                file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
                screenshots_directory.mkdir(parents=True, exist_ok=True)
                if msg.type == 'error' and file_name.endswith('.js') and file_name in specific_files:
                    error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
                    print(error_message)
                    error_tracker.append(error_message)
                    screenshot_path = screenshots_directory / f"js_error_{client}.png"
                    await page.screenshot(path=str(screenshot_path), animations='disabled', timeout=15000)  # keep fast  ⟵ CHANGED
                    print(f"Screenshot of JS error saved at {screenshot_path} for client {client}")
            except Exception as e:
                print(f"Console handler failed: {e}")
        if not getattr(page, "_js_error_handler_set", False):
            page.on('console', lambda msg: asyncio.create_task(handle_console_message(msg)))
            setattr(page, "_js_error_handler_set", True)

    detect_js_errors_from_specific_files(client, page, specific_js_files, error_tracker, current_dir)

    print(f"About to go to home_url {homepage_url}")
    try:
        print(f"Going to homepage_url {homepage_url}...")
        await navigate_and_settle(
            page,
            homepage_url,
            ready_selector="#main",
            wait_until="domcontentloaded",
            nav_timeout=45000,
            idle_ms=900,
            max_wait=12000,
        )

        # Full-page screenshot with animations disabled, *and* fonts blocked/patched  ⟵ CHANGED
        await page.screenshot(path=str(current_dir / 'homepage_screenshot.png'), full_page=True, animations='disabled', timeout=20000)
        await save_page_source(page, current_dir / 'homepage_source.html')

        print(f"Going to test_scenario_url {test_scenario_url}...")
        await navigate_and_settle(
            page,
            test_scenario_url,
            ready_selector="body",
            wait_until="domcontentloaded",
            nav_timeout=45000,
            idle_ms=900,
            max_wait=12000,
        )

        await page.screenshot(path=str(current_dir / 'product_page_for_ad_screenshot.png'), full_page=True, animations='disabled', timeout=20000)  # ⟵ CHANGED

        print(f"Returning to homepage_url {homepage_url} to view the ad...")
        await navigate_and_settle(
            page,
            homepage_url,
            ready_selector="#main",
            wait_until="domcontentloaded",
            nav_timeout=45000,
            idle_ms=900,
            max_wait=12000,
        )

        # Freeze motion and align viewport BEFORE capture
        await freeze_visual_changes(page)
        await align_viewport_to_baseline(page, baseline_hero_path)
        await page.evaluate("window.scrollTo(0,0)")

        # --- DOM assertion inside hero ---
        if not unexpected_in_hero_selectors:
            print("[HERO-CLEAN] No unexpected selector list provided; skipping hero DOM check.")
        else:
            for sel in unexpected_in_hero_selectors:
                scoped = f"#main .hero {sel}" if not sel.strip().startswith("#main .hero") else sel  # ⟵ FIXED
                cnt = await page.locator(scoped).count()
                if cnt > 0:
                    try:
                        first = page.locator(scoped).first
                        snippet = await first.evaluate("(el)=>el.outerHTML.slice(0,300)")
                    except Exception as e:
                        snippet = f"<unable to capture snippet: {e}>"
                    print(f"[UNEXPECTED-HERO] Found {cnt} element(s) matching '{sel}' inside #main .hero. Sample: {snippet}")
                    pytest.fail(f"Unexpected element in hero: selector '{sel}' matched {cnt} element(s).")
                else:
                    print(f"[HERO-CLEAN] No matches for '{sel}' inside #main .hero.")

        # ==== HERO RESOLUTION (robust, no page.wait_for_function) ====
        HERO_SEL = "#main .hero"  # ⟵ FIXED: definitive selector for gocu

        hero_loc = page.locator(HERO_SEL).first
        try:
            await hero_loc.wait_for(state="attached", timeout=10000)
            print("[HERO] Attached.")
        except PlaywrightTimeoutError:
            print("[HERO] Not attached in 10s; proceeding with JS bbox fallback.")

        await page.evaluate(
            "sel => { const el=document.querySelector(sel); if(el){ el.style.visibility='visible'; el.style.opacity='1'; el.scrollIntoView({block:'start'}); } }",
            HERO_SEL,
        )

        bbox = await page.evaluate(
            """
            (sel) => {
              const el = document.querySelector(sel);
              if (!el) return null;
              const r = el.getBoundingClientRect();
              return {x:r.x, y:r.y, width:Math.max(1,r.width), height:Math.max(1,r.height)};
            }
            """,
            HERO_SEL,
        )

        if not bbox:
            print("Hero bbox not resolved; using baseline-sized fallback clip at top of page.")
            try:
                bw, bh = Image.open(baseline_hero_path).size
            except Exception:
                bw, bh = (1280, 540)
            bbox = {"x": 0, "y": 0, "width": bw, "height": max(1, bh)}
        print(f"DEBUG hero bbox (w x h): {bbox['width']} x {bbox['height']}")

        current_hero_path = current_dir / 'hero_ad_only.png'

        try:
            if await hero_loc.count() > 0:
                await hero_loc.screenshot(path=str(current_hero_path), animations='disabled', timeout=20000)
            else:
                raise Exception("hero locator not found; using page.clip")
        except Exception:
            await page.screenshot(
                path=str(current_hero_path),
                clip={"x": max(0, bbox['x']), "y": max(0, bbox['y']), "width": bbox['width'], "height": bbox['height']},
                animations='disabled',
                timeout=20000,
            )
        print("Saved hero section screenshot as hero_ad_only.png")

        # === OCR + PIXEL comparison with tunable thresholds & blur ===
        ocr_match, pixels_ok, details = compare_images_ocr_and_pixels(
            baseline_hero_path,
            current_hero_path,
            rms_threshold=float(os.getenv("HERO_RMS_THRESHOLD", "12.0")),
            change_threshold=float(os.getenv("HERO_CHANGE_THRESHOLD", "60.0")),
            blur_radius=int(os.getenv("HERO_BLUR_RADIUS", "2")),
        )
        print(f"[COMPARE] {details}")

        if ocr_match and not pixels_ok:
            try:
                control_nav_count = await page.locator(".control-nav").count()
            except Exception:
                control_nav_count = -1
            extra = f" OCR PASSED, but pixel differences detected. '.control-nav' count={control_nav_count}."
            pytest.fail("Hero image mismatch: " + details + extra)

        if not ocr_match:
            pytest.fail(f"Hero image mismatch (OCR): {details}")
        if not pixels_ok:
            pytest.fail(f"Hero image mismatch (Pixels): {details}")

        print("Hero image comparison passed (OCR + Pixels).")

        await wait_for_js_and_element(page, hero_heading_selector, timeout=45000)
        await page.wait_for_selector(hero_heading_selector, state='visible', timeout=45000)

        html_content = await page.content()
        desired_cloudfront_urls = (html_finalytics_prod_cloudfront, html_finalytics_prod_cloudfront2)
        if not any(tag in html_content for tag in desired_cloudfront_urls):
            pytest.fail(f"HTML Finalytics STG cloudfront URL '{html_finalytics_prod_cloudfront2}' NOT FOUND in the page source!")
        else:
            print(f"HTML Finalytics STG cloudfront URL '{html_finalytics_prod_cloudfront2}' exists in the homepage source.")

        desired_finalytics_tags = [
            finalytics_css_tag,
            finalytics_js_tag,
            finalytics_function_js_tag,
            finalytics_settings_div_js_tag,
        ]
        missing_desired_finalytics_tags = [tag for tag in desired_finalytics_tags if tag not in html_content]
        if missing_desired_finalytics_tags:
            pytest.fail(
                f"The following Finalytics finalytics tags were NOT found in the page source: {', '.join(missing_desired_finalytics_tags)}"
            )
        print(
            f"The following Finalytics finalytics tags were found in the page source: {', '.join(desired_finalytics_tags)}"
        )

    except PlaywrightTimeoutError as e:
        pytest.fail(f"Timeout encountered during navigation: {e}")
    finally:
        if error_tracker:
            pytest.fail(f"Detected JavaScript errors: {error_tracker}")
        else:
            print(f"No JavaScript errors detected for {client}.")
