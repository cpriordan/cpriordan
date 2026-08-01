# Test Automation Project – README

## Overview
This project contains automated end-to-end tests written in Python using pytest and Playwright. The tests are located in the `tests/` folder and are designed to validate core site functionality for different scenarios (e.g., core product ads, multiproduct hero ads, cards) and checks for errors (Javacript errors but only for finalytics related javascript files and missing finalytics tags). The tests that are in the 'tests/ADMINSITETESTS' are tests that cannot be executed in groups and can only be executed one at a time since it uses 2FA authentication.

## Setup
1. Clone the repository and navigate to the root folder.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On macOS/Linux
   venv\Scripts\activate    # On Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Install Playwright browsers:
   ```bash
   playwright install
   ```
5. Add a `.env` file in the project root with your environment variables (example below).

## .env file
```
BASIC_AUTH_USER=your_username
BASIC_AUTH_PASS=your_password
```
Note: `.gitignore` includes `.env` so credentials are not pushed to GitHub.

## Running Tests
To run all tests in the `tests/` folder and generate an HTML report:

```bash
pytest tests/ --html=report.html --self-contained-html
```

The report will be saved as `report.html` in the root folder.

## Additional Commands
- Run specific tests by marker:
  ```bash
  pytest -m smoke --html=smoke_report.html --self-contained-html
  ```
- Run a single test file:
  ```bash
  pytest tests/test_example.py --html=example_report.html --self-contained-html
  ```
- Run tests in parallel:
  ```bash
  pytest -n auto --html=parallel_report.html --self-contained-html
  ```
