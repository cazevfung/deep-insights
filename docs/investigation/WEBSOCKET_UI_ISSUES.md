# WebSocket UI Issues Investigation

## Summary

This document outlines the investigation findings for two critical issues:
1. Research failed to sync with the web-based UI
2. Phase 1 doesn't obtain user input from the web-based UI

## Additional Finding: Missing UI Input Component

**Critical**: The frontend UI does NOT have any input field or mechanism for users to type and send their response when prompted.

- The `ResearchAgentPage` component shows a placeholder div when `waitingForUser` is true
- The placeholder only displays "等待用户输入..." (waiting for user input) text
- There is NO input field, textarea, or submit button
- There is NO way for users to actually provide their input

This means even if the backend issues were fixed, users still couldn't provide input because the UI component is missing.

## Root Causes

### Issue 1: Missing `display_synthesized_goal` Method

**Location**: `research/agent.py:271`

**Problem**: The research agent calls `self.ui.display_synthesized_goal(synthesized)` but `WebSocketUI` class doesn't implement this method.

**Error**: `'WebSocketUI' object has no attribute 'display_synthesized_goal'`

**Evidence**:
- `research/agent.py:271` calls `self.ui.display_synthesized_goal(synthesized)`
- `research/ui/mock_interface.py:168` has this method
- `research/ui/console_interface.py:102` has this method
- `backend/app/services/websocket_ui.py` does NOT have this method

**Fix Required**: Add `display_synthesized_goal` method to `WebSocketUI` class.

---

### Issue 2: Event Loop Not Available in Worker Threads

**Location**: `backend/app/services/websocket_ui.py:_schedule_coroutine()`

**Problem**: When research runs via `asyncio.to_thread()`, it executes in a worker thread that doesn't have an event loop. The `_schedule_coroutine()` method tries to use `asyncio.get_running_loop()` which fails in worker threads.

**Error**: `"There is no current event loop in thread 'asyncio_0'"`

**Evidence from Logs**:
- Multiple errors: `"Failed to send message: There is no current event loop in thread 'asyncio_0'"`
- Occurs in `display_message`, `display_goals`, and `prompt_user` methods
- All of these methods call `_schedule_coroutine()` which tries to get the event loop

**Current Flow**:
1. `workflow_service.py:186` calls `run_research_agent` via `asyncio.to_thread()`
2. This runs in a worker thread (no event loop)
3. Research agent calls `ui.display_message()`, `ui.display_goals()`, `ui.prompt_user()`
4. These methods call `_schedule_coroutine()` which tries `asyncio.get_running_loop()`
5. This fails because worker threads don't have a running event loop

**Current Code Logic**:
```python
def _get_main_loop(self) -> Optional[asyncio.AbstractEventLoop]:
    # If we have a stored reference, use it
    if self.main_loop is not None:
        try:
            if not self.main_loop.is_closed() and self.main_loop.is_running():
                return self.main_loop
        except RuntimeError:
            pass
    
    # Try to get the current event loop (only works in async context, not worker threads)
    try:
        loop = asyncio.get_running_loop()  # FAILS in worker threads
        ...
```

**Problem**: The check `self.main_loop.is_running()` might return `False` when called from a worker thread, even though the loop is running in the main thread. The code then falls through to `asyncio.get_running_loop()` which fails.

**Fix Required**: 
1. Better detection of the main loop from worker threads
2. Use `asyncio.run_coroutine_threadsafe()` with the stored `main_loop` reference even if `is_running()` check fails
3. Handle the case where the loop might not be running when checked from a different thread

---

### Issue 3: User Input Not Actually Waiting for Response

**Location**: `backend/app/services/websocket_ui.py:prompt_user()`

**Problem**: The `prompt_user()` method sends the prompt via WebSocket but immediately returns an empty string without waiting for user input.

**Current Implementation**:
```python
def prompt_user(self, prompt: str, choices: Optional[list] = None) -> str:
    """Request user input via WebSocket."""
    coro = self._send_user_prompt(prompt, choices)
    self._schedule_coroutine(coro)
    
    # For now, return empty string - in production, this would wait for response
    # This requires a more sophisticated async mechanism
    return ""
```

**Evidence**:
- In `research/agent.py:232`, it calls `amend = self.ui.prompt_user(...)` and expects a response
- The method currently returns `""` immediately
- No mechanism exists to wait for WebSocket response

**Required Flow**:
1. Send prompt to frontend via WebSocket
2. Wait for user response from frontend
3. Return the response string

**Fix Required**:
- Implement a mechanism to wait for user input via WebSocket
- This likely requires:
  - A queue or future to hold the response
  - A WebSocket message handler to receive user input
  - A timeout mechanism if user doesn't respond
  - Thread-safe coordination between the worker thread and the async event loop

---

### Issue 5: Missing Frontend UI Input Component

**Location**: `client/src/pages/ResearchAgentPage.tsx`

**Problem**: The frontend UI does NOT have any input field or mechanism for users to type and send their response when prompted.

