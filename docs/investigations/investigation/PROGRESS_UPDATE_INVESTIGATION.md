# Frontend Progress Update Investigation

## Executive Summary

The frontend is not receiving real-time progress updates from the Python backend, despite the backend generating detailed progress markers throughout the workflow. The root causes are:

1. **Event Loop Issues**: Research phases run in worker threads without event loops, preventing WebSocket messages from being sent
2. **Missing Progress Markers During API Calls**: Research phases don't send progress updates during long-running AI API calls (streaming)
3. **Insufficient Granular Updates**: Research phases only send updates at phase boundaries, not during internal processing
4. **WebSocket Message Delivery Failures**: Event loop issues cause `_schedule_coroutine()` to fail silently, preventing messages from reaching the frontend

## Evidence from Logs and Code

### 1. Backend IS Generating Progress Markers

From terminal logs, we can see:
- `Progress update: batch=20251105_070315, link=yt_reql, stage=loading, progress=10.0%`
- `Phase 0.5 complete: Generated role 'AI开发工具与开源生态分析师'`
- `Phase 1 complete: Generated 15 research goals`
- `Starting streaming request to https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`

**Conclusion**: The backend has detailed progress information, but it's not reaching the frontend.

### 2. Frontend IS Configured to Receive Updates

From `client/src/hooks/useWebSocket.ts`:
- Handles `research:phase_change` (line 182)
- Handles `workflow:progress` (line 131)
- Handles `research:stream_token` (line 193)
- Handles `scraping:status` and `scraping:item_progress` (lines 135-163)

**Conclusion**: Frontend infrastructure is ready, but messages aren't arriving.

### 3. WebSocket Infrastructure Exists

From `backend/app/services/websocket_ui.py`:
- `display_message()` sends `workflow:progress` messages (line 78)
- `notify_phase_change()` sends `research:phase_change` messages (line 149)
- `display_stream()` sends `research:stream_token` messages (line 125)

**Conclusion**: Infrastructure exists, but execution path is broken.

## Root Causes Identified

### Issue 1: Event Loop in Worker Threads (CRITICAL)

**Location**: `backend/app/services/workflow_service.py:350-354`

**Problem**: Research agent runs in a worker thread via `asyncio.to_thread()`, which doesn't have an event loop. When `WebSocketUI` methods try to send messages:

```python
# In workflow_service.py
result = await asyncio.to_thread(
    run_research_agent,
    batch_id,
    ui=ui,
    progress_callback=progress_callback
)
```

The `WebSocketUI` methods call `_schedule_coroutine()`, which tries to get the event loop:

```python
# In websocket_ui.py
def _get_main_loop(self) -> Optional[asyncio.AbstractEventLoop]:
    # ... tries to get loop
    try:
        loop = asyncio.get_running_loop()  # FAILS in worker threads
```

**Impact**: 
- `display_header()` calls fail silently
- `display_message()` calls fail silently  
- `notify_phase_change()` calls fail silently
- All UI updates during research phases are lost

**Evidence**: From `WEBSOCKET_UI_ISSUES.md`, there are errors like:
- `"Failed to send message: There is no current event loop in thread 'asyncio_0'"`

### Issue 2: No Progress Updates During Streaming (HIGH PRIORITY)

**Location**: `research/phases/base_phase.py:_stream_with_callback()`

**Problem**: When phases call AI APIs (e.g., Phase 0.5, Phase 1), they use `_stream_with_callback()` which streams tokens but doesn't send progress updates to the frontend. The frontend only sees "等待AI响应..." with no indication that:
- The API call has started
- Tokens are being received
- Progress is being made

**Current Flow**:
1. Phase calls `_stream_with_callback(messages)`
2. Method streams tokens internally
3. Only returns final response
4. No intermediate WebSocket messages sent

**Impact**: During Phase 0.5 and Phase 1 execution (which can take 30-60 seconds), the frontend shows static "等待AI响应..." with no updates.

### Issue 3: Insufficient Granular Progress Markers (MEDIUM PRIORITY)

**Location**: `research/agent.py` and phase files

**Problem**: Progress updates only occur at phase boundaries:
- `display_header("Phase 0.5: 生成研究角色")` - only at start
- `display_message("生成的研究角色: ...")` - only at end
- No updates during: prompt construction, API call, parsing, validation

