# Automatic Chrome Startup for Scrapers

## What Changed

The scrapers (especially Reddit) now automatically start Chrome with remote debugging enabled when needed. You no longer need to manually run `scripts\start_chrome_with_debugging.bat` before using the scrapers.

## How It Works

When `connect_to_existing_browser: true` is set in `config.yaml`, the scraper will:

1. **Check if Chrome is already running** with debugging on port 9222
2. **If not running**, automatically start Chrome with debugging enabled
3. **Connect to the running instance** to perform scraping
4. **Leave Chrome running** when done (so your session is preserved)

## Benefits

- ✅ **Fully automated** - No manual Chrome startup needed
- ✅ **Smart detection** - Only starts Chrome if it's not already running
- ✅ **Seamless experience** - You just run your scraper test and it works
- ✅ **Session preservation** - Chrome stays open with your login sessions

## Configuration

In `config.yaml`:

```yaml
browser:
  connect_to_existing_browser: true  # Enable automatic Chrome startup
  browser_cdp_url: 'http://localhost:9222'
```

## How to Use

### Reddit Scraper

Simply run the test (or your scraper):

```bash
python tests/test_reddit_scraper.py
```

The scraper will:
1. Check if Chrome is running on port 9222
2. If not, start Chrome automatically using `scripts/start_chrome_with_debugging.bat`
3. Wait for Chrome to become ready (up to 10 seconds)
4. Connect and perform scraping
5. Leave Chrome running for inspection

### Manual Override

You can still start Chrome manually if you prefer:

```bash
scripts\start_chrome_with_debugging.bat
```

In this case, the scraper will detect it's already running and skip the automatic startup.

## Fallback Behavior

If Chrome fails to start automatically (e.g., Chrome not installed or wrong path), the scraper will automatically fall back to launching a new browser instance, ensuring your tests always work.

## Implementation Details

Changes made to:
- `scrapers/base_scraper.py` - Added automatic Chrome detection and startup
  - `_check_chrome_running()` - Checks if Chrome debug port is open
  - `_start_chrome_with_debugging()` - Starts Chrome automatically
  - `_init_playwright()` - Enhanced to detect and start Chrome when needed

## Technical Notes

The scraper checks if port 9222 is listening to determine if Chrome is running with debugging. This approach works on Windows, Mac, and Linux.

If the batch script (`scripts/start_chrome_with_debugging.bat`) doesn't exist, the scraper will attempt to start Chrome directly with the appropriate flags.



