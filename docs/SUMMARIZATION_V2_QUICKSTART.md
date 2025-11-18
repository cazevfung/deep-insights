# StreamingSummarizationManagerV2 - Quick Start Guide

## TL;DR

```python
from research.phases.streaming_summarization_manager_v2 import StreamingSummarizationManagerV2

# 1. Create manager
manager = StreamingSummarizationManagerV2(client, config, ui, session, batch_id)

# 2. Register expected items
manager.register_expected_items(["req1", "req2", "req3"])

# 3. Start worker
manager.start_worker()

# 4. When scraping completes, send COMPLETE data (transcript + comments merged!)
manager.on_item_scraped("req1", {
    'source': 'youtube',
    'metadata': {'title': 'Video Title', 'url': 'https://...'},
    'transcript': 'Full transcript here...',
    'comments': [{'text': 'Comment 1'}, {'text': 'Comment 2'}]
})

# 5. Wait for completion
manager.wait_for_completion(timeout=300)

# 6. Get results
summarized_data = manager.get_all_summarized_data()

# 7. Shutdown
manager.shutdown()
```

---

## The Correct Workflow

### ✅ DO THIS: Merge Data Before Calling Manager

```python
class ScrapingCoordinator:
    def __init__(self, manager):
        self.manager = manager
        self.pending_items = {}  # Store incomplete items
    
    def on_transcript_complete(self, link_id, transcript_data):
        """Called when transcript scraping finishes."""
        # Store the data
        if link_id not in self.pending_items:
            self.pending_items[link_id] = {}
        self.pending_items[link_id]['transcript'] = transcript_data.get('transcript')
        self.pending_items[link_id]['source'] = transcript_data.get('source')
        self.pending_items[link_id]['metadata'] = transcript_data.get('metadata', {})
        
        # Try to complete the item
        self._check_and_complete(link_id)
    
    def on_comments_complete(self, link_id, comments_data):
        """Called when comments scraping finishes."""
        # Store the data
        if link_id not in self.pending_items:
            self.pending_items[link_id] = {}
        self.pending_items[link_id]['comments'] = comments_data.get('comments', [])
        
        # Try to complete the item
        self._check_and_complete(link_id)
    
    def _check_and_complete(self, link_id):
        """Check if item is ready and send to manager."""
        data = self.pending_items.get(link_id, {})
        
        # Check if we have at least one of transcript or comments
        has_transcript = bool(data.get('transcript'))
        has_comments = bool(data.get('comments'))
        
        if has_transcript or has_comments:
            # Ready! Send to manager
            merged_data = {
                'source': data.get('source', 'unknown'),
                'metadata': data.get('metadata', {}),
                'transcript': data.get('transcript', ''),
                'comments': data.get('comments', [])
            }
            
            self.manager.on_item_scraped(link_id, merged_data)
            
            # Clean up
            del self.pending_items[link_id]
            
            logger.info(f"✓ Sent complete data to manager: {link_id}")
```

### ❌ DON'T DO THIS: Call Manager Multiple Times

```python
# WRONG - This will fail!
def on_transcript_complete(self, link_id, transcript_data):
    manager.on_item_scraped(link_id, transcript_data)  # ❌ Incomplete data!

def on_comments_complete(self, link_id, comments_data):
    manager.on_item_scraped(link_id, comments_data)  # ❌ Duplicate call!

# V2 expects ONE call per item with COMPLETE data
```

---

## File Structure You'll See

After running, check your batch directory:

```
tests/results/run_20251114_150630/
├── 20251114_150630_YT_req1_scraped.json     ← Saved immediately after scraping
├── 20251114_150630_YT_req1_complete.json    ← Saved after AI summarization ✓
├── 20251114_150630_YT_req2_scraped.json
├── 20251114_150630_YT_req2_complete.json    ✓
└── 20251114_150630_YT_req3_scraped.json     ← Still summarizing...
```

**Debugging tip:** If you see `_scraped.json` but no `_complete.json`, the item is still being summarized (or failed).

