import pytest
from playwright.sync_api import expect
import sys
import os
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qa_tools import (
    AdminLoginPage,
    setup_admin_test_environment,
    admin_browser_context_sync,
    clear_screenshots_directory,
    validate_admin_login_success
)

def sanitize_filename(filename):
    """Remove or replace invalid filename characters for Windows."""
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # Remove any trailing dots or spaces
    sanitized = sanitized.rstrip('. ')
    return sanitized

def validate_no_server_error(page):
    """Validates that the page does not contain server error messages."""
    error_keywords = ["Server Error", "(500)", "error ", "Page not found"]
    page_text = page.inner_text("body")
    found_errors = [msg for msg in error_keywords if msg in page_text]
    assert not found_errors, f"Error messages found on the page: {', '.join(found_errors)}"

def check_admin_site_administration_page_first_link(page, screenshots_directory, test_env):
    """
    Navigate to site administration page and click through all admin links.
    For each admin section, click the first item in the results table if available.
    """
    print(f'Inside check_admin_site_administration_page_first_link function and screenshots directory is {screenshots_directory}')

    # Navigate directly to the admin page (the "Admin" link no longer exists after login)
    print(f"Navigating directly to https://{test_env}finalyticsdata.com/admin/")
    page.goto(f"https://{test_env}finalyticsdata.com/admin/", wait_until="networkidle", timeout=60000)
    page.screenshot(path=f'{screenshots_directory}2_navigated_to_admin_page.png')

    # Find all rows with class starting with "model-"
    locator_of_rows_in_table_of_class_model_on_admin_site_page = "div.app-app.module table tr[class^='model-']"
    rows = page.locator(locator_of_rows_in_table_of_class_model_on_admin_site_page)

    # Locator of the first link on the results table of all the site administration pages
    locator_of_first_link_on_the_results_table = "#result_list tbody tr:first-child th.field-first_field_display a:last-child"

    row_count = rows.count()
    print(f"Found {row_count} administration sections to check")

    for i in range(row_count):
        # Click on the <th scope="row"> link of the current row
        row = rows.nth(i)

        # Screenshot count
        screenshot_counter = i + 3

        # Extract and click the link in the <th scope="row">
        link_element = row.locator("th[scope='row'] a")
        if link_element.count() > 0:
            link_text = link_element.inner_text()
            link_href = link_element.get_attribute("href")
            print(f"Clicking link: {link_text} ({link_href}) and URL is https://{test_env}finalyticsdata.com{link_href}")
            link_element.click(timeout=60000)

            # Wait for the next page to load
            page.wait_for_load_state("networkidle", timeout=60000)

            # Check if the next page has a table with id="result_list"
            if page.locator(locator_of_first_link_on_the_results_table).count() > 0:
                # Click the first link in the table
                first_link = page.locator(locator_of_first_link_on_the_results_table).first
                first_link_text = first_link.inner_text()
                first_link_href = first_link.get_attribute("href")
                print(f"Clicking on first link in the table: {first_link_text} on {first_link_href} and URL is https://{test_env}finalyticsdata.com{first_link_href}")
                first_link.click(timeout=60000)

                # Wait for the page to load
                page.wait_for_load_state("networkidle", timeout=60000)

                # Validate the page for no server errors
                validate_no_server_error(page)

                # Take a screenshot with sanitized filename
                safe_link_text = sanitize_filename(link_text)
                safe_first_link_text = sanitize_filename(first_link_text)
                page.screenshot(path=f"{screenshots_directory}{screenshot_counter}_screenshot_{safe_link_text}_{safe_first_link_text}.png")

                # Go back to the second-level page
                page.go_back()
                page.wait_for_load_state("networkidle", timeout=60000)

            else:
                print(f"No links found in the table on the {link_text} page.")

            # Go back to the main admin page
            page.go_back()
            page.wait_for_load_state("networkidle", timeout=60000)

def test_check_admin_site_administration_page_and_first_link(admin_browser_context_sync):
    """Test admin site administration page access using consolidated qa_tools functions."""
    page = admin_browser_context_sync.new_page()

    # Setup environment using consolidated function
    findata_user, findata_pw, findata_otp, test_env, totp, base_screenshots_dir = setup_admin_test_environment('vys')
    screenshots_directory = os.path.join(os.path.dirname(__file__), 'screenshots_adminsite_using_pytest/admin_page_check/')

    # Clear screenshots directory
    clear_screenshots_directory(screenshots_directory)

    # Initialize consolidated login page
    login_page = AdminLoginPage(page, is_async=False)

    # Perform login using consolidated methods
    login_page.navigate(test_env)
    login_page.login(findata_user, findata_pw)
    otp_code = login_page.enter_2fa_code(totp)
    page.get_by_role("button", name="Login").click()

    # Validate login success
    login_page.take_screenshot(f'{screenshots_directory}1_successful_login_using_2fa.png')
    validate_admin_login_success(page, test_env)

    print(f"Successful login screenshot saved in {screenshots_directory} AND about to call check_admin_site_administration_page_first_link.")

    # Run the test to check all administration links
    check_admin_site_administration_page_first_link(page, screenshots_directory, test_env)

    # Take screenshot after done checking links
    page.screenshot(path=f'{screenshots_directory}999_after_checking_all_links.png')
    print("Admin site administration page test completed successfully")