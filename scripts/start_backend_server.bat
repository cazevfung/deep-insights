@echo off
REM Start backend server in a new terminal window
REM This allows us to see the console logs including Playwright/Chromium errors

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Open a new terminal window and run the server
REM /k keeps the window open after the command completes (for errors)
REM /t:0A sets the color scheme (green background, black text for better visibility)
start "Research Tool Backend Server" /t:0F cmd /k "cd /d %PROJECT_ROOT% && python backend/run_server.py --reuse-window"

echo.
echo Backend server is starting in a new terminal window...
echo The new window will show all server logs including Playwright/Chromium errors.
echo.
echo You can close this window - the server will continue running in the new terminal.
echo.
pause

