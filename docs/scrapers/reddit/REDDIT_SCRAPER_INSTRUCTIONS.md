# Reddit Scraper - Using Existing Chrome Browser

## Overview

The Reddit scraper has been updated to connect to your existing Chrome browser instead of launching a new browser instance. This helps bypass Reddit's anti-bot detection by using your real Chrome profile with your login session, cookies, and browser history.

## Key Changes

1. **Creates new window** - Opens a new Chrome window in your existing browser (doesn't close your existing windows)
2. **Leaves window open** - After scraping, the window stays open so you can inspect results
3. **Handles CAPTCHA** - If Reddit shows CAPTCHA, the scraper waits for you to complete it manually
4. **Preserves browser state** - Your existing tabs and windows remain untouched

## Setup Instructions

### Step 1: Start Chrome with Debugging Enabled

**Option A: Use the helper script (easier)**
```bash
scripts\start_chrome_with_debugging.bat
```

**Option B: Manually start Chrome**
```bash
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"
```

**Important:** 
- DON'T close the Chrome window that opens
- This Chrome instance must stay running while you run the scraper
- You can minimize it, but keep it running

### Step 2: Verify Configuration

Open `config.yaml` and make sure:
```yaml
browser:
  connect_to_existing_browser: true  # Should be true
  browser_cdp_url: 'http://localhost:9222'  # Should be localhost:9222
```

### Step 3: Run the Test

```bash
python tests\test_reddit_scraper.py
```

## What Happens

1. The scraper connects to your existing Chrome browser
2. A **new Chrome window opens** with the Reddit page
3. If Reddit shows CAPTCHA, the scraper waits for you to complete it
4. The scraper extracts the content
5. The window stays open so you can see the results

## If You See CAPTCHA

When the Reddit scraper detects a CAPTCHA:
- A message will appear in your console
- The browser window will show the CAPTCHA page
- Complete the CAPTCHA manually in the browser
- The scraper will automatically continue once you complete it

## Troubleshooting

### "Connection refused" error
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check that port 9222 is not blocked by firewall

### Still getting blocked by Reddit
- Try using your normal Chrome profile instead of a temporary one
- Edit `scripts\start_chrome_with_debugging.bat` and uncomment Option 2
- This will use your logged-in Reddit session

### Window closes immediately
- This shouldn't happen anymore - the new code keeps the window open
- If it does, check the logs for errors

## Testing

Here's a test URL that was working before:
```
https://www.reddit.com/r/ArcRaiders/comments/1kljxsb/does_anyone_else_think_the_extraction_genre_is/
```

## Notes

- The Reddit scraper specifically opens a **new window** (not reusing existing tabs)
- Your existing Chrome tabs/windows remain untouched
- The browser window stays open after scraping (you can close it manually)
- This approach is much less likely to trigger anti-bot detection






