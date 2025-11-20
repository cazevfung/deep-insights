# Plan: Total Scraping Processes Calculation and Tracking

## Overview

Create a system to calculate the total number of scraping processes at the beginning of the workflow (based on user-input links) and use this total consistently for progress tracking in both backend and frontend.

## Current State Analysis

### What Exists Now:
1. **Link Context Loading** (`workflow_service.py::_load_link_context`)
   - Loads links from `TestLinksLoader`
   - Calculates expected processes based on link types
   - Pre-registers processes in `ProgressService`
   - Stores in `self.link_context[batch_id]`

2. **ProgressService** (`progress_service.py`)
   - Has `expected_totals: Dict[str, int]` to store total counts
   - Uses `initialize_expected_links()` to pre-register processes
   - Tracks link states per batch

3. **Process Calculation Logic**
   - YouTube: 2 processes per link (transcript + comments)
   - Bilibili: 2 processes per link (transcript + comments)
   - Reddit: 1 process per link
   - Article: 1 process per link

### Current Issues:
1. Total count is calculated but not explicitly exposed to frontend early
2. Frontend may not receive total count until first status update
3. No single source of truth for total count calculation
4. Total count calculation logic is embedded in `_load_link_context`

---

## Plan: Total Processes Tracking System

### Phase 1: Centralize Total Count Calculation

#### 1.1 Create Total Count Calculator Function
**Location**: `backend/app/services/workflow_service.py` or new utility module

**Purpose**: Single function to calculate total processes from links

**Function Signature**:
```python
def calculate_total_scraping_processes(links_by_type: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Calculate total number of scraping processes from links.
    
    Args:
        links_by_type: Dict mapping link_type -> list of {id, url} dicts
            Example: {
                'youtube': [{'id': 'yt1', 'url': '...'}, ...],
                'bilibili': [{'id': 'bili1', 'url': '...'}, ...],
                'reddit': [{'id': 'rd1', 'url': '...'}, ...],
                'article': [{'id': 'art1', 'url': '...'}, ...]
            }
    
    Returns:
        Dict with:
            - total_processes: int (total count)
            - total_links: int (total link count)
            - breakdown: Dict[str, int] (processes per type)
            - link_breakdown: Dict[str, int] (links per type)
            - process_mapping: List[Dict] (detailed process list)
    """
```

**Calculation Logic**:
```python
PROCESSES_PER_LINK_TYPE = {
    'youtube': 2,      # transcript + comments
    'bilibili': 2,    # transcript + comments
    'reddit': 1,
    'article': 1
}

# Calculate:
total_links = sum(len(links) for links in links_by_type.values())
total_processes = sum(
    len(links) * PROCESSES_PER_LINK_TYPE.get(link_type, 1)
    for link_type, links in links_by_type.items()
)
```

**Benefits**:
- Single source of truth for calculation
- Reusable across different entry points
- Easy to test and validate
- Can be called before workflow starts

#### 1.2 Store Total Count in WorkflowService
**Location**: `WorkflowService` class

**New Attribute**:
```python
self.batch_totals: Dict[str, Dict[str, Any]] = {}
# Maps batch_id -> {
#     'total_processes': int,
#     'total_links': int,
#     'breakdown': Dict[str, int],
#     'calculated_at': datetime,
#     'source': 'user_input' | 'test_links_loader'
# }
```

**When to Calculate**:
- **Option A**: When workflow starts (in `run_workflow()` before `_load_link_context`)
- **Option B**: When links are submitted (in link submission endpoint)
- **Option C**: Both - calculate early, validate later

**Recommended**: Option C - Calculate as early as possible (when links are submitted), validate during `_load_link_context`

---

### Phase 2: Expose Total Count to Frontend

#### 2.1 Create Initial Batch Status Message
**Location**: `workflow_service.py::run_workflow()` or `_load_link_context()`

**When to Send**: Immediately after calculating total count, before scraping starts

