@echo off
REM Bankjoy Automation Setup Script for Windows

echo ==========================================
echo Bankjoy Automation Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%
echo.

REM Check if pip is installed
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not installed. Please install pip.
    pause
    exit /b 1
)

echo [OK] pip found
echo.

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully
echo.

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install chromium

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Playwright browsers
    pause
    exit /b 1
)

echo [OK] Playwright browsers installed successfully
echo.

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo You can now run the tests:
echo.
echo   1. Test all products (enhanced):
echo      python bankjoy_automation_enhanced.py
echo.
echo   2. Test all products (simple):
echo      python bankjoy_automation.py
echo.
echo   3. Test single product:
echo      python test_single_product.py "checking account"
echo.
echo   4. View available products:
echo      python test_single_product.py --list
echo.
echo ==========================================
pause
