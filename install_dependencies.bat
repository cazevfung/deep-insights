@echo off
setlocal

echo =============================================================
echo Research Tool - Dependency Installer (Windows)
echo =============================================================
echo.

set PYTHON_CMD=

py --version >nul 2>&1
if errorlevel 1 goto try_py314
set PYTHON_CMD=py
goto found

:try_py314
py -3.14 --version >nul 2>&1
if errorlevel 1 goto try_py3
set PYTHON_CMD=py -3.14
goto found

:try_py3
py -3 --version >nul 2>&1
if errorlevel 1 goto not_found
set PYTHON_CMD=py -3
goto found

:not_found

echo Python not found!
echo Please install Python 3.9+ from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:found
echo Python found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

echo Testing Python execution...
%PYTHON_CMD% -c "import sys; print('Python path:', sys.executable)" 2>nul
if errorlevel 1 goto test_failed
echo Python test passed!
echo.
goto test_ok

:test_failed
echo Python test failed!
pause
exit /b 1

:test_ok

set START_SERVER=0
set RESTART_BACKEND=0
for %%a in (%*) do (
    if "%%a"=="--start" set START_SERVER=1
    if "%%a"=="--restart-backend" set RESTART_BACKEND=1
)

echo.
echo ============================================================
echo Force quitting all server processes...
echo ============================================================
echo.

REM Use dedicated PowerShell script for comprehensive cleanup
if exist "scripts\kill_all_servers.ps1" (
    powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\kill_all_servers.ps1"
) else (
    REM Fallback: Basic cleanup using inline PowerShell
    echo Using fallback cleanup method...
    powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(3000, 3001); foreach ($port in $ports) { Write-Host \"Checking port $port...\"; $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($processes) { foreach ($pid in $processes) { Write-Host \"  Killing PID $pid\"; Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } } }"
)

REM Try Python cleanup script as backup
if exist "backend\kill_backend.py" (
    echo.
    echo Trying alternative cleanup method using Python script...
    %PYTHON_CMD% backend\kill_backend.py 2>nul
)

REM Additional force kill for any remaining processes by port
echo.
echo Performing final cleanup check...
powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(3000, 3001); foreach ($port in $ports) { $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($pid in $processes) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } }"
timeout /T 1 /NOBREAK >nul

echo.
echo ============================================================
echo.

echo Starting dependency installation...
echo.
%PYTHON_CMD% install_dependencies.py %*

if errorlevel 1 goto install_failed
echo.
echo Installation completed successfully!
echo.
pause
goto install_end

:install_failed
echo.
echo Installation completed with errors.
echo Exit code: %ERRORLEVEL%
echo.
pause
exit /b %ERRORLEVEL%

:install_end