**Message Format**:
```python
{
    'type': 'batch:initialized',
    'batch_id': str,
    'total_processes': int,        # Total scraping processes
    'total_links': int,             # Total links
    'breakdown': {                  # Processes per link type
        'youtube': int,
        'bilibili': int,
        'reddit': int,
        'article': int
    },
    'link_breakdown': {             # Links per type
        'youtube': int,
        'bilibili': int,
        'reddit': int,
        'article': int
    },
    'timestamp': str,               # ISO format
    'message': '已初始化批次，共 {total_processes} 个抓取任务'
}
```

**Send Via**: `await self.ws_manager.broadcast(batch_id, message)`

#### 2.2 Include Total in All Batch Status Updates
**Location**: `progress_service.py::_update_batch_status()`

**Modify**: Ensure all batch status messages include `total_processes` field

**Current Message Format** (enhance):
```python
{
    'type': 'batch:status',
    'batch_id': str,
    'total_processes': int,        # Always include
    'completed': int,
    'failed': int,
    'pending': int,
    'in_progress': int,
    'progress_percentage': float,  # calculated: (completed + failed) / total_processes * 100
    'status': 'scraping' | 'completed' | 'failed',
    'timestamp': str
}
```

#### 2.3 Create API Endpoint for Total Count
**Location**: `backend/app/routes/workflow.py` or `session.py`

**Endpoint**: `GET /api/batch/{batch_id}/total`

**Response**:
```python
{
    'batch_id': str,
    'total_processes': int,
    'total_links': int,
    'breakdown': Dict[str, int],
    'calculated_at': str,
    'status': 'calculated' | 'not_found'
}
```

**Use Case**: Frontend can fetch total count if missed WebSocket message

---

### Phase 3: Frontend Integration

#### 3.1 Store Total Count in Frontend State
**Location**: Frontend state management (React context/state)

**State Structure**:
```typescript
interface BatchState {
  batchId: string;
  totalProcesses: number | null;      // Set from batch:initialized
  totalLinks: number | null;
  breakdown: {
    youtube: number;
    bilibili: number;
    reddit: number;
    article: number;
  } | null;
  completed: number;
  failed: number;
  pending: number;
  inProgress: number;
  progressPercentage: number;         // Calculated: (completed + failed) / totalProcesses * 100
}
```

**Initialization**:
- Set `totalProcesses` to `null` initially
- Update when `batch:initialized` message received
- Fallback: Fetch from API endpoint if WebSocket message missed

#### 3.2 Progress Calculation
**Location**: Frontend progress calculation logic

**Formula**:
```typescript
const progressPercentage = totalProcesses 
  ? ((completed + failed) / totalProcesses) * 100 
  : 0;
```

**Display**:
- Progress bar: `{completed + failed} / {totalProcesses}`
- Percentage: `{progressPercentage.toFixed(1)}%`
- Breakdown by type: Show counts per link type

#### 3.3 Handle Missing Total Count
**Scenarios**:
1. WebSocket connection established after `batch:initialized` sent
2. Frontend loads after workflow started
3. WebSocket reconnection

**Solutions**:
1. **Poll API Endpoint**: Periodically fetch `/api/batch/{batch_id}/total` until received
2. **Request on Connect**: When WebSocket connects, request batch status
3. **Store in Session**: Backend stores total in session, frontend can fetch anytime

---

### Phase 4: Validation and Consistency

#### 4.1 Validate Total Count During Workflow
**Location**: `workflow_service.py::_load_link_context()`

**Validation Logic**:
```python
# After calculating expected processes
calculated_total = len(all_expected_processes)

# Check against stored total (if exists)
if batch_id in self.batch_totals:
    stored_total = self.batch_totals[batch_id]['total_processes']
    if calculated_total != stored_total:
        logger.warning(
            f"Total count mismatch: stored={stored_total}, "
            f"calculated={calculated_total}"
        )
        # Use calculated (more recent) but log warning
        self.batch_totals[batch_id]['total_processes'] = calculated_total
        self.batch_totals[batch_id]['validation_warning'] = True
```

#### 4.2 Ensure ProgressService Uses Correct Total
**Location**: `progress_service.py`

**Current**: Uses `expected_totals[batch_id]` set by `initialize_expected_links()`

**Enhancement**: 
- Verify `expected_totals[batch_id]` matches `batch_totals[batch_id]['total_processes']`
- Log warning if mismatch
- Use `batch_totals` as source of truth if available

