# Bankjoy Automation Testing Suite - Project Summary

## 📋 Overview

Complete automation testing solution for Bankjoy site that tests 10 core products across multiple scenarios (login page ads, overlay ads, and card ads) with automatic screenshot capture and verification.

## 📦 Deliverables

### Core Scripts
1. **bankjoy_automation.py** (Simple Version)
   - Clean, straightforward implementation
   - All tests in one file
   - Good for quick testing
   - ~400 lines of code

2. **bankjoy_automation_enhanced.py** (Recommended)
   - Configuration file support
   - Detailed test results tracking
   - Better error handling
   - JSON results export
   - ~700 lines of code

3. **test_single_product.py**
   - Test individual products
   - Test multiple specific products
   - Quick debugging tool
   - ~200 lines of code

### Configuration
4. **config.json**
   - Centralized configuration
   - Easy customization
   - No code changes needed
   - Contains:
     - URLs and endpoints
     - Credentials
     - CSS selectors
     - Timeouts
     - Browser settings
     - Screenshot settings

### Documentation
5. **README.md**
   - Complete documentation
   - Setup instructions
   - Usage examples
   - Troubleshooting guide
   - API reference

6. **QUICKSTART.md**
   - 5-minute quick start
   - Essential commands
   - Common use cases
   - Tips and tricks

### Setup Scripts
7. **setup.sh** (Linux/Mac)
   - Automated setup
   - Dependency installation
   - One-command setup

8. **setup.bat** (Windows)
   - Windows-compatible setup
   - Automated installation
   - User-friendly

9. **requirements.txt**
   - Python dependencies
   - Version-locked

## 🎯 Features

### Automated Testing
✓ Tests 10 core products automatically
✓ Three test scenarios per product:
  - Login page tile ad
  - Post-login overlay ad
  - Dashboard card ad
✓ Automatic CTA verification
✓ Link validation
✓ Screenshot capture at each stage

### Screenshot Management
✓ Organized directory structure
✓ Named by product and type
✓ Full-page screenshots
✓ Automatic directory creation

### Result Tracking (Enhanced Version)
✓ JSON results export
✓ Pass/fail tracking
✓ Detailed error reporting
✓ Timestamp tracking
✓ Success rate calculation

### Customization
✓ Config file support
✓ Adjustable timeouts
✓ Customizable selectors
✓ Flexible credentials
✓ Headless/headed modes

## 🔧 Technical Stack

- **Language**: Python 3.8+
- **Framework**: Playwright
- **Browser**: Chromium (Chrome)
- **Features Used**:
  - Async/await patterns
  - Page object model
  - Context isolation (incognito)
  - Dynamic element waiting
  - Automatic scrolling
  - Screenshot capture
  - JSON configuration

## 📊 Test Coverage

### Core Products (10)
1. Checking Account
2. CD
3. Equipment Loan
4. Personal Loan
5. RV Loan
6. IRA
7. Credit Card
8. Boat Loan
9. Car Loan
10. Savings Account

### Test Scenarios (3 per product = 30 total)
1. **Login Page Ad**
   - Navigation with URL parameter
   - Page refresh
   - Overlay detection
   - Screenshot capture
   - CTA text verification
   - CTA link verification

2. **Overlay Ad**
   - User authentication
   - Page refresh
   - Broadcast overlay detection
   - Screenshot capture
   - CTA text verification
   - CTA link verification

3. **Card Ad**
   - Overlay dismissal
   - Browser resize (80%)
   - Card ad detection
   - Screenshot capture
   - CTA text verification
   - CTA link verification

## 📁 Output Structure

```
statewide/
├── olb/
│   ├── login/
│   │   └── core_products/
│   │       ├── checking_account_login.png
│   │       ├── cd_login.png
│   │       ├── equipment_loan_login.png
│   │       ├── personal_loan_login.png
│   │       ├── rv_loan_login.png
│   │       ├── ira_login.png
│   │       ├── credit_card_login.png
│   │       ├── boat_loan_login.png
│   │       ├── car_loan_login.png
│   │       └── savings_account_login.png
│   ├── overlay/
│   │   └── core_products/
│   │       ├── checking_account_overlay.png
│   │       ├── cd_overlay.png
│   │       └── ... (10 files)
│   └── card/
│       └── core_products/
│           ├── checking_account_card.png
│           ├── cd_card.png
│           └── ... (10 files)
└── test_results.json (enhanced version only)
```

