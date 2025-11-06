# Backend Server Hanging Issue - Debugging Guide

## Problem

The backend server is listening on port 3001 but not responding to requests. Health checks are timing out.

## Symptoms

1. **Multiple Python processes using port 3001**:
   ```
   TCP    0.0.0.0:3001           0.0.0.0:0              LISTENING       19508
   TCP    0.0.0.0:3001           0.0.0.0:0              LISTENING       26088
   TCP    0.0.0.0:3001           0.0.0.0:0              LISTENING       81700
   ... (multiple instances)
   ```

2. **Many CLOSE_WAIT connections**:
   ```
   TCP    127.0.0.1:3001         127.0.0.1:49760        CLOSE_WAIT      19508
   TCP    127.0.0.1:3001         127.0.0.1:50242        CLOSE_WAIT      19508
   ... (many stuck connections)
   ```

3. **Health check times out**:
   ```
   Backend health check failed: TimeoutError: signal timed out
   ```

## Root Cause

Multiple instances of the backend server are running simultaneously on the same port. This causes:
- Port conflicts
- Connections getting stuck in CLOSE_WAIT state
- Server becoming unresponsive as it tries to handle stuck connections

## Solution

### Step 1: Kill All Processes Using Port 3001

**Option A: Using PowerShell (Recommended)**
```powershell
# Find all processes using port 3001
$processes = Get-NetTCPConnection -LocalPort 3001 | Select-Object -ExpandProperty OwningProcess -Unique

# Kill each process
foreach ($pid in $processes) {
    Stop-Process -Id $pid -Force
}
```

**Option B: Using the Restart Script**
```powershell
# From project root
.\backend\restart_server.ps1
```

**Option C: Manual Process Killing**
```powershell
# Find processes
netstat -ano | findstr :3001

# Kill specific process (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Step 2: Verify Port is Free

```powershell
# Check if port is still in use
Get-NetTCPConnection -LocalPort 3001

# Should return nothing if port is free
```

### Step 3: Start Fresh Backend Server

```powershell
# From project root
python backend/run_server.py
```

### Step 4: Verify Server is Working

```powershell
# Test health endpoint
Invoke-WebRequest -Uri http://localhost:3001/health -UseBasicParsing

# Should return: {"status": "healthy"}
```

## Prevention

1. **Always stop the previous server before starting a new one**
2. **Use the restart script** (`backend/restart_server.ps1`) to ensure clean restarts
3. **Check for running processes** before starting:
   ```powershell
   Get-NetTCPConnection -LocalPort 3001
   ```

## Quick Fix Script

Create a file `backend/restart_server.ps1` with the restart script (already created in the codebase).

## Additional Notes

- If you continue to see hanging connections, check backend logs for errors
- Make sure only ONE instance of the backend server is running at a time
- If the problem persists, restart your computer to clear all stuck connections

