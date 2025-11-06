# Research Tool - Quick Start Guide

## Prerequisites
- ✅ Node.js 18+ installed
- ✅ Python 3.9+ installed
- ✅ Dependencies installed (you've done this!)

## Starting the Application

### Step 1: Start Backend Server

Open a terminal and navigate to the backend directory:

```bash
cd backend
python run_server.py
```

Or alternatively:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Step 2: Start Frontend Client

Open a **new terminal** and navigate to the client directory:

```bash
cd client
npm run dev
```

The frontend will be available at:
- **Frontend**: http://localhost:3000

### Step 3: Verify Everything is Running

1. **Check Backend Health**:
   - Open browser: http://localhost:8000/health
   - Should return: `{"status": "healthy"}`

2. **Check Frontend**:
   - Open browser: http://localhost:3000
   - Should see the Research Tool interface

3. **Check API Docs**:
   - Open browser: http://localhost:8000/docs
   - Should see Swagger UI with all API endpoints

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Find and kill the process
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or change port in backend/run_server.py
```

**Module not found errors:**
```bash
cd backend
pip install -r requirements.txt
```

**Import errors (missing project root):**
- Make sure you're running from the project root
- Or adjust the path in `backend/app/main.py`

### Frontend Issues

**Port 3000 already in use:**
```bash
# Change port in client/vite.config.ts
# Or kill the process using port 3000
```

**npm errors:**
```bash
cd client
rm -rf node_modules package-lock.json
npm install
```

**CORS errors:**
- Make sure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`

### WebSocket Connection Issues

**WebSocket not connecting:**
- Verify backend is running
- Check browser console for WebSocket errors
- Verify WebSocket URL in `client/src/hooks/useWebSocket.ts`

## Using the Application

1. **Start with Link Input**:
   - Go to http://localhost:3000
   - Paste URLs (one per line) in the textarea
   - Click "开始研究" (Start Research)

2. **Watch Progress**:
   - The app will automatically navigate through phases
   - WebSocket will show real-time updates
   - Progress bars will update live

3. **Interactive Research**:
   - During Phase 1-2, you may need to interact
   - Select goals, confirm plans as needed

4. **View Results**:
   - Phase 3 shows step-by-step results
   - Phase 4 shows final report

## Development Workflow

### Running Both Servers

**Option 1: Two Terminals**
- Terminal 1: `cd backend && python run_server.py`
- Terminal 2: `cd client && npm run dev`

**Option 2: Use a process manager** (future enhancement)
- Could use `concurrently` or `pm2` to run both

### Hot Reload

- **Backend**: Auto-reloads on file changes (if using `--reload`)
- **Frontend**: Vite auto-reloads on file changes

### Making Changes

1. **Frontend Changes**: Save file → Browser auto-refreshes
2. **Backend Changes**: Save file → Server auto-reloads (if using `--reload`)
3. **API Changes**: Restart backend server

## Next Steps

Once both servers are running:
1. Test the link input page
2. Test the scraping progress
3. Test the research agent flow
4. Test the session display
5. Test the final report

## Common Commands

```bash
# Backend
cd backend
python run_server.py                    # Start server
pip install -r requirements.txt         # Install dependencies

# Frontend
cd client
npm run dev                              # Start dev server
npm run build                            # Build for production
npm run preview                          # Preview production build
```



