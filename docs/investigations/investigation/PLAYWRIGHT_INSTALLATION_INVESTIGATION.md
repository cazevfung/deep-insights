# Playwright Installation Investigation - YouTube Links Failing

## Problem Summary
All YouTube links failed during testing on localhost:3000. **UPDATE**: Playwright IS initializing correctly (confirmed by logs showing browser launch succeeds). The failure must occur AFTER browser initialization during the extraction process.

## Investigation Findings

### ✅ Playwright Initialization Status
**CONFIRMED**: Playwright browsers are installed and working correctly.
- Logs show: `[youtube] Initializing Playwright...`
- Logs show: `[youtube] New browser instance launched`
- Logs show: `[youtube] Browser initialized`

The issue is NOT with Playwright installation or browser startup.

## Revised Investigation Focus

Since Playwright is working correctly, the failure must occur during one of these steps:

1. **Page Navigation** (line 139): `page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)`
   - Timeout is 15000ms (15 seconds) from config
   - Could fail if YouTube page doesn't load in time
   - Could fail if YouTube detects automation and blocks

2. **Finding Transcript Button** (lines 165-169): Multiple selectors tried
   - Selectors: `button[aria-label="Show transcript"]`, etc.
   - If button not found after 2 seconds, extraction fails
   - YouTube UI changes could break selectors
   - Some videos may not have transcripts available

3. **Waiting for Transcript Segments** (line 177): `page.wait_for_selector('ytd-transcript-segment-renderer', timeout=5000)`
   - 5 second timeout for transcript to load
   - If segments don't appear, extraction fails
   - YouTube might delay transcript loading

4. **Extracting Transcript Text** (lines 315-331): Locating and extracting segment text
   - Could fail if selector changes
   - Could fail silently if segments found but text extraction fails

### Potential Failure Points

**Most Likely Issues:**
- **Timeout too short**: 15 seconds might not be enough for YouTube to fully load
- **YouTube UI changes**: Selectors may have changed
- **Anti-bot detection**: YouTube might be blocking automated browsers
- **Transcript availability**: Videos might not have transcripts (but "all" failing suggests systematic issue)
- **Network issues**: Slow connection causing timeouts

**Need to Check:**
- What specific error messages are in the logs after browser initialization?
- Do any logs appear after "Browser initialized"?
- Are there timeout errors?
- Are there selector not found errors?
- Are there network errors?

### 1. Installation Script Flow (Less Relevant Now)

The `scripts/install/run_windows.bat` script calls `scripts/install/install_dependencies.py`, which:
1. Installs Python dependencies from `requirements.txt` (includes `playwright>=1.40.0`)
2. Installs npm dependencies
3. **Attempts** to install Playwright browsers via `install_playwright_browsers()`

**Location**: `scripts/install/install_dependencies.py` lines 357-386

### 2. Playwright Browser Installation Issues

#### Issue #1: Installation Check May Be Unreliable
**Location**: `scripts/install/install_dependencies.py` lines 178-212 (`check_playwright_browsers_installed()`)

The check function:
- Uses `playwright install --dry-run chromium` to check if browsers are installed
- Falls back to actually launching a browser (lines 198-205)
- If the check incorrectly reports browsers as installed, installation is skipped

**Potential Problems**:
- `--dry-run` may not always accurately detect installed browsers
- The fallback browser launch test might fail silently or timeout
- Exception handling catches all errors and returns `False` (assumes not installed)

#### Issue #2: Installation Failure Is Not Fatal
**Location**: `scripts/install/install_dependencies.py` lines 357-386 (`install_playwright_browsers()`)

When browser installation fails:
- Returns `False` but installation continues
- Only prints a warning: "Playwright browser installation may have failed"
- The main function treats this as optional (line 889: "Installation skipped or failed (optional)")

**Potential Problems**:
- User may not notice the warning
- Installation appears successful even when browsers aren't installed
- No clear error message guiding user to fix the issue

#### Issue #3: Installation Command Execution
**Location**: `scripts/install/install_dependencies.py` line 370

```python
result = run_command([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
```

**Potential Problems**:
- Uses `check=False`, so errors are not raised
- May fail silently if:
  - Python executable path is incorrect
  - Playwright module is not yet installed (though it should be by this point)
  - Network issues prevent downloading browsers
  - Permission issues prevent writing to Playwright's browser directory

