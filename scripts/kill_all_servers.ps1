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
    # First check if port is actually in use with socket test
    $portInUse = $false
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 300
        $tcpClient.SendTimeout = 300
        $connect = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(300, $false)
        if ($wait) {
            $tcpClient.EndConnect($connect)
            $portInUse = $true  # Port is in use if we can connect
            $tcpClient.Close()
        } else {
            $tcpClient.Close()
        }
    } catch {
        # Connection refused or timeout means port is free
        $portInUse = $false
    }
    
    if (-not $portInUse) {
        Write-Host "No processes found using port $port (socket check)" -ForegroundColor Green
        continue
    }
    
    # Port is in use, find the process
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    $processList = @()
    if ($processes) {
        if ($processes -is [System.Array]) {
            $processList = $processes
        } else {
            $processList = @($processes)
        }
    }

    if ($processList.Count -gt 0) {
        Write-Host "Found $($processList.Count) process(es) using port ${port}:" -ForegroundColor Yellow
        foreach ($processId in $processList) {
                # Skip PID 0 (system idle process) - it's not a real process using the port
                if ($processId -eq 0) {
                    Write-Host "  - PID 0 : System Idle Process (ignoring)" -ForegroundColor Gray
                    continue
                }
                $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  - PID $processId : $($proc.ProcessName) ($($proc.Path))" -ForegroundColor Yellow
                    $killed = $false
                    # Try up to 3 times with retries
                    for ($attempt = 1; $attempt -le 3; $attempt++) {
                        try {
                            Stop-Process -Id $processId -Force -ErrorAction Stop
                            Write-Host "    ✓ Killed PID $processId" -ForegroundColor Green
                            $totalKilled++
                            $killed = $true
                            break
                        } catch {
                            if ($attempt -lt 3) {
                                Write-Host "    ⚠ Attempt $attempt failed, retrying..." -ForegroundColor Yellow
                                Start-Sleep -Milliseconds 500
                            } else {
                                # Check if process still exists
                                $stillExists = Get-Process -Id $processId -ErrorAction SilentlyContinue
                                if (-not $stillExists) {
                                    Write-Host "    ✓ Process $processId already terminated" -ForegroundColor Green
                                    $killed = $true
                                } else {
                                    Write-Host "    ✗ Failed to kill PID $processId after 3 attempts: $($_.Exception.Message)" -ForegroundColor Red
                                }
                            }
                        }
                    }
                    # Verify process is actually killed
                    if ($killed) {
                        Start-Sleep -Milliseconds 500
                        $verify = Get-Process -Id $processId -ErrorAction SilentlyContinue
                        if ($verify) {
                            Write-Host "    ⚠ Warning: PID $processId still appears to be running" -ForegroundColor Yellow
                        }
                    }
                } else {
                    Write-Host "  - PID $processId : Process no longer exists (already terminated)" -ForegroundColor Gray
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
            $shouldKill = $false
            if ($procPath -and ($procPath -like '*vite*' -or $procPath -like '*client*' -or $procPath -like '*research*')) {
                $shouldKill = $true
            } elseif ($cmdLine -and ($cmdLine -like '*vite*' -or $cmdLine -like '*client*' -or $cmdLine -like '*research*')) {
                $shouldKill = $true
            }
            
            if ($shouldKill) {
                Write-Host "  Killing Node.js PID $($proc.Id) : $($procPath -or $cmdLine)" -ForegroundColor Yellow
                $killed = $false
                for ($attempt = 1; $attempt -le 3; $attempt++) {
                    try {
                        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                        Write-Host "    ✓ Killed PID $($proc.Id)" -ForegroundColor Green
                        $totalKilled++
                        $killed = $true
                        break
                    } catch {
                        if ($attempt -lt 3) {
                            Start-Sleep -Milliseconds 500
                        } else {
                            $stillExists = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
                            if (-not $stillExists) {
                                Write-Host "    ✓ Process $($proc.Id) already terminated" -ForegroundColor Green
                                $killed = $true
                            } else {
                                Write-Host "    ✗ Failed to kill PID $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
                            }
                        }
                    }
                }
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
                $killed = $false
                for ($attempt = 1; $attempt -le 3; $attempt++) {
                    try {
                        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                        Write-Host "    ✓ Killed PID $($proc.Id)" -ForegroundColor Green
                        $totalKilled++
                        $killed = $true
                        break
                    } catch {
                        if ($attempt -lt 3) {
                            Start-Sleep -Milliseconds 500
                        } else {
                            $stillExists = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
                            if (-not $stillExists) {
                                Write-Host "    ✓ Process $($proc.Id) already terminated" -ForegroundColor Green
                                $killed = $true
                            } else {
                                Write-Host "    ✗ Failed to kill PID $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
                            }
                        }
                    }
                }
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
    # Use socket-based check instead of Get-NetTCPConnection (which shows stale TIME_WAIT connections)
    $portFree = $true
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 300
        $tcpClient.SendTimeout = 300
        $connect = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(300, $false)
        if ($wait) {
            $tcpClient.EndConnect($connect)
            $portFree = $false  # Port is in use if we can connect
            $tcpClient.Close()
        } else {
            $tcpClient.Close()
        }
    } catch {
        # Connection refused or timeout means port is free
        $portFree = $true
    }
    
    if (-not $portFree) {
        $stillInUse += $port
    }
}

if ($stillInUse.Count -gt 0) {
    Write-Host "WARNING: Ports $($stillInUse -join ', ') are still in use after cleanup!" -ForegroundColor Red
    Write-Host "Attempting additional cleanup..." -ForegroundColor Yellow
    
    # Try one more aggressive cleanup pass
    foreach ($port in $stillInUse) {
        $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($processId in $processes) {
            try {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            } catch {}
        }
    }
    
    # Final check using socket-based method
    Start-Sleep -Seconds 1
    $finalCheck = @()
    foreach ($port in $ports) {
        $portFree = $true
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.ReceiveTimeout = 300
            $tcpClient.SendTimeout = 300
            $connect = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
            $wait = $connect.AsyncWaitHandle.WaitOne(300, $false)
            if ($wait) {
                $tcpClient.EndConnect($connect)
                $portFree = $false  # Port is in use if we can connect
                $tcpClient.Close()
            } else {
                $tcpClient.Close()
            }
        } catch {
            # Connection refused or timeout means port is free
            $portFree = $true
        }
        
        if (-not $portFree) {
            $finalCheck += $port
        }
    }
    
    if ($finalCheck.Count -gt 0) {
        Write-Host "Ports $($finalCheck -join ', ') are still in use. You may need to:" -ForegroundColor Yellow
        Write-Host "  1. Manually kill the processes using Task Manager" -ForegroundColor Yellow
        Write-Host "  2. Restart your computer" -ForegroundColor Yellow
        Write-Host "  3. Run this script as Administrator" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "All server ports are now free after additional cleanup ($totalKilled process(es) killed)" -ForegroundColor Green
        exit 0
    }
} else {
    Write-Host "All server ports are now free ($totalKilled process(es) killed)" -ForegroundColor Green
    exit 0
}

