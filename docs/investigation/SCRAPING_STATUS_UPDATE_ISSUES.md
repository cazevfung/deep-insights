# Investigation: Scraping Status Update Issues

## Problem Summary
The scraping page on localhost:3000 cannot successfully identify success and failures, rendering:
- 0 success and 0 failures displayed
- All scraping items showing as "in progress"
- Scraping process unable to stop (because completion/failure detection doesn't work)

## Root Causes Identified

### Issue 1: Status Format Mismatch (Backend vs Frontend)

**Location:** 
- Backend: `backend/app/services/progress_service.py` (line 160, 193)
- Frontend: `client/src/stores/workflowStore.ts` (line 290)

**Problem:**
- Backend sends status values using **snake_case**: `'in_progress'`, `'completed'`, `'failed'`
- Frontend expects **kebab-case** for in-progress: `'in-progress'`, `'completed'`, `'failed'`

**Evidence:**
- Backend `progress_service.py` line 160: `'status': status` where `status` can be `'in_progress'`
- Backend `progress_service.py` line 193: Items sent with `'status': state.get('status', 'pending')` where status is stored as `'in_progress'`
- Frontend `workflowStore.ts` line 290: Filters for `i.status === 'in-progress'` (kebab-case)

**Impact:**
- Items that are in progress will never be counted correctly because `'in_progress' !== 'in-progress'`
- The frontend filter `items.filter((i) => i.status === 'in-progress')` will return 0 items when backend sends `'in_progress'`

---

### Issue 2: Missing Status Update for Successful Links

**Location:**
- Backend: `backend/app/services/workflow_service.py` (lines 258-321)

**Problem:**
When processing `scraping:complete_link` messages from scrapers:
- **For successful links** (`status: 'success'`): Only queues `update_link_progress` action, but **never queues** `update_link_status` action
- **For failed links** (`status: 'failed'`): Queues both `update_link_progress` AND `update_link_status` actions

**Evidence:**
```python
# workflow_service.py lines 258-321
elif message_type == 'scraping:complete_link':
    status = message.get('status', 'unknown')
    if status == 'success':
        stage = 'completed'
        progress = 100.0
        # ... queues update_link_progress only (line 289-304)
        # ❌ NO update_link_status call for success!
    else:
        stage = 'failed'
        progress = 0.0
        # ... queues update_link_progress (line 289-304)
        # ✅ Also queues update_link_status for failed (line 307-320)
        if status == 'failed':
            status_message = {
                'action': 'update_link_status',  # Only for failed!
                ...
            }
```

**Impact:**
- Successful links never receive a `scraping:item_update` WebSocket message
- Frontend never knows when a link has completed successfully
- The `scraping:item_update` handler in `useWebSocket.ts` (line 261-275) is never called for successful links
- Frontend counts remain at 0 for completed items

---

### Issue 3: Status Values in Batch Status Messages

**Location:**
- Backend: `backend/app/services/progress_service.py` (line 193)
- Frontend: `client/src/hooks/useWebSocket.ts` (line 231-238)

**Problem:**
The `scraping:status` batch update message includes items with status values in snake_case (`'in_progress'`), but the frontend expects kebab-case.

**Evidence:**
- Backend `progress_service.py` line 193: `'status': state.get('status', 'pending')` where status is stored as `'in_progress'`
- Frontend `useWebSocket.ts` line 237: Receives `items: data.items || []` and forwards to `updateScrapingStatus`
- Frontend `workflowStore.ts` line 290: Filters for `'in-progress'` (kebab-case), so items with `'in_progress'` are not counted

**Impact:**
- Even when batch status updates are sent, the status format mismatch prevents correct counting
- Items stuck in `'in_progress'` state are never recognized as completed/failed

---

## Data Flow Analysis

### Expected Flow for Successful Link:
1. Scraper calls `progress_callback` with `type: 'scraping:complete_link', status: 'success'`
2. `workflow_direct.py` sends message to queue
3. `workflow_service.py` processes message
4. **Should:** Queue `update_link_status` with `status: 'completed'`
5. **Actually:** Only queues `update_link_progress`, never `update_link_status`
6. `progress_service.update_link_status()` is never called for successful links
7. No `scraping:item_update` WebSocket message is sent
8. Frontend never receives completion notification

### Expected Flow for Failed Link:
1. Scraper calls `progress_callback` with `type: 'scraping:complete_link', status: 'failed'`
2. `workflow_direct.py` sends message to queue
3. `workflow_service.py` processes message
4. Queues `update_link_progress` AND `update_link_status` with `status: 'failed'`
5. `progress_service.update_link_status()` is called
6. `scraping:item_update` WebSocket message is sent
7. Frontend receives notification (but may have status format issue)

---

## Additional Findings

### Status Format Inconsistency
The codebase uses different status formats in different places:
- `scraping_service.py` line 167: Uses `'in_progress'` (snake_case)
- `scraping_service.py` line 258: Uses `'completed'` (no underscore)
- `scraping_service.py` line 268: Uses `'failed'` (no underscore)
- Frontend `workflowStore.ts` line 6: TypeScript interface expects `'in-progress'` (kebab-case)
- Frontend `workflowStore.ts` line 290: Filters for `'in-progress'` OR `'pending'`

### Note on Direct Scraping Service
The `scraping_service.py` (lines 256-271) DOES call `update_link_status` for both success and failure when scraping directly. However, when scraping is done through the workflow system (via `workflow_direct.py`), the workflow service doesn't properly forward status updates for successful links.

---

## Summary

The main issues are:

1. **Status format mismatch**: Backend sends `'in_progress'` but frontend expects `'in-progress'`
2. **Missing status updates for successful links**: Only failed links get `scraping:item_update` messages
3. **Inconsistent status handling**: Different code paths handle status updates differently

These issues combine to prevent the frontend from:
- Detecting when links complete successfully
- Counting completed/failed items correctly
- Knowing when scraping is done (all items remain in "in progress" state)

---

## Files Involved

### Backend:
- `backend/app/services/workflow_service.py` (lines 258-321)
- `backend/app/services/progress_service.py` (lines 110-214, 169-214)
- `backend/lib/workflow_direct.py` (lines 180-223)
- `backend/app/services/scraping_service.py` (lines 256-271)

### Frontend:
- `client/src/hooks/useWebSocket.ts` (lines 231-276)
- `client/src/stores/workflowStore.ts` (lines 264-301)
- `client/src/pages/ScrapingProgressPage.tsx` (lines 115-150)

---

## Recommended Fixes (Not Implemented Per Request)

1. **Fix status format mismatch:**
   - Convert backend status values from snake_case to kebab-case before sending
   - OR update frontend to accept both formats
   - Ensure consistent format: `'in-progress'`, `'completed'`, `'failed'`

2. **Fix missing status updates for successful links:**
   - In `workflow_service.py`, when processing `scraping:complete_link` with `status: 'success'`, also queue `update_link_status` with `status: 'completed'`

3. **Standardize status handling:**
   - Ensure all status updates go through `update_link_status` for final status changes
   - Use `update_link_progress` only for progress updates during processing




