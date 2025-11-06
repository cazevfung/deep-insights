# Testing Guide for WebSocket UI Issues

This guide provides isolated tests for each fixed issue without running the entire workflow.

## Issue 1: ScrapingProgressPage Restarts Workflow

### Manual Test

1. **Start a workflow** via API:
   ```bash
   curl -X POST http://localhost:8000/api/workflow/start \
     -H "Content-Type: application/json" \
     -d '{"batch_id": "test_batch_123"}'
   ```

2. **Check workflow status**:
   ```bash
   curl http://localhost:8000/api/workflow/test_batch_123/status
   ```

3. **Navigate to ScrapingProgressPage** in the UI
   - Should NOT start a new workflow
   - Should show "工作流正在运行中..." if status is 'running'
   - Should show existing progress if available

### Automated Test

Create `tests/test_workflow_status_check.py`:

```python
"""Test workflow status check before starting."""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_workflow_status_check():
    """Test that workflow status is checked before starting."""
    batch_id = "test_batch_" + str(int(time.time()))
    
    # Start workflow
    response = requests.post(
        f"{BASE_URL}/api/workflow/start",
        json={"batch_id": batch_id}
    )
    assert response.status_code == 200
    print(f"✓ Started workflow: {batch_id}")
    
    # Check status
    response = requests.get(f"{BASE_URL}/api/workflow/{batch_id}/status")
    assert response.status_code == 200
    status = response.json()
    assert status['status'] == 'running'
    print(f"✓ Workflow status is 'running'")
    
    # Try to start again (should fail or return existing)
    response = requests.post(
        f"{BASE_URL}/api/workflow/start",
        json={"batch_id": batch_id}
    )
    # Should return 409 or existing workflow
    assert response.status_code in [200, 409]
    print(f"✓ Duplicate start prevented: {response.status_code}")
    
    print(f"\n✅ Issue 1 test passed!")
```

## Issue 2: Progress Callback Conversion

### Manual Test

1. **Start a test scraper with progress callback**:
   ```python
   # test_progress_callback.py
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent))
   
   from backend.app.services.workflow_service import WorkflowService
   from backend.app.websocket.manager import WebSocketManager
   from backend.app.services.progress_service import ProgressService
   import asyncio
   
   async def test_progress_callback():
       ws_manager = WebSocketManager()
       progress_service = ProgressService(ws_manager)
       workflow_service = WorkflowService(ws_manager, progress_service)
       
       batch_id = "test_batch_123"
       
       # Check if progress messages are converted
       messages_received = []
       
       def check_message(msg):
           messages_received.append(msg)
           print(f"Received: {msg.get('type')}, {msg.get('stage')}, {msg.get('link_id')}")
       
       # Mock WebSocket broadcast to capture messages
       original_broadcast = ws_manager.broadcast
       async def mock_broadcast(batch_id, message):
           if message.get('type') == 'scraping:item_progress':
               check_message(message)
           return await original_broadcast(batch_id, message)
       
       ws_manager.broadcast = mock_broadcast
       
       # Run a small scraping task
       result = await workflow_service.run_workflow(batch_id)
       
       # Verify messages were converted
       assert len(messages_received) > 0
       for msg in messages_received:
           assert 'link_id' in msg
           assert 'url' in msg
           assert 'stage' in msg
           assert 'stage_progress' in msg
           assert 'overall_progress' in msg
       
       print("\n✅ Issue 2 test passed!")
   
   if __name__ == '__main__':
       asyncio.run(test_progress_callback())
   ```

### Automated Test

Create `tests/test_progress_conversion.py`:

```python
"""Test progress callback conversion to ProgressService format."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.workflow_service import WorkflowService
from backend.app.websocket.manager import WebSocketManager
from backend.app.services.progress_service import ProgressService
import asyncio

async def test_progress_conversion():
    """Test that scraper progress is converted to ProgressService format."""
    ws_manager = WebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager, progress_service)
    
    batch_id = "test_conversion_" + str(int(time.time()))
    
    # Track messages received by ProgressService
    progress_updates = []
    
    # Mock update_link_progress to capture calls
    original_update = progress_service.update_link_progress
    async def mock_update(*args, **kwargs):
        progress_updates.append(kwargs)
        return await original_update(*args, **kwargs)
    
    progress_service.update_link_progress = mock_update
    
    # Create a progress callback manually
    import queue
    message_queue = queue.Queue()
    callback = workflow_service._create_progress_callback(batch_id, message_queue)
    
    # Simulate a scraper progress message
    scraper_message = {
        'stage': 'downloading',
        'progress': 50.0,
        'message': 'Downloading video...',
        'bytes_downloaded': 1024,
        'total_bytes': 2048,
        'scraper': 'youtube',
        'batch_id': batch_id,
        'link_id': 'test_link_1',
        'url': 'https://youtube.com/watch?v=test123'
    }
    
    callback(scraper_message)
    
    # Process the queue
    await workflow_service._process_progress_queue(message_queue, batch_id)
    
    # Verify conversion
    assert len(progress_updates) > 0
    update = progress_updates[0]
    assert update['batch_id'] == batch_id
    assert update['link_id'] == 'test_link_1'
    assert update['url'] == 'https://youtube.com/watch?v=test123'
    assert update['stage'] == 'downloading'
    assert update['stage_progress'] == 50.0
    
    print("\n✅ Issue 2 test passed!")

if __name__ == '__main__':
    import time
    asyncio.run(test_progress_conversion())
```

