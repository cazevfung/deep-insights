"""Quick test: Progress callback conversion."""
import sys
import asyncio
import queue
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.workflow_service import WorkflowService
from backend.app.websocket.manager import WebSocketManager
from backend.app.services.progress_service import ProgressService

async def test_progress_conversion():
    """Test that scraper progress is converted to ProgressService format."""
    
    print("Testing progress callback conversion...")
    print()
    
    ws_manager = WebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager, progress_service)
    
    batch_id = "test_conversion_123"
    
    # Track messages received by ProgressService
    progress_updates = []
    
    # Mock update_link_progress to capture calls
    original_update = progress_service.update_link_progress
    async def mock_update(*args, **kwargs):
        progress_updates.append(kwargs)
        print(f"  ProgressService.update_link_progress called:")
        print(f"    batch_id: {kwargs.get('batch_id')}")
        print(f"    link_id: {kwargs.get('link_id')}")
        print(f"    url: {kwargs.get('url')}")
        print(f"    stage: {kwargs.get('stage')}")
        print(f"    stage_progress: {kwargs.get('stage_progress')}")
        print()
        return await original_update(*args, **kwargs)
    
    progress_service.update_link_progress = mock_update
    
    # Create a progress callback manually
    message_queue = queue.Queue()
    callback = workflow_service._create_progress_callback(batch_id, message_queue)
    
    # Simulate a scraper progress message
    print("Simulating scraper progress message...")
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
    
    print(f"  Original message: {scraper_message}")
    print()
    
    callback(scraper_message)
    
    # Process the queue
    print("Processing progress queue...")
    # Process one message
    try:
        message = message_queue.get_nowait()
        if message.get('action') == 'update_link_progress':
            await workflow_service._process_progress_queue(message_queue, batch_id)
            # Process the actual update
            await progress_service.update_link_progress(**message)
    except queue.Empty:
        print("  No messages in queue")
    
    # Verify conversion
    print()
    print("="*60)
    if len(progress_updates) > 0:
        update = progress_updates[0]
        print("✅ Conversion successful!")
        print(f"  Converted message has all required fields:")
        print(f"    batch_id: {update.get('batch_id')}")
        print(f"    link_id: {update.get('link_id')}")
        print(f"    url: {update.get('url')}")
        print(f"    stage: {update.get('stage')}")
        print(f"    stage_progress: {update.get('stage_progress')}")
        print(f"    overall_progress: {update.get('overall_progress')}")
    else:
        print("❌ No progress updates received!")
    
    print("="*60)

if __name__ == '__main__':
    asyncio.run(test_progress_conversion())




