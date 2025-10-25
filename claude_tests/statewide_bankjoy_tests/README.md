# Bankjoy Automation Testing Script

This Python script automates testing of the Bankjoy site with different core products using Playwright.

## Features

- Tests 10 different core products (checking account, cd, equipment loan, etc.)
- Captures screenshots at three different stages:
  1. Login page tile ad
  2. Post-login overlay ad
  3. Dashboard card ad
- Verifies CTA buttons and links for each ad type
- Organizes screenshots in structured directories
- Uses Chrome incognito mode for each test

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

Or install all browsers:

```bash
playwright install
```

## Usage

### Run All Tests

```bash
python bankjoy_automation.py
```

This will:
- Create necessary directories (`statewide/olb/login/core_products`, `statewide/olb/overlay/core_products`, `statewide/olb/card/core_products`)
- Test all 10 core products sequentially
- Save screenshots with appropriate naming conventions

### Output Structure

```
statewide/
├── olb/
│   ├── login/
│   │   └── core_products/
│   │       ├── checking_account_login.png
│   │       ├── cd_login.png
│   │       ├── equipment_loan_login.png
│   │       └── ...
│   ├── overlay/
│   │   └── core_products/
│   │       ├── checking_account_overlay.png
│   │       ├── cd_overlay.png
│   │       └── ...
│   └── card/
│       └── core_products/
│           ├── checking_account_card.png
│           ├── cd_card.png
│           └── ...
```

## Test Flow for Each Core Product

### Step 1: Login Page Ad
- Navigate to: `https://statewide.stage.bankjoy.com/?cb=1&session_init=1&debug_all=1&products_recommended={core_product}`
- Refresh the page
- Scroll to find overlay with selector: `#finalytics-information-wrapper-ad`
- Take screenshot
- Verify CTA button text and link

### Step 2: Sign In & Overlay Ad
- Scroll up and sign in with credentials:
  - Username: `cbracey25`
  - Password: `SwFCU2025$$$`
- Refresh page after login
- Wait for broadcast overlay: `#finalytics-broadcast-ad`
- Take screenshot
- Verify CTA button

### Step 3: Close Overlay & Card Ad
- Close overlay using X button
- Resize browser to 80%
- If card ad not visible, navigate to dashboard with products_recommended parameter
- Take screenshot
- Verify CTA link

## Core Products Tested

1. checking account
2. cd
3. equipment loan
4. personal loan
5. rv loan
6. ira
7. credit card
8. boat loan
9. car loan
10. savings account

## Configuration

### Credentials
Edit the `BankjoyTester` class to change credentials:
```python
self.username = "cbracey25"
self.password = "SwFCU2025$$$"
```

### Headless Mode
To run tests in headless mode (no browser window), modify the launch parameters:
```python
browser = await p.chromium.launch(
    headless=True,  # Change to True
    ...
)
```

### Screenshot Directory
Change the base directory:
```python
self.screenshot_base_dir = Path("your_custom_directory")
```

## Troubleshooting

### Element Not Found
If elements are not found:
- Check if the selectors have changed on the website
- Increase timeout values in `wait_for_element()` method
- Adjust scroll parameters if ads are not visible

### Login Issues
- Verify credentials are correct
- Check if the login page structure has changed
- Ensure network connectivity to staging environment

### Screenshot Issues
- Ensure write permissions for the output directory
- Check disk space availability

## Notes

- Each core product test runs in a fresh browser context (incognito)
- Tests include automatic retries and fallback strategies
- Full page screenshots are captured
- CTA verification checks both text content and href attributes
- The script handles dynamic content loading with appropriate waits

## Support

For issues or questions, refer to:
- Playwright documentation: https://playwright.dev/python/
- Bankjoy staging environment documentation