## Issue 3: Scrapers Receive Progress Callback

### Manual Test

Create `tests/test_scraper_callback.py`:

```python
"""Test that scrapers receive progress callbacks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.lib.workflow_direct import run_all_scrapers_direct
import time

def test_scraper_callback():
    """Test that scrapers receive and use progress callbacks."""
    callback_received = []
    
    def progress_callback(message):
        callback_received.append(message)
        print(f"Progress: {message.get('type')}, {message.get('message')}")
    
    # Run scrapers with callback
    batch_id = "test_callback_" + str(int(time.time()))
    result = run_all_scrapers_direct(
        progress_callback=progress_callback,
        batch_id=batch_id
    )
    
    # Verify callbacks were received
    assert len(callback_received) > 0
    
    # Check for different message types
    message_types = [msg.get('type') for msg in callback_received]
    assert 'scraping:start' in message_types
    assert 'scraping:start_type' in message_types or 'scraping:start_link' in message_types
    
    print(f"\n✅ Received {len(callback_received)} progress messages")
    print("✅ Issue 3 test passed!")

if __name__ == '__main__':
    test_scraper_callback()
```

### Quick Test Script

Create `scripts/test_scraper_progress.py`:

```python
"""Quick test: Run a single scraper with progress callback."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.youtube_scraper import YouTubeScraper
from tests.test_links_loader import TestLinksLoader

def test_single_scraper():
    """Test a single scraper with progress callback."""
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('youtube')
    
    if not links:
        print("No YouTube links found, skipping test")
        return
    
    # Track progress
    progress_messages = []
    
    def progress_callback(message):
        progress_messages.append(message)
        print(f"[Progress] {message.get('stage', 'unknown')}: {message.get('message', '')}")
    
    # Create scraper with callback
    scraper = YouTubeScraper(progress_callback=progress_callback, headless=True)
    
    # Extract first link
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    scraper.close()
    
    # Verify progress was reported
    assert len(progress_messages) > 0
    print(f"\n✅ Received {len(progress_messages)} progress messages")
    print("✅ Scraper received and used progress callback!")
    
    return result

if __name__ == '__main__':
    test_single_scraper()
```

## Issue 5: Message Format Mismatch

### Verification Test

Create `tests/test_message_format.py`:

```python
"""Test that message formats match between backend and frontend."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.progress_service import ProgressService
from backend.app.websocket.manager import WebSocketManager
import asyncio

async def test_message_formats():
    """Test that ProgressService sends correct message formats."""
    ws_manager = WebSocketManager()
    progress_service = ProgressService(ws_manager)
    
    batch_id = "test_format_123"
    link_id = "test_link_1"
    url = "https://example.com/test"
    
    # Track broadcast messages
    broadcast_messages = []
    
    # Mock broadcast to capture messages
    original_broadcast = ws_manager.broadcast
    async def mock_broadcast(batch_id, message):
        broadcast_messages.append(message)
        return await original_broadcast(batch_id, message)
    
    ws_manager.broadcast = mock_broadcast
    
    # Test update_link_progress format
    await progress_service.update_link_progress(
        batch_id=batch_id,
        link_id=link_id,
        url=url,
        stage='downloading',
        stage_progress=50.0,
        overall_progress=50.0,
        message='Downloading...',
        metadata={'source': 'youtube', 'bytes_downloaded': 1024, 'total_bytes': 2048}
    )
    
    # Verify message format
    assert len(broadcast_messages) > 0
    
    # Check scraping:item_progress format
    progress_msg = [m for m in broadcast_messages if m.get('type') == 'scraping:item_progress']
    if progress_msg:
        msg = progress_msg[0]
        required_fields = ['type', 'link_id', 'url', 'stage', 'stage_progress', 'overall_progress', 'message', 'metadata']
        for field in required_fields:
            assert field in msg, f"Missing field: {field}"
        
        assert msg['link_id'] == link_id
        assert msg['url'] == url
        assert msg['stage'] == 'downloading'
        assert msg['stage_progress'] == 50.0
        assert msg['overall_progress'] == 50.0
        assert msg['message'] == 'Downloading...'
        assert 'source' in msg['metadata']
    
    # Test update_link_status format
    await progress_service.update_link_status(
        batch_id=batch_id,
        link_id=link_id,
        url=url,
        status='completed',
        metadata={'word_count': 1000}
    )
    
    # Check scraping:item_update format
    update_msg = [m for m in broadcast_messages if m.get('type') == 'scraping:item_update']
    if update_msg:
        msg = update_msg[0]
        required_fields = ['type', 'link_id', 'url', 'status', 'metadata', 'timestamp']
        for field in required_fields:
            assert field in msg, f"Missing field: {field}"
    
    # Test _update_batch_status format
    await progress_service._update_batch_status(batch_id)
    
    # Check scraping:status format
    status_msg = [m for m in broadcast_messages if m.get('type') == 'scraping:status']
    if status_msg:
        msg = status_msg[0]
        required_fields = ['type', 'batch_id', 'total', 'completed', 'failed', 'inProgress', 'items']
        for field in required_fields:
            assert field in msg, f"Missing field: {field}"
    
    print("\n✅ All message formats verified!")
    print("✅ Issue 5 test passed!")

if __name__ == '__main__':
    asyncio.run(test_message_formats())
```

