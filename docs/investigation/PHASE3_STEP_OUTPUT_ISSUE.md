# Phase 3 Step Output Issue

## Problem

**Phase 3 step JSON outputs are NOT sent to the frontend in real time.**

### Current Flow

1. **Phase 3 executes steps** (`phase3_execute.py:102-165`)
   - Each step produces JSON findings
   - Calls `progress_tracker.complete_step(step_id, findings)` with JSON results

2. **ProgressTracker notifies callbacks** (`progress_tracker.py:67-100`)
   - `complete_step()` calls `_notify_callbacks(status)`
   - Status includes `findings` (the JSON output)

3. **UI callback registered** (`research/agent.py:288`)
   - `progress_tracker.add_callback(self.ui.display_progress)`
   - This callback is called when step completes

4. **But `display_progress()` only sends progress** (`websocket_ui.py:107-117`)
   - Only sends progress percentage message
   - Does NOT send the step JSON findings
   - Step results are lost!

5. **Frontend expects `phase3:step_complete`** (`useWebSocket.ts:189`)
   - Handler exists: `addPhase3Step(data.stepData)`
   - UI component ready: `Phase3SessionPage.tsx`
   - But message is never sent!

### Evidence

**Backend sends:**
- ❌ `phase3:step_complete` - **NEVER SENT**

**Frontend expects:**
- ✅ `phase3:step_complete` - Handler exists but never receives data

**Result:**
- Step JSON outputs are generated but never displayed
- UI shows "暂无步骤数据" (No step data)
- Users can't see step results in real time

---

## Solution Required

### Option 1: Enhance `display_progress()` to send step results

**Location**: `backend/app/services/websocket_ui.py`

**Change**: Modify `display_progress()` to detect when status contains step findings and send `phase3:step_complete` message.

**Pros**: 
- Reuses existing callback mechanism
- Minimal changes

**Cons**:
- Mixes progress updates with step results
- May send multiple messages

### Option 2: Add separate method for step completion

**Location**: `backend/app/services/websocket_ui.py`

**Change**: Add `display_step_complete(step_id, findings)` method and call it from ProgressTracker callback.

**Pros**:
- Clear separation of concerns
- Cleaner architecture

**Cons**:
- Requires modifying ProgressTracker callback mechanism

### Option 3: Add step completion callback in WebSocketUI

**Location**: `backend/app/services/websocket_ui.py` and `research/progress_tracker.py`

**Change**: 
- Add `display_step_complete()` method to WebSocketUI
- Register it as a separate callback in ProgressTracker
- Send `phase3:step_complete` message with step data

**Pros**:
- Best separation of concerns
- Doesn't interfere with progress updates
- Can send step results immediately when available

**Cons**:
- Requires modifying both files

---

## Recommended Solution: Option 3

Add a dedicated method to send step results when they're available.

### Implementation Steps

1. **Add `display_step_complete()` method to `WebSocketUI`**
   ```python
   def display_step_complete(self, step_id: int, findings: dict, insights: str, confidence: float):
       """Display step completion with JSON results."""
       coro = self._send_step_complete(step_id, findings, insights, confidence)
       self._schedule_coroutine(coro)
   
   async def _send_step_complete(self, step_id: int, findings: dict, insights: str, confidence: float):
       """Async helper to send step completion."""
       try:
           await self.ws_manager.broadcast(self.batch_id, {
               "type": "phase3:step_complete",
               "stepData": {
                   "step_id": step_id,
                   "findings": findings,
                   "insights": insights,
                   "confidence": confidence,
                   "timestamp": datetime.now().isoformat(),
               }
           })
       except Exception as e:
           logger.error(f"Failed to broadcast step complete: {e}")
   ```

2. **Register callback in `research/agent.py`**
   ```python
   progress_tracker.add_callback(self.ui.display_progress)
   progress_tracker.add_step_complete_callback(self.ui.display_step_complete)  # New
   ```

3. **Modify `ProgressTracker` to support step completion callbacks**
   ```python
   def __init__(self, total_steps: int):
       # ... existing code ...
       self.step_complete_callbacks: List[Callable] = []  # New
   
   def add_step_complete_callback(self, callback: Callable):
       """Add callback for step completion with findings."""
       self.step_complete_callbacks.append(callback)
   
   def complete_step(self, step_id: int, findings: Optional[Dict] = None):
       # ... existing code ...
       
       # Notify step completion callbacks with findings
       if findings:
           step_data = {
               "step_id": step_id,
               "findings": findings.get("findings", {}),
               "insights": findings.get("insights", ""),
               "confidence": findings.get("confidence", 0.0),
               "timestamp": end_time.isoformat(),
           }
           for callback in self.step_complete_callbacks:
               try:
                   callback(step_data)
               except Exception as e:
                   logger.warning(f"Step complete callback error: {str(e)}")
   ```

---

## Impact

**Current**: Step JSON outputs are generated but never displayed in UI.

**After Fix**: Step JSON outputs are sent to frontend in real time and displayed immediately after each step completes.

**User Experience**: Users can see step results as they complete, not just at the end.

---

## Verification

After implementation:
1. ✅ Step JSON is sent via `phase3:step_complete` message
2. ✅ Frontend receives message and updates state
3. ✅ UI displays step results in real time
4. ✅ Each step shows: summary, insights, confidence, findings


