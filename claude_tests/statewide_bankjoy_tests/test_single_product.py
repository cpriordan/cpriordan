"""
Helper script to run tests on specific core products
Usage: python test_single_product.py "checking account"
"""

import asyncio
import sys
from bankjoy_automation import BankjoyTester
from playwright.async_api import async_playwright


async def test_single_product(product_name: str):
    """Test a single core product"""
    tester = BankjoyTester()
    
    # Validate product name
    if product_name not in tester.core_products:
        print(f"\n[ERROR] Error: '{product_name}' is not a valid core product")
        print(f"\nAvailable products:")
        for i, product in enumerate(tester.core_products, 1):
            print(f"  {i}. {product}")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing single product: {product_name}")
    print(f"{'='*60}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        await tester.test_core_product(browser, product_name)
        await browser.close()
    
    print(f"\n[OK] Test completed for: {product_name}")
    print(f"Screenshots saved in: {tester.screenshot_base_dir.absolute()}")


async def test_multiple_products(product_names: list):
    """Test multiple specific core products"""
    tester = BankjoyTester()
    
    # Validate all product names
    invalid_products = [p for p in product_names if p not in tester.core_products]
    if invalid_products:
        print(f"\n[ERROR] Error: Invalid products: {', '.join(invalid_products)}")
        print(f"\nAvailable products:")
        for i, product in enumerate(tester.core_products, 1):
            print(f"  {i}. {product}")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing {len(product_names)} products: {', '.join(product_names)}")
    print(f"{'='*60}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        for product_name in product_names:
            await tester.test_core_product(browser, product_name)
            await asyncio.sleep(2)
        
        await browser.close()
    
    print(f"\n[OK] All tests completed!")
    print(f"Screenshots saved in: {tester.screenshot_base_dir.absolute()}")


def print_usage():
    """Print usage instructions"""
    print("\n" + "="*60)
    print("BANKJOY SINGLE PRODUCT TESTER")
    print("="*60)
    print("\nUsage:")
    print("  Test single product:")
    print('    python test_single_product.py "checking account"')
    print("\n  Test multiple products:")
    print('    python test_single_product.py "checking account" "cd" "ira"')
    print("\n  List available products:")
    print("    python test_single_product.py --list")
    print("\nAvailable products:")
    tester = BankjoyTester()
    for i, product in enumerate(tester.core_products, 1):
        print(f"  {i}. {product}")
    print("="*60)


def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    
    if sys.argv[1] in ['--list', '-l', 'list']:
        tester = BankjoyTester()
        print("\nAvailable core products:")
        for i, product in enumerate(tester.core_products, 1):
            print(f"  {i}. {product}")
        return
    
    if sys.argv[1] in ['--help', '-h', 'help']:
        print_usage()
        return
    
    # Get product names from arguments
    product_names = sys.argv[1:]
    
    if len(product_names) == 1:
        asyncio.run(test_single_product(product_names[0]))
    else:
        asyncio.run(test_multiple_products(product_names))


if __name__ == "__main__":
    main()
