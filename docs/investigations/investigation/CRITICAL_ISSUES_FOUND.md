# Critical Issues Found - Progress Updates and User Input

## Summary

After investigation, **NONE** of the frontend-backend interactions are actually working in production. All fixes were implemented but the core integration points are broken.

---

## Issue 1: ScrapingProgressPage RESTARTS Workflow Every Time

**Location**: `client/src/pages/ScrapingProgressPage.tsx:36-44`

**Problem**: 
```typescript
useEffect(() => {
  if (!batchId) {
    navigate('/')
    return
  }

  // Start workflow
  const startWorkflow = async () => {
    try {
      await apiService.startWorkflow(batchId)  // ❌ THIS STARTS A NEW WORKFLOW!
    } catch (error) {
      console.error('Failed to start workflow:', error)
    }
  }

  startWorkflow()
}, [batchId, navigate])  // ❌ Runs every time component mounts or batchId changes
```

**Impact**: 
- Every time user clicks "抓取进度" (Scraping Progress), it starts a **NEW** scraping process
- Cannot view existing progress - it always restarts
- Duplicate work running simultaneously

**Root Cause**: 
The component assumes it should start a workflow when mounted, but it should:
1. Check if workflow is already running
2. Only start if not running
3. Connect to existing WebSocket to receive updates

**Fix Required**:
- Check workflow status before starting
- Only start if not already running
- Always connect WebSocket regardless of workflow state

---

## Issue 2: Progress Callback Not Connected to ProgressService

**Location**: `backend/app/services/workflow_service.py:105` and `backend/lib/workflow.py`

**Problem**: 
The `progress_callback` created by `_create_progress_callback()` puts messages in a queue with format:
```python
{
  'stage': 'downloading',
  'progress': 50.0,
  'message': '...',
  'bytes_downloaded': 1000,
  'total_bytes': 2000,
  'scraper': 'bilibili'
}
```

But `ProgressService.update_link_progress()` expects:
```python
batch_id, link_id, url, stage, stage_progress, overall_progress, message, metadata
```

**Impact**:
- Progress callbacks from scrapers are queued but **never converted** to ProgressService calls
- No WebSocket messages sent for scraping progress
- Frontend receives **zero** progress updates

**Root Cause**: 
The queue processor `_process_progress_queue()` just broadcasts the raw message, but:
1. Messages don't have `batch_id` or `link_id` properly set
2. ProgressService expects different format
3. No conversion layer between scraper callbacks and ProgressService

**Fix Required**:
- Convert scraper callback format to ProgressService format
- Extract `batch_id` and `link_id` from context
- Call `progress_service.update_link_progress()` with proper parameters

---

## Issue 3: Scrapers Don't Receive Progress Callback

**Location**: `backend/lib/workflow.py` (run_all_scrapers function)

**Problem**: 
Need to verify if `run_all_scrapers` actually passes `progress_callback` to scrapers when creating them.

**Likely Issue**:
- Scrapers are created without `progress_callback` parameter
- `self.progress_callback` is `None` in scrapers
- `_report_progress()` calls do nothing

**Fix Required**:
- Ensure `run_all_scrapers` passes `progress_callback` to all scrapers
- Verify scrapers receive callback in `__init__()`

---

## Issue 4: Reddit Login Prompt Not Using WebSocket UI

**Location**: `scrapers/reddit_scraper.py:64-76`

**Problem**: 
```python
logger.info("WAITING FOR YOU TO LOG IN")
logger.info("Please log in to Reddit in the browser window.")
print("WAITING FOR YOU TO LOG IN")
```

Reddit scraper uses `logger.info()` and `print()` instead of `ui.prompt_user()`.

**Impact**:
- User input prompt appears in **terminal**, not web UI
- No interactive input in web app
- User can't respond via web interface

**Root Cause**: 
- Scrapers don't have access to `WebSocketUI` instance
- Scrapers are created before UI is initialized
- No mechanism to pass UI to scrapers

**Fix Required**:
- Pass UI instance to scrapers (or create adapter)
- Use `ui.prompt_user()` instead of logger/print
- Or use a different mechanism (e.g., ProgressService) to send prompts

---

## Issue 5: WebSocket Connection May Not Be Established

**Location**: `client/src/hooks/useWebSocket.ts:29-50`

**Problem**: 
WebSocket connection depends on `batchId` being set. If `batchId` is not set or changes, connection may fail.

**Impact**:
- WebSocket never connects
- No messages received
- Progress updates never arrive

**Fix Required**:
- Verify `batchId` is set before connecting
- Handle connection errors gracefully
- Reconnect on failure

---

## Issue 6: Progress Messages Not Matched to Frontend

**Location**: `backend/app/services/workflow_service.py:52-63`

**Problem**: 
The `progress_callback` creates messages with format:
```python
{
  'batch_id': batch_id,
  'stage': 'downloading',
  'progress': 50.0,
  ...
}
```

But frontend expects:
```typescript
{
  type: 'scraping:item_progress',
  link_id: ...,
  url: ...,
  stage: ...,
  ...
}
```

**Impact**:
- Messages are sent but don't match frontend handlers
- Frontend receives messages but doesn't process them correctly

**Fix Required**:
- Ensure message format matches frontend expectations
- Include `type` field in all messages
- Include `link_id` and `url` in progress messages

---

## Summary of Root Causes

1. **ScrapingProgressPage**: Starts new workflow instead of checking existing status
2. **Progress Callback**: Format mismatch between scraper callbacks and ProgressService
3. **Scraper Callback**: May not be passed to scrapers at all
4. **Reddit Login**: Uses terminal instead of WebSocket UI
5. **WebSocket**: Connection may not be established
6. **Message Format**: Messages don't match frontend expectations

---

## Priority Fix Order

### Critical (Blocks Everything)
1. **Fix ScrapingProgressPage** - Don't restart workflow, check status first
2. **Fix Progress Callback Connection** - Convert scraper callbacks to ProgressService calls
3. **Verify Scraper Callback Passing** - Ensure scrapers receive callback

### Important (Affects User Experience)
4. **Fix Reddit Login Prompt** - Use WebSocket UI instead of terminal
5. **Fix WebSocket Connection** - Ensure reliable connection
6. **Fix Message Format** - Match frontend expectations

---

## Files That Need Changes

### Frontend
- `client/src/pages/ScrapingProgressPage.tsx` - Fix workflow restart logic
- `client/src/hooks/useWebSocket.ts` - Verify connection handling

### Backend
- `backend/app/services/workflow_service.py` - Fix progress callback conversion
- `backend/lib/workflow.py` - Verify progress callback passing
- `scrapers/reddit_scraper.py` - Use WebSocket UI for login prompt
- `backend/app/services/progress_service.py` - May need adapter for scraper callbacks

---

## Verification Checklist

After fixes:
- [ ] ScrapingProgressPage doesn't restart workflow when navigating
- [ ] Progress updates appear in real-time in web UI
- [ ] Reddit login prompt appears in web UI, not terminal
- [ ] WebSocket connection is established and stable
- [ ] All progress messages match frontend handlers
- [ ] Scrapers receive progress callback correctly




