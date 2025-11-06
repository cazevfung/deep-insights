"""Check if Chrome is running with remote debugging enabled."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright

print("Checking Chrome connection...")
print("=" * 60)

try:
    playwright = sync_playwright().start()
    
    print("\nAttempting to connect to Chrome at http://localhost:9222...")
    browser = playwright.chromium.connect_over_cdp('http://localhost:9222')
    
    print("✅ SUCCESS: Connected to existing Chrome browser!")
    print(f"Browser contexts: {len(browser.contexts)}")
    print(f"Browser pages: {len(browser.pages)}")
    
    # Test creating a new window
    print("\nCreating a new window...")
    context = browser.new_context()
    page = context.new_page()
    page.goto('about:blank')
    
    print("✅ Successfully created new window!")
    print("\n✅ Your Chrome is ready to be used by the Reddit scraper!")
    
    # Clean up
    page.close()
    context.close()
    browser.close()
    playwright.stop()
    
except ConnectionRefusedError:
    print("❌ FAILED: Chrome is not running with debugging enabled")
    print("\nTo fix this, run:")
    print("  scripts\\start_chrome_with_debugging.bat")
    print("\nOr manually start Chrome with:")
    print('  chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"')
    
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}")
    print("\nChrome might not be running with debugging enabled.")
    print("Run: scripts\\start_chrome_with_debugging.bat")

print("\n" + "=" * 60)

