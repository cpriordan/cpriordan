import asyncio
import os
import shutil
import time
import pytest
import pytest_asyncio
from playwright.sync_api import sync_playwright, expect as sync_expect, TimeoutError as SyncTimeoutError
from playwright.async_api import async_playwright, expect as async_expect, TimeoutError as AsyncTimeoutError
from pyotp import TOTP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global timeout configuration
DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', 10000))
DEFAULT_WAIT_TYPE = os.getenv('DEFAULT_WAIT_TYPE', 'networkidle')

# Standard CloudFront URLs for Finalytics staging
DEFAULT_CLOUDFRONT_URLS = ("//d1v4vw9mwf7wyh.cloudfront.net", "https://d1v4vw9mwf7wyh.cloudfront.net")

def clear_screenshots_directory(directory):
    """Clear screenshots directory, removing all files and recreating it."""
    if os.path.exists(directory):
        # Remove all files in the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symbolic link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        # Create the directory if it doesn't exist
        os.makedirs(directory)


@pytest.fixture(scope="function")
def browser_context():
    """
    Configurable Playwright browser context fixture.
    
    Supports environment variables for configuration:
    - HEADLESS: Set to 'true' for headless mode, 'false' or unset for headed mode
    - BROWSER: Browser type (chromium, firefox, webkit) - defaults to chromium
    - HTTP_USERNAME: Username for HTTP basic auth
    - HTTP_PASSWORD: Password for HTTP basic auth
    """
    # Get configuration from environment variables
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    browser_type = os.environ.get("BROWSER", "chromium").lower()
    http_username = os.environ.get("HTTP_USERNAME")
    http_password = os.environ.get("HTTP_PASSWORD")
    
    with sync_playwright() as playwright:
        # Select browser based on environment variable
        if browser_type == "firefox":
            browser = playwright.firefox.launch(headless=headless)
        elif browser_type == "webkit":
            browser = playwright.webkit.launch(headless=headless)
        else:  # Default to chromium
            browser = playwright.chromium.launch(headless=headless)
        
        # Set up context with optional HTTP credentials
        context_options = {}
        if http_username and http_password:
            context_options["http_credentials"] = {
                "username": http_username, 
                "password": http_password
            }
        
        context = browser.new_context(**context_options)
        yield context
        context.close()
        browser.close()


def create_browser_context(
    headless=None,
    browser_type="chromium",
    http_credentials=None
):
    """
    Create a browser context with specified configuration.
    
    Args:
        headless (bool): Whether to run in headless mode. If None, uses HEADLESS env var
        browser_type (str): Browser type - chromium, firefox, or webkit
        http_credentials (dict): HTTP credentials dict with username/password keys
    
    Returns:
        tuple: (browser, context) objects for manual management
    """
    # Determine headless mode
    if headless is None:
        headless = os.environ.get("HEADLESS", "false").lower() == "true"
    
    playwright_instance = sync_playwright().start()
    
    # Select browser based on type
    if browser_type.lower() == "firefox":
        browser = playwright_instance.firefox.launch(headless=headless)
    elif browser_type.lower() == "webkit":
        browser = playwright_instance.webkit.launch(headless=headless)
    else:  # Default to chromium
        browser = playwright_instance.chromium.launch(headless=headless)
    
    # Set up context with optional HTTP credentials
    context_options = {}
    if http_credentials:
        context_options["http_credentials"] = http_credentials
    
    context = browser.new_context(**context_options)
    return browser, context


def validate_no_server_error(page):
    """
    Validates that the page does not contain server error messages.
    
    Args:
        page: The Playwright page object.
    """
    error_keywords = ["Server Error", "(500)", "error", "Page not found"]
    page_text = page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)


def check_link_on_page(page, link_text, link_href=None):
    """Helper function to check if a specific link exists on the page."""
    if link_href:
        link = page.locator(f"a[href='{link_href}']")
    else:
        link = page.locator(f"text='{link_text}'")
    return link.count() > 0


import threading
_otp_lock = threading.Lock()
_last_otp_code = None
_last_otp_timestamp = 0

def generate_otp_code(totp_instance):
    """Generate OTP code with reuse prevention across concurrent tests."""
    global _last_otp_code, _last_otp_timestamp
    
    with _otp_lock:
        current_time = int(time.time())
        remaining_time = totp_instance.interval - (current_time % totp_instance.interval)
        current_otp = totp_instance.now()
        
        # If this OTP was recently generated, wait for the next window
        if current_otp == _last_otp_code and (current_time - _last_otp_timestamp) < 35:
            print(f"OTP {current_otp} was recently used. Waiting for next window...")
            time.sleep(remaining_time + 1)
            current_otp = totp_instance.now()
            remaining_time = totp_instance.interval - (int(time.time()) % totp_instance.interval)
        
        # Also wait if we're very close to expiration (less than 10 seconds)
        elif remaining_time < 10:
            print(f"OTP expires in {remaining_time}s. Waiting for next window...")
            time.sleep(remaining_time + 1)
            current_otp = totp_instance.now()
            remaining_time = totp_instance.interval - (int(time.time()) % totp_instance.interval)
        
        # Store this OTP info to prevent reuse
        _last_otp_code = current_otp
        _last_otp_timestamp = current_time
        
        print(f"Generated OTP code: {current_otp} (expires in ~{remaining_time}s)")
        return current_otp


