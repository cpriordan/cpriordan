# OneAZ Finalytics Playwright Test

This repository contains a standalone Playwright script that tests the OneAZ homepage and business page for Finalytics tag validation and JavaScript errors. It uses the **Chrome** browser with HTTP basic auth and is scheduled to run **daily at 6 AM PST** using GitHub Actions.

---

## What it Does

* Navigates to the homepage and a test scenario page
* Validates expected Finalytics JS/CSS tags
* Detects JavaScript errors from specific files
* Verifies ad content on the hero section
* Saves screenshots and page source
* Clears old timestamped screenshot folders

---

## How to Run Locally

1. **Install dependencies:**

```bash
pip install -r requirements.txt
playwright install --with-deps
```

2. **Run the script manually:**

```bash
python script.py
```

---

## Output Structure

Screenshots and HTML sources are saved under:

```
PROD/
  screenshots_oneaz_<timestamp>/
    chromium/
      homepage_screenshot.png
      product_page_for_ad_screenshot.png
      homepage_before_selector_screenshot.png
      hero_ad1_screenshot_on_chromium.png
      homepage_source.html
      js_error_oneaz.png (if JS errors are detected)
```

Old screenshot folders for the `oneaz` client are deleted automatically before each run.

---

## GitHub Actions Setup

`.github/workflows/playwright.yml`:

```yaml
name: Run OneAZ Playwright Test

on:
  schedule:
    - cron: '0 14 * * *'  # Runs at 6 AM PST (14:00 UTC)
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Install Playwright browsers
        run: playwright install --with-deps

      - name: Run Playwright script
        run: python script.py
```

---

## Authentication

The script can uses HTTP basic authentication for the OneAZ staging site but it is not needed for running in production:

```python
context = await browser.new_context(http_credentials={"username": "OneAZ", "password": "pugs r potatoes!3"})
```

---

## JS Error Detection

If a JS error is triggered by any of these files:

* `finalytics.js`
* `finalytics-function.js`
* `settings_div.js`
* `settings.js`
* `controlbar.js`

A screenshot and error message will be captured.

---

## Cleanup Logic

The script deletes all existing screenshot folders starting with `screenshots_oneaz_` before each run to conserve space:

```python
clear_old_screenshot_directories("PROD", "oneaz")
```