#### 4.3 Track Total Count Changes
**Location**: Debug logging

**Track**:
- When total is calculated
- When total is sent to frontend
- When total is validated
- Any mismatches or corrections

---

### Phase 5: Entry Points and User Input

#### 5.1 Link Submission Endpoint
**Location**: `backend/app/routes/links.py` or `workflow.py`

**Current Flow**:
1. User submits links via API
2. Links saved to `TestLinksLoader` format
3. Workflow starts with batch_id

**Enhancement**:
1. User submits links via API
2. **Calculate total processes immediately**
3. Store total in `WorkflowService.batch_totals`
4. Send `batch:initialized` message to frontend
5. Save links to `TestLinksLoader` format
6. Workflow starts with batch_id

**API Endpoint**: `POST /api/links/submit`

**Request**:
```python
{
    'links': [
        {'type': 'youtube', 'url': '...', 'id': '...'},
        {'type': 'bilibili', 'url': '...', 'id': '...'},
        ...
    ]
}
```

**Response**:
```python
{
    'batch_id': str,
    'total_processes': int,
    'total_links': int,
    'breakdown': Dict[str, int],
    'status': 'submitted'
}
```

#### 5.2 TestLinksLoader Integration
**Location**: `tests/test_links_loader.py`

**Enhancement**: Add method to calculate total processes

```python
def get_total_processes(self) -> Dict[str, Any]:
    """
    Calculate total processes from loaded links.
    
    Returns:
        Dict with total_processes, total_links, breakdown
    """
```

**Use Case**: When workflow loads from existing test links file

---

### Phase 6: Error Handling and Edge Cases

#### 6.1 Handle Empty Links
**Scenario**: User submits no links or all links filtered out

**Behavior**:
- Calculate total = 0
- Send `batch:initialized` with `total_processes: 0`
- Frontend shows "No links to process"
- Workflow exits early with appropriate message

#### 6.2 Handle Link Type Changes
**Scenario**: Links modified after initial calculation

**Behavior**:
- Recalculate total when links change
- Send updated `batch:initialized` message
- Frontend updates total count
- Log warning about mid-workflow changes

#### 6.3 Handle Cancellation
**Scenario**: Workflow cancelled before all processes complete

**Behavior**:
- Total count remains unchanged
- Progress shows: `{completed + failed + cancelled} / {total_processes}`
- Status: `cancelled` with final counts

#### 6.4 Handle Scraper Failures
**Scenario**: Scraper fails to initialize, some processes never start

**Behavior**:
- Total count includes all expected processes
- Failed processes count toward completion
- Progress: `(completed + failed) / total_processes`
- Status shows: "X completed, Y failed out of Z total"

---

### Phase 7: Implementation Checklist

#### Backend Changes:
- [ ] Create `calculate_total_scraping_processes()` function
- [ ] Add `batch_totals` attribute to `WorkflowService`
- [ ] Calculate total in link submission endpoint
- [ ] Calculate total in `_load_link_context()` (validation)
- [ ] Send `batch:initialized` message after calculation
- [ ] Include `total_processes` in all batch status messages
- [ ] Create `GET /api/batch/{batch_id}/total` endpoint
- [ ] Add validation logic in `_load_link_context()`
- [ ] Update `ProgressService` to use `batch_totals` if available
- [ ] Add debug logging for total count tracking

#### Frontend Changes:
- [ ] Add `totalProcesses` to batch state
- [ ] Handle `batch:initialized` WebSocket message
- [ ] Update progress calculation to use `totalProcesses`
- [ ] Display progress as `X / Y` format
- [ ] Fetch total from API if WebSocket message missed
- [ ] Show breakdown by link type
- [ ] Handle `totalProcesses = null` gracefully

#### Testing:
- [ ] Test with various link combinations
- [ ] Test with empty links
- [ ] Test WebSocket message delivery
- [ ] Test API endpoint fallback
- [ ] Test total count validation
- [ ] Test cancellation scenarios
- [ ] Test scraper failure scenarios

---

### Phase 8: Data Flow Diagram

