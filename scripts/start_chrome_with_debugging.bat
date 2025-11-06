@echo off
REM Start Chrome with remote debugging enabled
REM This allows Playwright to connect to your existing Chrome browser

echo =============================================================
echo Starting Chrome with remote debugging on port 9222...
echo Using your existing Chrome profile (logged-in sessions)
echo =============================================================
echo.

REM Kill any existing Chrome processes first
echo Killing existing Chrome processes...
taskkill /F /IM chrome.exe > NUL 2>&1
timeout /T 2 /NOBREAK > NUL

REM Find Chrome executable
set CHROME_PATH=

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
)

if not exist "%CHROME_PATH%" (
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )
)

if not exist "%CHROME_PATH%" (
    echo ERROR: Chrome not found!
    echo Please install Google Chrome.
    pause
    exit /b 1
)

echo Found Chrome: %CHROME_PATH%
echo.
echo Starting Chrome with debugging and your profile...
echo.

REM Start Chrome with debugging using the user's profile
start "ChromeDebug" /B "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data"

echo Waiting for Chrome to start...
timeout /T 3 /NOBREAK > NUL

echo.
echo =============================================================
echo Chrome is now starting with debugging enabled
echo =============================================================
echo.
echo IMPORTANT: Please do the following:
echo 1. Log in to Reddit in the Chrome window
echo 2. Verify you're logged in and your account is active
echo 3. Once you're logged in, come back here and press a key
echo.
echo Chrome will stay open - you can minimize it if needed.
echo.
echo =============================================================
pause

REM Test the connection after user confirms they're logged in
echo.
echo Testing debugging connection...
curl -s http://127.0.0.1:9222/json/version > NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Chrome debugging is active!
    echo.
    echo Next step: Run the scraper
    echo   python tests\test_reddit_scraper.py
    echo.
    echo Chrome will stay running - don't close it yet!
) else (
    echo ERROR: Chrome debugging is NOT active
    echo Chrome may not have started properly
    echo.
    echo Try running this command manually:
    echo   "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data"
)
echo.
echo =============================================================
pause
