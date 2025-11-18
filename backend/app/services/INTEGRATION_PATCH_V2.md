# V2 Integration Patch for workflow_service.py

## Summary

This patch integrates StreamingSummarizationManagerV2 into the workflow with **MINIMAL changes** using an adapter.

## Changes Required

### 1. Update Import (Line ~2140)

**OLD:**
```python
from research.phases.streaming_summarization_manager import StreamingSummarizationManager
```

**NEW:**
```python
from research.phases.streaming_summarization_adapter import StreamingSummarizationAdapter as StreamingSummarizationManager
```

That's it! The adapter provides V1-compatible interface, so the rest of the code works as-is.

### 2. Optional: Pass Source Types (Line ~2145-2200)

To help the adapter know which items need merging, you can optionally pass source types:

**BEFORE** (Line ~2164):
```python
logger.info(f"[WorkflowService] Collected {len(all_link_ids)} link_ids for streaming summarization: {all_link_ids[:5]}...")
```

**ADD AFTER:**
```python
# Collect source types for adapter
source_types = {}
if batch_id in self.link_context:
    for link_type, links in self.link_context[batch_id].items():
        for link_info in links:
            link_id = link_info.get('link_id')
            if link_id:
                source_types[link_id] = link_type
logger.info(f"[WorkflowService] Collected source types for {len(source_types)} items")
```

**THEN UPDATE** (Line ~2200):
```python
# OLD:
streaming_manager.register_expected_items(all_link_ids)

# NEW:
streaming_manager.register_expected_items(all_link_ids, sources=source_types)
```

### 3. Update Worker Start Call (Line ~2203)

**OLD:**
```python
streaming_manager.start_workers()  # Starts 8 workers
```

**NEW:**
```python
streaming_manager.start_workers()  # Now starts 1 worker via adapter
```

No code change needed - adapter handles this!

## That's It!

The adapter provides:
- ✅ V1-compatible `on_scraping_complete()` interface
- ✅ Automatic transcript+comments merging
- ✅ V2 manager under the hood (simple, reliable)
- ✅ All V1 properties (`workers`, `summarization_queue`, etc.)

## Testing

After applying the patch:

1. **Start your workflow normally:**
```bash
# Your usual command to start the backend
python backend/main.py
```

2. **Monitor logs for V2 signatures:**
```
[SummarizationV2] Initialized for batch 20251115_...
[SummarizationV2] Registered 22 items
[SummarizationV2] Starting summarization worker
[DataMerger] Initialized
[StreamingSummarizationAdapter] Initialized for batch 20251115_...
```

3. **Check for scraping activity:**
```
[DataMerger] Received transcript for yt_req1
[DataMerger] Received comments for yt_req1
[DataMerger] ✓ Item complete and merged: yt_req1 (12345 chars transcript, 42 comments)
[StreamingSummarizationAdapter] Routing complete data to V2: yt_req1
[SummarizationV2] Queued yt_req1 for summarization (queue_size=1)
[SummarizationV2] Processing: yt_req1
[SummarizationV2] Creating summary for yt_req1 (attempt 1/3)
[SummarizationV2] Summary created for yt_req1 in 3.45s (attempt 1)
[SummarizationV2] Saved complete data: 20251115_053137_YT_yt_req1_complete.json
[SummarizationV2] ✓ Completed yt_req1
```

## Rollback Plan

If issues occur, simply revert the import:

```python
from research.phases.streaming_summarization_manager import StreamingSummarizationManager
```

Both V1 and V2 files remain in place, so rollback is instant.

## File Checklist

Ensure these files exist:
- ✅ `research/phases/streaming_summarization_manager_v2.py` (V2 manager)
- ✅ `backend/app/services/data_merger.py` (Data merger)
- ✅ `research/phases/streaming_summarization_adapter.py` (V1-compatible adapter)

## Benefits After Integration

| Aspect | Before (V1) | After (V2) |
|--------|-------------|------------|
| Workers | 8 competing | 1 sequential |
| State tracking | 5+ systems | 1 enum |
| Data merging | Inside manager (race conditions) | In adapter (clean) |
| Lock contention | High | Minimal |
| Debugging | Very difficult | Easy |
| Files saved | 1 per item | 2 per item (scraped + complete) |
| Race conditions | Many | None |
| Code complexity | 1009 lines | 650 lines + adapter |

## Next Steps

1. Apply the import change
2. Restart backend
3. Run a test workflow
4. Monitor logs
5. Check `tests/results/run_{batch_id}/` for output files
6. Celebrate! 🎉

