# Bankjoy Automation Workflow

## 📊 Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BANKJOY AUTOMATION                       │
│                   Testing Workflow                          │
└─────────────────────────────────────────────────────────────┘

FOR EACH CORE PRODUCT (10 total):

┌─────────────────────────────────────────────────────────────┐
│ STEP 1: LOGIN PAGE AD TESTING                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Open Chrome (Incognito)                                │
│     ↓                                                       │
│  2. Navigate to:                                           │
│     https://statewide.stage.bankjoy.com/                   │
│     ?cb=1&session_init=1&debug_all=1                      │
│     &products_recommended={core_product}                   │
│     ↓                                                       │
│  3. Refresh Page                                           │
│     ↓                                                       │
│  4. Scroll Down to Find Overlay                            │
│     CSS: #finalytics-information-wrapper-ad                │
│     ↓                                                       │
│  5. Take Screenshot → statewide/olb/login/core_products/   │
│     ↓                                                       │
│  6. Verify CTA Button                                      │
│     - Text contains expected keyword                       │
│     - Link is valid                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                            ↓

┌─────────────────────────────────────────────────────────────┐
│ STEP 2: AUTHENTICATION                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Navigate to signin page                                │
│     ↓                                                       │
│  2. Enter Username: cbracey25                              │
│     CSS: #username                                         │
│     ↓                                                       │
│  3. Enter Password: SwFCU2025$$$                           │
│     CSS: #password                                         │
│     ↓                                                       │
│  4. Click "Continue" Button                                │
│     ↓                                                       │
│  5. Wait for Login Success                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                            ↓

┌─────────────────────────────────────────────────────────────┐
│ STEP 3: OVERLAY AD TESTING                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Refresh Page                                           │
│     ↓                                                       │
│  2. Wait for Broadcast Overlay                             │
│     CSS: #finalytics-broadcast-ad                          │
│     ↓                                                       │
│  3. Scroll to Make Visible                                 │
│     ↓                                                       │
│  4. Take Screenshot → statewide/olb/overlay/core_products/ │
│     ↓                                                       │
│  5. Verify CTA Button                                      │
│     - Text contains expected keyword                       │
│     - Link is valid                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                            ↓

┌─────────────────────────────────────────────────────────────┐
│ STEP 4: CARD AD TESTING                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Close Overlay (Click X Button)                         │
│     CSS: #mat-mdc-dialog-0 > ... > button                  │
│     ↓                                                       │
│  2. Resize Browser to 80%                                  │
│     ↓                                                       │
│  3. Look for Card Ad                                       │
│     CSS: #finalytics-tile-ad > div > img                   │
│     ↓                                                       │
│  4. If Not Visible → Navigate to Dashboard                 │
│     https://statewide.stage.bankjoy.com/                   │
│     consumer/main/dashboard                                │
│     ?products_recommended={core_product}                   │
│     ↓                                                       │
│  5. Scroll to Find Card Ad                                 │
│     ↓                                                       │
│  6. Take Screenshot → statewide/olb/card/core_products/    │
│     ↓                                                       │
│  7. Verify CTA Link                                        │
│     - Text contains expected keyword                       │
│     - Link is valid                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                            ↓

┌─────────────────────────────────────────────────────────────┐
│ STEP 5: CLEANUP & NEXT PRODUCT                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Close Browser Context                                  │
│     ↓                                                       │
│  2. Save Test Results                                      │
│     ↓                                                       │
│  3. Move to Next Product                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                            ↓

┌─────────────────────────────────────────────────────────────┐
│ FINAL RESULTS                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✓ 30 Screenshots Captured                                 │
│    - 10 Login page ads                                     │
│    - 10 Overlay ads                                        │
│    - 10 Card ads                                           │
│                                                             │
│  ✓ Test Results JSON (Enhanced Version)                    │
│    - Total tests: 10                                       │
│    - Passed: X                                             │
│    - Failed: Y                                             │
│    - Success rate: Z%                                      │
│                                                             │
│  ✓ Organized Directory Structure                           │
│    statewide/                                              │
│    └── olb/                                                │
│        ├── login/core_products/                            │
│        ├── overlay/core_products/                          │
│        └── card/core_products/                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Parallel Structure

```
Core Product Loop (Sequential)
├── checking account
│   ├── Login Ad Test ✓
│   ├── Authentication ✓
│   ├── Overlay Ad Test ✓
│   └── Card Ad Test ✓
├── cd
│   ├── Login Ad Test ✓
│   ├── Authentication ✓
│   ├── Overlay Ad Test ✓
│   └── Card Ad Test ✓
├── equipment loan
│   └── ... (same 4 steps)
├── personal loan
│   └── ... (same 4 steps)
├── rv loan
│   └── ... (same 4 steps)
├── ira
│   └── ... (same 4 steps)
├── credit card
│   └── ... (same 4 steps)
├── boat loan
│   └── ... (same 4 steps)
├── car loan
│   └── ... (same 4 steps)
└── savings account
    └── ... (same 4 steps)
```

