# Chrome Connection Mode

This feature allows Playwright to connect to your existing Chrome browser instead of launching a new Chromium instance. This helps avoid login/anti-bot issues by using your normal Chrome profile with all your cookies, login sessions, and extensions.

## Benefits

- ✅ Uses your existing login sessions
- ✅ Has all your cookies and saved passwords
- ✅ Includes your browser extensions
- ✅ Reduces bot detection
- ✅ Looks more like a real user

## How to Use

### Step 1: Start Chrome with Remote Debugging

Run the helper script:

```bash
scripts\start_chrome_with_debugging.bat
```

Or manually start Chrome with this command:

```bash
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"
```

**Note:** Keep Chrome running while your scrapers work - don't close it!

### Step 2: Enable Browser Connection Mode

Edit `config.yaml` and set:

```yaml
browser:
  connect_to_existing_browser: true  # Enable connection mode
  browser_cdp_url: 'http://localhost:9222'  # CDP URL
```

### Step 3: Run Your Scrapers

Now run your scrapers as normal. They will connect to the running Chrome instance instead of launching a new browser.

```python
from scrapers.reddit_scraper import RedditScraper

scraper = RedditScraper()
result = scraper.extract("https://www.reddit.com/r/...")
```

## Configuration Options

In `config.yaml`:

```yaml
browser:
  # Enable/disable connecting to existing Chrome
  connect_to_existing_browser: true
  
  # Chrome DevTools Protocol URL
  browser_cdp_url: 'http://localhost:9222'
```

## Different Chrome Profiles

### Option 1: Temporary Profile (Recommended)

Use a clean temporary profile for scraping:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"
```

### Option 2: Your Normal Chrome Profile

Use your regular Chrome with all your sessions:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\\Google\\Chrome\\User Data"
```

**Warning:** Using your normal profile may have privacy implications as scrapers can access your browsing data.

## Troubleshooting

### Chrome won't start with debugging

- Make sure you close all Chrome windows first
- Try a different port (e.g., `--remote-debugging-port=9223`)
- Update the `browser_cdp_url` in config.yaml to match

### Connection fails

- Check that Chrome is running
- Verify the port number matches (default: 9222)
- Look for error messages in the logs

### Fallback behavior

If connection fails, the scraper will automatically fall back to launching a new browser instance.

## How It Works

1. Playwright uses Chrome DevTools Protocol (CDP) to connect to a running Chrome instance
2. Playwright can control the browser just like a normal automation
3. All your cookies, sessions, and extensions are available
4. The browser stays open after the scraper finishes

This approach is much more stealthy than launching a fresh browser and reduces the chance of being blocked by anti-bot systems.






