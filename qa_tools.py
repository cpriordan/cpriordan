import os
import shutil
import time
import pytest
from playwright.sync_api import sync_playwright
from pyotp import TOTP
from dotenv import load_dotenv


class PhoneAuthHandler:
    """Handler for phone-based 2FA authentication."""
    
    def __init__(self, static_code=None):
        """
        Initialize phone auth handler.
        
        Args:
            static_code: Optional static code for phone auth. If None, will need manual entry.
        """
        self.static_code = static_code
        self.interval = 30  # Compatibility with TOTP interface
    
    def now(self):
        """Return the static code or prompt for manual entry."""
        if self.static_code:
            return self.static_code
        else:
            # In automated tests, this would typically be set via environment variable
            # For manual testing, you could implement input() here
            raise ValueError("Phone auth code not provided. Set it via environment variable.")


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


def generate_otp_code(auth_handler):
    """Generate OTP code with timing validation.
    
    Args:
        auth_handler: Either a TOTP instance or PhoneAuthHandler
    
    Returns:
        str: The authentication code
    """
    # For TOTP, handle timing to avoid code expiration
    if isinstance(auth_handler, TOTP):
        remaining_time = auth_handler.interval - (int(time.time()) % auth_handler.interval)
        if remaining_time < 5:
            # Short pause so the token rolls over
            time.sleep(remaining_time + 1)
    # For both TOTP and PhoneAuthHandler, call now() to get the code
    return auth_handler.now()


def setup_environment_variables(user_key, pw_key, otp_key, auth_method="totp"):
    """
    Load and validate environment variables for authentication.
    
    Args:
        user_key: Environment variable key for username
        pw_key: Environment variable key for password
        otp_key: Environment variable key for OTP secret or phone code
        auth_method: Authentication method - "totp" or "phone" (default: "totp")
    
    Returns:
        tuple: (findata_user, findata_pw, findata_otp, test_env, auth_handler)
    """
    load_dotenv()
    
    findata_user = os.environ.get(user_key)
    findata_pw = os.environ.get(pw_key)
    findata_otp = os.environ.get(otp_key)
    test_env = os.environ.get("TEST_ENVIRONMENT")
    auth_method_env = os.environ.get("AUTH_METHOD", auth_method).lower()
    
    if not findata_user or not findata_pw or not test_env:
        raise ValueError(f"Required environment variables {user_key}, {pw_key}, or TEST_ENVIRONMENT are not set!")
    
    # Create appropriate auth handler based on method
    if auth_method_env == "totp":
        if not findata_otp:
            raise ValueError(f"TOTP secret ({otp_key}) is required for TOTP authentication!")
        auth_handler = TOTP(findata_otp, interval=30, digits=6, digest="sha1")
    elif auth_method_env == "phone":
        # For phone auth, findata_otp might contain a static code or be None if manual entry is needed
        auth_handler = PhoneAuthHandler(findata_otp)
    else:
        raise ValueError(f"Unsupported auth method: {auth_method_env}. Use 'totp' or 'phone'")
    
    return findata_user, findata_pw, findata_otp, test_env, auth_handler


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

    def enter_2fa_code(self, auth_handler):
        """Enter 2FA code - supports both TOTP and phone authentication."""
        otp_input = self.page.locator('#id_token-otp_token')
        self.page.wait_for_selector('#id_token-otp_token', timeout=60000)
        self.page.wait_for_timeout(300)
        otp_input.wait_for(state="visible", timeout=30000)
        
        # Generate auth code using the unified function
        otp_code = generate_otp_code(auth_handler)
        
        # Determine auth type for logging
        if isinstance(auth_handler, TOTP):
            auth_type = "TOTP"
        elif isinstance(auth_handler, PhoneAuthHandler):
            auth_type = "Phone"
        else:
            auth_type = "Auth"
        
        otp_input.fill(otp_code)
        self.page.wait_for_timeout(300)
        print(f"{auth_type} code {otp_code} entered.")
        return otp_code

    def retry_login_with_new_token(self, auth_handler, test_env):
        """Retry login with fresh auth tokens if needed."""
        for attempt in range(2):
            try:
                # Use unified generate_otp_code for all auth types
                otp_code = generate_otp_code(auth_handler)
                
                # Log based on auth type
                if isinstance(auth_handler, TOTP):
                    print(f"Attempt {attempt + 1}: Entering TOTP code {otp_code}.")
                elif isinstance(auth_handler, PhoneAuthHandler):
                    print(f"Attempt {attempt + 1}: Using phone code {otp_code}.")
                else:
                    print(f"Attempt {attempt + 1}: Entering auth code {otp_code}.")
                
                self.enter_2fa_code(auth_handler)
                # Check if login was successful by verifying the URL
                if f'https://{test_env}finalyticsdata.com/admin/' in self.page.url:
                    print("Login successful.")
                    return
            except Exception as e:
                print(f"Login attempt {attempt + 1} failed: {e}")
        
        raise Exception("Failed to login after multiple attempts.")

    def take_screenshot(self, path):
        self.page.screenshot(path=path)