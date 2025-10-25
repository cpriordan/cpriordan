#!/bin/bash

# Bankjoy Automation Setup Script
# This script sets up the environment and runs the automation

echo "=========================================="
echo "Bankjoy Automation Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "✓ pip3 found"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

if [ $? -eq 0 ]; then
    echo "✓ Playwright browsers installed successfully"
else
    echo "❌ Failed to install Playwright browsers"
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "You can now run the tests:"
echo ""
echo "  1. Test all products (enhanced):"
echo "     python3 bankjoy_automation_enhanced.py"
echo ""
echo "  2. Test all products (simple):"
echo "     python3 bankjoy_automation.py"
echo ""
echo "  3. Test single product:"
echo "     python3 test_single_product.py \"checking account\""
echo ""
echo "  4. View available products:"
echo "     python3 test_single_product.py --list"
echo ""
echo "=========================================="
