# Streaming Summarization Manager V2 - Migration Guide

## Overview

This guide explains how to migrate from the complex `StreamingSummarizationManager` to the simplified `StreamingSummarizationManagerV2`.

## Key Differences

### Old Manager (V1) Problems
- ❌ Multiple overlapping state tracking systems
- ❌ 8 workers competing for tasks, causing race conditions
- ❌ Complex merge logic for transcript/comments inside manager
- ❌ Lock contention with `time.sleep()` workarounds
- ❌ Confusing lifecycle with cancellation, queue sets, processing sets
- ❌ Hard to debug and reason about

### New Manager (V2) Improvements
- ✅ Single clear state machine per item
- ✅ Single worker thread (sequential processing)
- ✅ Caller handles data merging before calling manager
- ✅ Simple lock usage, minimal critical sections
- ✅ Clear file lifecycle: scraped.json → complete.json
- ✅ Easy to debug and test

## State Machine

```
PENDING → SCRAPED → QUEUED → SUMMARIZING → COMPLETED
                                    ↓
                                  FAILED
```

Each item has ONE state at a time - no overlapping flags.

## API Changes

### Initialization

**Old:**
```python
from research.phases.streaming_summarization_manager import StreamingSummarizationManager

manager = StreamingSummarizationManager(client, config, ui, session, batch_id)
manager.register_expected_items(link_ids)
manager.start_workers()  # Starts 8 workers
```

**New:**
```python
from research.phases.streaming_summarization_manager_v2 import StreamingSummarizationManagerV2

manager = StreamingSummarizationManagerV2(client, config, ui, session, batch_id)
manager.register_expected_items(link_ids)
manager.start_worker()  # Starts 1 worker
```

### On Scraping Complete

**Old (WRONG - allowed partial data):**
```python
# Called separately for transcript and comments
manager.on_scraping_complete(link_id, {'transcript': '...', 'source': 'youtube'})
manager.on_scraping_complete(link_id, {'comments': [...], 'source': 'youtube'})
# Manager tried to merge these internally - caused race conditions!
```

**New (CORRECT - requires complete data):**
```python
# Caller MUST merge transcript + comments BEFORE calling
merged_data = {
    'source': 'youtube',
    'metadata': {...},
    'transcript': 'full transcript here',  # Both present
    'comments': [...]  # Both present
}
manager.on_item_scraped(link_id, merged_data)  # Called ONCE when BOTH ready
```

### Important: Caller Responsibility

**The caller (workflow or scraping coordinator) MUST:**
1. Wait for BOTH transcript and comments to finish scraping
2. Merge them into a single data dict
3. Call `on_item_scraped()` ONCE with complete data

**The manager NO LONGER:**
- Handles partial data
- Merges transcript and comments
- Supports cancellation
- Handles multiple calls per item

## File Lifecycle

### Old Manager
```
{batch_id}_{SOURCE}_{link_id}_summary.json  # Only final file
```

### New Manager
```
{batch_id}_{SOURCE}_{link_id}_scraped.json   # Saved immediately after scraping
{batch_id}_{SOURCE}_{link_id}_complete.json  # Saved after AI summarization
```

This makes it easy to see what stage each item is at by looking at the filesystem.

## Migration Steps

### Step 1: Update Scraping Workflow

**Before (in workflow or coordinator):**
```python
# Old code called manager multiple times per item
def on_transcript_complete(link_id, transcript_data):
    manager.on_scraping_complete(link_id, transcript_data)

def on_comments_complete(link_id, comments_data):
    manager.on_scraping_complete(link_id, comments_data)
```

**After:**
```python
# New code must merge before calling manager
class ScrapingCoordinator:
    def __init__(self):
        self.partial_data = {}  # Track incomplete items
    
    def on_transcript_complete(self, link_id, transcript_data):
        # Store partial data
        if link_id not in self.partial_data:
            self.partial_data[link_id] = {}
        self.partial_data[link_id].update(transcript_data)
        
        # Check if we can complete this item
        self._try_complete_item(link_id)
    
    def on_comments_complete(self, link_id, comments_data):
        # Store partial data
        if link_id not in self.partial_data:
            self.partial_data[link_id] = {}
        self.partial_data[link_id].update(comments_data)
        
        # Check if we can complete this item
        self._try_complete_item(link_id)
    
    def _try_complete_item(self, link_id):
        data = self.partial_data.get(link_id, {})
        
        # Check if we have enough data to proceed
        has_transcript = bool(data.get('transcript'))
        has_comments = bool(data.get('comments'))
        
        # You can customize this logic based on your needs
        # For example: require both, or proceed with just one
        if has_transcript or has_comments:
            # Complete! Send to manager
            manager.on_item_scraped(link_id, data)
            
            # Clean up
            del self.partial_data[link_id]
```

