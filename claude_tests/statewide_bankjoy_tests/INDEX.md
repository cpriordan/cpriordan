# Bankjoy Automation Testing Suite - File Index

## 📋 Quick Navigation

### 🚀 Start Here
1. **QUICKSTART.md** - 5-minute quick start guide
2. **README.md** - Complete documentation

### 🔧 Setup & Installation
3. **setup.sh** - Linux/Mac setup script (run: `./setup.sh`)
4. **setup.bat** - Windows setup script (run: `setup.bat`)
5. **requirements.txt** - Python dependencies

### 💻 Main Scripts

#### Production Ready (Recommended)
6. **bankjoy_automation_enhanced.py** - Enhanced version with:
   - Config file support
   - Detailed logging
   - JSON results export
   - Better error handling
   
   **Run with:**
   ```bash
   python bankjoy_automation_enhanced.py
   ```

#### Simple Version
7. **bankjoy_automation.py** - Straightforward implementation
   
   **Run with:**
   ```bash
   python bankjoy_automation.py
   ```

#### Testing Utility
8. **test_single_product.py** - Test specific products
   
   **Run with:**
   ```bash
   python test_single_product.py "checking account"
   python test_single_product.py --list
   ```

### ⚙️ Configuration
9. **config.json** - Central configuration file
   - Change credentials
   - Update URLs
   - Modify selectors
   - Adjust timeouts
   - Browser settings

### 📚 Documentation
10. **PROJECT_SUMMARY.md** - This file - complete project overview

---

## 📖 How to Use This Suite

### First Time Setup
```bash
# Linux/Mac
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

### Run Tests
```bash
# All products (recommended)
python bankjoy_automation_enhanced.py

# All products (simple)
python bankjoy_automation.py

# Single product
python test_single_product.py "checking account"

# Multiple specific products
python test_single_product.py "cd" "ira" "credit card"

# List products
python test_single_product.py --list
```

### View Results
```bash
# Screenshots
statewide/olb/login/core_products/
statewide/olb/overlay/core_products/
statewide/olb/card/core_products/

# Test results (enhanced version)
statewide/test_results.json
```

---

## 📁 File Descriptions

| File | Size | Purpose |
|------|------|---------|
| bankjoy_automation_enhanced.py | 24KB | Main automation (recommended) |
| bankjoy_automation.py | 17KB | Simple automation version |
| test_single_product.py | 3.8KB | Test individual products |
| config.json | 1.8KB | Configuration settings |
| setup.sh | 1.8KB | Linux/Mac installer |
| setup.bat | 1.8KB | Windows installer |
| requirements.txt | 19B | Python dependencies |
| README.md | 4.1KB | Full documentation |
| QUICKSTART.md | 4.2KB | Quick start guide |
| PROJECT_SUMMARY.md | 8.0KB | Project overview |

---

## 🎯 What Gets Tested

For each of 10 core products:
1. ✓ Login page tile ad
2. ✓ Post-login overlay ad
3. ✓ Dashboard card ad

= **30 screenshots total**

---

## 🔑 Core Products

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

---

## 💡 Quick Tips

**First Run**: Start with QUICKSTART.md  
**Need Details**: Check README.md  
**Customize**: Edit config.json  
**Debug**: Use test_single_product.py  
**Problems**: See troubleshooting in README.md

---

## 📞 Need Help?

1. Check **QUICKSTART.md** for common scenarios
2. Read **README.md** for detailed info
3. Review **config.json** for customization
4. Check troubleshooting section in README.md

---

## ✅ Checklist

Before running tests:
- [ ] Python 3.8+ installed
- [ ] pip installed
- [ ] Run setup.sh or setup.bat
- [ ] Playwright browsers installed
- [ ] config.json reviewed (optional)
- [ ] Credentials verified (optional)

After running tests:
- [ ] Check statewide/ directory for screenshots
- [ ] Review test_results.json (enhanced version)
- [ ] Verify all products tested
- [ ] Review any error messages

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Python**: 3.8+  
**Framework**: Playwright

**Ready to start?** → Open QUICKSTART.md
