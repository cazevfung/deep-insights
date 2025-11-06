# History Page Investigation Report

## Problem Summary

The "研究历史" (Research History) page is not showing past researches. The frontend is calling `/api/history` which returns a 404 error because the backend endpoint doesn't exist.

## Root Cause

**Missing Backend Route**: The backend application (`backend/app/main.py`) does not have a `/api/history` route registered. The frontend expects this endpoint but it doesn't exist.

## Current State

### Frontend (`client/src/pages/HistoryPage.tsx`)
- Calls `apiService.getHistory()` which makes `GET /api/history`
- Expects response with:
  ```typescript
  {
    sessions: [{
      batch_id: string
      created_at: string
      status: 'completed' | 'in-progress' | 'failed' | 'cancelled'
      topic?: string
      url_count?: number
      current_phase?: string
    }]
  }
  ```
- Also expects these endpoints:
  - `GET /api/history/{batchId}` - get session details
  - `POST /api/history/{batchId}/resume` - resume a session
  - `DELETE /api/history/{batchId}` - delete a session

### Backend Routes (`backend/app/main.py`)
Currently registered routes:
- `/api/links` - link formatting
- `/api/workflow` - workflow management
- `/api/research` - research operations
- `/api/sessions` - session CRUD (by session_id, not batch_id)
- `/api/reports` - report generation

**Missing**: `/api/history` route

### Session Storage
- **Location**: `data/research/sessions/`
- **Format**: JSON files named `session_{session_id}.json`
- **Example files found**:
  - `session_20251030_130123.json`
  - `session_20251030_173448.json`
  - `session_20251031_205322.json`
  - `session_20251105_161806.json`
  - `session_20251105_215625.json`
  - ... and more

### Session Data Structure
From examining session files, each session contains:
```json
{
  "metadata": {
    "session_id": "20251105_215625",
    "batch_id": "20251105_135520",
    "created_at": "2025-11-05T21:56:25.432112",
    "updated_at": "2025-11-05T22:28:21.962968",
    "status": "completed" | "initialized" | etc.,
    "finished": true | false,
    "synthesized_goal": {
      "comprehensive_topic": "对话式简历优化的向量检索架构"
    },
    "quality_assessment": {
      "statistics": {
        "total_items": 13,
        ...
      }
    },
    ...
  },
  "scratchpad": { ... }
}
```

**Key observations**:
- Sessions have `batch_id` which links to the scraping batch
- Status can be "completed", "initialized", or other values
- Topic is available in `metadata.synthesized_goal.comprehensive_topic`
- URL count could be derived from `metadata.quality_assessment.statistics.total_items`
- WIP sessions exist (status != "completed" or finished != true)

## What Needs to be Implemented

### 1. Create History Route (`backend/app/routes/history.py`)
A new route file that:
- Scans `data/research/sessions/` directory for all session files
- Reads each session file's metadata
- Maps session data to frontend expected format:
  - `batch_id` from `metadata.batch_id`
  - `created_at` from `metadata.created_at`
  - `status` mapped from `metadata.status` and `metadata.finished`:
    - `"completed"` if `status == "completed"` and `finished == true`
    - `"in-progress"` if `finished != true` or status is "initialized"/"in-progress"
    - `"failed"` if status indicates failure
    - `"cancelled"` if status indicates cancellation
  - `topic` from `metadata.synthesized_goal.comprehensive_topic`
  - `url_count` from `metadata.quality_assessment.statistics.total_items` (if available)
  - `current_phase` determined from session progress (if available)

### 2. Endpoints to Implement

#### `GET /api/history`
- List all sessions
- Support query parameters:
  - `status` - filter by status
  - `date_from` - filter by date range
  - `date_to` - filter by date range
  - `limit` - pagination
  - `offset` - pagination
- **Important**: Include WIP/incomplete sessions (not just completed ones)

#### `GET /api/history/{batch_id}`
- Get session details by batch_id
- Find session file where `metadata.batch_id == batch_id`
- Return full session data

#### `POST /api/history/{batch_id}/resume`
- Resume a workflow for a batch_id
- Load session and restore workflow state
- May need to integrate with workflow service

#### `DELETE /api/history/{batch_id}`
- Delete a session by batch_id
- Find and delete the session file
- May need to clean up related data

### 3. Register Route in `backend/app/main.py`
Add:
```python
from app.routes import history
app.include_router(history.router, prefix="/api/history", tags=["history"])
```

## Implementation Considerations

1. **Session Discovery**: 
   - Scan `data/research/sessions/` for `session_*.json` files
   - Handle missing or corrupted files gracefully
   - Consider caching for performance

2. **Status Mapping**:
   - Map internal status values to frontend expected values
   - Handle edge cases (missing status, null finished flag, etc.)

3. **WIP Sessions**:
   - Include all sessions regardless of completion status
   - Ensure incomplete sessions are properly identified and displayed

4. **Batch ID vs Session ID**:
   - Frontend uses `batch_id` as primary identifier
   - Need to find sessions by `batch_id` (not `session_id`)
   - One batch_id may have multiple sessions (if resumed)

5. **Error Handling**:
   - Handle missing session files
   - Handle corrupted JSON files
   - Handle missing metadata fields

6. **Performance**:
   - Consider pagination for large numbers of sessions
   - Consider caching session list
   - Lazy load session details when needed

## Files to Create/Modify

1. **Create**: `backend/app/routes/history.py` - New history route
2. **Modify**: `backend/app/main.py` - Register history router
3. **Optional**: Create `backend/app/services/history_service.py` - Service layer for history operations

## Testing Checklist

After implementation:
- [ ] `GET /api/history` returns all sessions including WIP ones
- [ ] `GET /api/history?status=in-progress` filters correctly
- [ ] `GET /api/history/{batch_id}` returns correct session
- [ ] `POST /api/history/{batch_id}/resume` resumes workflow
- [ ] `DELETE /api/history/{batch_id}` deletes session
- [ ] WIP sessions are displayed with correct status badge
- [ ] Completed sessions are displayed correctly
- [ ] Frontend history page loads without errors

## Next Steps

1. Create `backend/app/routes/history.py` with all endpoints
2. Implement session discovery and mapping logic
3. Register route in `main.py`
4. Test with existing session files
5. Verify frontend displays all sessions correctly (including WIP)

