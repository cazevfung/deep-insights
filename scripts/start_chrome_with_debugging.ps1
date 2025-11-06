# PowerShell script to start Chrome with remote debugging
# This is more reliable than batch files for complex commands

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting Chrome with remote debugging on port 9222" -ForegroundColor Cyan
Write-Host "Using your existing Chrome profile" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing Chrome processes
Write-Host "Killing existing Chrome processes..." -ForegroundColor Yellow
Get-Process -Name chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Find Chrome
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

if (-not (Test-Path $chromePath)) {
    Write-Host "ERROR: Chrome not found!" -ForegroundColor Red
    Write-Host "Please install Google Chrome." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Found Chrome at: $chromePath" -ForegroundColor Green
Write-Host ""

# User data directory
$userDataDir = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Write-Host "Starting Chrome with debugging..." -ForegroundColor Yellow
Write-Host "Profile: $userDataDir" -ForegroundColor Gray
Write-Host ""

# Start Chrome with debugging
$arguments = @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$userDataDir`"",
    "--no-first-run",
    "--no-default-browser-check"
)

Start-Process -FilePath $chromePath -ArgumentList $arguments

Write-Host "Waiting for Chrome to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Testing debugging connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2
    Write-Host ""
    Write-Host "SUCCESS: Chrome debugging is active!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Cyan
    $response.Content
} catch {
    Write-Host ""
    Write-Host "ERROR: Chrome debugging is NOT active" -ForegroundColor Red
    Write-Host "Port 9222 is not responding" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check if Chrome actually opened"
    Write-Host "2. Try running Chrome manually with debugging"
    Write-Host "3. Check Windows Firewall settings"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Next step: Run python tests\test_reddit_scraper.py" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
pause

