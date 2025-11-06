@echo off
REM Stop all existing Chrome instances
echo Closing all Chrome instances...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting Chrome with remote debugging on port 9222...
echo Using your actual Chrome profile with all your logins...

REM Get user data directory
set USER_DATA="%LOCALAPPDATA%\Google\Chrome\User Data"

REM Start Chrome with debugging using your actual profile
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%USER_DATA%

echo.
echo Chrome started! Keep this window open while running scrapers.
echo The scrapers will now connect to your Chrome browser.
echo.
pause

