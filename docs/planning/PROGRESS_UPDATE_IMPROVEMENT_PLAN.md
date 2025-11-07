# Progress Update Improvement Plan

## Problem Statement

There is a significant delay between scraping completion and Phase 0 start, with no visible progress updates. The delay is caused by the summarization process (Phase 0) which uses qwen-flash API calls but doesn't stream progress updates like the scraping process does.

## Current Flow Analysis

### Current Process Flow
```
1. Scraping Phase
   ├─ Real-time progress updates via WebSocket
   ├─ Item-level progress (scraping:item_progress)
   └─ Status updates (scraping:status)

2. [GAP - No progress updates]
   └─ Summarization (Phase 0)
      ├─ Loads batch data
      ├─ Loops through each content item
      ├─ Calls qwen-flash API for each item (can take 5-30s per item)
      ├─ No progress updates sent during this time
      └─ User sees nothing happening

3. Phase 0.5: Role Generation
   └─ Minimal progress updates

4. Phase 1-4: Research Phases
   └─ Some progress updates but could be more granular
```

### Identified Issues

1. **Summarization Gap (Critical)**
   - Summarization happens in `Phase0Prepare._summarize_content_items()`
   - Loops through items sequentially
   - Each API call can take 5-30 seconds
   - Only sends UI messages via `self.ui.display_message()` which may not be streamed
   - No progress percentage or item-level tracking

2. **Phase 0.5 - Role Generation**
   - Single API call, no intermediate progress
   - Could show "Analyzing content..." → "Generating roles..."

3. **Phase 1 - Discovery**
   - Could show progress for goal extraction
   - Could show number of goals discovered

4. **Phase 2 - Synthesis**
   - Could show progress for question generation
   - Could show number of questions created

5. **Phase 3 - Execute**
   - Multiple research steps
   - Could show progress per step
   - Could show which step is currently executing

6. **Phase 4 - Final Synthesis**
   - Could show progress for report generation

## Solution Plan

### Priority 1: Add Summarization Progress Updates (Critical)

**Location**: `research/phases/phase0_prepare.py` → `_summarize_content_items()`

**Changes Needed**:

1. **Add Progress Tracking**
   - Track current item index
   - Calculate progress percentage: `(current_index / total_items) * 100`
   - Send progress updates before each API call

2. **Stream Progress Updates**
   - Use `self.ui.display_message()` with progress info
   - Send WebSocket messages with type: `workflow:progress` or new type: `summarization:progress`
   - Include:
     - Current item index / total items
     - Progress percentage
     - Current item link_id
     - Status: "正在总结", "阅读中", "完成"

3. **Per-Item Progress Updates**
   - Before API call: "正在总结 [1/5]: yt_req1"
   - During API call: Could stream tokens if API supports it (qwen-flash may not support streaming)
   - After API call: "总结好了 [1/5]: yt_req1 (15 标记)"

4. **WebSocket Message Format**
   ```json
   {
     "type": "summarization:progress",
     "batch_id": "...",
     "current_item": 1,
     "total_items": 5,
     "progress": 20.0,
     "link_id": "yt_req1",
     "stage": "summarizing_transcript" | "summarizing_comments" | "completed",
     "message": "正在总结 [1/5]: yt_req1",
     "timestamp": "2025-11-07T14:43:56.670121"
   }
   ```

**Implementation Steps**:
1. Modify `_summarize_content_items()` to send progress updates
2. Update `WebSocketUI.display_message()` to support progress data
3. Add new WebSocket message type `summarization:progress`
4. Update frontend to display summarization progress

### Priority 2: Improve Phase 0.5 Progress Updates

**Location**: `research/phases/phase0_5_role_generation.py`

**Changes Needed**:
1. Send "开始分析内容特征..." before API call
2. Send "正在生成研究角色..." during API call
3. Send "角色生成完成" after API call

### Priority 3: Improve Phase 1 Progress Updates

**Location**: `research/phases/phase1_discover.py`

**Changes Needed**:
1. Send progress when extracting goals
2. Show number of goals discovered: "已发现 3 个研究目标"
3. Show progress percentage if goals are processed in batches

### Priority 4: Improve Phase 2 Progress Updates

**Location**: `research/phases/phase2_synthesize.py`

**Changes Needed**:
1. Send progress when generating questions
2. Show number of questions created: "已生成 5 个研究问题"
3. Show progress if questions are processed sequentially

### Priority 5: Improve Phase 3 Progress Updates

**Location**: `research/phases/phase3_execute.py`

**Changes Needed**:
1. Send progress for each research step
2. Show current step: "执行研究步骤 [2/5]: 分析用户反馈模式"
3. Show progress percentage: `(current_step / total_steps) * 100`
4. Show which content chunks are being analyzed

### Priority 6: Improve Phase 4 Progress Updates

**Location**: `research/phases/phase4_synthesize.py`

**Changes Needed**:
1. Send "正在生成最终报告..."
2. Show progress if report generation is multi-step
3. Show "报告生成完成" when done

## Implementation Details

### WebSocket Message Types

