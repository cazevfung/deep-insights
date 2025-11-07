"""
Test script to find bugs in workflow_direct.py and workflow_service.py.

This test exercises the workflow with debug mode enabled to identify issues.
"""
import os
import sys
import asyncio
import time
from pathlib import Path

# Enable debug mode
os.environ['WORKFLOW_DEBUG'] = 'true'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.services.workflow_service import WorkflowService
from app.websocket.manager import WebSocketManager
from tests.test_links_loader import TestLinksLoader


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.broadcast_messages = []
        self.registered_uis = {}
    
    async def broadcast(self, batch_id: str, message: dict):
        """Store broadcast messages for inspection."""
        self.broadcast_messages.append({
            'batch_id': batch_id,
            'message': message,
            'timestamp': time.time()
        })
        logger.debug(f"[MOCK_WS] Broadcast: batch_id={batch_id}, type={message.get('type')}")
    
    def register_ui(self, batch_id: str, ui):
        """Register UI instance."""
        self.registered_uis[batch_id] = ui
        logger.debug(f"[MOCK_WS] Registered UI for batch {batch_id}")
    
    def unregister_ui(self, batch_id: str):
        """Unregister UI instance."""
        if batch_id in self.registered_uis:
            del self.registered_uis[batch_id]
            logger.debug(f"[MOCK_WS] Unregistered UI for batch {batch_id}")


