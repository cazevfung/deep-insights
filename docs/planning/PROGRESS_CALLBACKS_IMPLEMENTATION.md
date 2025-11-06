# Progress Callbacks Implementation - Minimal Changes

## Overview

Added **optional progress callbacks** to test functions with **minimal changes** that maintain backwards compatibility. All existing test scripts continue to work unchanged.

---

## Changes Made

### 1. `test_full_workflow_integration.py`

#### Modified Functions:

**`run_all_scrapers(progress_callback=None)`**
- Added optional `progress_callback` parameter
- Calls callback with progress messages if provided
- Falls back to print statements if callback is None (backwards compatible)

**`verify_scraper_results(batch_id, progress_callback=None)`**
- Added optional `progress_callback` parameter
- Reports progress on verification steps
- Falls back to print statements if callback is None

**`run_research_agent(batch_id, ui=None, progress_callback=None)`**
- Added optional `ui` parameter (allows custom UI with callbacks)
- Added optional `progress_callback` parameter
- Falls back to print statements if callback is None

#### Progress Message Types:

- `scraping:start` - Scraping started
- `scraping:complete` - Scraping completed with summary
- `verification:progress` - Verification in progress
- `verification:complete` - Verification completed
- `research:start` - Research agent started
- `research:complete` - Research agent completed
- `error` - Error occurred
- `warning` - Warning message

---

### 2. `test_all_scrapers_and_save_json.py`

#### Modified Functions:

**`test_all_scrapers_and_save(progress_callback=None)`**
- Added optional `progress_callback` parameter
- Reports progress as each scraper starts and completes
- Falls back to print statements if callback is None

#### Progress Message Types:

- `scraping:discover` - Discovering scraper scripts
- `scraping:start_script` - Individual scraper script started
- `scraping:script_complete` - Individual scraper script completed
- `scraping:summary` - Final summary with all results
- `warning` - Warning message

---

## Backwards Compatibility

✅ **All existing test scripts work unchanged**
- Functions default to `progress_callback=None`
- Print statements are used when callback is None
- No breaking changes to existing code

✅ **Test scripts can be run as before:**
```bash
python tests/test_full_workflow_integration.py
python tests/test_all_scrapers_and_save_json.py
```

✅ **Functions can be imported and used as before:**
```python
from tests.test_full_workflow_integration import run_all_scrapers
result = run_all_scrapers()  # Works exactly as before
```

---

## Usage Examples

### Example 1: Using with Progress Callback

```python
from tests.test_full_workflow_integration import run_all_scrapers

def progress_handler(message):
    print(f"[PROGRESS] {message['type']}: {message['message']}")

result = run_all_scrapers(progress_callback=progress_handler)
```

### Example 2: Backend Integration with WebSocket

```python
import asyncio
from tests.test_full_workflow_integration import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent
)

async def run_workflow_with_progress(batch_id: str, ws_manager):
    """Run workflow with real-time WebSocket progress updates."""
    
    def progress_callback(message):
        """Send progress updates via WebSocket."""
        asyncio.create_task(ws_manager.broadcast(batch_id, message))
    
    # Run scrapers with progress callbacks
    scrapers_result = await asyncio.to_thread(
        run_all_scrapers,
        progress_callback=progress_callback
    )
    
    # Verify with progress callbacks
    verified = await asyncio.to_thread(
        verify_scraper_results,
        batch_id,
        progress_callback=progress_callback
    )
    
    # Run research agent with progress callbacks
    # Note: For research agent, you'll want to use a custom UI that supports callbacks
    result = await asyncio.to_thread(
        run_research_agent,
        batch_id,
        ui=None,  # Or provide custom UI with callbacks
        progress_callback=progress_callback
    )
    
    return result
```

### Example 3: Using with Custom UI (Research Agent)

```python
from tests.test_full_workflow_integration import run_research_agent
from app.services.websocket_ui import WebSocketUI  # Your custom UI

def progress_callback(message):
    print(f"Progress: {message}")

# Use custom UI with WebSocket integration
custom_ui = WebSocketUI(ws_manager, batch_id)

result = run_research_agent(
    batch_id=batch_id,
    ui=custom_ui,  # Custom UI with built-in callbacks
    progress_callback=progress_callback  # High-level progress
)
```

