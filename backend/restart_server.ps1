# Restart Backend Server Script
# This script kills all Python processes using port 3001 and starts a fresh server

Write-Host "Restarting Backend Server..." -ForegroundColor Cyan
Write-Host ""

# Find all processes using port 3001
Write-Host "Finding processes using port 3001..." -ForegroundColor Yellow
$processes = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    Write-Host "Found $($processes.Count) process(es) using port 3001:" -ForegroundColor Yellow
    foreach ($pid in $processes) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  - PID $pid : $($proc.ProcessName) (Started: $($proc.StartTime))" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "Killing processes..." -ForegroundColor Yellow
    foreach ($pid in $processes) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  - Killed PID $pid" -ForegroundColor Green
        } catch {
            Write-Host "  - Failed to kill PID $pid : $_" -ForegroundColor Red
        }
    }
    
    # Wait a moment for ports to be released
    Start-Sleep -Seconds 2
} else {
    Write-Host "No processes found using port 3001" -ForegroundColor Green
}

# Verify port is free
Write-Host ""
Write-Host "Verifying port 3001 is free..." -ForegroundColor Yellow
$stillInUse = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
if ($stillInUse) {
    Write-Host "WARNING: Port 3001 is still in use!" -ForegroundColor Red
    Write-Host "You may need to manually kill the processes or restart your computer" -ForegroundColor Yellow
} else {
    Write-Host "Port 3001 is free" -ForegroundColor Green
}

# Start the server
Write-Host ""
Write-Host "Starting backend server..." -ForegroundColor Cyan
Write-Host ""

# Change to project root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Start the server
try {
    python backend/run_server.py
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're in the project root directory and have Python installed" -ForegroundColor Yellow
    exit 1
}