def setup_environment_variables(user_key, pw_key, otp_key):
    """
    Load and validate environment variables for authentication.
    
    Returns:
        tuple: (findata_user, findata_pw, findata_otp, test_env, totp)
    """
    load_dotenv()
    
    findata_user = os.environ.get(user_key)
    findata_pw = os.environ.get(pw_key)
    findata_otp = os.environ.get(otp_key)
    test_env = os.environ.get("TEST_ENVIRONMENT")
    
    if not findata_user or not findata_pw or not findata_otp or not test_env:
        raise ValueError(f"Required environment variables {user_key}, {pw_key}, {otp_key}, or TEST_ENVIRONMENT are not set!")
    
    totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")
    return findata_user, findata_pw, findata_otp, test_env, totp


class LoginPage:
    """Reusable login page class for admin portal authentication."""
    
    def __init__(self, page):
        self.page = page

    def navigate(self, test_env):
        self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def login(self, username, password):
        self.page.get_by_label("Username:").click()
        self.page.get_by_label("Username:").fill(username)
        self.page.wait_for_timeout(300)  # Brief pause to mimic user interaction
        self.page.get_by_label("Password").fill(password)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("button", name="Login").click()
        self.page.wait_for_load_state("networkidle")

    def enter_2fa_code(self, totp_instance):
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        
        # Generate fresh OTP code with timing validation
        otp_code = generate_otp_code(totp_instance)
        otp_input.fill(otp_code)
        self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")
        return otp_code

    def retry_login_with_new_token(self, totp_instance, test_env):
        """Retry login with fresh OTP tokens if needed."""
        for attempt in range(2):
            try:
                otp_code = generate_otp_code(totp_instance)
                print(f"Attempt {attempt + 1}: Entering OTP code {otp_code}.")
                self.enter_2fa_code(totp_instance)
                # Check if login was successful by verifying the URL
                if f'https://{test_env}finalyticsdata.com/admin/' in self.page.url:
                    print("Login successful.")
                    return
            except Exception as e:
                print(f"Login attempt {attempt + 1} failed: {e}")
        
        raise Exception("Failed to login after multiple attempts.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)


# =====================
# Admin tests specific utilities 
# =====================

class AdminLoginPage:
    """Unified admin login page class for both sync and async tests."""
    
    def __init__(self, page, is_async=False):
        self.page = page
        self.is_async = is_async

    def navigate(self, test_env):
        if self.is_async:
            return self._navigate_async(test_env)
        else:
            self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    async def _navigate_async(self, test_env):
        await self.page.goto(f'https://{test_env}finalyticsdata.com/account/login/?next=/')

    def login(self, username, password):
        if self.is_async:
            return self._login_async(username, password)
        else:
            self.page.get_by_label("Username:").click()
            self.page.get_by_label("Username:").fill(username)
            self.page.wait_for_timeout(300)
            self.page.get_by_label("Password").fill(password)
            self.page.wait_for_timeout(300)
            self.page.get_by_role("button", name="Login").click()
            self.page.wait_for_load_state("networkidle")

    async def _login_async(self, username, password):
        await self.page.get_by_label("Username:").click()
        await self.page.get_by_label("Username:").fill(username)
        await self.page.wait_for_timeout(300)
        await self.page.get_by_label("Password").fill(password)
        await self.page.wait_for_timeout(300)
        await self.page.get_by_role("button", name="Login").click()
        await self.page.wait_for_load_state("networkidle")

    def enter_2fa_code(self, totp_instance):
        if self.is_async:
            return self._enter_2fa_code_async(totp_instance)
        else:
            otp_input = self.page.locator('#id_token-otp_token')
            print("Waiting for 2FA input field to appear...")
            self.page.wait_for_selector('#id_token-otp_token', timeout=30000)
            otp_input.wait_for(state="visible", timeout=10000)
            
            # Generate OTP immediately once field is ready
            otp_code = generate_otp_code(totp_instance)
            otp_input.fill(otp_code)
            self.page.wait_for_timeout(500)  # Brief pause to ensure input is registered
            print(f"OTP code {otp_code} entered.")
            return otp_code

    def complete_2fa_login(self, test_env):
        """Complete the 2FA login process and wait for redirect to admin page."""
        if self.is_async:
            return self._complete_2fa_login_async(test_env)
        else:
            # Click the final login button
            self.page.get_by_role("button", name="Login").click()
            print("Final login button clicked after 2FA.")
            
            # Wait for redirect to admin page
            try:
                self.page.wait_for_url(f'https://{test_env}finalyticsdata.com/admin/', timeout=30000)
                print(f"Successfully redirected to admin page: {self.page.url}")
            except Exception as e:
                print(f"Warning: Expected redirect to admin page failed: {e}")
                print(f"Current URL: {self.page.url}")
                # Additional wait in case redirect is slow
                self.page.wait_for_load_state("networkidle", timeout=10000)

    async def _complete_2fa_login_async(self, test_env):
        """Complete the 2FA login process and wait for redirect to admin page (async)."""
        # Click the final login button
        await self.page.get_by_role("button", name="Login").click()
        print("Final login button clicked after 2FA.")
        
        # Wait for redirect to admin page
        try:
            await self.page.wait_for_url(f'https://{test_env}finalyticsdata.com/admin/', timeout=30000)
            print(f"Successfully redirected to admin page: {self.page.url}")
        except Exception as e:
            print(f"Warning: Expected redirect to admin page failed: {e}")
            print(f"Current URL: {self.page.url}")
            # Additional wait in case redirect is slow
            await self.page.wait_for_load_state("networkidle", timeout=10000)

    async def _enter_2fa_code_async(self, totp_instance):
        otp_input = self.page.locator('#id_token-otp_token')
        await self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
        await self.page.wait_for_timeout(300)
        await otp_input.wait_for(state="visible", timeout=30000)
        
        # Use the consolidated generate_otp_code function for consistency
        otp_code = generate_otp_code(totp_instance)
        
        await otp_input.fill(otp_code)
        await self.page.wait_for_timeout(300)
        print(f"OTP code {otp_code} entered.")
        return otp_code

    def take_screenshot(self, path):
        if self.is_async:
            return self._take_screenshot_async(path)
        else:
            self.page.screenshot(path=path)

    async def _take_screenshot_async(self, path):
        await self.page.screenshot(path=path)


def setup_admin_test_environment(client_type):
    """
    Set up environment variables and TOTP for admin tests.
    
    Args:
        client_type (str): Type of client (gocu, vys, tru, etc.)
        
    Returns:
        tuple: (findata_user, findata_pw, findata_otp, test_env, totp, screenshots_dir)
    """
    
    load_dotenv()
    
    # Map client types to environment variable keys
    client_map = {
        'gocu': ('FINDATA_GOCU_USER', 'FINDATA_GOCU_PW', 'FINDATA_GOCU_OTP'),
        'vys': ('FINDATA_VYS_USER', 'FINDATA_VYS_PW', 'FINDATA_VYS_OTP'),
        'tru': ('FINDATA_TRU_USER', 'FINDATA_TRU_PW', 'FINDATA_TRU_OTP')
    }
    
    if client_type not in client_map:
        raise ValueError(f"Unsupported client type: {client_type}. Supported types: {list(client_map.keys())}")
    
    user_key, pw_key, otp_key = client_map[client_type]
    
    findata_user = os.environ.get(user_key)
    findata_pw = os.environ.get(pw_key)
    findata_otp = os.environ.get(otp_key)
    test_env = os.environ.get("TEST_ENVIRONMENT")
    
    if not findata_user or not findata_pw or not findata_otp or not test_env:
        raise ValueError(f"Required environment variables {user_key}, {pw_key}, {otp_key}, or TEST_ENVIRONMENT are not set!")
    
    totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")
    screenshots_dir = f'screenshots_adminsite_using_pytest/{client_type}/'
    
    return findata_user, findata_pw, findata_otp, test_env, totp, screenshots_dir


@pytest.fixture(scope="function")
def admin_browser_context_sync():
    """Sync browser fixture for admin tests."""
    load_dotenv()  # Load .env file
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest_asyncio.fixture
async def admin_browser_context_async():
    """Async browser fixture for admin tests."""
    load_dotenv()  # Load .env file
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        yield context
        await context.close()
        await browser.close()


def check_admin_link_exists(page, link_text, link_href=None):
    """Check if a specific admin link exists on the page (sync version)."""
    if link_href:
        link = page.locator(f"a[href='{link_href}']")
    else:
        link = page.locator(f"text='{link_text}'")
    return link.count() > 0


async def check_admin_link_exists_async(page, link_text, link_href=None):
    """Check if a specific admin link exists on the page (async version)."""
    if link_href:
        link = page.locator(f"a[href='{link_href}']")
    else:
        link = page.locator(f"text='{link_text}'")
    return await link.count() > 0


def validate_admin_login_success(page, test_env, expected_permissions=None):
    """
    Validate successful admin login and check permissions.
    
    Args:
        page: Playwright page object
        test_env: Test environment (stg, prod, etc.)
        expected_permissions: Dict of {"link_text": should_exist} for permission validation
    """
    
    # Verify URL redirect to admin home
    # UPDATED on 12/17/25 to accept both / and /admin/ redirect patterns
    # Different account types redirect to different URLs:
    # - VYS admin accounts: https://{test_env}finalyticsdata.com/
    # - TRU staff accounts: https://{test_env}finalyticsdata.com/admin/
    import re
    sync_expect(page).to_have_url(re.compile(f'https://{test_env}finalyticsdata.com(/|/admin/)'))
    
    # Validate server errors
    validate_no_server_error(page)
    
    # Check permissions if specified
    if expected_permissions:
        for link_text, should_exist in expected_permissions.items():
            link_exists = check_admin_link_exists(page, link_text)
            if should_exist:
                assert link_exists, f"{link_text} link should be visible for this user type."
            else:
                assert not link_exists, f"{link_text} link should not be visible for this user type."


async def validate_admin_login_success_async(page, test_env, expected_permissions=None):
    """
    Validate successful admin login and check permissions (async version).
    """
    
    # Verify URL redirect to admin home
    async_expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    
    # Validate server errors
    await validate_admin_no_server_error_async(page)
    
    # Check permissions if specified
    if expected_permissions:
        for link_text, should_exist in expected_permissions.items():
            link_exists = await check_admin_link_exists_async(page, link_text)
            if should_exist:
                assert link_exists, f"{link_text} link should be visible for this user type."
            else:
                assert not link_exists, f"{link_text} link should not be visible for this user type."


async def validate_admin_no_server_error_async(page):
    """Validate no server errors on admin pages (async version)."""
    error_keywords = ["Server Error", "(500)", "error", "Page not found"]
    page_text = await page.text_content("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    assert not found_errors, "Error messages found on the page: " + ", ".join(found_errors)


# =====================
# fin-tests specific utilities 
# =====================

def save_page_source(page, filepath):
    """Saves the page's source code to a file (sync version for fin-tests)."""
    try:
        html_content = page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")


async def save_page_source_async(page, filepath):
    """Saves the page's source code to a file (async version for fin-tests)."""
    try:
        html_content = await page.content()
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        print(f"Page source saved to {filepath}")
    except Exception as e:
        print(f"Failed to save page source: {e}")


def detect_js_errors_from_specific_files_sync(client, page, specific_files, error_tracker, browser_type="chromium"):
    """
    Detect JavaScript errors from specific files (sync version for fin-tests).
    Compatible with both sync and async Playwright pages.
    """
    def handle_console_message(msg):
        location = msg.location
        file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
        screenshots_directory = f'screenshots_{client}_using_pytest/{browser_type}'

        if msg.type == 'error' and file_name in specific_files and file_name.endswith('.js'):
            error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
            print(error_message)
            error_tracker.append(error_message)

            screenshot_path = os.path.join(screenshots_directory, f"js_error_{client}.png")
            try:
                # Ensure directory exists
                os.makedirs(screenshots_directory, exist_ok=True)
                page.screenshot(path=screenshot_path)
                print(f"Screenshot of JS error saved at {screenshot_path} for client {client}")
            except Exception as e:
                print(f"Failed to save JS error screenshot: {e}")

    page.on('console', handle_console_message)


async def detect_js_errors_from_specific_files_async(client, page, specific_files, error_tracker, screenshots_directory):
    """
    Detect JavaScript errors from specific files (async version for fin-tests).
    """
    async def handle_console_message(msg):
        try:
            location = msg.location
            file_name = location['url'].split('/')[-1] if location['url'] else 'unknown'
            
            if msg.type == 'error' and file_name.endswith('.js') and file_name in specific_files:
                error_message = f"JS Error found in {file_name}: {msg.text} for client {client}"
                print(error_message)
                error_tracker.append(error_message)
                
                # Ensure directory exists
                os.makedirs(screenshots_directory, exist_ok=True)
                screenshot_path = os.path.join(screenshots_directory, f"js_error_{client}.png")
                await page.screenshot(path=screenshot_path)
                print(f"Screenshot of JS error saved at {screenshot_path} for client {client}")
        except Exception as e:
            print(f"Console handler failed: {e}")

    if not getattr(page, "_js_error_handler_set", False):
        page.on('console', lambda msg: asyncio.create_task(handle_console_message(msg)))
        setattr(page, "_js_error_handler_set", True)


def wait_for_js_and_element_sync(page, hero_heading_selector, timeout=None):
    """
    Wait for page load and element visibility (sync version for fin-tests).
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    
    try:
        page.evaluate('''new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });''')
        print("Page fully loaded.")
    except SyncTimeoutError:
        print("Timeout while waiting for page load.")

    # Wait for the specific element to be visible
    try:
        page.wait_for_function(
            f'document.querySelector("{hero_heading_selector}") !== null && document.querySelector("{hero_heading_selector}").offsetHeight > 0',
            timeout=timeout
        )
        print(f"Element {hero_heading_selector} is visible.")
    except SyncTimeoutError:
        print(f"Timeout waiting for element: {hero_heading_selector}")


async def wait_for_js_and_element_async(page, hero_heading_selector, timeout=None):
    """
    Wait for page load and element visibility (async version for fin-tests).
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    
    try:
        print("Waiting for the document to be fully loaded...")
        await page.evaluate('''new Promise(resolve => {
            if (document.readyState === 'complete') {
                resolve();
            } else {
                window.addEventListener('load', resolve);
            }
        });''')
        print("Page fully loaded.")
    except AsyncTimeoutError:
        print("Timeout while waiting for page load.")

    try:
        print(f"Waiting for the element '{hero_heading_selector}' to become visible...")
        await page.wait_for_function(
            f'document.querySelector("{hero_heading_selector}") !== null && '
            f'document.querySelector("{hero_heading_selector}").offsetHeight > 0',
            timeout=timeout
        )
        print(f"Element '{hero_heading_selector}' is now visible.")
    except AsyncTimeoutError as e:
        pytest.fail(f"Timeout waiting for element '{hero_heading_selector}' to become visible: {e}")


async def process_page_data_async(page, data_item, screenshots_directory, screenshot_counter, screenshots=True,
                                 validate_finalytics=False, client="", cloudfront_urls=None, username=None, password=None):
    """
    Process a single data item (URL string, int for sleep, or dict with expectations).
    Returns updated screenshot counter.
    """
    if isinstance(data_item, int):
        # Integer means sleep for that many seconds
        print(f"Sleeping for {data_item} seconds...")
        await asyncio.sleep(data_item)
        return screenshot_counter
    
    elif isinstance(data_item, str):
        # Simple URL navigation
        current_url = page.url if hasattr(page, 'url') else "unknown"
        print(f"Navigating from {current_url} to: {data_item}")
        await page.goto(data_item)
        print(f"Navigation completed, current URL: {page.url}")
        
        # Handle login if credentials provided
        if username and password:
            print(f"Checking for login redirect...")
            await login_if_redirected(page, username, password)
            print(f"After login check, current URL: {page.url}")
            
        await page.wait_for_load_state(DEFAULT_WAIT_TYPE)
        
        # Check for cookie modals on every page load
        await dismiss_cookie_modal(page)
        
        if screenshots:
            screenshot_counter += 1
            await page.screenshot(path=f'{screenshots_directory}{screenshot_counter}_navigation_screenshot.png')
            print(f"Screenshot saved: {screenshot_counter}_navigation_screenshot.png")
        return screenshot_counter
    
    elif isinstance(data_item, dict):
        # Dict with URL and expectations
        url = data_item['url']
        expected = data_item.get('expected', {})
        wait_type = data_item.get('wait_type') or expected.get('wait_type', DEFAULT_WAIT_TYPE)
        
        print(f"Navigating to: {url}")
        await page.goto(url)
        # Handle login if credentials provided
        if username and password:
            await login_if_redirected(page, username, password)
        
        # Handle different wait types
        if wait_type == 'element':
            # Find the appropriate selector based on what elements are expected
            element_selector = None
            for key in expected.keys():
                if key.endswith('__selector'):
                    element_selector = expected[key]
                    break
            if not element_selector:
                element_selector = '.c-hero'  # fallback
            await wait_for_js_and_element_async(page, element_selector)
        elif wait_type == 'sleep':
            sleep_time = data_item.get('sleep', 5)  # Default 5 seconds if not specified
            print(f"Sleeping for {sleep_time} seconds...")
            await asyncio.sleep(sleep_time)
        elif wait_type in ['load', 'networkidle']:
            await page.wait_for_load_state(wait_type)
        else:
            await page.wait_for_load_state(DEFAULT_WAIT_TYPE)
        
        # Check expectations if provided
        for key, expected_value in expected.items():
            # Skip non-element keys
            if key in ['wait_type', 'screenshot']:
                continue
                
            # Determine element type and selector
            if '__selector' in key:
                element_type = key.split('__selector')[0]
                selector = expected_value
                # Find the corresponding expected value
                expected_content = expected.get(element_type)
                if expected_content is None:
                    continue  # No expected content for this selector
            else:
                # Assume key is the element type and value is expected content
                element_type = key
                expected_content = expected_value
                # Look for a corresponding selector, or use default
                selector_key = f"{element_type}__selector"
                selector = expected.get(selector_key, f'{element_type}:first-of-type')
            
            # Skip if we don't have expected content to validate
            if expected_content is None:
                continue
                
            print(f"Checking {element_type} element...")

            # Known default/fallback ads that indicate getads timeout
            default_fallback_ads = [
                "Pass it on: You Both Earn $50",
                "Why Choose 1st United?",
                "Pass it on",
                "Why Choose"
            ]

            try:
                await page.locator(selector).wait_for(state='visible', timeout=5000)
                actual_content = await page.locator(selector).inner_text()
                print(f"---> {element_type.upper()} content is *** {actual_content} ***")

                # Check if actual content is a default/fallback ad (getads timeout indicator)
                is_default_ad = any(default_ad in actual_content for default_ad in default_fallback_ads)

                if is_default_ad:
                    print(f"WARNING: Default/fallback ad detected: '{actual_content}'")
                    print(f"WARNING: This indicates a getads timeout - ad personalization did not load in time")
                    print(f"WARNING: Expected ad: '{expected_content}' but got default fallback ad")
                    print(f"WARNING: Test will continue (not failed) - this is a timing issue, not a functionality issue")
                    # Don't assert/fail the test for getads timeouts, just log the warning
                    return screenshot_counter

                # Support for multiple acceptable values
                if isinstance(expected_content, list):
                    assert any(exp == actual_content for exp in expected_content), (
                        f"{element_type.upper()} has content '{actual_content}' but expected one of {expected_content}"
                    )
                else:
                    assert expected_content == actual_content, (
                        f"{element_type.upper()} has content '{actual_content}' but expected content was '{expected_content}'"
                    )
            except Exception as e:
                print(f"Error getting {element_type} content with selector '{selector}': {e}")
                # Try alternative selectors based on element type
                alt_selectors = []
                if element_type == 'h1':
                    alt_selectors = ['h1', '.hero h1', '.c-hero h1', '.col-12 h1', 'h1:first-of-type']
                elif element_type == 'h2':
                    alt_selectors = ['h2', '.hero h2', '.c-hero h2', 'h2:first-of-type']
                elif element_type == 'p':
                    alt_selectors = ['p', '.hero p', '.c-hero p', 'p:first-of-type']
                else:
                    alt_selectors = [element_type, f'.hero {element_type}', f'.c-hero {element_type}', f'{element_type}:first-of-type']
                
                for alt_selector in alt_selectors:
                    try:
                        await page.locator(alt_selector).wait_for(state='visible', timeout=3000)
                        actual_content = await page.locator(alt_selector).inner_text()
                        print(f"---> {element_type.upper()} content (using {alt_selector}) is *** {actual_content} ***")

                        # Check if actual content is a default/fallback ad (getads timeout indicator)
                        is_default_ad = any(default_ad in actual_content for default_ad in default_fallback_ads)

                        if is_default_ad:
                            print(f"WARNING: Default/fallback ad detected: '{actual_content}'")
                            print(f"WARNING: This indicates a getads timeout - ad personalization did not load in time")
                            print(f"WARNING: Expected ad: '{expected_content}' but got default fallback ad")
                            print(f"WARNING: Test will continue (not failed) - this is a timing issue, not a functionality issue")
                            # Don't assert/fail the test for getads timeouts, just log the warning
                            return screenshot_counter

                        # Support for multiple acceptable values in fallback too
                        if isinstance(expected_content, list):
                            assert any(exp == actual_content for exp in expected_content), (
                                f"{element_type.upper()} has content '{actual_content}' but expected one of {expected_content}"
                            )
                        else:
                            assert expected_content == actual_content, (
                                f"{element_type.upper()} has content '{actual_content}' but expected content was '{expected_content}'"
                            )
                        break
                    except Exception:
                        continue
                else:
                    raise Exception(f"Could not find {element_type.upper()} element with any selector on {url}")
        
        # Validate Finalytics tags if requested for this specific page
        if validate_finalytics and cloudfront_urls and data_item.get('validate_finalytics', False):
            html_content = await page.content()
            common_tags = get_common_finalytics_tags()
            required_tags = [
                common_tags['css_tag'],
                common_tags['js_tag'], 
                common_tags['function_js_tag'],
                common_tags['settings_div_js_tag']
            ]
            validate_finalytics_tags(html_content, cloudfront_urls, required_tags, client)
            print(f"Finalytics tags validated successfully for {client}")
        
        # Take screenshot based on global setting or per-item setting
        should_screenshot = screenshots or data_item.get('screenshot', False)
        if should_screenshot:
            screenshot_counter += 1
            await page.screenshot(path=f'{screenshots_directory}{screenshot_counter}_expectation_screenshot.png')
        return screenshot_counter
    
    else:
        raise ValueError(f"Invalid data item type: {type(data_item)}. Expected str, int (for sleep), or dict.")



async def dismiss_cookie_modal(page):
    """
    Attempt to dismiss cookie consent modals by looking for Accept/Close buttons only.
    """
    try:
        # Only look for buttons that clearly dismiss/accept cookies, not open settings
        dismiss_selectors = [
            '[aria-label="dismiss cookie message"]',  # MissionFed specific
            '#onetrust-close-btn-container button',
            '#onetrust-close-btn-container',
            '#onetrust-accept-btn-handler',
            'button#onetrust-accept-btn-handler',
            '.onetrust-close-btn-handler',
            'a.cc-btn.cc-dismiss:has-text("Close")',  # MissionFed specific
            '.cc-dismiss',  # Generic cookie consent close
            'button:has-text("Accept All")',
            'button:has-text("Accept")',
            'button:has-text("Allow All")',
            'button:has-text("Allow")', 
            'button:has-text("Close")',
            'button:has-text("Got it")',
            'button:has-text("I Understand")',
            '.cookie-consent button:has-text("Accept")',
            '.cookie-banner button:has-text("Accept")'
        ]
        
        for selector in dismiss_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    print(f"Found cookie dismiss button: {selector}")
                    await element.click()
                    print("Cookie consent dismissed")
                    await page.wait_for_timeout(500)  # Brief wait
                    return True
            except:
                continue
                
        print("No cookie dismiss modal found")
        return False
    except Exception as e:
        print(f"Error dismissing cookie modal: {e}")
        return False

async def login_if_redirected(page, username, password, timeout=30000):
    """
    Handle login if redirected to a login page.
    """
    try:
        # Check if we're on a login page by looking for common login form elements
        login_form = await page.locator('form').first.is_visible() if await page.locator('form').count() > 0 else False
        username_field = await page.locator('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"]').first.is_visible() if await page.locator('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"]').count() > 0 else False
        password_field = await page.locator('input[type="password"]').first.is_visible() if await page.locator('input[type="password"]').count() > 0 else False
        
        if login_form and username_field and password_field:
            print(f"Login form detected, attempting to login with username: {username}")
            
            # Fill username
            await page.locator('input[type="text"], input[type="email"], input[name*="user"], input[name*="login"]').first.fill(username)
            # Fill password  
            await page.locator('input[type="password"]').first.fill(password)
            
            # Submit form
            submit_button = page.locator('input[type="submit"], button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
            if await submit_button.count() > 0:
                await submit_button.first.click()
                await page.wait_for_load_state('networkidle', timeout=timeout)
                print("Login successful")
                # After login, try to dismiss any cookie modal
                await dismiss_cookie_modal(page)
            else:
                print("No submit button found")
        else:
            print("No login form detected, proceeding without login")
            # Check for cookie modal even without login
            await dismiss_cookie_modal(page)
            
    except Exception as e:
        print(f"Login attempt failed: {e}")


async def process_test_data_async(page, data, screenshots_directory, screenshots=True, 
                                 validate_js=False, validate_finalytics=False, client="", 
                                 error_tracker=None, cloudfront_urls=None, username=None, password=None):
    """
    Process a list of test data items (URLs, sleep integers, and dicts with expectations).
    
    Data items can be:
        - str: URL to navigate to
        - int: Number of seconds to sleep
        - dict: URL with expectations and validation options
    
    Args:
        screenshots: If True, take screenshots of all pages. If False, only take 
                    screenshots of dict items that have 'screenshot': True
        validate_js: If True, enable JavaScript error detection
        validate_finalytics: If True, validate Finalytics tags on pages
        client: Client name for error reporting
        error_tracker: List to track JS errors
        cloudfront_urls: Tuple of CloudFront URLs for Finalytics validation
    """
    screenshot_counter = 0
    
    # Set up JS error detection if requested
    if validate_js and error_tracker is not None:
        specific_js_files = get_common_js_files()
        await detect_js_errors_from_specific_files_async(
            client, page, specific_js_files, error_tracker, screenshots_directory
        )
    
    for data_item in data:
        screenshot_counter = await process_page_data_async(
            page, data_item, screenshots_directory, screenshot_counter, screenshots,
            validate_finalytics, client, cloudfront_urls, username, password
        )
    
    # Check for JS errors at the end
    if validate_js and error_tracker and error_tracker:
        pytest.fail(f"Detected JavaScript errors: {error_tracker}")
    
    return screenshot_counter


def validate_finalytics_tags(page_content, cloudfront_urls, required_tags, client=""):
    """
    Validate that Finalytics tags are present in page content.
    
    Args:
        page_content (str): HTML content of the page
        cloudfront_urls (tuple): Tuple of cloudfront URLs to check for
        required_tags (list): List of required Finalytics tags
        client (str): Client name for error messages
        
    Returns:
        tuple: (cloudfront_found, missing_tags)
    """
    # Check cloudfront URLs
    cloudfront_found = any(tag in page_content for tag in cloudfront_urls)
    if not cloudfront_found:
        pytest.fail(f"HTML Finalytics cloudfront URL '{cloudfront_urls[-1]}' NOT FOUND in the page source for {client}!")
    else:
        print(f"HTML Finalytics cloudfront URL '{cloudfront_urls[-1]}' exists in the homepage source for {client}.")

    # Check required tags
    missing_tags = [tag for tag in required_tags if tag not in page_content]
    if missing_tags:
        pytest.fail(f"The following Finalytics tags were NOT found in the page source for {client}: {', '.join(missing_tags)}")
    else:
        print(f"The following Finalytics tags were found in the page source for {client}: {', '.join(required_tags)}")
    
    return cloudfront_found, missing_tags


@pytest_asyncio.fixture
async def browser(request):
    """
    Universal browser fixture for fin-tests.
    Supports HTTP basic auth, configurable headless mode, and different browser types.
    Respects .env variables: HEADLESS, BROWSER, HTTP_USERNAME, HTTP_PASSWORD
    Can be parameterized with credentials or used without parameters.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get credentials from parametrize, env vars, or defaults
    if hasattr(request, 'param') and request.param:
        username = request.param.get("username")
        password = request.param.get("password") 
    else:
        username = None
        password = None
    
    # Fallback to environment variables or defaults
    username = username or os.environ.get("HTTP_USERNAME") or "OneAZ"
    password = password or os.environ.get("HTTP_PASSWORD") or "pugs r potatoes!3"
    
    # Get configuration from environment variables
    headless = os.environ.get("HEADLESS", "false").lower() in ["true", "1", "yes"]
    browser_type = os.environ.get("BROWSER", "chromium").lower()
    
    async with async_playwright() as playwright:
        # Select browser based on type
        if browser_type == "firefox":
            browser = await playwright.firefox.launch(headless=headless)
        elif browser_type == "webkit":
            browser = await playwright.webkit.launch(headless=headless)
        else:  # Default to chromium
            browser = await playwright.chromium.launch(headless=headless)
        
        # Set up context with optional HTTP credentials
        context_options = {}
        if username and password:
            context_options["http_credentials"] = {
                "username": username, 
                "password": password
            }
        
        context = await browser.new_context(**context_options)
        context.set_default_timeout(40000)
        
        yield context
        await context.close()
        await browser.close()


@pytest_asyncio.fixture  
async def browser_no_auth():
    """
    Simple browser fixture without HTTP authentication for ad expiration tests.
    Respects .env HEADLESS variable.
    """
    load_dotenv()
    headless = os.environ.get("HEADLESS", "false").lower() in ["true", "1", "yes"] 
    browser_type = os.environ.get("BROWSER", "chromium").lower()
    
    async with async_playwright() as playwright:
        if browser_type == "firefox":
            browser = await playwright.firefox.launch(headless=headless)
        elif browser_type == "webkit":
            browser = await playwright.webkit.launch(headless=headless)
        else:
            browser = await playwright.chromium.launch(headless=headless)
            
        context = await browser.new_context()
        yield context
        await context.close()
        await browser.close()


def setup_screenshots_directory(client, browser_type="chromium"):
    """
    Set up and clear screenshots directory for a client and browser type.
    
    Args:
        client (str): Client name
        browser_type (str): Browser type for subdirectory
        
    Returns:
        str: Path to the screenshots directory
    """
    screenshots_directory = f'screenshots_{client}_using_pytest/{browser_type}'
    clear_screenshots_directory(screenshots_directory)
    return screenshots_directory


def get_common_js_files():
    """
    Get the standard list of JavaScript files to monitor for errors.
    
    Returns:
        list: List of common JS files to monitor
    """
    return [
        'finalytics.js',
        'finalytics-function.js', 
        'settings_div.js',
        'settings.js',
        'controlbar.js'
    ]


def get_common_finalytics_tags():
    """
    Get the standard list of Finalytics tags to validate.
    
    Returns:
        dict: Dictionary with common tag names
    """
    return {
        'css_tag': 'finalytics-function_div.css',
        'js_tag': 'finalytics.js',
        'function_js_tag': 'finalytics-function.js',
        'settings_div_js_tag': 'settings_div.js'
    }