# Comprehensive Fix Plan - All Critical Issues

## Overview

This plan addresses all 6 critical issues preventing progress updates and user input from working.

---

## Issue 1: ScrapingProgressPage Restarts Workflow

### Problem
Every navigation to "抓取进度" starts a NEW workflow instead of viewing existing progress.

### Root Cause
`useEffect` in `ScrapingProgressPage.tsx` always calls `startWorkflow()` when component mounts.

### Solution Strategy

**1. Check Workflow Status First**
- Before starting, call `GET /api/workflow/status/{workflow_id}` to check if workflow is running
- Only start if status is "stopped" or doesn't exist
- If running, just connect WebSocket and display existing progress

**2. Track Workflow State in Frontend**
- Store `workflowStarted` flag in `workflowStore`
- Only allow one workflow start per batch_id
- Prevent multiple simultaneous starts

**3. Implementation**
```typescript
// In ScrapingProgressPage.tsx
useEffect(() => {
  if (!batchId) {
    navigate('/')
    return
  }

  const checkAndStart = async () => {
    try {
      // Check if workflow is already running
      const status = await apiService.getWorkflowStatus(`workflow_${batchId}`)
      
      if (status.status === 'running') {
        // Workflow already running, just connect WebSocket
        console.log('Workflow already running, connecting to updates...')
        return
      }
      
      // Only start if not running
      if (status.status === 'stopped' || !status.exists) {
        await apiService.startWorkflow(batchId)
      }
    } catch (error) {
      console.error('Failed to check workflow status:', error)
      // Fallback: try to start (might fail if already running)
      try {
        await apiService.startWorkflow(batchId)
      } catch (e) {
        console.error('Failed to start workflow:', e)
      }
    }
  }

  checkAndStart()
}, [batchId, navigate])
```

**Files to Modify**
- `client/src/pages/ScrapingProgressPage.tsx` - Add status check before starting
- `client/src/stores/workflowStore.ts` - Add `workflowStarted` flag
- `client/src/services/api.ts` - Add `getWorkflowStatus()` method if missing

---

## Issue 2: Progress Callback Not Converted to ProgressService

### Problem
Scraper callbacks queue messages but never call `ProgressService.update_link_progress()`.

### Root Cause
`_process_progress_queue()` just broadcasts raw messages without converting to ProgressService format.

### Solution Strategy

**1. Create Progress Message Converter**
- Transform scraper callback format to ProgressService format
- Extract `batch_id`, `link_id`, `url` from context
- Convert `{stage, progress, message}` to `ProgressService.update_link_progress()` parameters

**2. Track Link Context**
- Store mapping of `scraper_type` → `link_id` and `url` for each batch
- When scraper sends progress, look up link_id and url
- Pass correct parameters to ProgressService

**3. Implementation**
```python
# In workflow_service.py
class WorkflowService:
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.progress_service = ProgressService(websocket_manager)
        # Track link context for progress callbacks
        self.link_context: Dict[str, Dict[str, Dict]] = {}  # batch_id -> scraper_type -> {link_id, url}
    
    def _create_progress_callback(self, batch_id: str, message_queue: queue.Queue):
        """Create progress callback that converts to ProgressService format."""
        
        def progress_callback(message: dict):
            """Convert scraper callback to ProgressService format."""
            try:
                scraper_type = message.get('scraper', 'unknown')
                stage = message.get('stage', 'unknown')
                progress = message.get('progress', 0.0)
                message_text = message.get('message', '')
                
                # Look up link_id and url from context
                link_info = self.link_context.get(batch_id, {}).get(scraper_type, {})
                link_id = link_info.get('link_id', f'{scraper_type}_unknown')
                url = link_info.get('url', '')
                
                # Convert to ProgressService format
                metadata = {
                    'bytes_downloaded': message.get('bytes_downloaded', 0),
                    'total_bytes': message.get('total_bytes', 0),
                    'source': scraper_type
                }
                
                # Queue for async processing
                message_queue.put_nowait({
                    'action': 'update_link_progress',
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'url': url,
                    'stage': stage,
                    'stage_progress': progress,
                    'overall_progress': progress,
                    'message': message_text,
                    'metadata': metadata
                })
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        return progress_callback
    
    async def _process_progress_queue(self, message_queue: queue.Queue, batch_id: str):
        """Process queue and call ProgressService."""
        while True:
            try:
                message = message_queue.get_nowait()
                
                if message.get('action') == 'update_link_progress':
                    # Call ProgressService
                    await self.progress_service.update_link_progress(
                        batch_id=message['batch_id'],
                        link_id=message['link_id'],
                        url=message['url'],
                        stage=message['stage'],
                        stage_progress=message['stage_progress'],
                        overall_progress=message['overall_progress'],
                        message=message['message'],
                        metadata=message.get('metadata')
                    )
                else:
                    # Fallback: broadcast raw message
                    await self.ws_manager.broadcast(batch_id, message)
                    
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing progress queue: {e}")
                await asyncio.sleep(0.1)
```