### 3. Runtime Error Handling

#### Browser Initialization
**Location**: `scrapers/base_scraper.py` lines 157-219 (`_init_playwright()`)

When YouTube scraper tries to extract:
1. `YouTubeScraper.extract()` calls `_create_context()` (line 134)
2. `_create_context()` calls `_init_playwright()` if browser not initialized (line 229)
3. `_init_playwright()` calls `self._playwright.chromium.launch()` (line 210)

**Potential Problems**:
- If Playwright browsers aren't installed, `chromium.launch()` will fail
- Error message may not clearly indicate "browsers not installed"
- Common errors:
  - `Executable doesn't exist at ...` (path to chromium executable)
  - `Browser type "chromium" is not installed` (if Playwright detects it)
  - Generic `Failed to launch browser` error

#### Error Reporting in YouTube Scraper
**Location**: `scrapers/youtube_scraper.py` lines 386-410

When extraction fails:
- Exception is caught and logged: `logger.error(f"[YouTube] Extraction failed: {e}")`
- Error message is stored in result: `'error': str(e)`
- But the error message may not clearly indicate Playwright installation issue

### 4. Specific Issues Identified

#### Issue A: Browser Installation Check Logic
The `check_playwright_browsers_installed()` function has a fallback that tries to launch a browser. However:
- This launch might fail for reasons other than "not installed" (e.g., permission issues, other browser errors)
- The exception is caught and ignored (line 204: `except: pass`)
- This makes the check unreliable

#### Issue B: Silent Installation Failures
The installation script doesn't verify that browsers were actually installed after running the install command. It only checks:
- If the command succeeded (return code 0)
- But doesn't verify browsers are actually usable

#### Issue C: Error Messages Not User-Friendly
When `chromium.launch()` fails due to missing browsers:
- Error might be: `Executable doesn't exist at C:\Users\...\AppData\Local\ms-playwright\chromium-...\chrome-win\chrome.exe`
- User might not understand this means "browsers not installed"
- Should check for this specific error and provide clearer guidance

### 5. Recommended Fixes (Not Implemented Yet)

#### Fix #1: Improve Browser Installation Verification
1. After running `playwright install chromium`, verify installation by:
   - Checking if the browser executable exists
   - Or actually launching a browser in headless mode
   - If verification fails, report clear error and stop installation

#### Fix #2: Better Error Detection
In `_init_playwright()`, catch specific errors related to missing browsers:
- Check for `Executable doesn't exist` errors
- Check for `Browser type "chromium" is not installed` errors
- Provide clear error message: "Playwright browsers not installed. Run: python -m playwright install chromium"

#### Fix #3: Make Browser Installation Required
- Change `install_playwright_browsers()` to return `False` on failure
- Make the main function exit with error code if browser installation fails
- Don't treat it as "optional" - it's required for YouTube scraping

#### Fix #4: Add Installation Verification Step
After installation, run a verification test:
```python
def verify_playwright_installation():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        logger.error(f"Playwright verification failed: {e}")
        return False
```

## Testing Recommendations

To verify the issue:

1. **Check if browsers are installed**:
   ```bash
   python -m playwright install --dry-run chromium
   ```

2. **Try manual installation**:
   ```bash
   python -m playwright install chromium
   ```

3. **Test browser launch**:
   ```python
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       browser = p.chromium.launch(headless=True)
       browser.close()
   ```

4. **Check Playwright browser directory**:
   - Windows: `%USERPROFILE%\AppData\Local\ms-playwright\`
   - Should contain `chromium-XXXXX` directory with `chrome-win\chrome.exe`

5. **Check logs for specific errors**:
   - Look for "Executable doesn't exist" errors
   - Look for "Browser type not installed" errors
   - Look for any errors in `_init_playwright()` method

## Next Steps

1. **Verify Playwright browsers are installed** on the system
2. **Check installation logs** for any errors during `playwright install chromium`
3. **Test browser launch manually** to confirm it works
4. **Review error messages** from failed YouTube extractions to identify the specific error
5. **Implement fixes** based on findings

## Files to Review

- `scripts/install/install_dependencies.py` - Installation logic
- `scrapers/base_scraper.py` - Browser initialization
- `scrapers/youtube_scraper.py` - Error handling
- Backend logs from failed YouTube extractions

