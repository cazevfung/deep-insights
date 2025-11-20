# Progress Tracking Improvement Plan

## Executive Summary

The current progress tracking system on the scraping page appears to be stuck at 0% because:
1. **Link status updates are not being persisted to database in real-time**
2. **Scraper progress callbacks are not connected to the backend/WebSocket system**
3. **WebSocket messages may not be sent frequently enough or at the right times**
4. **Frontend lacks detailed per-link progress information**
5. **No intermediate progress indicators during scraping operations**

This plan outlines a comprehensive solution to make progress tracking **real-time, informative, and user-friendly** - similar to how Cursor shows dynamic progress updates.

---

## Current Implementation Analysis

### Frontend (`ScrapingProgressPage.tsx`)
- ✅ Uses WebSocket via `useWebSocket` hook
- ✅ Calculates overall progress: `(completed + failed) / total * 100`
- ✅ Displays status badges (Success, Failed, In Progress, Total)
- ✅ Shows individual link list
- ❌ **No per-link detailed progress (stages, sub-steps)**
- ❌ **No intermediate progress during single link scraping**
- ❌ **No time estimates or ETA**
- ❌ **No visual indicators for active scraping operations**

### Backend WebSocket (`useWebSocket.ts`)
- ✅ Connects to `ws://localhost:8000/ws/${batchId}`
- ✅ Handles `scraping:status` messages for batch-level updates
- ✅ Handles `scraping:item_update` for individual link updates
- ❌ **May not be receiving frequent enough updates**
- ❌ **No per-link stage/progress information**

### Scrapers (`BaseScraper`, individual scrapers)
- ✅ Has `progress_callback` mechanism
- ✅ `_report_progress()` method exists
- ✅ Used in test scripts (`test_progress_tracking.py`)
- ❌ **NOT connected to backend/WebSocket system**
- ❌ **Progress callbacks are only used in CLI tests, not in workflow**

### Database/Storage
- ❌ **Link status may not be updated in real-time during scraping**
- ❌ **No intermediate progress storage**
- ❌ **Status updates likely only happen at completion/failure**

---

## Root Cause Analysis

**The Problem**: Progress shows 0% because:

1. **Disconnected Progress Pipeline**: Scrapers have `progress_callback` but it's not connected to the backend workflow system. Progress updates are only used in test scripts.

2. **No Real-time Database Updates**: Link status is probably only updated when a link completes or fails, not during intermediate stages.

3. **Missing WebSocket Broadcasts**: Even if scrapers report progress, there's no mechanism to broadcast these updates via WebSocket to the frontend.

4. **Insufficient Progress Data**: The frontend only receives final status (completed/failed), not intermediate progress information.

---

## Proposed Solution Architecture

### Goal
Make progress tracking **real-time, granular, and informative** - showing users exactly what's happening at every step, just like Cursor's progress indicators.

### Key Principles
1. **Real-time Updates**: Every significant event should trigger a WebSocket broadcast
2. **Granular Progress**: Show progress at multiple levels (batch → link → stage → sub-step)
3. **Informative Messages**: Tell users what's happening right now, not just numbers
4. **Visual Feedback**: Use animations, colors, and indicators to show activity
5. **Time Awareness**: Show elapsed time, estimated time remaining
6. **Error Transparency**: Show errors immediately with context

---

## Implementation Plan

### Phase 1: Backend - Progress Tracking Infrastructure

#### 1.1 Database Schema Enhancement
Add progress tracking fields to Link model:
- `current_stage`: Current operation stage (e.g., "downloading", "transcribing")
- `stage_progress`: Progress within current stage (0.0-100.0)
- `overall_progress`: Overall progress for entire link (0.0-100.0)
- `status_message`: Human-readable status message
- `bytes_downloaded` / `total_bytes`: For download progress
- `started_at` / `updated_at` / `completed_at`: Timestamps

#### 1.2 Progress Service (NEW)
Create `backend/app/services/progress_service.py`:
- Centralized service for progress updates
- Updates database and broadcasts to WebSocket
- Tracks batch-level statistics

#### 1.3 Scraper Integration
Modify scraping workflow to:
- Create progress callbacks connected to ProgressService
- Pass callbacks to scrapers when starting extraction
- Ensure scrapers call callbacks at key stages