**Missing Markers**:
- "正在构建提示词..." (Building prompt...)
- "正在调用AI API..." (Calling AI API...)
- "正在接收响应..." (Receiving response...)
- "正在解析结果..." (Parsing results...)
- "正在验证数据..." (Validating data...)

**Impact**: Long gaps between updates make the UI appear frozen.

### Issue 4: Scraping Progress May Not Be Broadcasting (MEDIUM PRIORITY)

**Location**: `backend/app/services/workflow_service.py:_process_progress_queue()`

**Problem**: Scraper progress callbacks are queued and processed, but:
- Queue processing happens in async task
- If the task is cancelled or fails, messages are lost
- Messages may be throttled too aggressively

**Evidence**: From logs, we see `Progress update` messages in DEBUG logs, but frontend shows 0% progress.

## Solution Architecture

### Solution 1: Fix Event Loop Issues (CRITICAL - MUST FIX)

**Approach**: Ensure `WebSocketUI` can send messages from worker threads.

**Implementation**:
1. Store main event loop reference when creating `WebSocketUI` (already done)
2. Fix `_get_main_loop()` to reliably use stored reference from worker threads
3. Ensure `_schedule_coroutine()` always uses `asyncio.run_coroutine_threadsafe()` with stored loop
4. Add retry/fallback mechanism if loop is temporarily unavailable

**Files to Modify**:
- `backend/app/services/websocket_ui.py`:
  - Improve `_get_main_loop()` to check stored loop first
  - Add thread-safe queue for messages when loop is unavailable
  - Add message queuing and retry mechanism

**Code Changes**:
```python
def _get_main_loop(self) -> Optional[asyncio.AbstractEventLoop]:
    # Always try stored reference first (works from worker threads)
    if self.main_loop is not None:
        try:
            # Don't check is_running() - it returns False from worker threads
            # Just check if loop is closed
            if not self.main_loop.is_closed():
                return self.main_loop
        except RuntimeError:
            pass
    
    # Fallback: try to get current loop (only works in async context)
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None

def _schedule_coroutine(self, coro):
    """Schedule coroutine with message queuing fallback."""
    loop = self._get_main_loop()
    
    if loop is not None:
        try:
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future
        except Exception as e:
            logger.error(f"Failed to schedule coroutine: {e}")
            # Fallback: queue message for later delivery
            self._queue_message_for_retry(coro)
            return None
    else:
        # No loop available - queue for retry
        self._queue_message_for_retry(coro)
        return None
```

### Solution 2: Add Progress Markers During Streaming (HIGH PRIORITY)

**Approach**: Send progress updates throughout the streaming process.

**Implementation**:
1. Send "starting" message when API call begins
2. Send periodic progress updates during streaming (every N tokens or every X seconds)
3. Send "parsing" message when stream completes
4. Send "validating" message during validation
5. Send "complete" message when done

**Files to Modify**:
- `research/phases/base_phase.py`:
  - Add progress callbacks to `_stream_with_callback()`
  - Send WebSocket messages at key points
  - Integrate with `WebSocketUI` for progress reporting

**Code Changes**:
```python
def _stream_with_callback(self, messages):
    """Stream with progress updates."""
    # Send "starting" update
    if hasattr(self, 'ui') and self.ui:
        self.ui.display_message("正在调用AI API...", "info")
    
    response = ""
    token_count = 0
    
    # Stream with progress updates
    for token in self.client.stream_completion(messages):
        response += token
        token_count += 1
        
        # Send progress update every 10 tokens or every 2 seconds
        if token_count % 10 == 0 or (time.time() - last_update) > 2:
            if hasattr(self, 'ui') and self.ui:
                self.ui.display_message(f"正在接收响应... ({token_count} tokens)", "info")
            last_update = time.time()
    
    # Send "parsing" update
    if hasattr(self, 'ui') and self.ui:
        self.ui.display_message("正在解析结果...", "info")
    
    return response
```

### Solution 3: Add Granular Progress Markers (MEDIUM PRIORITY)

**Approach**: Add progress markers at every significant step within phases.

