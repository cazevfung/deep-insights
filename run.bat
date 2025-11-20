@echo off
setlocal

set ROOT_DIR=%~dp0
set INSTALLER=%ROOT_DIR%scripts\install\run_windows.bat

if not exist "%INSTALLER%" (
    echo Error: "%INSTALLER%" not found. Please verify the repository structure.
    exit /b 1
)

echo Note: Windows installer moved to scripts\install\run_windows.bat
call "%INSTALLER%" %*