### Step 2: Update Initialization

```python
# Replace import
from research.phases.streaming_summarization_manager_v2 import StreamingSummarizationManagerV2

# Update initialization
manager = StreamingSummarizationManagerV2(client, config, ui, session, batch_id)
manager.register_expected_items(link_ids)
manager.start_worker()  # Note: singular, not plural
```

### Step 3: Remove Cancellation Logic

The new manager does NOT support cancellation. If you need to restart:
```python
# Old
manager.cancel_item(link_id)

# New - just create a new manager instance
manager.shutdown()
manager = StreamingSummarizationManagerV2(client, config, ui, session, batch_id)
```

### Step 4: Update Method Names

```python
# Old
manager.on_scraping_complete(link_id, data)
manager.start_workers()

# New
manager.on_item_scraped(link_id, data)
manager.start_worker()
```

## Testing

### Quick Test Script

```python
# test_summarization_v2.py
from research.phases.streaming_summarization_manager_v2 import StreamingSummarizationManagerV2

def test_simple_flow():
    manager = StreamingSummarizationManagerV2(client, config, ui, session, "test_batch")
    
    # Register items
    manager.register_expected_items(["item1", "item2"])
    
    # Start worker
    manager.start_worker()
    
    # Simulate scraping complete
    manager.on_item_scraped("item1", {
        'source': 'youtube',
        'metadata': {'title': 'Test Video'},
        'transcript': 'This is a test transcript',
        'comments': [{'text': 'Great video!'}]
    })
    
    manager.on_item_scraped("item2", {
        'source': 'youtube',
        'metadata': {'title': 'Another Video'},
        'transcript': 'Another test transcript',
        'comments': []
    })
    
    # Wait for completion
    success = manager.wait_for_completion(timeout=60)
    
    if success:
        stats = manager.get_statistics()
        print(f"Success! {stats['summarized']} items summarized")
    else:
        print("Timeout!")
    
    manager.shutdown()
```

## Debugging

### Check Item States

```python
# Get current state of all items
states = manager.get_item_states()
print(states)
# {'item1': 'COMPLETED', 'item2': 'SUMMARIZING', 'item3': 'QUEUED'}
```

### Check Files on Disk

```bash
# See what's been scraped
ls tests/results/run_{batch_id}/*_scraped.json

# See what's completed
ls tests/results/run_{batch_id}/*_complete.json
```

### Check Statistics

```python
stats = manager.get_statistics()
print(stats)
# {
#   'total': 10,
#   'scraped': 10,
#   'summarized': 8,
#   'reused': 1,
#   'failed': 1,
#   'created': 7
# }
```

## Configuration

### Config File Options

```yaml
research:
  summarization:
    enabled: true
    model: "qwen-flash"
    reuse_existing_summaries: true
    max_retries: 3  # New option for V2
```

## Rollback Plan

If you need to rollback to V1:
1. Keep both files (`streaming_summarization_manager.py` and `streaming_summarization_manager_v2.py`)
2. Change import back to V1
3. Restore old workflow code that calls manager multiple times

## Benefits Summary

| Aspect | V1 (Old) | V2 (New) |
|--------|----------|----------|
| Workers | 8 competing threads | 1 sequential thread |
| State tracking | 5+ overlapping systems | 1 clear enum |
| Data merging | Inside manager (complex) | Caller's responsibility |
| Lock usage | Complex with workarounds | Simple and minimal |
| Debugging | Very difficult | Easy with filesystem markers |
| Code lines | ~1009 lines | ~650 lines |
| Race conditions | Many | None |

## Common Issues

### Issue: "No scraped data for {link_id}"
**Cause:** Called `on_item_scraped()` with empty or invalid data
**Fix:** Ensure data has `transcript` or `comments` before calling

### Issue: Items stuck in QUEUED state
**Cause:** Worker not started or crashed
**Fix:** Check worker is alive: `manager.worker_thread.is_alive()`

### Issue: Summary not saved to file
**Cause:** Permission error or invalid characters in link_id
**Fix:** Check logs for file save errors, ensure link_id is filesystem-safe

## Questions?

Check the code comments in `streaming_summarization_manager_v2.py` for detailed explanations of each method.

