# Bankjoy Automation Quick Start Guide

## 📦 Files Included

1. **bankjoy_automation.py** - Main automation script (simple version)
2. **bankjoy_automation_enhanced.py** - Enhanced version with config support and detailed logging
3. **test_single_product.py** - Helper script to test specific products
4. **config.json** - Configuration file for customization
5. **requirements.txt** - Python dependencies
6. **README.md** - Full documentation

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Step 2: Run Tests

**Option A: Test All Products (Enhanced Version - Recommended)**
```bash
python bankjoy_automation_enhanced.py
```

**Option B: Test All Products (Simple Version)**
```bash
python bankjoy_automation.py
```

**Option C: Test Single Product**
```bash
python test_single_product.py "checking account"
```

**Option D: Test Multiple Specific Products**
```bash
python test_single_product.py "checking account" "cd" "ira"
```

## 📁 Output Structure

After running, you'll find:
```
statewide/
├── olb/
│   ├── login/core_products/     # Login page screenshots
│   ├── overlay/core_products/   # Overlay ad screenshots
│   └── card/core_products/      # Card ad screenshots
└── test_results.json            # Detailed test results (enhanced version only)
```

## ⚙️ Customization

### Change Credentials
Edit `config.json`:
```json
"credentials": {
  "username": "your_username",
  "password": "your_password"
}
```

### Run in Headless Mode
Edit `config.json`:
```json
"browser": {
  "headless": true,
  ...
}
```

### Change Screenshot Directory
Edit `config.json`:
```json
"screenshots": {
  "base_directory": "your_directory_name",
  ...
}
```

## 🎯 What Each Script Tests

For each core product, the automation:

1. **Login Page Ad** ✓
   - Navigates with products_recommended parameter
   - Finds and screenshots tile ad overlay
   - Verifies CTA button text and link

2. **Sign In** ✓
   - Enters credentials
   - Clicks Continue
   - Waits for successful login

3. **Overlay Ad** ✓
   - Refreshes page
   - Finds broadcast overlay
   - Screenshots overlay
   - Verifies CTA button

4. **Card Ad** ✓
   - Closes overlay
   - Resizes browser to 80%
   - Finds card/tile ad
   - Screenshots card
   - Verifies CTA link

## 🔍 Viewing Results

### Enhanced Version
Check `statewide/test_results.json` for detailed results:
```json
{
  "total": 10,
  "passed": 10,
  "failed": 0,
  "details": [...]
}
```

### All Versions
Browse screenshots in `statewide/olb/` directories.

## 📊 Core Products Tested

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

## 🆘 Troubleshooting

### "playwright not found"
```bash
pip install playwright
playwright install
```

### "Element not found"
- Check if selectors in `config.json` match the website
- Increase timeouts in `config.json`
- Run with `headless: false` to see what's happening

### Login fails
- Verify credentials in `config.json`
- Check if staging environment is accessible
- Ensure you have network connectivity

## 💡 Tips

1. **First Run**: Use enhanced version with headless=false to watch the automation
2. **Production Runs**: Switch to headless=true for faster execution
3. **Debugging**: Test single products first using `test_single_product.py`
4. **CI/CD Integration**: Use enhanced version and parse `test_results.json`

## 📝 Example Commands

```bash
# List available products
python test_single_product.py --list

# Test just checking account and CD
python test_single_product.py "checking account" "cd"

# Run all tests in headless mode (edit config.json first)
python bankjoy_automation_enhanced.py

# View test results
cat statewide/test_results.json | python -m json.tool
```

## 🎓 Next Steps

1. Review screenshots in `statewide/olb/` directories
2. Check `test_results.json` for any failed tests
3. Customize `config.json` for your specific needs
4. Integrate into your CI/CD pipeline

---

**Need Help?** Check the full README.md for comprehensive documentation.
