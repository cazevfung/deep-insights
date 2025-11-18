"""Test V2 integration with adapter and data merger."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.phases.streaming_summarization_adapter import StreamingSummarizationAdapter
from research.client import QwenStreamingClient
from core.config import Config
from research.session import ResearchSession
from loguru import logger
import time


def test_v2_integration_basic():
    """Test basic V2 integration with adapter and data merger."""
    
    logger.info("=" * 80)
    logger.info("Testing V2 Integration")
    logger.info("=" * 80)
    
    # Create test batch ID
    batch_id = f"test_{int(time.time())}"
    logger.info(f"Test batch ID: {batch_id}")
    
    # Create client
    config = Config()
    api_key = config.get("qwen.api_key")
    if not api_key:
        logger.error("No API key found! Set qwen.api_key in config.yaml")
        return False
    
    client = QwenStreamingClient(api_key=api_key)
    
    # Create simple UI mock
    class SimpleUI:
        def display_message(self, message, level="info"):
            logger.info(f"[UI {level}] {message}")
        
        def display_summarization_progress(self, **kwargs):
            logger.info(f"[UI Progress] {kwargs}")
        
        def display_summary(self, **kwargs):
            logger.info(f"[UI Summary] {kwargs}")
    
    ui = SimpleUI()
    
    # Create session
    session = ResearchSession.create_or_load(batch_id)
    
    # Create adapter (wraps V2 + data merger)
    logger.info("Creating StreamingSummarizationAdapter...")
    adapter = StreamingSummarizationAdapter(
        client=client,
        config=config,
        ui=ui,
        session=session,
        batch_id=batch_id
    )
    
    # Register test items
    test_items = ["test_yt1", "test_bili1", "test_reddit1"]
    source_types = {
        "test_yt1": "youtube",
        "test_bili1": "bilibili",
        "test_reddit1": "reddit"
    }
    
    logger.info(f"Registering {len(test_items)} test items...")
    adapter.register_expected_items(test_items, sources=source_types)
    
    # Start workers
    logger.info("Starting workers...")
    adapter.start_workers()
    
    # Check worker is alive
    if adapter.workers:
        logger.info(f"✓ Worker started: {adapter.workers[0].is_alive()}")
    else:
        logger.error("✗ No workers started!")
        return False
    
    # Simulate scraping completing for YouTube item (2-part)
    logger.info("\n--- Simulating YouTube scraping (2-part) ---")
    
    # Transcript completes first
    transcript_data = {
        'source': 'youtube',
        'metadata': {
            'title': 'Test Video',
            'url': 'https://youtube.com/watch?v=test123'
        },
        'transcript': 'This is a test transcript. ' * 50  # Make it realistic length
    }
    
    logger.info("Sending transcript completion...")
    adapter.on_scraping_complete("test_yt1", transcript_data)
    
    # Check if item is in merger (not yet complete)
    pending = adapter.data_merger.get_pending_items()
    if "test_yt1" in pending:
        logger.info("✓ Item in data merger, waiting for comments")
    else:
        logger.warning("✗ Item not in merger - may have completed prematurely")
    
    # Wait a moment
    time.sleep(0.5)
    
    # Comments complete second
    comments_data = {
        'source': 'youtube',
        'metadata': {},
        'comments': [
            {'author': 'User1', 'text': 'Great video!'},
            {'author': 'User2', 'text': 'Very helpful!'},
        ]
    }
    
    logger.info("Sending comments completion...")
    adapter.on_scraping_complete("test_yt1_comments", comments_data)
    
    # Check if item completed merging
    time.sleep(0.5)
    pending = adapter.data_merger.get_pending_items()
    if "test_yt1" not in pending:
        logger.info("✓ Item completed merging and sent to V2")
    else:
        logger.warning("✗ Item still in merger - merge may have failed")
    
    # Simulate Reddit item (1-part, no merging needed)
    logger.info("\n--- Simulating Reddit scraping (1-part) ---")
    
    reddit_data = {
        'source': 'reddit',
        'metadata': {
            'title': 'Test Reddit Post',
            'url': 'https://reddit.com/r/test/comments/abc123'
        },
        'transcript': 'This is a test Reddit post content. ' * 30,
        'comments': [
            {'author': 'Redditor1', 'text': 'Interesting post!'},
        ]
    }
    
    logger.info("Sending Reddit completion...")
    adapter.on_scraping_complete("test_reddit1", reddit_data)
    
    # Wait for processing
    logger.info("\nWaiting for summarization to complete...")
    logger.info("(This will call AI API, may take 10-30 seconds per item)")
    
    # Wait with timeout
    success = adapter.wait_for_completion(timeout=120)  # 2 minutes
    
    if success:
        logger.info("✓ All items completed!")
    else:
        logger.warning("✗ Timeout - not all items completed")
    
    # Get statistics
    stats = adapter.get_statistics()
    logger.info(f"\nFinal Statistics:")
    logger.info(f"  Total: {stats.get('total', 0)}")
    logger.info(f"  Scraped: {stats.get('scraped', 0)}")
    logger.info(f"  Summarized: {stats.get('summarized', 0)}")
    logger.info(f"  Created: {stats.get('created', 0)}")
    logger.info(f"  Reused: {stats.get('reused', 0)}")
    logger.info(f"  Failed: {stats.get('failed', 0)}")
    logger.info(f"  Merger Completed: {stats.get('merger_completed', 0)}")
    logger.info(f"  Merger Pending: {stats.get('merger_pending', 0)}")
    
    # Get results
    results = adapter.get_all_summarized_data()
    logger.info(f"\nCompleted Items: {list(results.keys())}")
    
    # Shutdown
    logger.info("\nShutting down...")
    adapter.shutdown()
    
    logger.info("\n" + "=" * 80)
    logger.info("Test Complete!")
    logger.info("=" * 80)
    
    return success


def test_data_merger_only():
    """Test data merger in isolation."""
    from backend.app.services.data_merger import DataMerger
    
    logger.info("\n=== Testing DataMerger Only ===")
    
    completed_items = []
    
    def on_complete(link_id, data):
        logger.info(f"✓ Merger completed: {link_id}")
        completed_items.append((link_id, data))
    
    merger = DataMerger(completion_callback=on_complete)
    
    # Test YouTube (2-part)
    logger.info("Testing YouTube (2-part)...")
    merger.on_transcript_complete("yt1", {
        'source': 'youtube',
        'transcript': 'Test transcript',
        'metadata': {'title': 'Test'}
    })
    
    # Not complete yet
    assert len(completed_items) == 0, "Should not complete after transcript only"
    
    merger.on_comments_complete("yt1", {
        'source': 'youtube',
        'comments': [{'text': 'Test comment'}],
        'metadata': {}
    })
    
    # Should be complete now
    assert len(completed_items) == 1, "Should complete after transcript + comments"
    assert completed_items[0][0] == "yt1"
    assert completed_items[0][1]['transcript'] == 'Test transcript'
    assert len(completed_items[0][1]['comments']) == 1
    
    logger.info("✓ DataMerger test passed!")
    
    # Test Reddit (1-part)
    logger.info("Testing Reddit (1-part)...")
    merger.on_single_item_complete("reddit1", {
        'source': 'reddit',
        'transcript': 'Reddit post',
        'comments': []
    })
    
    assert len(completed_items) == 2, "Should complete immediately for single-part"
    assert completed_items[1][0] == "reddit1"
    
    logger.info("✓ All DataMerger tests passed!")
    
    return True


if __name__ == "__main__":
    logger.info("Starting V2 Integration Tests")
    logger.info(f"Project root: {project_root}")
    
    # Test data merger first (fast, no API calls)
    try:
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: DataMerger Isolation Test")
        logger.info("=" * 80)
        result1 = test_data_merger_only()
        logger.info(f"Result: {'PASS' if result1 else 'FAIL'}")
    except Exception as e:
        logger.error(f"DataMerger test failed: {e}", exc_info=True)
        result1 = False
    
    # Test full integration (slow, calls AI API)
    try:
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: Full V2 Integration Test (will call AI API)")
        logger.info("=" * 80)
        result2 = test_v2_integration_basic()
        logger.info(f"Result: {'PASS' if result2 else 'FAIL'}")
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        result2 = False
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"DataMerger Test: {'PASS ✓' if result1 else 'FAIL ✗'}")
    logger.info(f"Integration Test: {'PASS ✓' if result2 else 'FAIL ✗'}")
    logger.info(f"Overall: {'ALL TESTS PASSED ✓' if (result1 and result2) else 'SOME TESTS FAILED ✗'}")
    
    sys.exit(0 if (result1 and result2) else 1)

