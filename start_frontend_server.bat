@echo off
setlocal

REM ============================================================================
REM  Research Tool Frontend Dev Server Launcher
REM  - Starts the Vite development server in a new terminal window
REM  - Automatically opens the frontend in the default browser
REM  - Supports optional FRONTEND_HOST_OVERRIDE / FRONTEND_PORT_OVERRIDE env vars
REM ============================================================================

REM Determine paths relative to this script file (supports UNC paths)
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%.."
set PROJECT_ROOT=%CD%
popd

REM Default host/port (match config.yaml defaults)
set FRONTEND_HOST=localhost
set FRONTEND_PORT=3000

REM Allow environment overrides (e.g., set FRONTEND_PORT_OVERRIDE=5173 before running)
if not "%FRONTEND_HOST_OVERRIDE%"=="" set FRONTEND_HOST=%FRONTEND_HOST_OVERRIDE%
if not "%FRONTEND_PORT_OVERRIDE%"=="" set FRONTEND_PORT=%FRONTEND_PORT_OVERRIDE%

set FRONTEND_URL=http://%FRONTEND_HOST%:%FRONTEND_PORT%

REM Launch the Vite dev server in a new window to keep logs visible
start "Research Tool Frontend Server" cmd /k "pushd ""%PROJECT_ROOT%\client"" && npm run dev"

REM Launch the Research Tool backend server (includes scraping/research logs)
start "Research Tool Backend Server" cmd /k "pushd ""%PROJECT_ROOT%"" && call scripts\start_backend_server.bat"

REM Open the live backend log viewer (shows scraping and research phase updates)
if exist "%PROJECT_ROOT%\logs\tail_logs.bat" (
    start "Research Tool Backend Logs" cmd /k "pushd ""%PROJECT_ROOT%\logs"" && call tail_logs.bat"
)

REM Provide user feedback in the current window
echo.
echo Frontend development server is starting in a new terminal window...
echo Backend server is starting in a separate terminal window...
echo Waiting briefly before opening the browser at %FRONTEND_URL%
echo.

REM Short delay to give Vite time to boot (adjust if needed)
timeout /t 5 /nobreak > nul

REM Open the default browser to the frontend URL
start "" "%FRONTEND_URL%"

echo Browser launch command issued for %FRONTEND_URL%.
echo You can close this window; the server will keep running in the other terminal.
echo.
pause

endlocal

