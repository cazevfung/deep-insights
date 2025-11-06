# PowerShell script to force quit all server processes
# Used by install_dependencies.bat

$ErrorActionPreference = 'SilentlyContinue'
$totalKilled = 0
$ports = @(3000, 3001)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Force Quitting All Server Processes" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Kill processes on ports 3000 and 3001
foreach ($port in $ports) {
    Write-Host "Checking port $port..." -ForegroundColor Cyan
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    
    if ($processes) {
        Write-Host "Found $($processes.Count) process(es) using port $port:" -ForegroundColor Yellow
        foreach ($pid in $processes) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  - PID $pid : $($proc.ProcessName) ($($proc.Path))" -ForegroundColor Yellow
                try {
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Host "    Killed PID $pid" -ForegroundColor Green
                    $totalKilled++
                } catch {
                    Write-Host "    Failed to kill PID $pid : $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "No processes found using port $port" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Killing Node.js processes (Vite/Frontend)..." -ForegroundColor Cyan
$nodeProcs = Get-Process -Name node -ErrorAction SilentlyContinue
if ($nodeProcs) {
    foreach ($proc in $nodeProcs) {
        try {
            $procPath = $proc.Path
            $cmdLine = ""
            try {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            } catch {}
            
            # Check if it's a Vite or frontend-related process
            if ($procPath -and ($procPath -like '*vite*' -or $procPath -like '*client*' -or $procPath -like '*research*')) {
                Write-Host "  Killing Node.js PID $($proc.Id) : $procPath" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    Killed PID $($proc.Id)" -ForegroundColor Green
                $totalKilled++
            } elseif ($cmdLine -and ($cmdLine -like '*vite*' -or $cmdLine -like '*client*' -or $cmdLine -like '*research*')) {
                Write-Host "  Killing Node.js PID $($proc.Id) : $cmdLine" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    Killed PID $($proc.Id)" -ForegroundColor Green
                $totalKilled++
            }
        } catch {
            # Ignore errors
        }
    }
} else {
    Write-Host "No Node.js processes found" -ForegroundColor Green
}

Write-Host ""
Write-Host "Killing Python backend processes..." -ForegroundColor Cyan
$pythonProcs = Get-Process -Name python,pythonw -ErrorAction SilentlyContinue
if ($pythonProcs) {
    foreach ($proc in $pythonProcs) {
        try {
            $cmdLine = ""
            try {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            } catch {}
            
            # Check if it's a backend server process
            if ($cmdLine -and ($cmdLine -like '*run_server*' -or $cmdLine -like '*backend*' -or $cmdLine -like '*uvicorn*' -or ($cmdLine -like '*research*' -and $cmdLine -like '*server*'))) {
                Write-Host "  Killing Python PID $($proc.Id) : $cmdLine" -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    Killed PID $($proc.Id)" -ForegroundColor Green
                $totalKilled++
            }
        } catch {
            # Ignore errors
        }
    }
} else {
    Write-Host "No Python backend processes found" -ForegroundColor Green
}

# Wait a moment for processes to fully terminate
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Verifying ports are free..." -ForegroundColor Cyan
$stillInUse = @()
foreach ($port in $ports) {
    $check = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($check) {
        $stillInUse += $port
    }
}

if ($stillInUse.Count -gt 0) {
    Write-Host "WARNING: Ports $($stillInUse -join ', ') are still in use after cleanup!" -ForegroundColor Red
    Write-Host "You may need to manually kill the processes or restart your computer." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "All server ports are now free ($totalKilled process(es) killed)" -ForegroundColor Green
    exit 0
}

