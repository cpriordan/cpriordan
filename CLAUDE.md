# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Playwright-based test automation repository for Finalytics, containing UI tests for various credit union websites and admin site functionality. The tests validate tag loading, JavaScript errors, ad content, and admin portal operations.

## Test Structure

### Test Directories
- **fin-tests/**: Main UI tests for credit union websites
  - `PROD/`: Production environment tests
  - `QA/`: QA environment tests
- **fin-admin-tests/**: Legacy admin site tests (deprecated - use pytests/ADMINSITETESTS instead)
- **pytests/**: Current pytest-based tests
  - `ADMINSITETESTS/`: Admin portal test suite

### Test Naming Convention
Tests follow the pattern: `test_[client]_[feature]_[environment]_[details].py`
- Example: `test_oneaz_business_stgtags_and_js_errors.py`
- Admin tests: `test_findata_stg_login_[account_type]_[feature].py`

## Commands

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt
playwright install --with-deps

# Run all tests in a directory
pytest fin-tests/QA/

# Run specific test by name pattern
pytest -k test_oneaz_business

# Run with verbose output and stop on first failure
pytest -q -s fin-tests/PROD -k test_oneaz_hero_ocr_ci --maxfail=1 --disable-warnings

# Run admin site tests
pytest pytests/ADMINSITETESTS/
```

### Common Test Execution Patterns

```bash
# Run tests with screenshot capture
pytest --screenshot=on --screenshot-only-on-failure

# Run specific client tests
pytest -k oneaz  # OneAZ tests
pytest -k gocu   # GOCU tests
pytest -k missionfed  # MissionFed tests

# Run with specific browser
pytest --browser chromium
pytest --browser firefox
```

## Architecture

### Test Framework
- **Playwright**: Browser automation framework
- **pytest**: Test runner with async support via pytest-asyncio
- **pyotp**: For 2FA authentication in admin tests
- **Tesseract/Pillow**: OCR capabilities for visual validation

### Key Test Patterns

1. **Tag Validation Tests**: Verify Finalytics JS/CSS tags load correctly
   - Check for: `finalytics.js`, `finalytics-function.js`, `settings_div.js`, `controlbar.js`
   - Validate proper script loading and initialization

2. **JavaScript Error Detection**: Monitor console for errors from specific files
   - Capture screenshots when errors occur
   - Save page source for debugging

3. **Ad Content Validation**: Verify personalized ad content appears correctly
   - Hero ads, card ads, product recommendations
   - OCR validation for visual content

4. **Admin Portal Tests**: Validate admin functionality
   - 2FA login flows
   - Campaign management
   - Content segmentation
   - Media library operations

### Environment Variables

Admin tests require environment variables (typically in .env file):
- `FINDATA_GOCU_USER`: Admin username
- `FINDATA_GOCU_PW`: Admin password  
- `FINDATA_GOCU_OTP`: TOTP secret for 2FA
- `TEST_ENVIRONMENT`: Target environment (stg/prod)

### Screenshot Management

Tests automatically manage screenshots in timestamped directories:
- Pattern: `screenshots_[client]_[timestamp]/`
- Auto-cleanup of old directories before test runs
- Separate folders for different browsers

## GitHub Actions Workflows

Workflows in `.github/workflows/`:
- **Daily production tests**: Run at 6 AM PST
- **QA tests**: Triggered on code changes or manually
- **OCR validation tests**: Visual regression testing

Workflow patterns:
- Use `workflow_dispatch` for manual triggers
- Path filters to run tests only when relevant files change
- Artifact upload for test results and screenshots

## Important Considerations

- Tests use HTTP basic auth for staging environments
- Headless mode is enforced in CI environments
- Tests include retry logic for flaky network conditions
- Screenshot directories are cleared before each test run to manage disk space
- Admin tests use TOTP-based 2FA requiring accurate time sync
- OCR tests compare visual output against baseline images