Add new message types:
- `summarization:progress` - Summarization progress updates
- `phase:progress` - Generic phase progress (for Phases 1-4)

### WebSocketUI Enhancements

**File**: `backend/app/services/websocket_ui.py`

**New Methods**:
```python
def display_summarization_progress(
    self,
    current_item: int,
    total_items: int,
    link_id: str,
    stage: str,
    message: str
):
    """Send summarization progress update."""
    progress = (current_item / total_items) * 100 if total_items > 0 else 0
    coro = self._send_summarization_progress(
        current_item, total_items, link_id, stage, message, progress
    )
    self._schedule_coroutine(coro)

async def _send_summarization_progress(
    self,
    current_item: int,
    total_items: int,
    link_id: str,
    stage: str,
    message: str,
    progress: float
):
    """Async helper to send summarization progress."""
    payload = {
        "type": "summarization:progress",
        "batch_id": self.batch_id,
        "current_item": current_item,
        "total_items": total_items,
        "link_id": link_id,
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    await self.ws_manager.broadcast(self.batch_id, payload)
```

### Phase0Prepare Modifications

**File**: `research/phases/phase0_prepare.py`

**Changes in `_summarize_content_items()`**:

```python
def _summarize_content_items(
    self, 
    batch_data: Dict[str, Any], 
    batch_id: str
) -> Dict[str, Any]:
    """Summarize all content items with progress updates."""
    # ... existing code ...
    
    total_items = len(batch_data)
    self.logger.info(f"Starting summarization for {total_items} content items")
    
    # Send initial progress update
    if hasattr(self, 'ui') and self.ui:
        self.ui.display_summarization_progress(
            current_item=0,
            total_items=total_items,
            link_id="",
            stage="starting",
            message=f"开始创建摘要 ({total_items} 个内容项)"
        )
    
    for idx, (link_id, data) in enumerate(batch_data.items(), 1):
        # Send progress update before processing item
        if hasattr(self, 'ui') and self.ui:
            self.ui.display_summarization_progress(
                current_item=idx,
                total_items=total_items,
                link_id=link_id,
                stage="summarizing",
                message=f"正在创建摘要 [{idx}/{total_items}]: {link_id}"
            )
        
        # ... existing summarization code ...
        
        # Send completion update after item
        if hasattr(self, 'ui') and self.ui:
            transcript_markers = summary.get("transcript_summary", {}).get("total_markers", 0)
            comments_markers = summary.get("comments_summary", {}).get("total_markers", 0)
            self.ui.display_summarization_progress(
                current_item=idx,
                total_items=total_items,
                link_id=link_id,
                stage="completed",
                message=f"摘要创建完成 [{idx}/{total_items}]: {link_id} ({transcript_markers + comments_markers} 标记)"
            )
    
    # Send final completion update
    if hasattr(self, 'ui') and self.ui:
        self.ui.display_summarization_progress(
            current_item=total_items,
            total_items=total_items,
            link_id="",
            stage="all_completed",
            message=f"所有摘要创建完成 ({summaries_created} 新建, {summaries_reused} 重用)"
        )
```

### Frontend Updates

**File**: `client/src/hooks/useWebSocket.ts`

**Changes**:
1. Handle `summarization:progress` message type
2. Update UI to show summarization progress bar
3. Display current item being processed
4. Show progress percentage

**New UI Component** (optional):
- Create a `SummarizationProgress` component similar to `ScrapingProgress`
- Show progress bar with current item / total items
- Display link_id being processed
- Show stage (summarizing_transcript, summarizing_comments, completed)

## Testing Plan

1. **Unit Tests**
   - Test progress calculation (current_item / total_items)
   - Test WebSocket message format
   - Test UI display updates

2. **Integration Tests**
   - Test full workflow with summarization progress
   - Verify progress updates are sent at correct times
   - Verify frontend receives and displays updates

3. **Performance Tests**
   - Verify progress updates don't slow down summarization
   - Check WebSocket message frequency (shouldn't be too high)

## Estimated Impact

### User Experience
- **Before**: User sees nothing for 30-120 seconds after scraping completes
- **After**: User sees real-time progress: "正在创建摘要 [1/5]: yt_req1 (20%)"

### Time Visibility
- Summarization typically takes 5-30 seconds per item
- With 5 items: 25-150 seconds total
- Progress updates will show exactly where we are in this process

## Implementation Order

1. ✅ **Priority 1**: Add summarization progress updates (Critical)
2. ⏳ **Priority 2**: Improve Phase 0.5 progress
3. ⏳ **Priority 3**: Improve Phase 1 progress
4. ⏳ **Priority 4**: Improve Phase 2 progress
5. ⏳ **Priority 5**: Improve Phase 3 progress
6. ⏳ **Priority 6**: Improve Phase 4 progress

## Notes

- Summarization uses qwen-flash which may not support streaming, so we can't stream tokens
- Progress updates should be sent before and after each API call
- Consider rate limiting progress updates if there are many items (e.g., only send every 5% progress)
- Progress updates should not block the summarization process
- Use async/await properly to avoid blocking

