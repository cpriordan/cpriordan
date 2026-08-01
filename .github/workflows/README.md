# GitHub Actions Workflows - MissionFed Funnel Tests

This directory contains automated test workflows for MissionFed funnel scenarios using GitHub Actions.

## 📋 Available Workflows

### 1. MissionFed Checking Funnel Test - Weekly

**File:** `missionfed_checking_funnel_weekly.yml`

**Description:** Runs the standalone checking account funnel test.

**Schedule:**
- Every Monday at 6:00 AM PST (14:00 UTC)
- Can be triggered manually from GitHub UI

**Test File:** `fin-tests/test_missionfed_checking_funnel_scenario_PROD.py`

**What it tests:**
- Checking account product selection flow
- Cross-frame iframe detection
- Hero image validation
- Funnel CTA detection
- Image URL verification

---

### 2. MissionFed All Funnel Scenarios - Weekly

**File:** `missionfed_all_scenarios_weekly.yml`

**Description:** Runs all 7 MissionFed funnel scenarios with visual regression testing.

**Schedule:**
- Every Sunday at 6:00 AM PST (14:00 UTC)
- Can be triggered manually from GitHub UI

**Test File:** `pytests/test_missionfed_funnel_scenarios_PROD.py`

**What it tests:**
- ✅ checking (may fail - personalization)
- ✅ savings
- ✅ cd (Certificate of Deposit)
- ✅ personal loan
- ✅ credit card (may fail - personalization)
- ✅ hispanic checking
- ✅ hispanic credit card

**Expected Results:**
- **Pass Rate:** 71% (5/7 scenarios)
- **Known Issues:** checking & credit card may show Hispanic personalization variants

---

### 3. GOCU — Admin Basic Account Access (STG)

**File:** `gocu_admin_basic_account_access_stg.yml`

**Description:** Logs into the GOCU admin portal on STG with TOTP-based 2FA and
verifies a basic admin account has the expected permissions (e.g. `Content`
visible, `AI Scenarios` not visible).

**Schedule:**
- Manual only (`workflow_dispatch`) — this test performs a live 2FA login,
  so it isn't run automatically on push/schedule.

**Test File:** `pytests/ADMINSITETESTS/test_findata_stg_login_gocu_basic_admin_account_access.py`

**Required repository secrets:**

| Secret | Description |
|---|---|
| `FINDATA_GOCU_USER` | GOCU admin username used to log in |
| `FINDATA_GOCU_PW` | Password for the above account |
| `FINDATA_GOCU_OTP` | TOTP secret (base32) used to generate the 2FA code |

**Secrets setup checklist:**

- [ ] Go to repo **Settings → Secrets and variables → Actions**
- [ ] Add `FINDATA_GOCU_USER` (matches the value in your local `.env`)
- [ ] Add `FINDATA_GOCU_PW`
- [ ] Add `FINDATA_GOCU_OTP` (the TOTP seed, not a generated 6-digit code)
- [ ] Run the workflow once manually to confirm login + 2FA succeed in CI
- [ ] Confirm the uploaded screenshot artifact shows a successful admin login

**What it tests:**
- Username/password login
- TOTP-based 2FA code entry and submission
- Redirect to the admin home page
- Permission visibility for a basic admin account (`Content` visible, `AI Scenarios` hidden)

---

## 🚀 How to Run Workflows Manually

### Via GitHub UI:

1. Go to your repository on GitHub
2. Click the **"Actions"** tab
3. Select the workflow you want to run from the left sidebar
4. Click **"Run workflow"** button (top right)
5. Select options if available
6. Click the green **"Run workflow"** button

### Via GitHub CLI:

```bash
# Run checking funnel test
gh workflow run missionfed_checking_funnel_weekly.yml

# Run all scenarios
gh workflow run missionfed_all_scenarios_weekly.yml

# Run specific scenarios only
gh workflow run missionfed_all_scenarios_weekly.yml -f scenarios="savings,cd,personal loan"

# Run GOCU admin basic account access test (STG)
gh workflow run gocu_admin_basic_account_access_stg.yml
```

---

## 📊 Workflow Features

### Automated Test Execution

- ✅ Runs on Ubuntu Linux with latest dependencies
- ✅ Python 3.11 environment
- ✅ Playwright Chromium browser
- ✅ Pillow for image comparison
- ✅ All baseline images included

### Artifact Uploads

After each test run, the following artifacts are automatically uploaded:

1. **Test Report** (HTML)
   - Detailed pytest HTML report
   - Self-contained (includes all CSS/JS)
   - Pass/fail status for each test
   - Execution times

2. **Screenshots**
   - All screenshots from test execution
   - Organized by scenario
   - Step-by-step visual progression

3. **Image Comparison Diffs**
   - RMS difference heatmaps
   - Side-by-side triptychs (baseline | actual | diff)
   - Visual validation of changes

4. **Page Source Files**
   - HTML source for debugging
   - Saved at key test steps
   - Available when tests fail

**Retention:** Artifacts are kept for 30 days

