# FFmpeg Installation Script for Bilibili Scraper
# This script downloads and installs ffmpeg to the system PATH

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "FFmpeg Installation for Bilibili Scraper" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run as Admin: Right-click PowerShell > 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

# Configuration
$ffmpegDir = "C:\ffmpeg"
$ffmpegZip = "$ffmpegDir\ffmpeg.zip"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Step 1: Create directory
Write-Host ""
Write-Host "Step 1: Creating directories..." -ForegroundColor Green
if (Test-Path $ffmpegDir) {
    Write-Host "  Directory already exists: $ffmpegDir" -ForegroundColor Yellow
} else {
    New-Item -ItemType Directory -Path $ffmpegDir -Force | Out-Null
    Write-Host "  Created: $ffmpegDir" -ForegroundColor Green
}

# Step 2: Download ffmpeg
Write-Host ""
Write-Host "Step 2: Downloading ffmpeg..." -ForegroundColor Green
Write-Host "  URL: $ffmpegUrl" -ForegroundColor Gray

try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip
    Write-Host "  Downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to download ffmpeg" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    pause
    exit 1
}

# Step 3: Extract
Write-Host ""
Write-Host "Step 3: Extracting ffmpeg..." -ForegroundColor Green
try {
    Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegDir -Force
    Write-Host "  Extracted successfully" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to extract archive" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    pause
    exit 1
}

# Step 4: Find ffmpeg.exe
Write-Host ""
Write-Host "Step 4: Locating ffmpeg.exe..." -ForegroundColor Green
$ffmpegExe = Get-ChildItem -Path $ffmpegDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1

if (-not $ffmpegExe) {
    Write-Host "  ERROR: ffmpeg.exe not found" -ForegroundColor Red
    pause
    exit 1
}

$ffmpegBinDir = $ffmpegExe.DirectoryName
Write-Host "  Found at: $ffmpegBinDir" -ForegroundColor Green

# Step 5: Add to PATH
Write-Host ""
Write-Host "Step 5: Adding to system PATH..." -ForegroundColor Green

# Check if already in PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -like "*$ffmpegBinDir*") {
    Write-Host "  Already in PATH" -ForegroundColor Yellow
} else {
    try {
        # Add to machine PATH (requires admin)
        $newPath = $currentPath + ";$ffmpegBinDir"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
        Write-Host "  Added to PATH successfully" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to add to PATH" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Manual step required:" -ForegroundColor Yellow
        Write-Host "  1. Open System Properties > Environment Variables" -ForegroundColor Yellow
        Write-Host "  2. Add to Path: $ffmpegBinDir" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Step 6: Set current session PATH
Write-Host ""
Write-Host "Step 6: Setting current session PATH..." -ForegroundColor Green
$env:Path += ";$ffmpegBinDir"

# Step 7: Cleanup zip file
Write-Host ""
Write-Host "Step 7: Cleaning up..." -ForegroundColor Green
Remove-Item $ffmpegZip -Force -ErrorAction SilentlyContinue
Write-Host "  Removed: $ffmpegZip" -ForegroundColor Green

# Step 8: Verify installation
Write-Host ""
Write-Host "Step 8: Verifying installation..." -ForegroundColor Green
try {
    $versionOutput = ffmpeg -version 2>&1 | Select-Object -First 1
    if ($versionOutput -match "ffmpeg version") {
        Write-Host "  SUCCESS: FFmpeg is installed and accessible" -ForegroundColor Green
        Write-Host "  $versionOutput" -ForegroundColor Gray
    } else {
        Write-Host "  WARNING: ffmpeg command returned unexpected output" -ForegroundColor Yellow
        Write-Host "  You may need to restart your terminal" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARNING: ffmpeg not found in current session" -ForegroundColor Yellow
    Write-Host "  Please restart your terminal/PowerShell window" -ForegroundColor Yellow
    Write-Host "  Then run: ffmpeg -version" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "FFmpeg Location: $ffmpegBinDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Restart your terminal/PowerShell window" -ForegroundColor White
Write-Host "2. Test with: ffmpeg -version" -ForegroundColor White
Write-Host "3. Run: py -3.13 test_bilibili_snapany.py" -ForegroundColor White
Write-Host ""
pause

