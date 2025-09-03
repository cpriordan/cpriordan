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

### Virtual Environment

The project virtual environment is located at: `~/projects/testenv`

```bash
# Activate the virtual environment
source ~/projects/testenv/bin/activate
```

### Running Tests

```bash
# Install dependencies (if not already installed)
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
- `DEFAULT_TIMEOUT`: Global timeout in milliseconds (default: 10000)

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

### Test Parameter Integrity

**CRITICAL**: Do not modify test parameter values (URLs, expected headings, selectors, etc.) just to make tests pass. Test failures often indicate:
- Content changes that need investigation
- Environment issues requiring attention
- Actual bugs in the application under test

Only change test parameters when:
- Explicitly instructed to do so
- The change reflects an intentional application update
- Working on a specific content assertion fix that's been requested

Tests are designed to fail when something is wrong - this is their primary value proposition.

## Serana MCP Integration

This project is configured with [Serana MCP (Model Context Protocol)](https://github.com/oraios/serena) for enhanced code understanding and AI-assisted development. Serana provides semantic code analysis and context-aware assistance.

### Serana Configuration Files

- **serena_config.yml**: Main server configuration with security settings and language servers
- **.serena/project.yml**: Project-specific settings for test automation context
- **start_serena.sh**: Quick start script for the MCP server
- **launch_serena.py**: Management utility for diagnostics and configuration

### Using Serana

```bash
# Run diagnostics to check installation
python3 launch_serena.py diagnostics

# View project information
python3 launch_serena.py info

# Start server (for SSE transport)
./start_serena.sh sse

# For Claude Code integration (stdio transport)
./start_serena.sh
```

### Security Configuration

Serana is configured to block access to sensitive files:
- `.env` files with credentials
- Any files containing passwords, secrets, or API keys
- Test environment variables with authentication data

### Language Server Support

For optimal code analysis, install the Python language server:
```bash
source ~/projects/testenv/bin/activate
pip install python-lsp-server
```

This enables better code completion, navigation, and refactoring suggestions when working with the test suite.

## Cleanup and Maintenance

### Temporary Files
When working on test consolidation or refactoring, temporary files may be created:
- `batch_refactor_fin_tests.py`
- `clean_imports.py` 
- `consolidate_browser_fixtures.py`
- `consolidate_browser_fixtures_pytests.py`
- `fix_import_paths.py`
- `fix_syntax_errors.py`
- `manual_fix_remaining.py`
- `test_consolidation_results.py`
- `test_qa_tools_consolidation.py`

These can be safely deleted after successful test consolidation:
```bash
rm -f batch_refactor_fin_tests.py clean_imports.py consolidate_browser_fixtures.py
rm -f consolidate_browser_fixtures_pytests.py fix_import_paths.py fix_syntax_errors.py  
rm -f manual_fix_remaining.py test_consolidation_results.py test_qa_tools_consolidation.py
```