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


def generate_otp_code(totp_instance):
    """Generate OTP code with timing validation."""
    remaining_time = totp_instance.interval - (int(time.time()) % totp_instance.interval)
    if remaining_time < 5:
        # Short pause so the token rolls over
        time.sleep(remaining_time + 1)
    return totp_instance.now()


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
            self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
            self.page.wait_for_timeout(300)
            otp_input.wait_for(state="visible", timeout=30000)
            
            otp_code = generate_otp_code(totp_instance)
            otp_input.fill(otp_code)
            self.page.wait_for_timeout(300)
            print(f"OTP code {otp_code} entered.")
            return otp_code

    async def _enter_2fa_code_async(self, totp_instance):
        otp_input = self.page.locator('#id_token-otp_token')
        await self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
        await self.page.wait_for_timeout(300)
        await otp_input.wait_for(state="visible", timeout=30000)
        
        # Generate OTP with timing validation
        remaining_time = totp_instance.interval - (int(time.time()) % totp_instance.interval)
        if remaining_time < 5:
            await asyncio.sleep(remaining_time + 1)
        otp_code = totp_instance.now()
        
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
    sync_expect(page).to_have_url(f'https://{test_env}finalyticsdata.com/admin/')
    
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


def wait_for_js_and_element_sync(page, hero_heading_selector, timeout=60000):
    """
    Wait for page load and element visibility (sync version for fin-tests).
    """
    
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


async def wait_for_js_and_element_async(page, hero_heading_selector, timeout=10000):
    """
    Wait for page load and element visibility (async version for fin-tests).
    """
    
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