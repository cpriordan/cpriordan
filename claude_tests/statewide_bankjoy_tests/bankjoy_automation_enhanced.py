"""
Enhanced Bankjoy Site Automation Testing Script with Config Support
Tests different core products with screenshots at various stages
"""

import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page
from typing import Dict, List, Optional
import time
from datetime import datetime


class BankjoyTesterEnhanced:
    def __init__(self, config_path: str = "config.json"):
        """Initialize tester with configuration"""
        self.config = self._load_config(config_path)
        self.base_url = self.config['base_url']
        self.signin_url = self.config['signin_url']
        self.dashboard_url = self.config['dashboard_url']
        self.username = self.config['credentials']['username']
        self.password = self.config['credentials']['password']
        self.core_products = self.config['core_products']
        self.selectors = self.config['selectors']
        self.timeouts = self.config['timeouts']
        self.browser_config = self.config['browser']
        self.screenshot_config = self.config['screenshots']
        self.screenshot_base_dir = Path(self.screenshot_config['base_directory'])
        
        # Test results tracking
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        self._create_directories()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[WARN] Config file not found: {config_path}, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"[WARN] Error parsing config file: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'base_url': "https://statewide.stage.bankjoy.com/?cb=1&session_init=1&debug_all=1",
            'signin_url': "https://statewide.stage.bankjoy.com/?cb=1&session_init=1",
            'dashboard_url': "https://statewide.stage.bankjoy.com/consumer/main/dashboard",
            'credentials': {
                'username': "cbracey25",
                'password': "SwFCU2025$$$"
            },
            'core_products': [
                "checking account", "cd", "equipment loan", "personal loan",
                "rv loan", "ira", "credit card", "boat loan", "car loan", "savings account"
            ],
            'selectors': {
                'login': {
                    'username': "#username",
                    'password': "#password",
                    'tile_ad_wrapper': "#finalytics-information-wrapper-ad",
                    'tile_ad_cta': "#finalytics-information-wrapper-ad > div > div:nth-child(3) > div > a"
                },
                'overlay': {
                    'broadcast_ad': "#finalytics-broadcast-ad",
                    'broadcast_ad_cta': "#finalytics-broadcast-ad > div:nth-child(3) > div > a",
                    'close_button': "#mat-mdc-dialog-0 > div > div > app-broadcast-ad-dialog > button"
                },
                'card': {
                    'tile_ad_image': "#finalytics-tile-ad > div > img",
                    'tile_ad_cta': "#finalytics-tile-ad > div > div > div > a"
                }
            },
            'timeouts': {
                'element_wait': 10000,
                'page_load': 30000,
                'scroll_delay': 500,
                'max_scrolls': 10
            },
            'browser': {
                'headless': False,
                'viewport': {'width': 1920, 'height': 1080},
                'card_ad_zoom': 0.8
            },
            'screenshots': {
                'base_directory': "statewide",
                'full_page': True,
                'subdirectories': {
                    'login': "olb/login/core_products",
                    'overlay': "olb/overlay/core_products",
                    'card': "olb/card/core_products"
                }
            }
        }
    
    def _create_directories(self):
        """Create necessary directories for screenshots"""
        subdirs = self.screenshot_config['subdirectories']
        for subdir in subdirs.values():
            directory = self.screenshot_base_dir / subdir
            directory.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created directories in {self.screenshot_base_dir}")
    
    def _sanitize_filename(self, core_product: str) -> str:
        """Convert core product name to valid filename"""
        return core_product.replace(" ", "_").replace("/", "_")
    
    async def wait_for_element(self, page: Page, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for element to be visible"""
        if timeout is None:
            timeout = self.timeouts['element_wait']
        try:
            await page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception as e:
            print(f"  [WARN] Element {selector} not found: {str(e)[:50]}")
            return False
    
    async def scroll_to_element(self, page: Page, selector: str) -> bool:
        """Scroll to make element visible"""
        try:
            await page.evaluate(f"""
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            """)
            await page.wait_for_timeout(1000)
            return True
        except Exception as e:
            print(f"  [WARN] Could not scroll to {selector}: {str(e)[:50]}")
            return False
    
    async def find_element_with_scroll(self, page: Page, selector: str) -> bool:
        """Try to find element by scrolling down"""
        max_scrolls = self.timeouts['max_scrolls']
        scroll_delay = self.timeouts['scroll_delay']
        
        for i in range(max_scrolls):
            if await page.locator(selector).is_visible():
                return True
            await page.evaluate(f"window.scrollBy(0, 300)")
            await page.wait_for_timeout(scroll_delay)
        
        return False
    
    async def test_login_page_ad(self, page: Page, core_product: str) -> Dict:
        """Step 1: Test login page tile ad"""
        print(f"\n  -> Step 1: Testing login page ad")
        result = {
            'step': 'login_page_ad',
            'success': False,
            'screenshot': None,
            'cta_verified': False,
            'errors': []
        }
        
        try:
            # Navigate to login page with products_recommended parameter
            url = f"{self.base_url}&products_recommended={core_product}"
            await page.goto(url, wait_until="networkidle", timeout=self.timeouts['page_load'])
            
            # Refresh the page
            await page.reload(wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Find the overlay by scrolling
            overlay_selector = self.selectors['login']['tile_ad_wrapper']
            found = await self.find_element_with_scroll(page, overlay_selector)
            
            if found:
                await self.scroll_to_element(page, overlay_selector)
                
                # Take screenshot
                filename = self._sanitize_filename(core_product) + "_login.png"
                screenshot_path = self.screenshot_base_dir / self.screenshot_config['subdirectories']['login'] / filename
                await page.screenshot(
                    path=str(screenshot_path),
                    full_page=self.screenshot_config['full_page']
                )
                result['screenshot'] = str(screenshot_path)
                print(f"  [OK] Screenshot saved: {screenshot_path}")
                
                # Verify CTA button
                cta_selector = self.selectors['login']['tile_ad_cta']
                try:
                    cta_element = page.locator(cta_selector)
                    if await cta_element.is_visible():
                        cta_text = await cta_element.inner_text()
                        cta_href = await cta_element.get_attribute("href")
                        print(f"  [OK] CTA text: {cta_text}")
                        print(f"  [OK] CTA href: {cta_href}")
                        result['cta_verified'] = True
                        result['cta_text'] = cta_text
                        result['cta_href'] = cta_href
                    else:
                        result['errors'].append("CTA button not visible")
                except Exception as e:
                    result['errors'].append(f"CTA verification failed: {str(e)}")
                
                result['success'] = True
            else:
                result['errors'].append("Login page overlay not found")
        
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            print(f"  [FAIL] Error: {str(e)}")
        
        return result
    
    async def signin(self, page: Page) -> Dict:
        """Step 2a: Sign in to the application"""
        print(f"\n  -> Step 2a: Signing in")
        result = {
            'step': 'signin',
            'success': False,
            'errors': []
        }
        
        try:
            # Navigate to signin page
            await page.goto(self.signin_url, wait_until="networkidle", timeout=self.timeouts['page_load'])
            
            # Wait for and fill username
            username_selector = self.selectors['login']['username']
            if await self.wait_for_element(page, username_selector):
                await page.fill(username_selector, self.username)
                print(f"  [OK] Entered username")
            else:
                result['errors'].append("Username field not found")
                return result
            
            # Fill password
            password_selector = self.selectors['login']['password']
            await page.fill(password_selector, self.password)
            print(f"  [OK] Entered password")
            
            # Click Continue button
            continue_selectors = [
                "button:has-text('Continue')",
                "button[type='submit']",
                "button.continue-button"
            ]
            
            clicked = False
            for selector in continue_selectors:
                try:
                    if await page.locator(selector).is_visible():
                        await page.locator(selector).click()
                        clicked = True
                        print(f"  [OK] Clicked Continue")
                        break
                except:
                    continue
            
            if not clicked:
                print(f"  [WARN] Continue button not found, trying Enter")
                await page.keyboard.press("Enter")
            
            # Wait for navigation
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("networkidle")
            print(f"  [OK] Signed in successfully")
            result['success'] = True
        
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            print(f"  [FAIL] Signin error: {str(e)}")
        
        return result
    
    async def test_overlay_ad(self, page: Page, core_product: str) -> Dict:
        """Step 2b: Test overlay/broadcast ad after login"""
        print(f"\n  -> Step 2b: Testing overlay ad")
        result = {
            'step': 'overlay_ad',
            'success': False,
            'screenshot': None,
            'cta_verified': False,
            'errors': []
        }
        
        try:
            # Refresh page
            await page.reload(wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Find broadcast overlay
            overlay_selector = self.selectors['overlay']['broadcast_ad']
            found = await self.find_element_with_scroll(page, overlay_selector)
            
            if found:
                await self.scroll_to_element(page, overlay_selector)
                
                # Take screenshot
                filename = self._sanitize_filename(core_product) + "_overlay.png"
                screenshot_path = self.screenshot_base_dir / self.screenshot_config['subdirectories']['overlay'] / filename
                await page.screenshot(
                    path=str(screenshot_path),
                    full_page=self.screenshot_config['full_page']
                )
                result['screenshot'] = str(screenshot_path)
                print(f"  [OK] Screenshot saved: {screenshot_path}")
                
                # Verify CTA
                cta_selector = self.selectors['overlay']['broadcast_ad_cta']
                try:
                    cta_element = page.locator(cta_selector)
                    if await cta_element.is_visible():
                        cta_text = await cta_element.inner_text()
                        cta_href = await cta_element.get_attribute("href")
                        print(f"  [OK] CTA text: {cta_text}")
                        print(f"  [OK] CTA href: {cta_href}")
                        result['cta_verified'] = True
                        result['cta_text'] = cta_text
                        result['cta_href'] = cta_href
                except Exception as e:
                    result['errors'].append(f"CTA verification failed: {str(e)}")
                
                result['success'] = True
            else:
                result['errors'].append("Overlay not found")
        
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            print(f"  [FAIL] Error: {str(e)}")
        
        return result
    
    async def close_overlay(self, page: Page) -> Dict:
        """Step 3a: Close the overlay"""
        print(f"\n  -> Step 3a: Closing overlay")
        result = {
            'step': 'close_overlay',
            'success': False,
            'errors': []
        }
        
        try:
            # Try multiple close button selectors
            close_selectors = [
                self.selectors['overlay']['close_button'],
                "button[aria-label='Close']",
                ".close-button",
                "button.mat-mdc-dialog-close"
            ]
            
            closed = False
            for selector in close_selectors:
                try:
                    if await page.locator(selector).is_visible():
                        await page.locator(selector).click()
                        closed = True
                        print(f"  [OK] Overlay closed")
                        break
                except:
                    continue
            
            if not closed:
                print(f"  [WARN] Close button not found, pressing Escape")
                await page.keyboard.press("Escape")
            
            await page.wait_for_timeout(1000)
            result['success'] = True
        
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            print(f"  [FAIL] Error: {str(e)}")
        
        return result
    
    async def test_card_ad(self, page: Page, core_product: str) -> Dict:
        """Step 3b: Test card/tile ad"""
        print(f"\n  -> Step 3b: Testing card ad")
        result = {
            'step': 'card_ad',
            'success': False,
            'screenshot': None,
            'cta_verified': False,
            'errors': []
        }
        
        try:
            # Resize browser
            zoom = self.browser_config['card_ad_zoom']
            viewport_size = page.viewport_size
            if viewport_size:
                new_width = int(viewport_size['width'] * zoom)
                new_height = int(viewport_size['height'] * zoom)
                await page.set_viewport_size({"width": new_width, "height": new_height})
                print(f"  [OK] Browser resized to {int(zoom*100)}%")
            
            await page.wait_for_timeout(1000)
            
            # Check for card ad
            card_selector = self.selectors['card']['tile_ad_image']
            
            if not await page.locator(card_selector).is_visible():
                print(f"  [WARN] Card ad not visible, navigating to dashboard")
                dashboard_url = f"{self.dashboard_url}?products_recommended={core_product}"
                await page.goto(dashboard_url, wait_until="networkidle")
                await page.wait_for_timeout(2000)
            
            # Find card ad by scrolling
            found = await self.find_element_with_scroll(page, card_selector)
            
            if found:
                await self.scroll_to_element(page, card_selector)
                
                # Take screenshot
                filename = self._sanitize_filename(core_product) + "_card.png"
                screenshot_path = self.screenshot_base_dir / self.screenshot_config['subdirectories']['card'] / filename
                await page.screenshot(
                    path=str(screenshot_path),
                    full_page=self.screenshot_config['full_page']
                )
                result['screenshot'] = str(screenshot_path)
                print(f"  [OK] Screenshot saved: {screenshot_path}")
                
                # Verify CTA
                cta_selector = self.selectors['card']['tile_ad_cta']
                try:
                    cta_element = page.locator(cta_selector)
                    if await cta_element.is_visible():
                        cta_text = await cta_element.inner_text()
                        cta_href = await cta_element.get_attribute("href")
                        print(f"  [OK] CTA text: {cta_text}")
                        print(f"  [OK] CTA href: {cta_href}")
                        result['cta_verified'] = True
                        result['cta_text'] = cta_text
                        result['cta_href'] = cta_href
                except Exception as e:
                    result['errors'].append(f"CTA verification failed: {str(e)}")
                
                result['success'] = True
            else:
                result['errors'].append("Card ad not found")
        
        except Exception as e:
            result['errors'].append(f"Exception: {str(e)}")
            print(f"  [FAIL] Error: {str(e)}")
        
        return result
    
    async def test_core_product(self, browser, core_product: str):
        """Test a single core product through all steps"""
        print(f"\n{'='*70}")
        print(f"Testing Core Product: {core_product.upper()}")
        print(f"{'='*70}")
        
        product_result = {
            'product': core_product,
            'timestamp': datetime.now().isoformat(),
            'steps': {},
            'overall_success': False
        }
        
        # Create new context (incognito)
        context = await browser.new_context(
            viewport=self.browser_config['viewport']
        )
        page = await context.new_page()
        
        try:
            # Step 1: Login page ad
            product_result['steps']['login_page_ad'] = await self.test_login_page_ad(page, core_product)
            
            # Step 2: Sign in
            product_result['steps']['signin'] = await self.signin(page)
            
            # Step 2b: Overlay ad
            product_result['steps']['overlay_ad'] = await self.test_overlay_ad(page, core_product)
            
            # Step 3: Close overlay and card ad
            if product_result['steps']['overlay_ad']['success']:
                product_result['steps']['close_overlay'] = await self.close_overlay(page)
            
            product_result['steps']['card_ad'] = await self.test_card_ad(page, core_product)
            
            # Determine overall success
            critical_steps = ['login_page_ad', 'signin', 'overlay_ad', 'card_ad']
            product_result['overall_success'] = all(
                product_result['steps'].get(step, {}).get('success', False)
                for step in critical_steps
            )
            
            if product_result['overall_success']:
                print(f"\n[OK] ALL STEPS PASSED for: {core_product}")
                self.results['passed'] += 1
            else:
                print(f"\n[WARN] SOME STEPS FAILED for: {core_product}")
                self.results['failed'] += 1
        
        except Exception as e:
            print(f"\n[FAIL] CRITICAL ERROR for {core_product}: {str(e)}")
            product_result['critical_error'] = str(e)
            self.results['failed'] += 1
            import traceback
            traceback.print_exc()
        
        finally:
            await context.close()
            self.results['total'] += 1
            self.results['details'].append(product_result)
    
    async def run_all_tests(self):
        """Run tests for all core products"""
        print("\n" + "="*70)
        print("BANKJOY AUTOMATION TESTING - ENHANCED VERSION")
        print("="*70)
        print(f"Base URL: {self.base_url}")
        print(f"Total products: {len(self.core_products)}")
        print(f"Products: {', '.join(self.core_products)}")
        print(f"Headless mode: {self.browser_config['headless']}")
        print("="*70)
        
        start_time = datetime.now()
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=self.browser_config['headless'],
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Test each product
            for i, core_product in enumerate(self.core_products, 1):
                print(f"\n[{i}/{len(self.core_products)}]", end=" ")
                await self.test_core_product(browser, core_product)
                await asyncio.sleep(2)
            
            await browser.close()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print summary
        self._print_summary(duration)
        
        # Save results to JSON
        self._save_results()
    
    def _print_summary(self, duration):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total products tested: {self.results['total']}")
        print(f"Passed: {self.results['passed']} [OK]")
        print(f"Failed: {self.results['failed']} [FAIL]")
        print(f"Success rate: {(self.results['passed']/self.results['total']*100):.1f}%")
        print(f"Duration: {duration}")
        print(f"Screenshots saved in: {self.screenshot_base_dir.absolute()}")
        print("="*70)
    
    def _save_results(self):
        """Save test results to JSON file"""
        results_file = self.screenshot_base_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[OK] Test results saved to: {results_file}")


async def main():
    tester = BankjoyTesterEnhanced()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
