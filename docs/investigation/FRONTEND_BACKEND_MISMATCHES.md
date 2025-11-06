# Frontend-Backend Interaction Issues

## Summary

This document identifies all mismatches, missing implementations, and incomplete integrations between the frontend and backend.

---

## WebSocket Message Type Mismatches

### Messages Backend Sends vs Frontend Handles

| Backend Sends | Frontend Handles | Status |
|--------------|------------------|--------|
| `workflow:progress` | ✅ `workflow:progress` | ✅ Match |
| `scraping:status` | ✅ `scraping:status` | ✅ Match |
| `scraping:item_progress` | ✅ `scraping:item_progress` | ✅ Match |
| `scraping:item_update` | ✅ `scraping:item_update` | ✅ Match |
| `scraping:cancelled` | ✅ `scraping:cancelled` | ✅ Match |
| `phase:changed` | ✅ `research:phase_change` | ⚠️ **Name Mismatch** |
| `research:stream_token` | ✅ `research:stream_token` | ✅ Match |
| `research:user_input_required` | ✅ `research:user_input_required` | ✅ Match (but no UI) |
| `research:goals` | ❌ **NOT HANDLED** | ❌ **Missing** |
| `research:plan_confirmation` | ❌ **NOT HANDLED** | ❌ **Missing** |
| `workflow:complete` | ❌ **NOT HANDLED** | ❌ **Missing** |
| `phase4:report_ready` | ✅ `phase4:report_ready` | ⚠️ **Handler exists but backend doesn't send** |
| `error` | ✅ `error` | ✅ Match |
| `connected` | ❌ **NOT HANDLED** | ⚠️ **Optional** |
| `pong` | ❌ **NOT HANDLED** | ⚠️ **Optional** |

### Issue 1: Phase Change Message Name Mismatch

**Backend**: `websocket_ui.py:162` sends `"type": "phase:changed"`
**Frontend**: `useWebSocket.ts:123` handles `case 'research:phase_change'`

**Problem**: The frontend will never receive phase change notifications because the message type names don't match.

**Fix Required**: Either:
- Change backend to send `"research:phase_change"` OR
- Change frontend to handle `"phase:changed"`

---

### Issue 2: Missing Handler for `research:goals`

**Backend**: `websocket_ui.py:204` sends `"type": "research:goals"` with goals list
**Frontend**: No handler exists in `useWebSocket.ts`

**Problem**: When research agent calls `display_goals()`, the frontend receives the message but doesn't process it. Users never see the research goals.

**Evidence**:
- `research/agent.py:228` calls `self.ui.display_goals(goals)`
- `websocket_ui.py:195-208` sends `research:goals` message
- `useWebSocket.ts` has no case for `research:goals`

**Fix Required**: Add handler in `useWebSocket.ts` to update state with goals data.

---

### Issue 3: Missing Handler for `research:plan_confirmation`

**Backend**: `websocket_ui.py:223` sends `"type": "research:plan_confirmation"` with plan data
**Frontend**: No handler exists in `useWebSocket.ts`

**Problem**: When research agent calls `confirm_plan()`, the frontend receives the message but doesn't process it. Users never see the research plan for confirmation.