**Current Implementation**:
```tsx
{researchAgentStatus.waitingForUser && (
  <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
    <p className="text-sm text-neutral-400 mb-4">
      等待用户输入...
    </p>
    {/* User input components will be added here */}
  </div>
)}
```

**Evidence**:
- The WebSocket hook receives `research:user_input_required` messages and updates state correctly (`useWebSocket.ts:142-149`)
- The state includes `userInputRequired` with `prompt` and `choices` data from the message
- However, the UI component only shows a placeholder message
- There is NO input field, textarea, choice buttons, or submit button
- There is NO way for users to actually provide their input

**Backend Endpoint**:
- `POST /api/research/user_input` exists (`backend/app/routes/research.py:17`) but only acknowledges receipt
- Does not actually deliver the input back to the waiting `prompt_user()` call

**Fix Required**:
1. Add UI components to `ResearchAgentPage.tsx`:
   - Display the prompt text from `userInputRequired.data.prompt`
   - Show choice buttons if `userInputRequired.data.choices` is provided
   - Add textarea for free-text input if no choices
   - Add submit button to send the response
2. Implement sending mechanism:
   - Use `sendMessage` from `useWebSocket` hook to send user input
   - Send message type: `research:user_input` with response data
   - Include batch_id and prompt_id if needed for matching
3. Update backend to handle user input:
   - WebSocket manager should receive `research:user_input` messages
   - Route the input back to the waiting `prompt_user()` call
   - Use the queue/future mechanism from Issue 3 fix

---

## Additional Issues

### Issue 4: File Watching Causing Reloads

**Evidence from Logs**:
```
WARNING: WatchFiles detected changes in 'app\websocket\_init.py', 'app\websocket\manager.py', 'app\services\websocket_ui.py', 'app\_init__.py', 'app\routes\_init__.py', 'app\routes\research.py'. Reloading...
```

**Impact**: Application reloads can disrupt existing asyncio event loops and WebSocketUI object state, potentially causing the issues above to manifest.

**Note**: This is likely a symptom rather than a root cause, but it could exacerbate the event loop issues.

---

## Files That Need Changes

1. **`backend/app/services/websocket_ui.py`**
   - Add `display_synthesized_goal()` method
   - Fix `_get_main_loop()` to properly detect main loop from worker threads
   - Fix `_schedule_coroutine()` to handle worker thread case
   - Implement actual waiting mechanism in `prompt_user()`

2. **`backend/app/websocket/manager.py`** (if needed)
   - May need to add user input response handling
   - May need to store pending prompts/requests

3. **`backend/app/routes/research.py`** (if needed)
   - May need endpoint to receive user input responses
   - May need to coordinate with WebSocketUI to deliver responses

4. **`backend/app/services/workflow_service.py`** (if needed)
   - May need to ensure main_loop is properly passed and maintained

---

## Recommended Fix Strategy

### Phase 1: Fix Missing Method and Event Loop Detection
1. Add `display_synthesized_goal()` method to `WebSocketUI`
2. Improve `_get_main_loop()` to use stored `main_loop` reference more reliably
3. Ensure `_schedule_coroutine()` always uses the stored main loop when available

### Phase 2: Implement User Input Waiting
1. Add a response queue or future mechanism to `WebSocketUI`
2. Modify `prompt_user()` to wait for response (with timeout)
3. Add WebSocket message handler to receive user input
4. Route user input responses back to waiting `prompt_user()` calls

### Phase 3: Testing and Validation
1. Test event loop detection from worker threads
2. Test user input flow end-to-end
3. Verify all UI methods work correctly
4. Test with file watching/reload scenarios

---

## Technical Notes

### Event Loop in Worker Threads

When code runs via `asyncio.to_thread()`, it executes in a separate thread that:
- Does NOT have an event loop running
- Cannot call `asyncio.get_running_loop()` (will raise RuntimeError)
- Must use `asyncio.run_coroutine_threadsafe()` to schedule coroutines on the main loop

### Thread Safety

The `_schedule_coroutine()` method is called from worker threads but needs to schedule coroutines on the main event loop. This requires:
- Proper thread-safe access to the main loop reference
- Using `asyncio.run_coroutine_threadsafe()` instead of directly awaiting
- Not blocking the worker thread while waiting for async operations

### User Input Coordination

To implement blocking user input:
- Need a way to wait for WebSocket message in a worker thread
- Could use a `threading.Event` or `queue.Queue` to block until response arrives
- WebSocket handler must be able to deliver response to the waiting thread
- Need unique request IDs to match responses to waiting calls

---

## Related Code References

- `research/agent.py:228-244` - Phase 1 goal display and user prompting
- `research/agent.py:271` - display_synthesized_goal call
- `research/agent.py:281` - prompt_user for plan confirmation
- `backend/app/services/workflow_service.py:179-180` - WebSocketUI initialization
- `backend/app/services/workflow_service.py:186` - Research agent run in thread

