# Browser Connection Mode - Summary

## What Was Added

Added the ability to connect Playwright to your existing Chrome browser instead of launching a fresh Chromium instance. This helps avoid login and anti-bot issues.

## Files Modified

1. **`config.yaml`** - Added browser configuration section
2. **`scrapers/base_scraper.py`** - Added CDP connection logic
3. **`scripts/start_chrome_with_debugging.bat`** - Helper script to start Chrome with debugging
4. **`docs/CHROME_CONNECTION_MODE.md`** - Complete documentation

## Quick Start

### 1. Start Chrome with Debugging

Run the helper script:
```bash
scripts\start_chrome_with_debugging.bat
```

Or manually:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"
```

### 2. Enable in Config

Edit `config.yaml`:
```yaml
browser:
  connect_to_existing_browser: true  # Change from false to true
  browser_cdp_url: 'http://localhost:9222'
```

### 3. Run Your Scrapers

Run as normal. They'll connect to your Chrome instead of launching a new browser.

## Benefits

- ✅ Your login sessions work automatically
- ✅ Cookies and saved passwords available
- ✅ Browser extensions included
- ✅ Less likely to be detected as a bot
- ✅ More realistic browsing behavior
- ✅ **Reddit scraper creates new window without closing existing ones**

## How It Works

```
Your Chrome → CDP (port 9222) → Playwright → Scrapers
```

Playwright connects to Chrome via Chrome DevTools Protocol, giving it full control while using your actual Chrome profile.

## Reddit Scraper Behavior

The Reddit scraper has been specifically optimized for browser connection mode:

- **Opens a new Chrome window** (doesn't reuse existing windows)
- **Leaves the window open** after scraping completes (so you can inspect results)
- **Doesn't close your browser** when done
- **Handles CAPTCHA** by waiting for you to complete it manually

This is perfect for Reddit, which has aggressive anti-bot detection. Your existing browser with your login session makes it much more likely to work.

## Fallback

If connection fails (Chrome not running, wrong port, etc.), the scraper automatically falls back to launching a new browser instance.

## See Also

- Full documentation: `docs/CHROME_CONNECTION_MODE.md`
- Helper script: `scripts/start_chrome_with_debugging.bat`






