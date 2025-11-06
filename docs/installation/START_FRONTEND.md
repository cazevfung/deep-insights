# Starting the Frontend Development Server

## Issue

The frontend timeout error occurs because:
1. **The Vite dev server is not running** - The frontend needs to run on port 3000 to use the API proxy
2. **You're accessing the wrong port** - If you're accessing `http://localhost:3001/`, that's the backend API, not the frontend

## Solution

### Step 1: Start the Frontend Dev Server

Open a terminal in the `client` directory and run:

```bash
cd client
npm run dev
```

This will start the Vite dev server on **port 3000**.

### Step 2: Access the Frontend

Once the dev server is running, access the frontend at:
- **http://localhost:3000** (NOT port 3001)

The Vite proxy will automatically forward all `/api` requests to the backend on port 3001.

### Step 3: Verify Backend is Running

Make sure the backend is running on port 3001:

```bash
cd backend
python run_server.py
```

## Quick Start (Both Servers)

**Terminal 1 - Backend:**
```bash
cd backend
python run_server.py
```

**Terminal 2 - Frontend:**
```bash
cd client
npm run dev
```

Then open **http://localhost:3000** in your browser.

## Architecture

- **Frontend**: Runs on port 3000 (Vite dev server)
- **Backend**: Runs on port 3001 (FastAPI/uvicorn)
- **Proxy**: Vite automatically proxies `/api/*` to `http://localhost:3001/api/*`

## Troubleshooting

### If you see "Backend health check failed: TimeoutError"

1. ✅ Check backend is running: `curl http://localhost:3001/api/links/health`
2. ✅ Check frontend dev server is running: `curl http://localhost:3000`
3. ✅ Make sure you're accessing `http://localhost:3000` (not 3001)
4. ✅ Check CORS is configured correctly in `backend/app/main.py`
5. ✅ Verify Vite proxy is configured in `client/vite.config.ts`

### If port 3000 is already in use

Vite will automatically try the next available port (3001, 3002, etc.). If this happens:
- Update CORS in `backend/app/main.py` to include the new port
- Access the frontend at the port Vite shows in the terminal