```
User Input Links
    ↓
Link Submission Endpoint
    ↓
Calculate Total Processes (Phase 1)
    ↓
Store in WorkflowService.batch_totals
    ↓
Send batch:initialized (Phase 2)
    ↓
Frontend Receives & Stores (Phase 3)
    ↓
Workflow Starts
    ↓
_load_link_context() validates total (Phase 4)
    ↓
ProgressService.initialize_expected_links()
    ↓
Scraping Processes Execute
    ↓
Progress Updates (include total_processes)
    ↓
Frontend Updates Progress Display
```

---

### Phase 9: Message Sequence

```
1. User submits links
   → POST /api/links/submit
   → Calculate total_processes
   → Store in batch_totals
   → Return {batch_id, total_processes, ...}

2. Frontend receives response
   → Store total_processes in state
   → Display "X processes to run"

3. Workflow starts
   → run_workflow(batch_id)
   → _load_link_context(batch_id)
   → Validate total_processes
   → Send batch:initialized (if not sent earlier)

4. Scraping begins
   → Progress updates include total_processes
   → Frontend calculates: (completed + failed) / total_processes

5. Completion
   → Final status: completed + failed = total_processes
   → Frontend shows 100% progress
```

---

### Phase 10: Benefits

1. **Early Total Count**: Frontend knows total before scraping starts
2. **Consistent Tracking**: Same total used throughout workflow
3. **Better UX**: Accurate progress bars from start
4. **Debugging**: Easy to identify missing processes
5. **Validation**: Can detect mismatches early
6. **Flexibility**: Works with user input or test files
7. **Resilience**: API fallback if WebSocket fails

---

### Phase 11: Potential Issues and Solutions

#### Issue 1: Total Count Changes Mid-Workflow
**Solution**: 
- Lock total count after first calculation
- Log warnings if recalculation differs
- Use original total for progress tracking

#### Issue 2: Frontend Misses Initial Message
**Solution**:
- API endpoint provides fallback
- Frontend polls until total received
- Store total in session storage

#### Issue 3: Process Count Mismatch
**Solution**:
- Validation in `_load_link_context()`
- Use calculated total (more accurate)
- Log warnings for investigation

#### Issue 4: Comments Scrapers Not Running
**Solution**:
- Total includes all expected processes
- Failed processes count toward completion
- Status shows which processes failed

---

---

## Phase 12: Research Phase Trigger Based on 100% Completion Rate

### 12.1 Current Research Phase Trigger Logic

**Location**: `workflow_service.py::run_workflow()` (lines 1183-1216)

**Current Flow**:
1. Wait for `scraping:complete` message from `workflow_direct.py`
2. Wait for status updates to be processed (`_wait_for_status_updates`)
3. Wait for `scraping:all_complete_confirmed` signal (`wait_for_scraping_confirmation`)
4. Check if `confirmation.get('confirmed') == True`
5. If confirmed, proceed to research phase

**Current Completion Check** (`progress_service.py::confirm_all_scraping_complete`):
```python
confirmed = (registered_count >= expected_total) and all_have_final_status
```

### 12.2 Issues Identified

#### Issue 1: No Explicit 100% Completion Rate Check
**Problem**: The completion check doesn't explicitly verify that `(completed + failed) / total_processes == 100%`

**Current Logic**:
- Checks: `registered_count >= expected_total` (all processes registered)
- Checks: `all_have_final_status` (all have 'completed' or 'failed' status)
- **Missing**: Explicit check that `completed + failed == expected_total`

**Why This Matters**:
- If some processes are registered but not yet in final status, `all_have_final_status` might be False
- But if `registered_count < expected_total`, confirmation fails
- However, there's no explicit check that `completed + failed == expected_total` (100% completion rate)

#### Issue 2: Completion Rate Not Calculated or Broadcast
**Problem**: The completion rate is calculated in `_update_batch_status()` but not used to trigger research phase

**Current Calculation** (line 301):
```python
overall_progress = ((completed + failed) / total) * 100.0
```

**Issue**: This is calculated but:
- Not explicitly checked for 100%
- Not sent as a clear signal to trigger research phase
- Research phase trigger relies on `confirmed` boolean, not completion rate