---

## Progress Message Structure

All progress messages follow this structure:

```python
{
    "type": "message_type",  # e.g., "scraping:start", "scraping:complete"
    "message": "Human-readable message",
    # ... additional fields based on message type
}
```

### Message Types and Fields

#### Scraping Messages
- `scraping:start` - `{"type": "scraping:start", "message": "..."}`
- `scraping:discover` - `{"type": "scraping:discover", "message": "..."}`
- `scraping:start_script` - `{"type": "scraping:start_script", "message": "...", "script": "...", "line": "..."}`
- `scraping:script_complete` - `{"type": "scraping:script_complete", "message": "...", "script": "...", "success": bool, "duration": float, "progress": "1/5"}`
- `scraping:summary` - `{"type": "scraping:summary", "message": "...", "passed": int, "total": int, "results": [...]}`
- `scraping:complete` - `{"type": "scraping:complete", "message": "...", "passed": int, "total": int, "batch_id": "..."}`

#### Verification Messages
- `verification:progress` - `{"type": "verification:progress", "message": "...", "file_count": int}`
- `verification:complete` - `{"type": "verification:complete", "message": "...", "file_count": int}`

#### Research Messages
- `research:start` - `{"type": "research:start", "message": "..."}`
- `research:complete` - `{"type": "research:complete", "message": "...", "elapsed_time": float, "result": {...}}`

#### Error/Warning Messages
- `error` - `{"type": "error", "message": "..."}`
- `warning` - `{"type": "warning", "message": "..."}`

---

## Testing

### Test Backwards Compatibility

```bash
# Run existing tests - should work exactly as before
python tests/test_full_workflow_integration.py
python tests/test_all_scrapers_and_save_json.py
```

### Test with Callbacks

```python
# test_progress_callbacks.py
from tests.test_full_workflow_integration import run_all_scrapers

messages = []

def callback(message):
    messages.append(message)
    print(f"Callback: {message}")

result = run_all_scrapers(progress_callback=callback)
print(f"Received {len(messages)} progress messages")
```

---

## Migration Guide

### For Backend Services

**Before:**
```python
from tests.test_full_workflow_integration import run_all_scrapers

result = await asyncio.to_thread(run_all_scrapers)
```

**After (with progress):**
```python
from tests.test_full_workflow_integration import run_all_scrapers

def progress_callback(message):
    await ws_manager.broadcast(batch_id, message)

result = await asyncio.to_thread(
    run_all_scrapers,
    progress_callback=progress_callback
)
```

**Note:** Since `asyncio.to_thread()` runs in a thread, the callback will be called from that thread. You may need to use `asyncio.run_coroutine_threadsafe()` or similar to safely call async code from the callback.

---

## Implementation Details

### Thread Safety

Progress callbacks are called from the same thread as the function execution. For async WebSocket broadcasting, you may need to:

1. Use `asyncio.run_coroutine_threadsafe()` to safely call async code
2. Use a thread-safe queue to pass messages to the async event loop
3. Use a synchronous callback that queues messages for async processing

### Example: Thread-Safe Async Callback

```python
import asyncio
from asyncio import Queue

# Create a queue for progress messages
progress_queue = Queue()

def progress_callback(message):
    """Thread-safe callback that queues messages."""
    try:
        # Try to put_nowait (non-blocking)
        progress_queue.put_nowait(message)
    except:
        pass  # Queue full, skip message

async def process_progress_messages():
    """Process queued progress messages."""
    while True:
        message = await progress_queue.get()
        await ws_manager.broadcast(batch_id, message)

# Start background task
asyncio.create_task(process_progress_messages())

# Run function with callback
result = await asyncio.to_thread(
    run_all_scrapers,
    progress_callback=progress_callback
)
```

---

## Summary

✅ **Minimal changes** - Only added optional parameters  
✅ **Backwards compatible** - All existing code works unchanged  
✅ **Real-time progress** - Callbacks provide detailed progress updates  
✅ **Flexible** - Can use callbacks or not, depending on needs  

The test scripts are now ready for backend integration with real-time progress updates!