## 🚀 Usage Examples

### Run All Tests
```bash
# Enhanced version with results tracking
python bankjoy_automation_enhanced.py

# Simple version
python bankjoy_automation.py
```

### Test Specific Products
```bash
# Single product
python test_single_product.py "checking account"

# Multiple products
python test_single_product.py "checking account" "cd" "ira"

# List available products
python test_single_product.py --list
```

### Customization
```bash
# Edit config.json to change:
# - Credentials
# - URLs
# - Selectors
# - Timeouts
# - Browser settings
# - Screenshot settings
```

## ⚙️ Configuration Options

### Credentials
- Username: cbracey25
- Password: SwFCU2025$$$
- Easily changed in config.json

### Browser Settings
- Headless mode: false (default)
- Viewport: 1920x1080
- Card ad zoom: 80%

### Timeouts
- Element wait: 10 seconds
- Page load: 30 seconds
- Scroll delay: 500ms
- Max scrolls: 10

### Screenshots
- Base directory: "statewide"
- Full page: true
- Organized by type

## 🔍 Verification Checks

Each test performs:
1. ✓ Element visibility check
2. ✓ Screenshot capture
3. ✓ CTA button/link existence
4. ✓ CTA text content
5. ✓ CTA href attribute
6. ✓ Page navigation

## 📈 Success Metrics

The enhanced version tracks:
- Total products tested
- Passed tests
- Failed tests
- Success rate percentage
- Duration
- Individual step results
- Error messages
- Screenshots captured

## 🎓 Best Practices Implemented

1. **Async/Await**: Non-blocking I/O
2. **Context Isolation**: Fresh state per test
3. **Error Handling**: Try-catch blocks
4. **Retry Logic**: Multiple selector attempts
5. **Wait Strategies**: Dynamic element waiting
6. **Logging**: Detailed console output
7. **Results Export**: JSON format
8. **Configuration**: External config file
9. **Documentation**: Comprehensive guides
10. **Cross-platform**: Works on Windows, Mac, Linux

## 🛠️ Maintenance

### Adding New Products
Edit config.json:
```json
"core_products": [
  "existing product",
  "new product name"
]
```

### Updating Selectors
Edit config.json selectors section:
```json
"selectors": {
  "login": {
    "tile_ad_wrapper": "#new-selector"
  }
}
```

### Changing Timeouts
Edit config.json timeouts section:
```json
"timeouts": {
  "element_wait": 15000
}
```

## 📞 Support Resources

- **Documentation**: README.md
- **Quick Start**: QUICKSTART.md
- **Configuration**: config.json (with comments)
- **Playwright Docs**: https://playwright.dev/python/

## 🎯 Success Criteria

This automation suite successfully:
✓ Tests all 10 core products
✓ Captures 30 screenshots (3 per product)
✓ Verifies all CTA buttons/links
✓ Handles authentication
✓ Manages dynamic content
✓ Provides detailed results
✓ Supports customization
✓ Works cross-platform
✓ Includes comprehensive documentation
✓ Offers multiple usage modes

## 📝 Notes

- **Environment**: Staging (statewide.stage.bankjoy.com)
- **Browser**: Chrome (Chromium via Playwright)
- **Mode**: Incognito (new context per product)
- **Network**: Requires internet connectivity
- **Credentials**: Staging environment credentials
- **Screenshots**: Full-page, organized by type

## 🔄 Future Enhancements

Potential improvements:
- Parallel test execution
- Video recording option
- Email reporting
- Slack notifications
- Database storage
- CI/CD integration examples
- Docker containerization
- Cloud deployment scripts

---

**Version**: 1.0.0  
**Created**: 2025  
**Language**: Python 3.8+  
**Framework**: Playwright  
**License**: [Your License]  

For questions or issues, refer to the comprehensive documentation in README.md or QUICKSTART.md.