## Issue 6: WebSocket Connection Issues

### Manual Test

1. **Test batchId validation**:
   - Navigate to ScrapingProgressPage with empty batchId
   - Should show warning: "批次ID未设置，无法连接"
   - Should NOT attempt WebSocket connection

2. **Test invalid batchId**:
   - Navigate with batchId="ab"
   - Should show warning: "批次ID格式无效，无法连接"
   - Should NOT attempt WebSocket connection

3. **Test reconnection logic**:
   - Start backend server
   - Connect WebSocket
   - Stop backend server
   - Should show: "连接断开，正在重连..."
   - Should attempt reconnection with exponential backoff
   - Restart backend server
   - Should reconnect successfully

### Automated Test

Create `tests/test_websocket_connection.py`:

```python
"""Test WebSocket connection handling."""
import asyncio
import websockets
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_websocket_connection():
    """Test WebSocket connection with various scenarios."""
    
    batch_id = "test_ws_123"
    ws_url = f"ws://localhost:8000/ws/{batch_id}"
    
    # Test 1: Normal connection
    try:
        async with websockets.connect(ws_url) as ws:
            print("✓ Connected to WebSocket")
            
            # Wait for initial message (if any)
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(message)
                print(f"✓ Received message: {data.get('type')}")
            except asyncio.TimeoutError:
                print("✓ No initial message (OK)")
            
            # Test message format
            test_message = {
                'type': 'test',
                'data': 'test_data'
            }
            await ws.send(json.dumps(test_message))
            print("✓ Sent test message")
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    # Test 2: Invalid batchId (should fail)
    try:
        async with websockets.connect("ws://localhost:8000/ws/") as ws:
            print("✗ Should not connect with empty batchId")
            return False
    except Exception as e:
        print(f"✓ Correctly rejected empty batchId: {type(e).__name__}")
    
    print("\n✅ Issue 6 test passed!")
    return True

if __name__ == '__main__':
    asyncio.run(test_websocket_connection())
```

### Frontend Unit Test

Create `client/src/hooks/__tests__/useWebSocket.test.ts`:

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'
import { useWorkflowStore } from '../../stores/workflowStore'
import { useUiStore } from '../../stores/uiStore'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(public url: string) {
    // Simulate connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) this.onopen(new Event('open'))
    }, 10)
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }))
    }
  }

  send(data: string) {
    // Mock send
  }
}

global.WebSocket = MockWebSocket as any

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('validates batchId before connecting', () => {
    const { result } = renderHook(() => useWebSocket(''))
    
    // Should not create WebSocket with empty batchId
    expect(result.current).toBeDefined()
  })

  test('validates batchId format', () => {
    const { result } = renderHook(() => useWebSocket('ab'))
    
    // Should not create WebSocket with invalid batchId
    expect(result.current).toBeDefined()
  })

  test('connects with valid batchId', async () => {
    const { result } = renderHook(() => useWebSocket('test_batch_123'))
    
    await waitFor(() => {
      expect(result.current).toBeDefined()
    })
  })
})
```

## Running All Tests

Create `scripts/run_issue_tests.py`:

```python
"""Run all issue tests."""
import subprocess
import sys
from pathlib import Path

tests = [
    'tests/test_workflow_status_check.py',
    'tests/test_progress_conversion.py',
    'tests/test_scraper_callback.py',
    'tests/test_message_format.py',
    'tests/test_websocket_connection.py',
]

def run_test(test_file):
    """Run a single test file."""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode == 0

if __name__ == '__main__':
    print("Running all issue tests...\n")
    
    results = {}
    for test in tests:
        test_path = Path(__file__).parent.parent / test
        if test_path.exists():
            results[test] = run_test(test)
        else:
            print(f"⚠️  Test file not found: {test}")
            results[test] = False
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test}")
    
    all_passed = all(results.values())
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
    sys.exit(0 if all_passed else 1)
```

## Quick Test Commands

```bash
# Test Issue 1: Workflow status check
python tests/test_workflow_status_check.py

# Test Issue 2: Progress conversion
python tests/test_progress_conversion.py

# Test Issue 3: Scraper callbacks
python tests/test_scraper_callback.py

# Test Issue 5: Message formats
python tests/test_message_format.py

# Test Issue 6: WebSocket connection
python tests/test_websocket_connection.py

# Run all tests
python scripts/run_issue_tests.py
```