**Implementation**:
1. Add markers in `Phase0_5RoleGeneration.execute()`:
   - "正在构建提示词..."
   - "正在调用AI生成角色..."
   - "正在解析角色..."
   - "正在验证角色..."
   - "角色生成完成"

2. Add markers in `Phase1Discover.execute()`:
   - "正在构建提示词..."
   - "正在生成研究目标..."
   - "正在解析目标..."
   - "正在验证目标..."
   - "正在检测重叠..."
   - "目标生成完成"

**Files to Modify**:
- `research/phases/phase0_5_role_generation.py`
- `research/phases/phase1_discover.py`
- `research/phases/base_phase.py`

**Code Changes**:
```python
# In Phase0_5RoleGeneration.execute()
self.logger.info("Phase 0.5: Generating research role")
self.ui.display_message("正在构建提示词...", "info")

context = {...}
messages = compose_messages("phase0_5_role_generation", context=context)

self.ui.display_message("正在调用AI生成角色...", "info")
response = self._stream_with_callback(messages)

self.ui.display_message("正在解析角色...", "info")
try:
    parsed = self.client.parse_json_from_stream(iter([response]))
    # ...
except Exception as e:
    # ...

self.ui.display_message("正在验证角色...", "info")
schema = load_schema(...)
if schema:
    self._validate_against_schema(parsed, schema)

self.ui.display_message("角色生成完成", "success")
```

### Solution 4: Improve Scraping Progress Broadcasting (MEDIUM PRIORITY)

**Approach**: Ensure scraping progress messages are reliably delivered.

**Implementation**:
1. Add error handling and retry logic to `_process_progress_queue()`
2. Reduce throttling aggressiveness
3. Add heartbeat messages to verify connection
4. Ensure messages are sent even if queue processing is slow

**Files to Modify**:
- `backend/app/services/workflow_service.py:_process_progress_queue()`
- `backend/app/services/progress_service.py:update_link_progress()`

## Implementation Priority

1. **CRITICAL**: Fix event loop issues (Solution 1) - This blocks ALL progress updates
2. **HIGH**: Add progress markers during streaming (Solution 2) - This fixes the "waiting" issue
3. **MEDIUM**: Add granular progress markers (Solution 3) - This improves UX
4. **MEDIUM**: Improve scraping progress broadcasting (Solution 4) - This ensures scraping updates work

## Testing Strategy

### Test 1: Event Loop Fix
1. Start research workflow
2. Monitor WebSocket messages in browser DevTools
3. Verify messages are received during Phase 0.5 and Phase 1
4. Check backend logs for successful message sending (no errors)

### Test 2: Streaming Progress
1. Start Phase 0.5 or Phase 1
2. Verify frontend receives "正在调用AI API..." message
3. Verify periodic progress updates during streaming
4. Verify "正在解析结果..." message appears

### Test 3: Granular Markers
1. Start research workflow
2. Verify frontend shows progress at each step:
   - "正在构建提示词..."
   - "正在调用AI..."
   - "正在解析..."
   - "正在验证..."
   - "完成"

### Test 4: End-to-End
1. Start full workflow (scraping → research)
2. Verify frontend updates in real-time throughout
3. Verify no static "等待AI响应..." messages
4. Verify progress bars and status updates work

## Additional Considerations

### Message Throttling
- Current throttling: 0.2s minimum interval, 1% progress change
- Consider: Reduce throttling for research phases (more frequent updates)
- Consider: Different throttling for different message types

### Error Handling
- Add retry logic for failed WebSocket sends
- Add message queue for offline scenarios
- Add connection status indicators in frontend

### Frontend Display
- Ensure UI components actually display received messages
- Add progress bars for research phases
- Add timestamps for progress updates
- Add visual indicators for active phases

## Conclusion

The backend has all the necessary infrastructure and generates detailed progress information, but event loop issues prevent messages from being sent to the frontend. Additionally, insufficient granular progress markers during long-running operations make the UI appear frozen.

**Key Actions**:
1. Fix event loop detection in `WebSocketUI` (CRITICAL)
2. Add progress updates during streaming (HIGH)
3. Add granular markers in phases (MEDIUM)
4. Improve scraping progress delivery (MEDIUM)

Once these are implemented, the frontend should receive real-time updates throughout the entire workflow.




