# How to Run Reddit Scraper with Chrome Connection

## Step-by-Step Instructions

### Step 1: Start Chrome with Debugging

**IMPORTANT**: You must do this FIRST before running the scraper!

#### Option A: Use the helper script
```
scripts\start_chrome_with_debugging.bat
```

#### Option B: Manual command
Open a new terminal and run:
```powershell
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-debug-profile"
```

**Keep this Chrome window open** (you can minimize it, but don't close it).

### Step 2: Verify Chrome is Running

Open a new PowerShell terminal and run:
```powershell
cd "D:\App Dev\Research Tool"
python check_chrome_connection.py
```

You should see: ✅ SUCCESS: Connected to existing Chrome browser!

If you see an error, go back to Step 1 and make sure Chrome is running with debugging enabled.

### Step 3: Run the Reddit Test

In the same PowerShell terminal:
```powershell
python tests\test_reddit_scraper.py
```

### What You Should See

1. Chrome opens a **NEW WINDOW** (not a new browser, but a new window in the Chrome that's already running)
2. The window navigates to the Reddit page
3. If there's CAPTCHA, you complete it manually
4. Content is extracted
5. The window **stays open** so you can see the results

### Troubleshooting

#### "Still running on Chromium"
- Make sure Chrome is running with debugging (Step 1)
- Verify with `check_chrome_connection.py`
- Check the logs for "Successfully connected to existing browser"

#### "Connection refused"
- Chrome debugging is not enabled
- Run Step 1 again
- Make sure port 9222 is not blocked by firewall

#### "connect_to_existing_browser setting: False"
- The config is not being read correctly
- Check `config.yaml` has `connect_to_existing_browser: true`

### Expected Output in Logs

```
[Reddit] connect_to_existing_browser setting: True
[Reddit] Connecting to existing browser at http://localhost:9222
[Reddit] Successfully connected to existing browser
[Reddit] Creating new window in existing browser
[Reddit] New context created in existing browser
```

If you see "Creating new browser instance (not connecting to existing)" instead, something is wrong with the connection.



