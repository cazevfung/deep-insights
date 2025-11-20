# 🔍 V2 Debug: Source Types Issue

## Problem Identified

From line 411 in your log:
```
[DataMerger] ✓ Item complete and merged: yt_req1 (source=unknown) (0 chars transcript, 32 comments)
```

The DataMerger is treating YouTube items as `source=unknown`, so it's completing them immediately with only comments instead of waiting for both transcript AND comments.

## Root Cause

The adapter determines whether an item needs merging (YouTube/Bilibili) or can complete immediately (Reddit/Article) by checking the source type:

```python
if source in ['youtube', 'bilibili']:
    # Multi-part item - needs merging
    if is_comments:
        self.data_merger.on_comments_complete(base_link_id, data)
    else:
        self.data_merger.on_transcript_complete(base_link_id, data)
else:
    # Single-part item - send directly (WRONG BRANCH!)
    self.data_merger.on_single_item_complete(base_link_id, data)
```

If the source type lookup fails, it takes the `else` branch and completes the item immediately!

## Debug Changes Added

I've added extensive logging to diagnose the source type lookup failure:

### 1. In `register_expected_items()` (line 65-77):

```python
if sources:
    self.item_sources.update(sources)
    logger.info(
        f"[StreamingSummarizationAdapter] Updated item_sources with {len(sources)} types. "
        f"Sample: {dict(list(sources.items())[:3])}"
    )
else:
    logger.warning("[StreamingSummarizationAdapter] No source types provided!")

logger.info(
    f"[StreamingSummarizationAdapter] Registered {len(link_ids)} items. "
    f"Total source_types: {len(self.item_sources)}"
)
```

### 2. In `on_scraping_complete()` (line 101-105):

```python
logger.info(
    f"[StreamingSummarizationAdapter] Routing {link_id}: "
    f"base_id={base_link_id}, is_comments={is_comments}, source={source}, "
    f"available_sources={list(self.item_sources.keys())[:5]}"
)
```

## What to Look For in New Logs

**Restart your backend** and run a new workflow. Look for these log lines:

### ✅ Good Flow (Expected):

```
[StreamingSummarizationAdapter] Updated item_sources with 22 types. Sample: {'yt_req1': 'youtube', 'yt_req2': 'youtube', 'yt_req3': 'youtube'}
[StreamingSummarizationAdapter] Registered 22 items. Total source_types: 22
[StreamingSummarizationAdapter] Routing yt_req1_comments: base_id=yt_req1, is_comments=True, source=youtube, available_sources=['yt_req1', 'yt_req2', 'yt_req3', 'yt_req4', 'yt_req5']
[DataMerger] Received comments for yt_req1
[DataMerger] ⏳ Waiting for yt_req1 (source=youtube): has_transcript=False, has_comments=True
[StreamingSummarizationAdapter] Routing yt_req1: base_id=yt_req1, is_comments=False, source=youtube, available_sources=[...]
[DataMerger] Received transcript for yt_req1
[DataMerger] ✓ Item complete and merged: yt_req1 (source=youtube) (18371 chars, 32 comments) ✅
```

### ❌ Bad Flow (Current Problem):

```
[StreamingSummarizationAdapter] No source types provided!  ← PROBLEM!
[StreamingSummarizationAdapter] Registered 22 items. Total source_types: 0  ← PROBLEM!
[StreamingSummarizationAdapter] Routing yt_req1_comments: base_id=yt_req1, is_comments=True, source=, available_sources=[]  ← PROBLEM!
[StreamingSummarizationAdapter] Treating yt_req1 as single-part item (source=)  ← PROBLEM!
[DataMerger] ✓ Item complete: yt_req1 (source=unknown) (0 chars, 32 comments)  ← PROBLEM!
```

## Possible Issues

1. **`sources` parameter is None**: The `workflow_service.py` isn't passing the `source_types` dict
2. **`sources` is empty dict**: The `source_types` dict is being created but not populated
3. **Wrong key format**: The keys in `source_types` don't match the `link_id` format

The debug logs will reveal which of these is the problem!

## Next Steps

1. **Restart backend**: `python backend/main.py`
2. **Run workflow** from frontend
3. **Check logs** for the new debug messages
4. **Share the new log** with the debug output showing source type info

