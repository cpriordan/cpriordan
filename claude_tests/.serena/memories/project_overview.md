# Project Overview

## Purpose
This is a Playwright-based end-to-end testing suite for testing financial services websites and applications. The tests focus on:

- User authentication and 2FA flows
- Ad personalization and targeting
- Multi-product scenarios for financial institutions
- Campaign management and publishing workflows
- Admin interface testing
- JavaScript error detection and tag validation

## Tech Stack

### Core Dependencies
- **Python**: Programming language
- **Playwright**: Browser automation (async and sync APIs)
- **pytest**: Test framework
- **pytest-asyncio**: Async support for pytest
- **pyotp**: TOTP 2FA code generation
- **python-dotenv**: Environment variable management
- **Pillow (PIL)**: Optional - for image comparison in visual testing

### Browser Configuration
- Tests primarily use Chromium via Playwright
- Support for headless and headed modes
- DevTools integration for debugging

## Environment Support
Tests support multiple environments:
- **STG** (Staging): Testing environment
- **PROD** (Production): Production environment
- Environment controlled via `test_env` variable or `--env` CLI flag
- Environment-specific screenshot directories created automatically

## Key Features
- Retry mechanisms for authentication failures
- Timeout handling for slow-loading elements
- Comprehensive error logging and reporting
- Screenshot capture and management
- TOTP-based 2FA automation
- Page Object Model pattern