#### Issue 3: Race Condition in Confirmation
**Problem**: `scraping:verify_completion` is sent from `workflow_direct.py` after `scraping:complete`, but:
- There's a 0.5s delay before verification
- Verification happens in async queue processor
- Research phase might proceed before all status updates are fully processed

**Timeline**:
1. `scraping:complete` sent (line 761 in workflow_direct.py)
2. 0.5s wait (line 783)
3. `scraping:verify_completion` sent (line 788)
4. Queue processor handles verification (line 976 in workflow_service.py)
5. Confirmation sent (line 1009)
6. Research phase starts (line 1235)

**Potential Issue**: Status updates might still be in queue when verification happens

#### Issue 4: No Explicit 100% Signal
**Problem**: There's no explicit `scraping:100_percent_complete` message that clearly signals 100% completion

**Current Messages**:
- `scraping:complete` - Sent when scrapers finish (but might not be 100%)
- `scraping:verify_completion` - Request to verify
- `scraping:all_complete_confirmed` - Confirmation (but not explicitly 100%)

### 12.3 Root Cause Analysis

**Why Research Phase Might Start Prematurely**:

1. **Total Count Mismatch**:
   - `expected_total` might not match actual `total_processes`
   - If `expected_total` is lower than actual, confirmation succeeds early
   - If `expected_total` is higher, confirmation never succeeds

2. **Status Update Timing**:
   - Status updates are queued and processed asynchronously
   - Verification might happen before all status updates are processed
   - Some links might still be in 'in-progress' or 'pending' when verification runs

3. **Completion Check Logic**:
   - `all_have_final_status` checks if all registered links have final status
   - But if `registered_count < expected_total`, some links haven't started yet
   - The check `registered_count >= expected_total` should prevent this, but timing issues might cause problems

4. **No Completion Rate Validation**:
   - No explicit check: `(completed + failed) / expected_total == 1.0`
   - No explicit check: `completed + failed == expected_total`
   - Relies on boolean `confirmed` which might have edge cases

### 12.4 Proposed Solution

#### Solution 1: Add Explicit 100% Completion Rate Check

**Location**: `progress_service.py::confirm_all_scraping_complete()`

**Enhancement**:
```python
# Calculate completion rate
completion_rate = (completed_count + failed_count) / expected_total if expected_total > 0 else 0.0
is_100_percent = completion_rate >= 1.0  # Allow for floating point precision

# Enhanced confirmation check
confirmed = (
    registered_count >= expected_total and
    all_have_final_status and
    is_100_percent and
    (completed_count + failed_count) == expected_total  # Explicit equality check
)
```

**Add to Result**:
```python
result = {
    'confirmed': confirmed,
    'completion_rate': completion_rate,  # 0.0 to 1.0
    'completion_percentage': completion_rate * 100.0,  # 0.0 to 100.0
    'is_100_percent': is_100_percent,
    'expected_total': expected_total,
    'completed_count': completed_count,
    'failed_count': failed_count,
    'total_final': completed_count + failed_count,
    ...
}
```

#### Solution 2: Send Explicit 100% Completion Signal

**Location**: `progress_service.py::confirm_all_scraping_complete()` and `workflow_service.py::_process_progress_queue()`

**New Message Type**: `scraping:100_percent_complete`

**When to Send**:
- After `scraping:all_complete_confirmed` is sent
- Only if `completion_rate >= 1.0` and `(completed + failed) == expected_total`

**Message Format**:
```python
{
    'type': 'scraping:100_percent_complete',
    'batch_id': str,
    'completion_rate': 1.0,
    'completion_percentage': 100.0,
    'completed_count': int,
    'failed_count': int,
    'expected_total': int,
    'message': '所有抓取任务已完成 (100%)',
    'timestamp': str
}
```

#### Solution 3: Use Completion Rate to Trigger Research Phase

**Location**: `workflow_service.py::run_workflow()`