---

## 📈 Test Results & Notifications

### Success Indicators

The workflow provides clear feedback:

```
::notice::All MissionFed funnel scenarios completed successfully!
::notice::7/7 scenarios passed - excellent results!
```

### Expected Failures

Some failures are expected due to personalization:

```
::warning::Some MissionFed scenarios failed - this may be expected
::notice::Expected: 5/7 scenarios passing (71% pass rate)
::notice::Known issues: checking & credit card may show personalization variants
```

### Viewing Results

1. **In GitHub Actions UI:**
   - Click on the workflow run
   - View step-by-step logs
   - Download artifacts

2. **In Job Summary:**
   - Automatic summary generated
   - Pass/fail counts
   - Links to artifacts

3. **In Test Report:**
   - Download the HTML report artifact
   - Open in browser
   - See detailed results with screenshots

---

## 🔧 Workflow Configuration

### Environment Variables

```yaml
env:
  DEFAULT_TIMEOUT: 10000      # Playwright timeout (10 seconds)
  TEST_ENVIRONMENT: PROD      # Target environment
```

### Python Dependencies

Automatically installed:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-html` - HTML report generation
- `playwright` - Browser automation
- `python-dotenv` - Environment variables
- `pillow` - Image comparison

### System Dependencies

Automatically installed for Playwright:
- Chrome/Chromium dependencies
- Graphics libraries
- Font rendering
- Audio support (for complete browser emulation)

---

## 📝 Customization

### Change Schedule

Edit the cron expression in the workflow file:

```yaml
schedule:
  - cron: '0 14 * * 1'  # Monday 6 AM PST
```

**Cron format:** `minute hour day-of-month month day-of-week`

**Examples:**
- `0 14 * * *` - Daily at 6 AM PST
- `0 14 * * 1,3,5` - Monday, Wednesday, Friday at 6 AM PST
- `0 14 1 * *` - First day of every month at 6 AM PST

### Add Email Notifications

Add this step at the end of the workflow:

```yaml
- name: Send email notification
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "MissionFed Test Failed - ${{ github.workflow }}"
    body: "Test run failed. Check artifacts at ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    to: your-email@example.com
    from: github-actions@yourdomain.com
```

### Add Slack Notifications

```yaml
- name: Slack notification
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "MissionFed Test Failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "Test run failed. <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Details>"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 🐛 Troubleshooting

### Workflow not running automatically

**Issue:** Scheduled workflows don't run

**Solutions:**
1. Ensure workflows are on the default branch (main/master) or refactored_tests
2. Check that the repository has had recent activity (GitHub pauses scheduled workflows on inactive repos)
3. Verify cron syntax is correct
4. Manually trigger once to "wake up" the workflow

### Tests failing in CI but passing locally

**Common causes:**
1. **Timing issues** - CI may be slower, increase timeouts
2. **Environment differences** - Check browser versions
3. **Missing dependencies** - Verify all packages installed
4. **Baseline images** - Ensure they're committed and accessible

**Solutions:**
```yaml
# Increase timeouts for CI
env:
  DEFAULT_TIMEOUT: 30000  # 30 seconds instead of 10
```

### Artifacts not uploading

**Issue:** Screenshots or reports missing

**Solution:**
```yaml
# Check path exists before upload
- name: Debug artifacts
  run: |
    ls -la screenshots_missionfed_using_pytest/
    ls -la *.html
```

---

## 📚 Additional Resources

### GitHub Actions Documentation
- [Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Cron schedule syntax](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)

### Playwright Documentation
- [Playwright Python](https://playwright.dev/python/)
- [Best practices](https://playwright.dev/python/docs/best-practices)
- [CI/CD Integration](https://playwright.dev/python/docs/ci)

### Test Documentation
- [TEST_FIXES_SUMMARY.md](../../TEST_FIXES_SUMMARY.md) - Detailed test implementation guide
- [CLAUDE.md](../../CLAUDE.md) - Repository overview and testing patterns

---

## 🔐 Security Notes

### Secrets Management

If your tests require authentication:

1. Add secrets in repository settings:
   - Go to Settings > Secrets and variables > Actions
   - Click "New repository secret"

2. Reference in workflow:
```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}
  USERNAME: ${{ secrets.TEST_USERNAME }}
```

3. Never commit secrets to code!

### Token Permissions

GitHub Actions uses `GITHUB_TOKEN` automatically with limited permissions:
- Read repository content
- Write to Actions artifacts
- Create check runs

No additional setup needed for these workflows.

---

## 📞 Support

For issues with:
- **Workflows:** Check GitHub Actions logs and artifacts
- **Tests:** See TEST_FIXES_SUMMARY.md for implementation details
- **Playwright:** Review screenshots and page source in artifacts
- **Baseline Images:** Ensure pytests/baseline_images_for_comparison/ is committed

---

**Last Updated:** 2025-12-11
**Maintained By:** Claude (Anthropic)
**Test Framework:** Pytest + Playwright (async)
