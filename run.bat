@echo off
setlocal enabledelayedexpansion

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
exit /b 1

:test_ok

REM Default to starting servers and opening browser unless --no-start is specified
set START_SERVER=1
set RESTART_BACKEND=0
for %%a in (%*) do (
    if "%%a"=="--no-start" set START_SERVER=0
    if "%%a"=="--restart-backend" set RESTART_BACKEND=1
)

REM If --start is explicitly provided, ensure it's set
for %%a in (%*) do (
    if "%%a"=="--start" set START_SERVER=1
)

echo.
echo ============================================================
echo Force quitting all server processes...
echo ============================================================
echo.

REM Use dedicated PowerShell script for comprehensive cleanup
if exist "scripts\kill_all_servers.ps1" (
    echo Running comprehensive cleanup script...
    powershell -ExecutionPolicy Bypass -NoProfile -File "scripts\kill_all_servers.ps1"
    if errorlevel 1 (
        echo Warning: Some processes may still be running, continuing anyway...
    )
) else (
    REM Fallback: Basic cleanup using inline PowerShell
    echo Using fallback cleanup method...
    powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(3000, 3001); foreach ($port in $ports) { Write-Host \"Checking port $port...\"; $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($processes) { foreach ($pid in $processes) { Write-Host \"  Killing PID $pid\"; Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } } }"
)

REM Try Python cleanup script as backup (don't fail if it errors)
if exist "backend\kill_backend.py" (
    echo.
    echo Trying alternative cleanup method using Python script...
    %PYTHON_CMD% backend\kill_backend.py 2>nul
    if errorlevel 1 (
        echo Note: Python cleanup script reported issues, but continuing...
    )
)

REM Additional force kill for any remaining processes by port
echo.
echo Performing final cleanup check...
powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(3000, 3001); foreach ($port in $ports) { $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($pid in $processes) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } }"
timeout /T 2 /NOBREAK >nul

REM Final verification - check if ports are free using socket-based method
echo Verifying ports are free...
powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'SilentlyContinue'; $ports = @(3000, 3001); $inUse = @(); foreach ($port in $ports) { $portFree = $true; try { $tcpClient = New-Object System.Net.Sockets.TcpClient; $tcpClient.ReceiveTimeout = 300; $tcpClient.SendTimeout = 300; $connect = $tcpClient.BeginConnect('127.0.0.1', $port, $null, $null); $wait = $connect.AsyncWaitHandle.WaitOne(300, $false); if ($wait) { $tcpClient.EndConnect($connect); $portFree = $false; $tcpClient.Close() } else { $tcpClient.Close() } } catch { $portFree = $true }; if (-not $portFree) { $inUse += $port } }; if ($inUse.Count -gt 0) { Write-Host \"WARNING: Ports $($inUse -join ', ') may still be in use\" -ForegroundColor Yellow; exit 1 } else { Write-Host \"All server ports are free\" -ForegroundColor Green; exit 0 }"
if errorlevel 1 (
    echo Warning: Some ports may still be in use. Installation will continue anyway.
    echo If you encounter port conflicts, manually kill the processes or restart your computer.
)

echo.
echo ============================================================
echo.

echo Starting dependency installation...
echo.

REM Check if --start or --no-start is already in arguments
set HAS_START_ARG=0
for %%a in (%*) do (
    if "%%a"=="--start" set HAS_START_ARG=1
    if "%%a"=="--no-start" set HAS_START_ARG=1
)

REM If START_SERVER is 1 and no start argument provided, add --start
if %START_SERVER%==1 if !HAS_START_ARG!==0 (
    %PYTHON_CMD% install_dependencies.py %* --start
) else (
    %PYTHON_CMD% install_dependencies.py %*
)

if errorlevel 1 goto install_failed
echo.
echo Installation completed successfully!
echo.
goto install_end

:install_failed
echo.
echo Installation completed with errors.
echo Exit code: %ERRORLEVEL%
echo.
exit /b %ERRORLEVEL%

:install_end