**Enhanced Check**:
```python
confirmation = await self.wait_for_scraping_confirmation(...)

# Explicit 100% completion check
if confirmation:
    completion_rate = confirmation.get('completion_rate', 0.0)
    completion_percentage = confirmation.get('completion_percentage', 0.0)
    is_100_percent = confirmation.get('is_100_percent', False)
    total_final = confirmation.get('total_final', 0)
    expected_total = confirmation.get('expected_total', 0)
    
    # Require explicit 100% completion
    if not (is_100_percent and total_final == expected_total and completion_percentage >= 100.0):
        logger.error(
            f"Completion rate not 100%: {completion_percentage:.1f}% "
            f"({total_final}/{expected_total})"
        )
        raise Exception(
            f"Scraping not 100% complete: {completion_percentage:.1f}% "
            f"({total_final}/{expected_total}). Cannot proceed to research phase."
        )
    
    logger.info(
        f"Scraping 100% COMPLETE for batch {batch_id}: "
        f"{completion_percentage:.1f}% ({total_final}/{expected_total})"
    )
```

#### Solution 4: Add Completion Rate Monitoring

**Location**: `progress_service.py::_update_batch_status()`

**Enhancement**: Include completion rate in all batch status messages

**Current** (line 324):
```python
await self.ws_manager.broadcast(batch_id, {
    'type': 'scraping:status',
    'batch_id': batch_id,
    'total': total,
    'completed': completed,
    'failed': failed,
    'in_progress': in_progress,
    'overall_progress': overall_progress,  # Already calculated
    ...
})
```

**Enhancement**: Add explicit completion rate fields
```python
completion_rate = (completed + failed) / total if total > 0 else 0.0
is_100_percent = completion_rate >= 1.0

await self.ws_manager.broadcast(batch_id, {
    'type': 'scraping:status',
    'batch_id': batch_id,
    'total': total,
    'completed': completed,
    'failed': failed,
    'in_progress': in_progress,
    'overall_progress': overall_progress,
    'completion_rate': completion_rate,  # NEW: 0.0 to 1.0
    'completion_percentage': overall_progress,  # Same as overall_progress, but explicit
    'is_100_percent': is_100_percent,  # NEW: boolean flag
    'can_proceed_to_research': is_100_percent,  # NEW: explicit flag for research phase
    ...
})
```

#### Solution 5: Poll for 100% Completion

**Location**: `workflow_service.py::run_workflow()`

**Enhancement**: After confirmation, poll until 100% completion rate is reached

**New Function**:
```python
async def wait_for_100_percent_completion(
    self,
    batch_id: str,
    max_wait_seconds: float = 10.0,
    check_interval: float = 0.5
) -> bool:
    """
    Poll ProgressService until 100% completion rate is reached.
    
    Returns:
        True if 100% reached, False if timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        result = await self.progress_service.confirm_all_scraping_complete(batch_id)
        
        completion_rate = result.get('completion_rate', 0.0)
        is_100_percent = result.get('is_100_percent', False)
        total_final = result.get('total_final', 0)
        expected_total = result.get('expected_total', 0)
        
        if is_100_percent and total_final == expected_total:
            logger.info(
                f"100% completion confirmed: {completion_rate * 100:.1f}% "
                f"({total_final}/{expected_total})"
            )
            return True
        
        logger.debug(
            f"Waiting for 100%: {completion_rate * 100:.1f}% "
            f"({total_final}/{expected_total}), elapsed={time.time() - start_time:.1f}s"
        )
        
        await asyncio.sleep(check_interval)
    
    return False
```

**Use in Workflow**:
```python
# After confirmation received
if confirmation and confirmation.get('confirmed'):
    # Additional check: Poll until 100% completion rate
    is_100_percent = await self.wait_for_100_percent_completion(
        batch_id,
        max_wait_seconds=10.0
    )
    
    if not is_100_percent:
        logger.error("100% completion not reached after polling")
        raise Exception("Scraping not 100% complete. Cannot proceed to research phase.")
```

### 12.5 Why Current System Might Not Work

#### Problem 1: Timing Issues
- Status updates are queued and processed asynchronously
- Verification might run before all status updates are applied
- Some links might be in transition state (e.g., 'in-progress' → 'completed')

#### Problem 2: Boolean Confirmation Not Explicit Enough
- `confirmed = True` doesn't explicitly mean 100%
- Edge cases where `registered_count == expected_total` but `completed + failed < expected_total`
- Race conditions where status updates are in flight

