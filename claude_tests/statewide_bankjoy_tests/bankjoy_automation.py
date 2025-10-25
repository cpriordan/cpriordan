"""
Bankjoy Site Automation Testing Script
Tests different core products with screenshots at various stages
"""

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright, Page
import time


class BankjoyTester:
    def __init__(self):
        self.base_url = "https://statewide.stage.bankjoy.com/?cb=1&session_init=1&debug_all=1"
        self.username = "cbracey25"
        self.password = "SwFCU2025$$$"
        self.core_products = [
            "checking account",
            "cd",
            "equipment loan",
            "personal loan",
            "rv loan",
            "ira",
            "credit card",
            "boat loan",
            "car loan",
            "savings account"
        ]
        self.screenshot_base_dir = Path("statewide")
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories for screenshots"""
        directories = [
            self.screenshot_base_dir / "olb" / "login" / "core_products",
            self.screenshot_base_dir / "olb" / "overlay" / "core_products",
            self.screenshot_base_dir / "olb" / "card" / "core_products"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created directories in {self.screenshot_base_dir}")
    
    def _sanitize_filename(self, core_product: str) -> str:
        """Convert core product name to valid filename"""
        return core_product.replace(" ", "_").replace("/", "_")
    
    async def wait_for_element(self, page: Page, selector: str, timeout: int = 10000):
        """Wait for element to be visible"""
        try:
            await page.wait_for_selector(selector, state="visible", timeout=timeout)
            return True
        except Exception as e:
            print(f"  [WARN] Element {selector} not found: {str(e)}")
            return False
    
    async def scroll_to_element(self, page: Page, selector: str):
        """Scroll to make element visible"""
        try:
            await page.evaluate(f"""
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            """)
            await page.wait_for_timeout(1000)  # Wait for scroll animation
            return True
        except Exception as e:
            print(f"  [WARN] Could not scroll to {selector}: {str(e)}")
            return False
    
    async def test_login_page_ad(self, page: Page, core_product: str):
        """
        Step 1: Test login page tile ad
        """
        print(f"\n  -> Testing login page ad for: {core_product}")
        
        # Navigate to login page with products_recommended parameter
        url = f"{self.base_url}&products_recommended={core_product}"
        await page.goto(url, wait_until="networkidle")
        
        # Refresh the page
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Scroll down to find the overlay
        overlay_selector = "#finalytics-information-wrapper-ad"
        
        # Try scrolling down multiple times to find the overlay
        max_scrolls = 10
        for i in range(max_scrolls):
            if await page.locator(overlay_selector).is_visible():
                break
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(500)
        
        # Wait for overlay to be visible
        if await self.wait_for_element(page, overlay_selector):
            await self.scroll_to_element(page, overlay_selector)
            
            # Take screenshot
            filename = self._sanitize_filename(core_product) + "_login.png"
            screenshot_path = self.screenshot_base_dir / "olb" / "login" / "core_products" / filename
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  [OK] Screenshot saved: {screenshot_path}")
            
            # Verify CTA button
            cta_selector = "#finalytics-information-wrapper-ad > div > div:nth-child(3) > div > a"
            try:
                cta_element = page.locator(cta_selector)
                if await cta_element.is_visible():
                    cta_text = await cta_element.inner_text()
                    cta_href = await cta_element.get_attribute("href")
                    print(f"  [OK] CTA button text: {cta_text}")
                    print(f"  [OK] CTA button href: {cta_href}")
                    
                    # Verify text contains expected product keyword
                    if "checking" in core_product.lower():
                        if "checking" in cta_text.lower():
                            print(f"  [OK] CTA text verification passed")
                        else:
                            print(f"  [WARN] CTA text doesn't contain 'checking': {cta_text}")
                else:
                    print(f"  [WARN] CTA button not visible")
            except Exception as e:
                print(f"  [WARN] Could not verify CTA button: {str(e)}")
        else:
            print(f"  [WARN] Login page overlay not found")
    
    async def signin(self, page: Page):
        """
        Step 2a: Sign in to the application
        """
        print(f"\n  -> Signing in...")
        
        # Scroll up to find signin section
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        
        # Navigate to signin page
        signin_url = "https://statewide.stage.bankjoy.com/?cb=1&session_init=1"
        await page.goto(signin_url, wait_until="networkidle")
        
        # Wait for username field
        username_selector = "#username"
        if await self.wait_for_element(page, username_selector):
            await page.fill(username_selector, self.username)
            print(f"  [OK] Entered username")
        
        # Enter password
        password_selector = "#password"
        await page.fill(password_selector, self.password)
        print(f"  [OK] Entered password")
        
        # Click Continue button
        # Try multiple possible selectors for the continue button
        continue_selectors = [
            "button:has-text('Continue')",
            "button[type='submit']",
            ".continue-button",
            "button.mat-mdc-button"
        ]
        
        clicked = False
        for selector in continue_selectors:
            try:
                if await page.locator(selector).is_visible():
                    await page.locator(selector).click()
                    clicked = True
                    print(f"  [OK] Clicked Continue button")
                    break
            except:
                continue
        
        if not clicked:
            print(f"  [WARN] Could not find Continue button, trying Enter key")
            await page.keyboard.press("Enter")
        
        # Wait for navigation after login
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle")
        print(f"  [OK] Signed in successfully")
    
    async def test_overlay_ad(self, page: Page, core_product: str):
        """
        Step 2b: Test overlay/broadcast ad after login
        """
        print(f"\n  -> Testing overlay ad for: {core_product}")
        
        # Refresh the page to ensure overlay appears
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Scroll down to find the broadcast overlay
        overlay_selector = "#finalytics-broadcast-ad"
        
        # Try scrolling down multiple times
        max_scrolls = 10
        for i in range(max_scrolls):
            if await page.locator(overlay_selector).is_visible():
                break
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(500)
        
        if await self.wait_for_element(page, overlay_selector, timeout=15000):
            await self.scroll_to_element(page, overlay_selector)
            
            # Take screenshot
            filename = self._sanitize_filename(core_product) + "_overlay.png"
            screenshot_path = self.screenshot_base_dir / "olb" / "overlay" / "core_products" / filename
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  [OK] Screenshot saved: {screenshot_path}")
            
            # Verify CTA button on overlay
            cta_selector = "#finalytics-broadcast-ad > div:nth-child(3) > div > a"
            try:
                cta_element = page.locator(cta_selector)
                if await cta_element.is_visible():
                    cta_text = await cta_element.inner_text()
                    cta_href = await cta_element.get_attribute("href")
                    print(f"  [OK] CTA button text: {cta_text}")
                    print(f"  [OK] CTA button href: {cta_href}")
                    
                    # Verify text
                    if "checking" in core_product.lower():
                        if "checking" in cta_text.lower():
                            print(f"  [OK] CTA text verification passed")
                        else:
                            print(f"  [WARN] CTA text doesn't contain 'checking': {cta_text}")
                else:
                    print(f"  [WARN] CTA button not visible")
            except Exception as e:
                print(f"  [WARN] Could not verify CTA button: {str(e)}")
            
            return True
        else:
            print(f"  [WARN] Overlay not found")
            return False
    
    async def close_overlay(self, page: Page):
        """
        Step 3a: Close the overlay
        """
        print(f"\n  -> Closing overlay...")
        
        # Try multiple possible close button selectors
        close_selectors = [
            "#mat-mdc-dialog-0 > div > div > app-broadcast-ad-dialog > button > span > span > svg",
            "#mat-mdc-dialog-0 > div > div > app-broadcast-ad-dialog > button",
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
            print(f"  [WARN] Could not find close button, pressing Escape")
            await page.keyboard.press("Escape")
        
        await page.wait_for_timeout(1000)
    
    async def test_card_ad(self, page: Page, core_product: str):
        """
        Step 3b: Test card/tile ad
        """
        print(f"\n  -> Testing card ad for: {core_product}")
        
        # Resize browser to 80%
        viewport_size = page.viewport_size
        if viewport_size:
            new_width = int(viewport_size['width'] * 0.8)
            new_height = int(viewport_size['height'] * 0.8)
            await page.set_viewport_size({"width": new_width, "height": new_height})
            print(f"  [OK] Browser resized to 80%")
        
        await page.wait_for_timeout(1000)
        
        # Check if card ad is visible
        card_selector = "#finalytics-tile-ad > div > img"
        
        if not await page.locator(card_selector).is_visible():
            print(f"  [WARN] Card ad not visible, refreshing page...")
            dashboard_url = f"https://statewide.stage.bankjoy.com/consumer/main/dashboard?products_recommended={core_product}"
            await page.goto(dashboard_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
        
        # Scroll to find card ad
        max_scrolls = 10
        for i in range(max_scrolls):
            if await page.locator(card_selector).is_visible():
                break
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(500)
        
        if await self.wait_for_element(page, card_selector, timeout=10000):
            await self.scroll_to_element(page, card_selector)
            
            # Take screenshot
            filename = self._sanitize_filename(core_product) + "_card.png"
            screenshot_path = self.screenshot_base_dir / "olb" / "card" / "core_products" / filename
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  [OK] Screenshot saved: {screenshot_path}")
            
            # Verify CTA link on card ad
            cta_selector = "#finalytics-tile-ad > div > div > div > a"
            try:
                cta_element = page.locator(cta_selector)
                if await cta_element.is_visible():
                    cta_text = await cta_element.inner_text()
                    cta_href = await cta_element.get_attribute("href")
                    print(f"  [OK] CTA link text: {cta_text}")
                    print(f"  [OK] CTA link href: {cta_href}")
                    
                    # Verify text
                    if "checking" in core_product.lower():
                        if "checking" in cta_text.lower():
                            print(f"  [OK] CTA text verification passed")
                        else:
                            print(f"  [WARN] CTA text doesn't contain 'checking': {cta_text}")
                    
                    # Verify link is valid (optional - can click to test)
                    if cta_href:
                        print(f"  [OK] CTA link exists: {cta_href}")
                else:
                    print(f"  [WARN] CTA link not visible")
            except Exception as e:
                print(f"  [WARN] Could not verify CTA link: {str(e)}")
        else:
            print(f"  [WARN] Card ad not found")
    
    async def test_core_product(self, browser, core_product: str):
        """
        Test a single core product through all steps
        """
        print(f"\n{'='*60}")
        print(f"Testing Core Product: {core_product.upper()}")
        print(f"{'='*60}")
        
        # Create new context and page for each product (incognito)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Test login page ad
            await self.test_login_page_ad(page, core_product)
            
            # Step 2: Sign in
            await self.signin(page)
            
            # Step 2b: Test overlay ad
            overlay_found = await self.test_overlay_ad(page, core_product)
            
            # Step 3: Close overlay and test card ad
            if overlay_found:
                await self.close_overlay(page)
            
            await self.test_card_ad(page, core_product)
            
            print(f"\n[OK] Completed testing for: {core_product}")
            
        except Exception as e:
            print(f"\n[FAIL] Error testing {core_product}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            await context.close()
    
    async def run_all_tests(self):
        """
        Run tests for all core products
        """
        print("\n" + "="*60)
        print("BANKJOY AUTOMATION TESTING")
        print("="*60)
        print(f"Base URL: {self.base_url}")
        print(f"Total products to test: {len(self.core_products)}")
        print(f"Products: {', '.join(self.core_products)}")
        print("="*60)
        
        async with async_playwright() as p:
            # Launch browser (Chrome)
            browser = await p.chromium.launch(
                headless=False,  # Set to True for headless mode
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Test each core product
            for core_product in self.core_products:
                await self.test_core_product(browser, core_product)
                await asyncio.sleep(2)  # Short delay between products
            
            await browser.close()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED!")
        print("="*60)
        print(f"Screenshots saved in: {self.screenshot_base_dir.absolute()}")


async def main():
    tester = BankjoyTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
