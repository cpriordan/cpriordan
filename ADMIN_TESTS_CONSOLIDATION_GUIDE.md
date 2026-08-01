# Admin Tests Consolidation Guide

This guide explains how the admin tests have been consolidated using `qa_tools.py` to reduce code duplication and improve maintainability.

## Overview

The admin tests previously had significant code duplication across multiple files, particularly around:
- Environment variable loading and validation  
- TOTP authentication setup
- Browser context creation
- Login page interactions
- Screenshot management
- Error validation

## Consolidated Functions

### Core Admin Functions Added to qa_tools.py

#### 1. `AdminLoginPage` Class
Unified login page class that supports both sync and async operations:

```python
from qa_tools import AdminLoginPage

# For sync tests
login_page = AdminLoginPage(page, is_async=False)

# For async tests  
login_page = AdminLoginPage(page, is_async=True)

# Common methods work for both:
login_page.navigate(test_env)
login_page.login(username, password)
otp_code = login_page.enter_2fa_code(totp)
login_page.take_screenshot(path)
```

#### 2. `setup_admin_test_environment(client_type)`
Consolidates environment setup for different client types:

```python
# Automatically loads .env, validates variables, creates TOTP
findata_user, findata_pw, findata_otp, test_env, totp, screenshots_dir = setup_admin_test_environment('gocu')

# Supported client types: 'gocu', 'vys', 'tru'
```

#### 3. Browser Context Fixtures
Consolidated browser fixtures for both sync and async tests:

```python
# For sync tests
def test_something(admin_browser_context_sync):
    page = admin_browser_context_sync.new_page()

# For async tests  
@pytest.mark.asyncio
async def test_something(admin_browser_context_async):
    page = await admin_browser_context_async.new_page()
```

#### 4. Validation Functions
Consolidated validation with permission checking:

```python
# Validate login success and check user permissions
expected_permissions = {
    "AI Scenarios": False,  # Should not be visible for basic users
    "Content": True         # Should be visible for basic users
}
validate_admin_login_success(page, test_env, expected_permissions)

# Async version
await validate_admin_login_success_async(page, test_env, expected_permissions)
```

## Migration Examples

### Before (Original Code)
```python
# Duplicated in every test file
import os
from dotenv import load_dotenv
from pyotp import TOTP

load_dotenv()
findata_user = os.environ.get("FINDATA_GOCU_USER")
findata_pw = os.environ.get("FINDATA_GOCU_PW")
findata_otp = os.environ.get("FINDATA_GOCU_OTP")
test_env = os.environ.get("TEST_ENVIRONMENT")

if not findata_user or not findata_pw or not findata_otp or not test_env:
    raise ValueError("Required environment variables not set!")

totp = TOTP(findata_otp, interval=30, digits=6, digest="sha1")

class LoginPage:
    # ... 50+ lines of duplicated code
    
def clear_screenshots_directory(directory):
    # ... duplicated implementation

@pytest.fixture(scope="function")
def browser_context():
    # ... duplicated browser setup
```

### After (Consolidated Code)
```python
from qa_tools import (
    AdminLoginPage, 
    setup_admin_test_environment,
    admin_browser_context_sync,
    clear_screenshots_directory,
    validate_admin_login_success
)

def test_admin_function(admin_browser_context_sync):
    # Single line setup
    findata_user, findata_pw, findata_otp, test_env, totp, screenshots_dir = setup_admin_test_environment('gocu')
    
    # Use consolidated components
    login_page = AdminLoginPage(page, is_async=False)
    # ... rest of test logic
```

## Benefits of Consolidation

### 1. **Reduced Code Duplication**
- Eliminated ~100+ lines of duplicate code per test file
- Single source of truth for common functionality
- Consistent behavior across all admin tests

### 2. **Improved Maintainability**
- Changes to login logic only need to be made in one place
- Easier to add new client types or authentication methods
- Centralized error handling and validation

### 3. **Better Error Handling**
- Consistent TOTP timing validation prevents authentication failures
- Unified error messaging and debugging capabilities
- Centralized retry logic for flaky network conditions

### 4. **Environment Management**
- Automatic client type mapping to environment variables
- Consistent screenshot directory management
- Better separation of test configuration

### 5. **Test Reliability**
- Standardized wait strategies and timeouts
- Consistent screenshot capture for debugging
- Unified server error validation

## Client Type Support

The consolidation supports multiple client types with automatic environment variable mapping:

| Client Type | User Variable | Password Variable | OTP Variable |
|-------------|---------------|-------------------|--------------|
| `gocu` | `FINDATA_GOCU_USER` | `FINDATA_GOCU_PW` | `FINDATA_GOCU_OTP` |
| `vys` | `FINDATA_VYS_USER` | `FINDATA_VYS_PW` | `FINDATA_VYS_OTP` |
| `tru` | `FINDATA_TRU_USER` | `FINDATA_TRU_PW` | `FINDATA_TRU_OTP` |

## Usage Recommendations

### 1. For Simple Login Tests
Use the basic consolidated pattern shown in the GOCU example.

### 2. For Complex Workflow Tests  
Build on the consolidated base but keep specific page objects for complex interactions (like MediaLibraryPage).

### 3. For New Client Types
Add new client mappings to the `client_map` dictionary in `setup_admin_test_environment()`.

### 4. For Permission Testing
Use the `expected_permissions` parameter to validate user access levels consistently.

## Migration Strategy

1. **Start with new tests**: Use consolidated functions for all new admin tests
2. **Gradual migration**: Refactor existing tests one at a time when making changes  
3. **Validate behavior**: Ensure refactored tests produce identical results to originals
4. **Remove duplicates**: Delete original test files after confirming refactored versions work

## Example Files

Reference implementations can be found in:
- `test_findata_stg_login_gocu_basic_admin_account_access_REFACTORED_EXAMPLE.py`
- `test_findata_stg_gocu_basic_login_using_2fa_REFACTORED_EXAMPLE.py` 
- `test_findata_stg_login_vys_admin_account_media_library_REFACTORED_EXAMPLE.py`

These examples demonstrate both sync and async consolidation patterns and can be used as templates for migrating other admin tests.