#### Problem 3: No Completion Rate in Confirmation
- Confirmation result doesn't include `completion_rate` or `completion_percentage`
- Research phase trigger can't verify 100% explicitly
- Relies on boolean `confirmed` which might have edge cases

#### Problem 4: Frontend Might Trigger Early
- Frontend might calculate completion rate independently
- If frontend's calculation differs from backend, premature transition
- No explicit signal that backend has verified 100%

### 12.6 Implementation Plan

#### Step 1: Add Completion Rate to Confirmation Result
**File**: `progress_service.py::confirm_all_scraping_complete()`

**Changes**:
1. Calculate `completion_rate = (completed_count + failed_count) / expected_total`
2. Calculate `is_100_percent = completion_rate >= 1.0`
3. Add explicit check: `(completed_count + failed_count) == expected_total`
4. Include in result dict

#### Step 2: Enhance Confirmation Check
**File**: `progress_service.py::confirm_all_scraping_complete()`

**Changes**:
1. Add completion rate check to `confirmed` calculation
2. Require: `(completed + failed) == expected_total`
3. Require: `completion_rate >= 1.0`

#### Step 3: Send 100% Completion Signal
**File**: `workflow_service.py::_process_progress_queue()`

**Changes**:
1. After sending `scraping:all_complete_confirmed`
2. Check if `completion_rate >= 1.0`
3. Send `scraping:100_percent_complete` message

#### Step 4: Use 100% Check in Research Phase Trigger
**File**: `workflow_service.py::run_workflow()`

**Changes**:
1. After receiving confirmation
2. Explicitly check `completion_rate >= 1.0`
3. Explicitly check `(completed + failed) == expected_total`
4. Only proceed if both checks pass
5. Add polling function as backup

#### Step 5: Include Completion Rate in Batch Status
**File**: `progress_service.py::_update_batch_status()`

**Changes**:
1. Calculate `completion_rate` and `is_100_percent`
2. Include in broadcast message
3. Add `can_proceed_to_research` flag

#### Step 6: Frontend Integration
**Files**: Frontend components

**Changes**:
1. Listen for `scraping:100_percent_complete` message
2. Use `completion_rate` from batch status
3. Only enable research phase when `is_100_percent === true`
4. Display completion rate: "X / Y (Z%)"

### 12.7 Testing Scenarios

1. **Normal Completion**: All processes complete successfully
   - Verify: `completion_rate = 1.0`, `is_100_percent = True`
   - Verify: Research phase starts only after 100% signal

2. **Partial Failure**: Some processes fail
   - Verify: `completed + failed == expected_total`
   - Verify: `completion_rate = 1.0` even with failures
   - Verify: Research phase starts (failed processes count as complete)

3. **Missing Processes**: Some processes never start
   - Verify: `registered_count < expected_total`
   - Verify: `completion_rate < 1.0`
   - Verify: Research phase does NOT start

4. **Race Condition**: Status updates in flight
   - Verify: Polling waits for all updates
   - Verify: 100% check happens after all updates processed

5. **Timing Edge Cases**: Verification before all status updates
   - Verify: Additional polling catches delayed updates
   - Verify: 100% check is accurate

---

## Summary

This plan creates a comprehensive system for:
1. **Calculating** total processes from user input early
2. **Storing** total in backend state
3. **Exposing** total to frontend via WebSocket and API
4. **Using** total consistently for progress tracking
5. **Validating** total throughout workflow
6. **Handling** edge cases and errors
7. **Triggering** research phase only at 100% completion rate

### Key Addition: 100% Completion Rate Trigger

The enhanced plan now includes:
- Explicit completion rate calculation: `(completed + failed) / total_processes`
- 100% completion check: `completion_rate >= 1.0` AND `(completed + failed) == expected_total`
- Clear signal: `scraping:100_percent_complete` message
- Research phase trigger: Only proceeds when 100% confirmed
- Polling backup: Additional verification to catch timing issues

The system ensures both backend and frontend use the same total count from the beginning, and research phase only starts when scraping is truly 100% complete (all expected processes have final status).

