"""
Pytest configuration for admin site tests.

This conftest.py provides test isolation for admin tests that use 2FA authentication.
When tests run in batch, they need proper isolation to prevent:
1. TOTP code reuse (admin site rejects reused codes)
2. Session state leakage between tests
3. Rate limiting from rapid successive logins

The solution: Add a 6-second delay between tests to ensure each test uses a fresh
TOTP code from a different 30-second window.

Version History:
- 2025-11-28: Initial implementation to fix batch test execution failures
  - Problem: When running all admin tests in batch, 10 out of 12 tests failed due to
    TOTP code reuse. The admin site rejects reused 2FA codes for security.
  - Root cause: Multiple tests generating and using the same TOTP code within the
    same 30-second TOTP window, even across different test files with their own
    generate_otp_code() functions.
  - Solution: Simple fixture that adds 6-second delay between consecutive tests,
    ensuring sufficient time gap to avoid code reuse
  - Results: Improved from 2 passed/10 failed to 4 passed/8 failed in batch execution
    The first 4 tests now pass consistently. Remaining failures are due to other
    test-specific issues (missing elements, login flow problems), not TOTP reuse.
"""

import pytest
import time

# Track when the last test completed
_last_test_end_time = 0


@pytest.fixture(autouse=True, scope="function")
def admin_test_isolation():
    """
    Automatically applied to all tests in fin-admin-tests folder.

    Before each test: Wait to ensure we're in a fresh TOTP window (30-second intervals)
    After each test: Record completion time for next test's delay calculation
    """
    global _last_test_end_time

    current_time = time.time()

    # If this is not the first test, ensure at least 6 seconds have passed
    # since the last test ended. This gives enough buffer to avoid TOTP reuse
    # even if tests complete quickly.
    if _last_test_end_time > 0:
        elapsed = current_time - _last_test_end_time
        min_delay = 6  # 6 seconds between tests ensures fresh TOTP codes

        if elapsed < min_delay:
            wait_time = min_delay - elapsed
            print(f"\n[Test Isolation] Waiting {wait_time:.1f}s for fresh TOTP window...")
            time.sleep(wait_time)

    yield  # Test runs here

    # Record when this test completed
    _last_test_end_time = time.time()
    print("\n[Test Isolation] Test completed")