**Evidence**:
- `research/agent.py:278` calls `self.ui.display_plan(plan)` (but this method doesn't exist in WebSocketUI)
- `websocket_ui.py:210-227` sends `research:plan_confirmation` message
- `useWebSocket.ts` has no case for `research:plan_confirmation`

**Fix Required**: 
1. Add `display_plan()` method to `WebSocketUI` (currently missing)
2. Add handler in `useWebSocket.ts` to update state with plan data
3. Add UI component to display plan and allow confirmation

---

### Issue 4: Missing Handler for `workflow:complete`

**Backend**: `workflow_service.py:197` sends `"type": "workflow:complete"` with result
**Frontend**: No handler exists in `useWebSocket.ts`

**Problem**: When workflow completes, the frontend doesn't receive the completion notification.

**Fix Required**: Add handler in `useWebSocket.ts` to update state with completion status.

---

### Issue 4b: Missing Backend Sender for `phase4:report_ready`

**Backend**: No code sends `phase4:report_ready` message
**Frontend**: `useWebSocket.ts:156` handles `phase4:report_ready` message

**Problem**: The frontend expects a `phase4:report_ready` message when the final report is ready, but the backend never sends it. The `display_report()` method is called but doesn't send a WebSocket message.

**Evidence**:
- `research/agent.py:342` calls `self.ui.display_report(report, str(report_file))`
- `WebSocketUI` doesn't have `display_report()` method
- `useWebSocket.ts:156` handles `phase4:report_ready` but it's never sent

**Fix Required**: 
1. Add `display_report()` method to `WebSocketUI`
2. Send `phase4:report_ready` message with report content

---

### Issue 5: Missing Handler for `workflow:complete`

**Backend**: `workflow_service.py:197` sends `"type": "workflow:complete"` with result
**Frontend**: No handler exists in `useWebSocket.ts`

**Problem**: When workflow completes, the frontend doesn't receive the completion notification.

**Fix Required**: Add handler in `useWebSocket.ts` to update state with completion status.

---

## Missing WebSocketUI Methods

### Methods Called by Research Agent but Not Implemented

| Method Called | Location | Status |
|--------------|----------|--------|
| `display_synthesized_goal()` | `research/agent.py:271` | ❌ **Missing** |
| `display_plan()` | `research/agent.py:278` | ❌ **Missing** |
| `display_report()` | `research/agent.py:342` | ❌ **Missing** |

**Evidence**:
- `research/agent.py:271` calls `self.ui.display_synthesized_goal(synthesized)`
- `research/agent.py:278` calls `self.ui.display_plan(plan)`
- `websocket_ui.py` has neither method
- `mock_interface.py` and `console_interface.py` have both methods

**Fix Required**: 
1. Add `display_synthesized_goal()` to `WebSocketUI`
2. Add `display_plan()` to `WebSocketUI` (or use `confirm_plan()` which already exists)
3. Add `display_report()` to `WebSocketUI`

**Note**: `display_report()` is called with the final report content. The frontend already has a `FinalReportPage` that displays `finalReport` from state, but there's no WebSocket message type to send the report. The `phase4:report_ready` message exists but may not be used by `display_report()`.

---

## API Endpoint Mismatches

### Endpoints Backend Provides vs Frontend Uses

| Backend Endpoint | Frontend Uses | Status |
|-----------------|---------------|--------|
| `POST /api/links/format` | ✅ `apiService.formatLinks()` | ✅ Match |
| `POST /api/workflow/start` | ✅ `apiService.startWorkflow()` | ✅ Match |
| `GET /api/workflow/status/{workflow_id}` | ✅ `apiService.getWorkflowStatus()` | ✅ Match |
| `POST /api/workflow/cancel` | ✅ `apiService.cancelWorkflow()` | ✅ Match |
| `GET /api/sessions/{session_id}` | ✅ `apiService.getSession()` | ✅ Match |
| `POST /api/research/user_input` | ❌ **NOT USED** | ⚠️ **Exists but unused** |

### Issue 6: User Input Endpoint Not Used

**Backend**: `POST /api/research/user_input` exists in `research.py:17`
**Frontend**: No code calls this endpoint

**Problem**: The endpoint exists but is never called. User input should be sent via WebSocket, not HTTP POST.

**Note**: This is actually correct - user input should be sent via WebSocket (`research:user_input`), but the WebSocket handler doesn't process it either.

---

## Frontend State Management Issues

### State Fields Expected vs Provided

| State Field | Backend Provides | Frontend Uses | Status |
|------------|------------------|---------------|--------|
| `researchAgentStatus.phase` | ✅ Via `research:phase_change` | ✅ Used | ✅ Match |
| `researchAgentStatus.streamBuffer` | ✅ Via `research:stream_token` | ✅ Used | ✅ Match |
| `researchAgentStatus.waitingForUser` | ✅ Via `research:user_input_required` | ✅ Used | ✅ Match |
| `researchAgentStatus.userInputRequired` | ✅ Via `research:user_input_required` | ✅ Used | ✅ Match |
| `researchAgentStatus.goals` | ❌ **NOT PROVIDED** | ❌ **NOT IN STATE** | ❌ **Missing** |
| `researchAgentStatus.plan` | ❌ **NOT PROVIDED** | ❌ **NOT IN STATE** | ❌ **Missing** |
| `researchAgentStatus.synthesizedGoal` | ❌ **NOT PROVIDED** | ❌ **NOT IN STATE** | ❌ **Missing** |

### Issue 7: Missing State for Goals

**Problem**: When `research:goals` message arrives, there's no state field to store it.

**Fix Required**: 
1. Add `goals` field to `researchAgentStatus` in `workflowStore.ts`
2. Add action to update goals
3. Handle `research:goals` message in `useWebSocket.ts`

---

### Issue 8: Missing State for Plan

**Problem**: When `research:plan_confirmation` message arrives, there's no state field to store it.

**Fix Required**: 
1. Add `plan` field to `researchAgentStatus` in `workflowStore.ts`
2. Add action to update plan
3. Handle `research:plan_confirmation` message in `useWebSocket.ts`

---

### Issue 9: Missing State for Synthesized Goal

**Problem**: When `display_synthesized_goal()` is called, there's no state field to store it.

**Fix Required**: 
1. Add `synthesizedGoal` field to `researchAgentStatus` in `workflowStore.ts`
2. Add action to update synthesized goal
3. Add WebSocket message type for synthesized goal (or use existing mechanism)
4. Add `display_synthesized_goal()` method to `WebSocketUI`

---

## UI Component Issues

### Components Missing Data Display

| Component | Expected Data | Status |
|-----------|--------------|--------|
| `ResearchAgentPage` | Goals list | ❌ **No component** |
| `ResearchAgentPage` | Plan display | ❌ **No component** |
| `ResearchAgentPage` | Synthesized goal | ❌ **No component** |
| `ResearchAgentPage` | User input field | ❌ **No component** |
| `Phase3SessionPage` | Phase 3 steps | ✅ **Has component** |
| `FinalReportPage` | Final report | ✅ **Has component** |

### Issue 10: Missing Goals Display Component

**Problem**: Even if goals data is received, there's no UI component to display them.

**Fix Required**: Add goals display component to `ResearchAgentPage.tsx`

---

### Issue 11: Missing Plan Display Component

**Problem**: Even if plan data is received, there's no UI component to display it.

**Fix Required**: Add plan display component to `ResearchAgentPage.tsx`

---

### Issue 12: Missing Synthesized Goal Display Component

**Problem**: Even if synthesized goal data is received, there's no UI component to display it.

**Fix Required**: Add synthesized goal display component to `ResearchAgentPage.tsx`

---

## User Input Flow Issues

### Complete User Input Flow Analysis

**Backend Flow**:
1. `research/agent.py:232` calls `self.ui.prompt_user(...)`
2. `websocket_ui.py:170` calls `_schedule_coroutine(_send_user_prompt(...))`
3. `websocket_ui.py:184` sends `research:user_input_required` message
4. `websocket_ui.py:182` returns `""` immediately (doesn't wait)

**Frontend Flow**:
1. `useWebSocket.ts:142` receives `research:user_input_required`
2. `useWebSocket.ts:144` updates state with `waitingForUser: true`
3. `ResearchAgentPage.tsx:23` shows placeholder div (no input field)
4. **USER CANNOT PROVIDE INPUT** ❌

**Backend Receipt**:
1. User input should be sent via WebSocket as `research:user_input`
2. `websocket/manager.py:100` has handler but it's just a pass
3. `websocket_ui.py` has no mechanism to receive input and deliver to waiting `prompt_user()`

**Complete Flow Missing**:
- ❌ No UI input field
- ❌ No send mechanism from frontend
- ❌ No receipt mechanism in backend
- ❌ No delivery mechanism to waiting `prompt_user()`

---

## Summary of All Issues

### Critical (Blocks Functionality)

1. **Missing `display_synthesized_goal()` method** - Causes AttributeError
2. **Missing `display_plan()` method** - Causes AttributeError (if called)
3. **Missing `display_report()` method** - Causes AttributeError
4. **Phase change message name mismatch** - Phase changes never received
5. **Missing handler for `research:goals`** - Goals never displayed
6. **Missing handler for `research:plan_confirmation`** - Plan never displayed
7. **Missing handler for `workflow:complete`** - Completion never notified
8. **Missing backend sender for `phase4:report_ready`** - Report never sent
9. **Missing user input UI component** - Users cannot provide input
10. **Missing user input send mechanism** - Input cannot be sent
11. **Missing user input receipt mechanism** - Input cannot be received
12. **Missing user input delivery mechanism** - Input cannot reach waiting code

### Important (Affects User Experience)

13. **Missing state fields for goals** - Data cannot be stored
14. **Missing state fields for plan** - Data cannot be stored
15. **Missing state fields for synthesized goal** - Data cannot be stored
16. **Missing goals display component** - Data cannot be shown
17. **Missing plan display component** - Data cannot be shown
18. **Missing synthesized goal display component** - Data cannot be shown

### Minor (Optional Features)

17. **Unused `POST /api/research/user_input` endpoint** - Should use WebSocket instead
18. **Missing handler for `connected` message** - Optional
19. **Missing handler for `pong` message** - Optional

---

## Priority Fix Order

### Phase 1: Critical Backend Fixes
1. Add `display_synthesized_goal()` method to `WebSocketUI`
2. Add `display_plan()` method to `WebSocketUI` (or fix `confirm_plan()`)
3. Fix phase change message name mismatch
4. Fix event loop detection in `_schedule_coroutine()`

### Phase 2: Critical Frontend Fixes
5. Add handler for `research:goals` message
6. Add handler for `research:plan_confirmation` message
7. Add handler for `workflow:complete` message
8. Add state fields for goals, plan, synthesized goal
9. Add user input UI component
10. Add user input send mechanism

### Phase 3: Backend User Input Flow
11. Add user input receipt mechanism in WebSocket manager
12. Add user input delivery mechanism to `prompt_user()`
13. Implement waiting mechanism with timeout

### Phase 4: UI Components
14. Add goals display component
15. Add plan display component
16. Add synthesized goal display component

---

## Related Files

### Backend Files Needing Changes
- `backend/app/services/websocket_ui.py` - Add missing methods, fix event loop
- `backend/app/websocket/manager.py` - Add user input handling
- `backend/app/services/workflow_service.py` - Verify message types

### Frontend Files Needing Changes
- `client/src/hooks/useWebSocket.ts` - Add missing handlers
- `client/src/stores/workflowStore.ts` - Add missing state fields
- `client/src/pages/ResearchAgentPage.tsx` - Add missing UI components

