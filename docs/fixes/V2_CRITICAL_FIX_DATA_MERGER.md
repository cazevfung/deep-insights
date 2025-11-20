# 🐛 Critical Fix: DataMerger Wait Logic

## Problem Identified

The DataMerger was completing items **too early**, sending incomplete data (only comments, no transcript) to the V2 manager.

### Evidence from Logs

```
Line 409: [DataMerger] ✓ Item complete and merged: yt_req2 (0 chars transcript, 31 comments)
Line 546: [WorkflowService] ✓ Data loaded for yt_req1: 18371 chars transcript, 0 comments
```

The transcript arrived AFTER the item was already marked complete and sent to V2!

## Root Cause

The original `_try_complete_item()` logic completed items as soon as it had **either** transcript OR comments:

```python
# OLD LOGIC (BROKEN)
has_transcript = bool(data.get('transcript'))
has_comments = bool(data.get('comments'))

if not (has_transcript or has_comments):
    # Not ready yet
    return

# Complete immediately if we have EITHER part! ❌
```

This worked for Reddit/Article items (which only have one part), but **failed for YouTube/Bilibili** items (which need both transcript AND comments).

## Solution

Updated the DataMerger to:

1. **Accept source types** during initialization
2. **Wait for BOTH parts** for YouTube/Bilibili items
3. **Complete immediately** for Reddit/Article items

### New Logic

```python
# NEW LOGIC (FIXED)
source_type = self.source_types.get(link_id, 'unknown')

if source_type in ['youtube', 'bilibili']:
    # Need BOTH transcript AND comments ✓
    is_ready = has_transcript and has_comments
    
    if not is_ready:
        logger.info(
            f"[DataMerger] ⏳ Waiting for {link_id} (source={source_type}): "
            f"has_transcript={has_transcript}, has_comments={has_comments}"
        )
        return
else:
    # For Reddit/Article, complete as soon as we have either part ✓
    is_ready = has_transcript or has_comments
```

## Files Changed

1. **`backend/app/services/data_merger.py`**
   - Added `source_types` parameter to `__init__`
   - Updated `_try_complete_item()` to check source type
   - Added waiting log when missing parts

2. **`research/phases/streaming_summarization_adapter.py`**
   - Pass `source_types` dict to DataMerger during initialization
   - Moved `item_sources` initialization before DataMerger creation

## Expected Behavior Now

With this fix, the logs should show:

```
[DataMerger] Received comments for yt_req1
[DataMerger] ⏳ Waiting for yt_req1 (source=youtube): has_transcript=False, has_comments=True
[DataMerger] Received transcript for yt_req1
[DataMerger] ✓ Item complete and merged: yt_req1 (source=youtube) (18371 chars transcript, 37 comments)
[StreamingSummarizationAdapter] Routing complete data to V2: yt_req1
[SummarizationV2] Queued yt_req1 for summarization
[SummarizationV2] Processing: yt_req1
[SummarizationV2] Creating summary for yt_req1
[SummarizationV2] Summary created for yt_req1 in X.XXs
[SummarizationV2] ✓ Completed yt_req1
```

## Testing

Restart your backend and run a new workflow. You should see:

1. ✅ DataMerger waits for both transcript and comments
2. ✅ Items only complete when they have BOTH parts
3. ✅ Summaries are created with complete data
4. ✅ No more "0 chars transcript" in completion logs

## Impact

This was a **critical bug** that prevented proper summarization:
- ❌ Before: Items summarized with only comments (missing transcript)
- ✅ After: Items summarized with complete transcript + comments data