---

## Monitoring Progress

### Check Item States

```python
# Get state of all items
states = manager.get_item_states()
print(states)
# {'req1': 'COMPLETED', 'req2': 'SUMMARIZING', 'req3': 'QUEUED'}

# Check specific item
if states['req1'] == 'COMPLETED':
    print("req1 is done!")
```

### Check Statistics

```python
stats = manager.get_statistics()
print(f"Progress: {stats['summarized']}/{stats['total']}")
print(f"Created: {stats['created']}, Reused: {stats['reused']}, Failed: {stats['failed']}")

# Example output:
# Progress: 8/10
# Created: 7, Reused: 1, Failed: 0
```

### Watch Logs

```
[SummarizationV2] Initialized for batch 20251114_150630
[SummarizationV2] Registered 3 items
[SummarizationV2] Starting summarization worker
[ItemState] req1: SCRAPED
[ItemState] req1: QUEUED
[SummarizationV2] Queued req1 for summarization (queue_size=1)
[SummarizationV2] Processing: req1
[ItemState] req1: SUMMARIZING
[SummarizationV2] Creating summary for req1 (attempt 1/3)
[SummarizationV2] Summary created for req1 in 3.45s (attempt 1)
[SummarizationV2] Saved complete data: 20251114_150630_YT_req1_complete.json
[ItemState] req1: COMPLETED
[SummarizationV2] ✓ Completed req1
```

Clear progression, easy to follow!

---

## Error Handling

### Automatic Retries

If AI API fails, V2 automatically retries with exponential backoff:

```
Attempt 1 fails → wait 2 seconds → retry
Attempt 2 fails → wait 4 seconds → retry
Attempt 3 fails → wait 8 seconds → retry
All attempts fail → mark as FAILED
```

### Check Failed Items

```python
states = manager.get_item_states()
failed_items = [link_id for link_id, state in states.items() if state == 'FAILED']

if failed_items:
    print(f"Failed items: {failed_items}")
    
    # Get details
    with manager.items_lock:
        for link_id in failed_items:
            item = manager.items[link_id]
            print(f"{link_id}: {item.error}")
```

### Configuration

Set max retries in config:

```yaml
research:
  summarization:
    max_retries: 3  # Default: 3
```

---

## Common Patterns

### Pattern 1: Process Everything

```python
# Setup
manager = StreamingSummarizationManagerV2(client, config, ui, session, batch_id)
manager.register_expected_items(all_link_ids)
manager.start_worker()

# As items finish scraping, send them
for link_id, scraped_data in scraped_items:
    manager.on_item_scraped(link_id, scraped_data)

# Wait for all
manager.wait_for_completion(timeout=600)  # 10 minutes

# Get results
results = manager.get_all_summarized_data()

# Cleanup
manager.shutdown()
```

### Pattern 2: Process with Timeout

```python
# Start processing
manager.start_worker()

# Send items as they complete
for link_id, data in items:
    manager.on_item_scraped(link_id, data)

# Wait with timeout
success = manager.wait_for_completion(timeout=300)

if success:
    print("All completed!")
else:
    print("Timeout - some items not finished")
    
    # Check what's incomplete
    states = manager.get_item_states()
    incomplete = [lid for lid, state in states.items() 
                  if state not in ('COMPLETED', 'FAILED')]
    print(f"Incomplete items: {incomplete}")

manager.shutdown()
```

### Pattern 3: Real-time Monitoring

```python
manager.start_worker()

# Process items
for link_id, data in items:
    manager.on_item_scraped(link_id, data)
    
    # Show progress after each item
    stats = manager.get_statistics()
    print(f"Progress: {stats['summarized']}/{stats['total']}")

# Wait for completion
manager.wait_for_completion()
manager.shutdown()
```

---

## Data Format Requirements

### Minimum Required Data

