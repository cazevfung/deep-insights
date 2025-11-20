# Bug Fix: Research Agent Running Status Not Ending

## Problem

In previous tests, the research report was generated successfully, but the research agent still showed a "running" status instead of "completed". This caused confusion about whether the research process had finished.

## Root Cause

The bug was in `backend/app/services/workflow_service.py`. When the research agent completed and the report was generated, the system would:

1. ✅ Send `phase4:report_ready` when Phase 4 completes
2. ✅ Send `workflow:complete` when the entire workflow finishes
3. ❌ **BUT** it did NOT send a clear `research:complete` signal to explicitly mark the research phase as finished

The frontend was likely waiting for a specific completion signal that never arrived, causing the agent to remain in "running" status.

## Solution

Added explicit `research:complete` WebSocket messages in three scenarios:

### 1. Normal Workflow Completion
**Location:** `workflow_service.py` lines 1885-1892

After the research agent finishes, now sends:
```python
await self.ws_manager.broadcast(batch_id, {
    "type": "research:complete",
    "batch_id": batch_id,
    "session_id": session_id,
    "status": "completed",
    "message": "研究完成",
})
```

### 2. Phase 4 Rerun Completion
**Location:** `workflow_service.py` lines 469-476

When Phase 4 is rerun and completes, now sends the same `research:complete` signal.

### 3. Phase 3 Step Rerun with Report Regeneration
**Location:** `workflow_service.py` lines 546-553

When a Phase 3 step is rerun and the report is regenerated, now sends the `research:complete` signal.

## Message Flow (After Fix)

```
Research Agent Execution
    ↓
Phase 0 → Phase 0.5 → Phase 1 → Phase 2 → Phase 3 → Phase 4
    ↓
phase4:report_ready (report generated)
    ↓
research:complete (NEW - explicitly marks research as done) ✨
    ↓
workflow:complete (entire workflow finished)
```

## Frontend Integration

The frontend should now listen for the `research:complete` message:

```typescript
{
  "type": "research:complete",
  "batch_id": string,
  "session_id": string,
  "status": "completed",
  "message": "研究完成"
}
```

When this message is received, the frontend should:
- Update the research agent status from "running" to "completed"
- Show a completion indicator
- Enable report download/export buttons
- Stop any loading animations

## Testing

To verify the fix:

1. Start a new research workflow
2. Let it complete all phases including Phase 4 (report generation)
3. Check that the research agent status changes from "running" to "completed" immediately after the report is generated
4. Also test phase reruns and step reruns to ensure they also properly signal completion

## Related Files

- `backend/app/services/workflow_service.py` - Main fix location
- `backend/app/services/websocket_ui.py` - Sends `phase4:report_ready`
- `research/agent.py` - Research agent execution and session metadata

## Date

November 10, 2025