async def test_workflow_execution():
    """Test full workflow execution and identify bugs."""
    logger.info("=" * 80)
    logger.info("WORKFLOW DEBUG TEST - Starting")
    logger.info("=" * 80)
    
    # Load test links
    try:
        loader = TestLinksLoader()
        batch_id = loader.get_batch_id()
        logger.info(f"Loaded batch_id: {batch_id}")
        
        # Get link counts
        youtube_links = loader.get_links('youtube')
        bilibili_links = loader.get_links('bilibili')
        reddit_links = loader.get_links('reddit')
        article_links = loader.get_links('article')
        
        total_links = len(youtube_links) + len(bilibili_links) + len(reddit_links) + len(article_links)
        logger.info(f"Total links: {total_links}")
        logger.info(f"  YouTube: {len(youtube_links)}")
        logger.info(f"  Bilibili: {len(bilibili_links)}")
        logger.info(f"  Reddit: {len(reddit_links)}")
        logger.info(f"  Article: {len(article_links)}")
        
        # Calculate expected processes
        # YouTube: transcript + comments = 2 per link
        # Bilibili: transcript + comments = 2 per link
        # Reddit: 1 per link
        # Article: 1 per link
        expected_processes = (
            len(youtube_links) * 2 +
            len(bilibili_links) * 2 +
            len(reddit_links) +
            len(article_links)
        )
        logger.info(f"Expected processes: {expected_processes}")
        
    except Exception as e:
        logger.error(f"Failed to load test links: {e}", exc_info=True)
        return False
    
    # Create mock WebSocket manager
    ws_manager = MockWebSocketManager()
    
    # Create workflow service
    workflow_service = WorkflowService(ws_manager)
    
    # Track issues found
    issues = []
    
    try:
        logger.info(f"\n{'='*80}")
        logger.info("Starting workflow execution...")
        logger.info(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Run workflow (but we'll cancel it early to test cancellation)
        # Actually, let's run a shorter test - just test the scraping phase
        # by running the workflow but catching early
        
        # For now, let's test the link context loading
        logger.info("Testing link context loading...")
        await workflow_service._load_link_context(batch_id)
        
        # Check link context
        if batch_id not in workflow_service.link_context:
            issues.append("Link context not loaded")
            logger.error("❌ Link context not loaded")
        else:
            logger.info("✓ Link context loaded")
            
            # Verify context structure
            context = workflow_service.link_context[batch_id]
            for link_type in ['youtube', 'bilibili', 'reddit', 'article']:
                if link_type in context:
                    logger.info(f"  {link_type}: {len(context[link_type])} links")
                else:
                    logger.warning(f"  {link_type}: missing from context")
        
        # Test progress callback creation
        logger.info("\nTesting progress callback creation...")
        import queue
        progress_queue = queue.Queue()
        progress_callback = workflow_service._create_progress_callback(batch_id, progress_queue)
        
        if progress_callback is None:
            issues.append("Progress callback is None")
            logger.error("❌ Progress callback is None")
        else:
            logger.info("✓ Progress callback created")
        
        # Test message processing
        logger.info("\nTesting message processing...")
        
        # Send test messages
        test_messages = [
            {
                'type': 'scraping:start',
                'message': 'Test start',
                'batch_id': batch_id
            },
            {
                'type': 'scraping:discover',
                'message': 'Test discover',
                'total_links': total_links,
                'batch_id': batch_id
            },
            {
                'type': 'scraping:start_link',
                'scraper': 'youtube',
                'url': 'https://test.com',
                'link_id': 'test_link_1',
                'index': 1,
                'total': 1,
                'batch_id': batch_id
            },
            {
                'type': 'scraping:complete_link',
                'scraper': 'youtube',
                'url': 'https://test.com',
                'link_id': 'test_link_1',
                'status': 'success',
                'batch_id': batch_id
            },
            {
                'type': 'scraping:start_link',
                'scraper': 'youtubecomments',
                'url': 'https://test.com',
                'link_id': 'test_link_1',  # Should be transformed to test_link_1_comments
                'index': 1,
                'total': 1,
                'batch_id': batch_id
            },
            {
                'type': 'scraping:complete_link',
                'scraper': 'youtubecomments',
                'url': 'https://test.com',
                'link_id': 'test_link_1',  # Should be transformed to test_link_1_comments
                'status': 'success',
                'batch_id': batch_id
            },
        ]
        
        for msg in test_messages:
            try:
                progress_callback(msg)
                logger.debug(f"  Sent: {msg['type']}")
            except Exception as e:
                issues.append(f"Error sending {msg['type']}: {e}")
                logger.error(f"❌ Error sending {msg['type']}: {e}", exc_info=True)
        
        # Check queue
        queue_size = progress_queue.qsize()
        logger.info(f"  Queue size after sending messages: {queue_size}")
        
        if queue_size == 0:
            issues.append("No messages in queue after sending")
            logger.error("❌ No messages in queue")
        else:
            logger.info(f"✓ {queue_size} messages in queue")
        
        # Test message processing (run for a short time)
        logger.info("\nTesting message processing (5 seconds)...")
        process_task = asyncio.create_task(
            workflow_service._process_progress_queue(progress_queue, batch_id)
        )
        
        # Wait a bit for processing
        await asyncio.sleep(5)
        
        # Cancel processing task
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass
        
        # Check final queue size
        final_queue_size = progress_queue.qsize()
        logger.info(f"  Final queue size: {final_queue_size}")
        
        # Check broadcast messages
        broadcast_count = len(ws_manager.broadcast_messages)
        logger.info(f"  Broadcast messages: {broadcast_count}")
        
        if broadcast_count == 0:
            issues.append("No broadcast messages sent")
            logger.warning("⚠ No broadcast messages sent")
        else:
            logger.info(f"✓ {broadcast_count} broadcast messages sent")
            # Log message types
            message_types = [msg['message'].get('type') for msg in ws_manager.broadcast_messages]
            logger.info(f"  Message types: {set(message_types)}")
        
        # Test link ID transformations
        logger.info("\nTesting link ID transformations...")
        if hasattr(workflow_service, '_link_id_transformations'):
            transformations = workflow_service._link_id_transformations.get(batch_id, [])
            logger.info(f"  Transformations recorded: {len(transformations)}")
            for trans in transformations:
                logger.info(
                    f"    {trans['original']} -> {trans['transformed']} "
                    f"({trans['scraper']}, {trans['reason']})"
                )
            
            # Check if comments scrapers were transformed
            comments_transforms = [
                t for t in transformations
                if t['scraper'] in ['youtubecomments', 'bilibilicomments']
            ]
            if len(comments_transforms) == 0:
                issues.append("No link ID transformations for comments scrapers")
                logger.warning("⚠ No transformations for comments scrapers")
            else:
                logger.info(f"✓ {len(comments_transforms)} comments scraper transformations")
        
        # Test queue statistics
        logger.info("\nTesting queue statistics...")
        if hasattr(workflow_service, '_queue_stats'):
            stats = workflow_service._queue_stats.get(batch_id, {})
            logger.info(f"  Messages processed: {stats.get('messages_processed', 0)}")
            logger.info(f"  Messages dropped: {stats.get('messages_dropped', 0)}")
            logger.info(f"  Max queue size: {stats.get('max_queue_size', 0)}")
            
            if stats.get('messages_dropped', 0) > 0:
                issues.append(f"{stats['messages_dropped']} messages dropped")
                logger.warning(f"⚠ {stats['messages_dropped']} messages dropped")
        
        elapsed = time.time() - start_time
        logger.info(f"\nTest completed in {elapsed:.2f}s")
        
    except Exception as e:
        issues.append(f"Test exception: {e}")
        logger.error(f"❌ Test failed: {e}", exc_info=True)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    if issues:
        logger.error(f"Found {len(issues)} potential issues:")
        for i, issue in enumerate(issues, 1):
            logger.error(f"  {i}. {issue}")
        return False
    else:
        logger.info("✓ No issues found!")
        return True


async def test_message_validation():
    """Test message validation logic."""
    logger.info("\n" + "=" * 80)
    logger.info("MESSAGE VALIDATION TEST")
    logger.info("=" * 80)
    
    # Import validation function
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "lib"))
    from workflow_direct import _validate_message
    
    test_cases = [
        # Valid messages
        ({
            'type': 'scraping:start',
            'message': 'Test'
        }, True, 'Valid scraping:start'),
        
        ({
            'type': 'scraping:complete_link',
            'scraper': 'youtube',
            'url': 'https://test.com',
            'link_id': 'test_1',
            'status': 'success'
        }, True, 'Valid scraping:complete_link'),
        
        # Invalid messages
        ({
            'type': 'scraping:start'
            # Missing 'message'
        }, False, 'Missing required field'),
        
        ({
            'type': 'scraping:complete_link',
            'scraper': 'youtube',
            'url': 'https://test.com',
            'link_id': 'test_1',
            'status': 'invalid_status'  # Invalid status
        }, False, 'Invalid status value'),
        
        ({
            'type': 'scraping:start_link',
            'scraper': 'youtube',
            'url': 'https://test.com',
            'link_id': 'test_1',
            'index': 1,
            'total': 1,
            'progress': 150.0  # Invalid progress
        }, False, 'Invalid progress value'),
    ]
    
    issues = []
    for message, expected_valid, description in test_cases:
        is_valid, error_msg = _validate_message(message, message.get('type', ''))
        if is_valid != expected_valid:
            issues.append(f"{description}: expected_valid={expected_valid}, got={is_valid}")
            logger.error(f"❌ {description}: validation={is_valid}, expected={expected_valid}")
            if error_msg:
                logger.error(f"   Error: {error_msg}")
        else:
            logger.info(f"✓ {description}: validation={is_valid}")
    
    if issues:
        logger.error(f"\nFound {len(issues)} validation issues")
        return False
    else:
        logger.info("\n✓ All validation tests passed")
        return True


async def main():
    """Run all tests."""
    logger.info("Starting workflow debug tests...")
    logger.info(f"Debug mode: {os.environ.get('WORKFLOW_DEBUG', 'false')}")
    
    # Test message validation
    validation_ok = await test_message_validation()
    
    # Test workflow execution
    workflow_ok = await test_workflow_execution()
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    
    if validation_ok and workflow_ok:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG"
    )
    
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