**4. Initialize Link Context**
- Before calling `run_all_scrapers`, load links from TestLinksLoader
- Map each scraper type to its link_id and url
- Store in `self.link_context[batch_id]`

**Files to Modify**
- `backend/app/services/workflow_service.py` - Add link context tracking and converter
- `backend/app/services/workflow_service.py` - Modify `_process_progress_queue()` to call ProgressService

---

## Issue 3: Scrapers Don't Receive Progress Callback

### Problem
Scrapers run as subprocesses (test scripts), so progress_callback can't be passed directly.

### Root Cause
`test_all_scrapers_and_save()` runs test scripts as subprocesses, so Python callbacks can't be passed.

### Solution Strategy

**Option A: Modify Test Scripts to Accept Progress Callback (Preferred)**
- Modify test scripts to accept `progress_callback` parameter
- Pass callback when creating scrapers
- Scrapers call `_report_progress()` which calls callback

**Option B: Use File-Based Progress Tracking (Fallback)**
- Test scripts write progress to JSON files
- Backend polls files for progress updates
- Convert file updates to ProgressService calls

**Option C: Use Environment Variables/Shared State (Complex)**
- Use Redis/database or shared memory
- Test scripts write progress to shared state
- Backend reads and converts

### Implementation (Option A - Preferred)

**1. Modify Test Scripts**
- Update `test_bilibili_scraper.py`, `test_youtube_scraper.py`, etc.
- Accept `progress_callback` parameter from command line or environment
- Pass to scrapers when creating them

**2. Pass Callback via Environment Variable**
- Serialize callback as JSON/string (limited)
- Or use named pipe/queue file
- Or modify scripts to accept callback function (requires Python import)

**3. Better Approach: Modify run_all_scrapers**
- Instead of running subprocesses, directly import and run scraper tests
- Pass progress_callback directly to scrapers
- This requires refactoring test scripts to be importable functions

**4. Implementation**
```python
# In backend/lib/workflow.py or new file
def run_all_scrapers_direct(progress_callback=None, batch_id: str = None):
    """Run scrapers directly (not as subprocesses) with progress callback."""
    from tests.test_links_loader import TestLinksLoader
    from scrapers.bilibili_scraper import BilibiliScraper
    from scrapers.youtube_scraper import YouTubeScraper
    # ... etc
    
    loader = TestLinksLoader()
    batch_id = batch_id or loader.get_batch_id()
    
    # Get links
    links_by_type = {
        'bilibili': loader.get_links('bilibili'),
        'youtube': loader.get_links('youtube'),
        # ... etc
    }
    
    # Create scrapers with progress callback
    scrapers = {
        'bilibili': BilibiliScraper(progress_callback=progress_callback),
        'youtube': YouTubeScraper(progress_callback=progress_callback),
        # ... etc
    }
    
    # Run scrapers in parallel
    results = []
    for scraper_type, scraper in scrapers.items():
        for link in links_by_type.get(scraper_type, []):
            result = scraper.extract(
                link['url'],
                batch_id=batch_id,
                link_id=link['id']
            )
            results.append(result)
    
    return {
        'batch_id': batch_id,
        'success': any(r.get('success') for r in results),
        'results': results
    }
```

**Files to Modify**
- `backend/lib/workflow.py` - Add `run_all_scrapers_direct()` function
- `backend/app/services/workflow_service.py` - Use `run_all_scrapers_direct()` instead of `run_all_scrapers()`
- Or modify `tests/test_all_scrapers_and_save_json.py` to accept and pass callbacks

---

## Issue 4: Reddit Login Prompt Not Using WebSocket UI

### Problem
Reddit scraper uses `logger.info()` and `print()` instead of `ui.prompt_user()`.

### Root Cause
Scrapers don't have access to `WebSocketUI` instance.

### Solution Strategy

**Option A: Pass UI Instance to Scrapers (Preferred)**
- Pass `ui` parameter to scrapers when creating them
- Scrapers call `ui.prompt_user()` when needed
- Requires UI instance to be available in scraping phase

**Option B: Use ProgressService for Prompts**
- Add `prompt_user()` method to ProgressService
- Send `research:user_input_required` message via ProgressService
- Scrapers receive UI instance via ProgressService

**Option C: Use Shared State**
- Scrapers write prompts to shared state/file
- Backend reads and sends via WebSocket
- Backend writes response back to shared state
- Scrapers read response

### Implementation (Option A - Preferred)

**1. Modify Scrapers to Accept UI Parameter**
```python
# In scrapers/reddit_scraper.py
class RedditScraper(BaseScraper):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.ui = kwargs.get('ui', None)  # Optional UI instance
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None):
        # ... existing code ...
        
        # Instead of logger.info/print:
        if self.ui:
            confirm = self.ui.prompt_user(
                "请在浏览器窗口中登录 Reddit。登录完成后，抓取器将自动继续...",
                choices=None
            )
            # Wait for user to login (check page state)
        else:
            # Fallback to terminal
            logger.info("WAITING FOR YOU TO LOG IN")
            print("WAITING FOR YOU TO LOG IN")
```