```python
# At minimum, need ONE of transcript or comments
data = {
    'source': 'youtube',           # Required
    'metadata': {},                # Optional but recommended
    'transcript': 'Some text...',  # Optional (but need this or comments)
    'comments': []                 # Optional (but need this or transcript)
}
```

### Full Data Example

```python
data = {
    'source': 'youtube',
    'metadata': {
        'url': 'https://youtube.com/watch?v=abc123',
        'title': 'How to Train Your Dragon',
        'author': 'Awesome Channel',
        'duration': 3600,
        'upload_date': '2024-01-15'
    },
    'transcript': '''
        [00:00] Welcome to this video...
        [01:23] Today we'll discuss...
        [05:45] The main points are...
    ''',
    'comments': [
        {
            'author': 'User1',
            'text': 'Great video!',
            'timestamp': '2024-01-16 10:30:00'
        },
        {
            'author': 'User2',
            'text': 'Very helpful, thanks!',
            'timestamp': '2024-01-16 11:45:00'
        }
    ]
}
```

### Reusing Existing Summaries

If data already has a summary, V2 will reuse it:

```python
data = {
    'source': 'youtube',
    'metadata': {...},
    'transcript': '...',
    'comments': [...],
    'summary': {  # Already exists!
        'transcript_summary': {...},
        'comments_summary': {...},
        'created_at': '2024-01-15T10:30:00',
        'model_used': 'qwen-flash'
    }
}

# V2 will skip AI call and mark as completed immediately
manager.on_item_scraped(link_id, data)
```

---

## Configuration Options

### Full Config

```yaml
research:
  summarization:
    enabled: true                      # Enable/disable summarization
    model: "qwen-flash"                # Model to use
    reuse_existing_summaries: true     # Skip if summary exists
    max_retries: 3                     # Retry failed summarizations
    save_to_files: true                # Save JSON files
```

### Disable Summarization

```yaml
research:
  summarization:
    enabled: false
```

When disabled, manager does nothing (all calls are no-ops).

---

## Troubleshooting

### "Worker not processing items"

Check worker is alive:
```python
if manager.worker_thread and manager.worker_thread.is_alive():
    print("Worker is running")
else:
    print("Worker is dead! Call manager.start_worker()")
```

### "Items stuck in QUEUED"

Check queue size:
```python
print(f"Queue size: {manager.processing_queue.qsize()}")
```

If queue has items but worker is alive, check logs for errors.

### "Summary files not created"

Check batch directory exists:
```python
print(f"Batch dir: {manager.batch_dir}")
print(f"Exists: {manager.batch_dir.exists()}")
```

Check for file write errors in logs.

### "Progress not updating in UI"

Ensure UI has the method:
```python
if hasattr(manager.ui, 'display_summarization_progress'):
    print("UI supports progress updates")
else:
    print("UI doesn't have display_summarization_progress method")
```

---

## Comparison with V1

| Feature | V1 | V2 |
|---------|----|----|
| Calls per item | Multiple (transcript, comments separate) | One (merged data) |
| Workers | 8 competing | 1 sequential |
| State tracking | 5+ systems | 1 enum |
| Race conditions | Many | None |
| Debugging | Very difficult | Easy |
| Files saved | 1 (final) | 2 (scraped + complete) |
| Code complexity | High (1009 lines) | Low (650 lines) |

**Verdict:** V2 is simpler, more reliable, and easier to use.

---

## Next Steps

1. **Read the migration guide:** `docs/SUMMARIZATION_MANAGER_V2_MIGRATION.md`
2. **Update your scraping workflow** to merge data before calling manager
3. **Test with a small batch** (3-5 items)
4. **Monitor the logs** to ensure correct behavior
5. **Check the file output** to verify data is saved correctly
6. **Replace V1** once V2 is working

---

## Questions?

- Check code comments in `streaming_summarization_manager_v2.py`
- Read comparison doc: `docs/SUMMARIZATION_V1_VS_V2_COMPARISON.md`
- Read migration guide: `docs/SUMMARIZATION_MANAGER_V2_MIGRATION.md`

