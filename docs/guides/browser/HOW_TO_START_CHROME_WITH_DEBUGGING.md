# How to Start Chrome with Debugging Manually

## Quick Method: Use the Batch Script

**Just double-click this file:**
```
scripts\start_chrome_with_debugging.bat
```

This will:
- ✅ Find Chrome automatically
- ✅ Start Chrome with debugging on port 9222
- ✅ Use your existing logged-in sessions
- ✅ Keep Chrome running

Then run your scraper:
```bash
python tests/test_reddit_scraper.py
```

The scraper will connect to the running Chrome and use your logged-in sessions!

---

## Manual Method: Command Line

If you prefer to run it manually from command line:

### Option 1: Using Your Existing Profile (Logged-In Sessions)
```cmd
start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\\Google\\Chrome\\User Data"
```

### Option 2: Using Program Files (x86) Path
```cmd
start "" "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\\Google\\Chrome\\User Data"
```

---

## Verify It's Working

After starting Chrome, check if debugging is enabled:

1. Open a new tab in Chrome
2. Go to: `chrome://version/`
3. Look for "Command Line" section
4. You should see `--remote-debugging-port=9222`

OR

Check if port 9222 is open:
```cmd
netstat -an | findstr 9222
```

---

## Then Run Your Scraper

Once Chrome is running with debugging:

```bash
python tests/test_reddit_scraper.py
```

The scraper will:
- Connect to your existing Chrome (not create a new one)
- Use all your logged-in sessions
- Open a new window for scraping
- Leave your original Chrome windows open

---

## Troubleshooting

**"Chrome is already running"**
- Close all Chrome windows first
- Then run the batch script again

**"Port 9222 already in use"**
- Another Chrome instance with debugging is already running
- Close it first

**Chrome starts with no sessions**
- Make sure you're using: `--user-data-dir="%LOCALAPPDATA%\\Google\\Chrome\\User Data"`
- This path uses your existing Chrome profile

---

## Why This Works

When you start Chrome with debugging:
- Chrome opens normally with all your sessions
- But now it accepts remote connections on port 9222
- Playwright can connect and control it
- Your logged-in sessions are preserved!