**2. Pass UI to Scrapers**
- Create `WebSocketUI` instance in scraping phase
- Pass to scrapers when creating them
- Or use ProgressService as adapter

**Files to Modify**
- `scrapers/reddit_scraper.py` - Add UI parameter and use `ui.prompt_user()`
- `scrapers/base_scraper.py` - Add `ui` parameter to `__init__`
- `backend/app/services/workflow_service.py` - Create UI instance and pass to scrapers

---

## Issue 5: Progress Message Format Mismatch

### Problem
Progress messages don't match frontend handler expectations.

### Root Cause
Raw scraper callbacks don't include `type`, `link_id`, `url` fields that frontend expects.

### Solution Strategy

**1. Ensure ProgressService Format**
- ProgressService already sends correct format (verified in code)
- Issue is that scraper callbacks aren't reaching ProgressService
- Fix Issue 2 first (convert callbacks to ProgressService)

**2. Verify Message Format**
- Check that `ProgressService.update_link_progress()` sends:
  ```python
  {
    'type': 'scraping:item_progress',
    'link_id': link_id,
    'url': url,
    'stage': stage,
    'stage_progress': stage_progress,
    'overall_progress': overall_progress,
    'message': message,
    'metadata': metadata or {},
    'timestamp': timestamp
  }
  ```
- This matches frontend handler in `useWebSocket.ts`

**Files to Verify**
- `backend/app/services/progress_service.py` - Already correct
- `client/src/hooks/useWebSocket.ts` - Already handles correctly
- Fix Issue 2 to ensure messages reach ProgressService

---

## Issue 6: WebSocket Connection Issues

### Problem
WebSocket may not connect if `batchId` is not set correctly.

### Root Cause
Connection depends on `batchId` being available when component mounts.

### Solution Strategy

**1. Ensure batchId is Set**
- Verify `batchId` is set in store before connecting
- Add validation and error handling

**2. Handle Connection Errors**
- Add retry logic
- Show user-friendly error messages
- Fallback to polling if WebSocket fails

**3. Implementation**
```typescript
// In useWebSocket.ts
useEffect(() => {
  if (!batchId) {
    console.warn('WebSocket: batchId not set, skipping connection')
    return
  }

  const connect = () => {
    const wsUrl = `ws://localhost:8000/ws/${batchId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      reconnectAttemptsRef.current = 0
      addNotification('已连接到服务器', 'success')
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      addNotification('WebSocket连接错误，将尝试重新连接', 'warning')
    }

    // ... rest of connection logic
  }

  connect()
}, [batchId])
```

**Files to Modify**
- `client/src/hooks/useWebSocket.ts` - Add batchId validation
- `client/src/pages/ScrapingProgressPage.tsx` - Ensure batchId is set before mounting

---

## Implementation Priority

### Phase 1: Critical (Blocks Everything)
1. **Fix Issue 1** - ScrapingProgressPage workflow restart
2. **Fix Issue 2** - Progress callback conversion to ProgressService
3. **Fix Issue 3** - Scrapers receive progress callback

### Phase 2: Important (User Experience)
4. **Fix Issue 4** - Reddit login prompt via WebSocket
5. **Fix Issue 6** - WebSocket connection reliability

### Phase 3: Verification
6. **Verify Issue 5** - Message format (should be fixed by Issue 2)

---

## Testing Strategy

After each fix:
1. Test workflow doesn't restart on navigation
2. Test progress updates appear in real-time
3. Test Reddit login prompt appears in web UI
4. Test WebSocket connection is stable
5. Test all message types are received correctly

---

## Files to Modify Summary

### Frontend
- `client/src/pages/ScrapingProgressPage.tsx` - Add workflow status check
- `client/src/stores/workflowStore.ts` - Add workflow state tracking
- `client/src/services/api.ts` - Add/verify `getWorkflowStatus()`
- `client/src/hooks/useWebSocket.ts` - Add batchId validation

### Backend
- `backend/app/services/workflow_service.py` - Add link context tracking, progress callback converter
- `backend/lib/workflow.py` - Add `run_all_scrapers_direct()` or modify to pass callbacks
- `scrapers/reddit_scraper.py` - Use UI for login prompt
- `scrapers/base_scraper.py` - Add UI parameter support

---

## Risk Assessment

**High Risk**
- Modifying test scripts to accept callbacks (may break existing tests)
- Changing scraper execution model (from subprocess to direct)

**Medium Risk**
- Adding link context tracking (needs proper initialization)
- WebSocket UI for scrapers (needs proper instance passing)

**Low Risk**
- Workflow status check (simple API call)
- WebSocket connection validation (simple checks)

---

## Alternative Approaches

If direct scraper execution is too risky:
1. Keep subprocess model but use file-based progress tracking
2. Test scripts write progress to JSON files
3. Backend polls files and converts to ProgressService
4. Slower updates but more reliable

---

## Estimated Implementation Time

- Issue 1: 30 minutes
- Issue 2: 2-3 hours
- Issue 3: 2-4 hours (depending on approach)
- Issue 4: 1-2 hours
- Issue 6: 30 minutes

**Total: 6-10 hours**




