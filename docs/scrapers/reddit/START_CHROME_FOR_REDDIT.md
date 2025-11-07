# Quick Start for Reddit Scraper with Your Logged-In Session

## The Problem
You want the Reddit scraper to use your **existing logged-in Chrome session** with all your cookies and login info.

## The Solution

### Step 1: Close Chrome
If Chrome is currently running, close it completely.

### Step 2: Run Your Scraper
```bash
python tests/test_reddit_scraper.py
```

Chrome will **automatically start** with:
- ✅ Your logged-in sessions preserved
- ✅ Your cookies and saved passwords
- ✅ Remote debugging enabled on port 9222
- ✅ A new window opened for scraping (doesn't close your existing windows)

## How It Works

1. Scraper checks if Chrome has debugging enabled
2. If not, it starts Chrome with your profile path: `C:\\Users\\[YourName]\\AppData\\Local\\Google\\Chrome\\User Data`
3. This means all your logged-in sessions are available!

## Alternative: Manual Chrome Start

If you prefer to manually start Chrome:

1. Run the batch script: `scripts\start_chrome_with_debugging.bat`
2. This starts Chrome with your normal profile + debugging
3. Then run your scraper - it will connect to the running Chrome

## Troubleshooting

**"Chrome is running but does NOT have debugging enabled"**
- Close Chrome completely and run the scraper again

**"Chrome not found"**
- Make sure Chrome is installed in the standard location

**"Port 9222 already in use"**
- Close all Chrome windows and try again

## Why This Works

The scraper now uses your **actual Chrome profile** instead of a temporary one, so all your logged-in sessions are preserved!