#### 1.4 Enhanced Scraper Reporting
Update scrapers to report progress at appropriate points:
- **Bilibili**: loading → downloading (0-50%) → converting (50-60%) → uploading (60-70%) → transcribing (70-95%) → completed
- **YouTube**: loading → extracting → completed
- **Articles**: loading → extracting → completed

---

### Phase 2: Frontend - Enhanced UI Components

#### 2.1 Enhanced Progress Display
- **Per-link progress bars** with stage information
- **Stage indicators** showing current operation
- **Active indicators** (spinning/animated) for active links
- **Status messages** in real-time
- **Time information** (elapsed, ETA)

#### 2.2 Store Enhancement
Extend `ScrapingItem` interface with:
- `currentStage`, `stageProgress`, `overallProgress`
- `statusMessage`, `startedAt`, `completedAt`
- Metadata (bytes, word count, etc.)

#### 2.3 WebSocket Handler
Add handler for `scraping:item_progress` messages to update per-link progress in real-time.

---

### Phase 3: API Endpoints

#### 3.1 Batch Status Endpoint
Add `GET /api/batches/{batch_id}/status` for polling fallback:
- Returns current batch status with all links
- Includes detailed progress information
- Useful if WebSocket connection fails

---

### Phase 4: Time Estimation

#### 4.1 Time Tracking
- Track time for each stage per source type
- Calculate ETA based on historical averages
- Display elapsed time and estimated remaining time

---

## Expected User Experience

### Before (Current State)
```
总体进度: ░░░░░░░░░░░░░░░░░░░░ 0%

成功: 0  失败: 0  进行中: 0  总计: 5

[Static list with no progress information]
```

### After (Improved)
```
总体进度: ████████████░░░░░░░░ 60%

成功: 3  失败: 0  进行中: 2  总计: 5

链接列表:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[✓] https://youtube.com/watch?v=...
    ✅ 已完成 | 词数: 1,234 | 用时: 2分30秒

[⟳] https://bilibili.com/video/BV...
    🔄 进行中 | 正在转录中... 85%
    ████████████████████░░░░ 85%
    当前阶段: 转录中 85% | 预计剩余: 1分15秒

[⟳] https://example.com/article/...
    🔄 进行中 | 正在提取内容... 30%
    ███████░░░░░░░░░░░░░░░░ 30%
    当前阶段: 提取中 30%
```

---

## Implementation Checklist

### Backend
- [ ] Add progress tracking fields to Link model
- [ ] Create ProgressService for centralized progress tracking
- [ ] Integrate scraper progress callbacks with ProgressService
- [ ] Enhance scrapers to report progress at key stages
- [ ] Ensure WebSocket broadcasts on progress updates
- [ ] Add batch status API endpoint

### Frontend
- [ ] Extend ScrapingItem interface with progress fields
- [ ] Add WebSocket handler for `scraping:item_progress`
- [ ] Create enhanced link progress item component
- [ ] Add per-link progress bars with stage info
- [ ] Add activity indicators (spinning/pulsing)
- [ ] Display status messages and time information
- [ ] Add polling fallback if WebSocket unavailable

### Testing
- [ ] Test WebSocket connection and message delivery
- [ ] Test progress updates at various stages
- [ ] Test with multiple links in parallel
- [ ] Test error scenarios
- [ ] Test UI responsiveness

---

## Performance Considerations

1. **WebSocket Message Frequency**: Update on significant events (>5% progress change), throttle to max 2-3 updates/sec per link
2. **Database Updates**: Update only changed fields, index `batch_id` and `status`
3. **Frontend Rendering**: Use React.memo, update only changed items, virtualize long lists

---

## Conclusion

This plan addresses the core issue by:
1. **Connecting scraper progress callbacks to backend/WebSocket system**
2. **Persisting progress updates to database in real-time**
3. **Broadcasting detailed progress updates via WebSocket**
4. **Enhancing frontend to display rich progress information**
5. **Adding visual feedback and activity indicators**

Result: A **responsive, informative progress tracking system** that gives users confidence the system is working, showing exactly what's happening at every step.
