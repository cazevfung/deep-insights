# How to Fix the HTTP 500 Error

## Problem
You're getting a 500 error when accessing `http://localhost:3000/api/links/health`. This usually means:
1. The backend server isn't running, OR
2. There's an initialization error when the backend starts

## Solution Steps

### Step 1: Start the Backend Server

Open a new terminal window and run:

```bash
cd "d:\App Dev\Research Tool\backend"
python run_server.py
```

Or if you're using a virtual environment:

```bash
cd "d:\App Dev\Research Tool\backend"
.venv\Scripts\activate  # Activate virtual environment
python run_server.py
```

### Step 2: Check for Startup Errors

When you start the server, look for these messages in the console:

**✅ Good signs:**
- "LinkFormatterService initialized successfully"
- "Uvicorn running on http://0.0.0.0:3001"
- No error messages

**❌ Bad signs:**
- "Failed to initialize LinkFormatterService"
- Import errors
- Any Python tracebacks

### Step 3: Test the Health Endpoint

Once the server is running, test the health endpoint:

1. **Direct backend test** (should work if backend is running):
   ```
   http://localhost:3001/api/links/health
   ```

2. **Through frontend proxy** (should work if both frontend and backend are running):
   ```
   http://localhost:3000/api/links/health
   ```

### Step 4: If You See Initialization Errors

If you see "Failed to initialize LinkFormatterService", check:

1. **Import errors**: Make sure `utils/link_formatter.py` exists and is accessible
2. **Path issues**: The service tries to find the project root - make sure you're running from the correct directory

### Step 5: Check Both Servers Are Running

You need BOTH servers running:

1. **Backend** (port 3001): `python backend/run_server.py`
2. **Frontend** (port 3000): Usually `npm run dev` or `vite` in the `client` directory

The frontend proxies `/api/*` requests to `http://localhost:3001`, so both must be running.

## Quick Diagnostic Commands

Check if backend is running:
```powershell
netstat -ano | findstr ":3001"
```

Check if frontend is running:
```powershell
netstat -ano | findstr ":3000"
```

## Common Issues

### Issue 1: Backend not running
**Solution**: Start the backend server first

### Issue 2: Import errors
**Solution**: Make sure you're in the correct directory and all dependencies are installed

### Issue 3: Port already in use
**Solution**: Kill the process using port 3001 or change the port in `backend/run_server.py`

### Issue 4: Virtual environment not activated
**Solution**: Activate your virtual environment before starting the server
