# Codebase Structure

## Directory Layout
```
claude_tests/
├── .serena/                    # Serena MCP server configuration
├── CLAUDE.md                   # Project instructions for Claude Code
└── test_*.py                   # All test files (flat structure)
```

## Test File Categories

### Authentication Tests
- `test_findata_stg_login_*`: Admin login flows with 2FA
- `test_findata_stg_gocu_basic_login_using_2fa.py`: Basic 2FA login test

### Personalization Tests
- `test_*_auto_loan_personalization_*`: Dynamic content personalization tests
- Tests for different clients: barcons, marketusafcu, stanthony, etc.

### Multi-product Tests
- `test_*_multiproduct_*`: Multiple financial product display tests
- Tests for clients: ssscu, tru, u1st

### Funnel Tests
- `test_*_funnel_*`: User conversion funnel tests
- `test_missionfed_funnel_scenarios_*`: Mission Fed credit union funnel tests

### Error Detection Tests
- `test_*_stgtags_and_js_errors*`: Page functionality and JS error validation
- Tests for various clients and pages

### Campaign Tests
- `test_findata_stg_login_tru_staff_account_*`: Campaign creation, management, publishing

### Ad Expiration Tests
- `test_ad_expiration_by_time.py`: Time-based ad expiration
- `test_ad_expiration_by_views.py`: View-based ad expiration
- `test_ad_expiration_by_aggressive_expiration_by_time.py`: Aggressive time-based expiration

## Common Patterns

### Naming Conventions
- Test files: `test_<client>_<feature>_<scenario>.py`
- Test functions: `test_<description>`
- Fixtures: `<resource>_context` or `<resource>`
- Utility functions: `<verb>_<noun>` (e.g., `clear_screenshots_directory`)

### Screenshot Management
- Screenshots saved to: `tests/screenshots_{client}_using_pytest/<scenario>/{ENV}/`
- Environment-specific subdirectories (STG, PROD in UPPERCASE)
- Automatic cleanup before test runs