## 📸 Screenshot Matrix

```
                 Login Page    Overlay Ad    Card Ad
              ┌─────────────┬─────────────┬─────────────┐
checking      │     ✓       │      ✓      │      ✓      │
cd            │     ✓       │      ✓      │      ✓      │
equipment loan│     ✓       │      ✓      │      ✓      │
personal loan │     ✓       │      ✓      │      ✓      │
rv loan       │     ✓       │      ✓      │      ✓      │
ira           │     ✓       │      ✓      │      ✓      │
credit card   │     ✓       │      ✓      │      ✓      │
boat loan     │     ✓       │      ✓      │      ✓      │
car loan      │     ✓       │      ✓      │      ✓      │
savings       │     ✓       │      ✓      │      ✓      │
              └─────────────┴─────────────┴─────────────┘
                   10            10            10
                        = 30 Screenshots Total
```

## 🎯 Verification Points

```
For Each Ad Type:

Login Page Ad
├── Element Visibility ✓
├── Screenshot Capture ✓
├── CTA Button Exists ✓
├── CTA Text Correct ✓
└── CTA Link Valid ✓

Overlay Ad
├── Element Visibility ✓
├── Screenshot Capture ✓
├── CTA Button Exists ✓
├── CTA Text Correct ✓
└── CTA Link Valid ✓

Card Ad
├── Element Visibility ✓
├── Screenshot Capture ✓
├── CTA Link Exists ✓
├── CTA Text Correct ✓
└── CTA Link Valid ✓
```

## ⚙️ Configuration Flow

```
config.json
├── URLs & Endpoints
│   ├── base_url
│   ├── signin_url
│   └── dashboard_url
│
├── Credentials
│   ├── username
│   └── password
│
├── Core Products (10)
│   └── [list of products]
│
├── Selectors (CSS)
│   ├── login
│   ├── overlay
│   └── card
│
├── Timeouts
│   ├── element_wait
│   ├── page_load
│   ├── scroll_delay
│   └── max_scrolls
│
├── Browser Settings
│   ├── headless
│   ├── viewport
│   └── card_ad_zoom
│
└── Screenshots
    ├── base_directory
    ├── full_page
    └── subdirectories
```

## 🔍 Error Handling Flow

```
Try Test Step
    ↓
  Success?
    ├─ Yes → Continue
    │         ↓
    │    Take Screenshot
    │         ↓
    │    Verify CTA
    │         ↓
    │    Log Success
    │
    └─ No → Retry with Fallback
              ↓
           Success?
              ├─ Yes → Continue
              │
              └─ No → Log Error
                       ↓
                  Continue to Next Step
                       ↓
                  Mark Test as Partial Failure
```

## 📊 Results Aggregation

```
Test Results (Enhanced Version)
├── Total Products Tested: 10
├── Passed: X
├── Failed: Y
├── Success Rate: Z%
├── Duration: HH:MM:SS
│
└── Per Product Details
    ├── Product Name
    ├── Timestamp
    ├── Overall Success: true/false
    │
    └── Step Results
        ├── login_page_ad
        │   ├── success: true/false
        │   ├── screenshot: path
        │   ├── cta_verified: true/false
        │   └── errors: []
        │
        ├── signin
        │   ├── success: true/false
        │   └── errors: []
        │
        ├── overlay_ad
        │   ├── success: true/false
        │   ├── screenshot: path
        │   ├── cta_verified: true/false
        │   └── errors: []
        │
        └── card_ad
            ├── success: true/false
            ├── screenshot: path
            ├── cta_verified: true/false
            └── errors: []
```

## 🚀 Execution Timeline

```
Start
  ↓
[Setup] 0:00:00
  - Load config
  - Create directories
  ↓
[Product 1] 0:00:05 - 0:02:00
  - Login ad (30s)
  - Signin (20s)
  - Overlay ad (30s)
  - Card ad (35s)
  ↓
[Product 2] 0:02:00 - 0:04:00
  - ... (same timing)
  ↓
[Product 3-10] ...
  ↓
[Results] ~0:20:00
  - Print summary
  - Save JSON
  ↓
Complete
```

---

**Estimated Total Time**: 15-25 minutes for all 10 products  
**Per Product**: ~1.5-2.5 minutes  
**Parallelization**: Not currently implemented (could reduce to 5-10 min)
