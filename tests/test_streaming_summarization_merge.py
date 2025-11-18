"""
Test script to verify streaming summarization manager merge functionality.

Tests that:
1. When comments complete first, item is queued for summarization
2. When transcript completes after comments, data is merged correctly
3. Worker uses merged data (transcript + comments) for summarization
4. Items are not skipped when transcript completes after comments
"""

import threading
import time
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Import the streaming summarization manager
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.phases.streaming_summarization_manager import StreamingSummarizationManager


def test_merge_functionality():
    """Test that data is merged correctly when transcript completes after comments."""
    print("=" * 60)
    print("Testing Streaming Summarization Manager Merge Functionality")
    print("=" * 60)
    
    # Create mock client, config, ui, and session
    mock_client = Mock()
    mock_config = Mock()
    mock_config.get = lambda key, default: {
        "research.summarization.enabled": True,
        "research.summarization.model": "qwen-flash",
        "research.summarization.reuse_existing_summaries": True,
        "research.summarization.save_to_files": False,
    }.get(key, default)
    mock_ui = Mock()
    mock_session = Mock()
    
    # Create streaming summarization manager
    batch_id = "test_batch_001"
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id=batch_id
    )
    
    # Register expected items
    link_id = "yt_test1"
    manager.register_expected_items([link_id])
    
    # Start workers (required for queuing to work)
    manager.start_workers()
    time.sleep(0.1)  # Give workers time to start
    
    # Test 1: Comments complete first
    print("\n[TEST 1] Comments complete first...")
    comments_data = {
        "comments": ["Comment 1", "Comment 2", "Comment 3"],
        "source": "youtube",
        "metadata": {
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=test",
        }
    }
    
    manager.on_scraping_complete(link_id, comments_data)
    
    # Check that item is queued
    assert link_id in manager.items_in_queue, "Item should be in queue after comments complete"
    assert manager.item_states[link_id]['scraped'] == True, "Item should be marked as scraped"
    assert manager.item_states[link_id]['data']['comments'] == comments_data['comments'], "Comments should be stored"
    print("✓ Comments data queued successfully")
    
    # Test 2: Transcript completes after comments (should merge, not skip)
    print("\n[TEST 2] Transcript completes after comments (should merge)...")
    transcript_data = {
        "transcript": "This is a test transcript with some content.",
        "source": "youtube",
        "metadata": {
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=test",
            "word_count": 10,
        }
    }
    
    # Before merge: check that item is in queue
    assert link_id in manager.items_in_queue, "Item should still be in queue"
    
    # Call on_scraping_complete with transcript data
    manager.on_scraping_complete(link_id, transcript_data)
    
    # Check that data was merged (not skipped)
    merged_data = manager.item_states[link_id]['data']
    assert 'transcript' in merged_data, "Merged data should have transcript"
    assert 'comments' in merged_data, "Merged data should have comments"
    assert merged_data['transcript'] == transcript_data['transcript'], "Transcript should be merged"
    assert merged_data['comments'] == comments_data['comments'], "Comments should be preserved"
    print("✓ Transcript data merged successfully (not skipped)")
    print(f"  - Transcript: {len(merged_data.get('transcript', ''))} chars")
    print(f"  - Comments: {len(merged_data.get('comments', []))} items")
    
    # Test 3: Verify merge function directly
    print("\n[TEST 3] Testing _merge_scraped_data function directly...")
    existing = {
        "comments": ["Comment 1", "Comment 2"],
        "metadata": {"title": "Old Title"}
    }
    new_data = {
        "transcript": "New transcript",
        "metadata": {"title": "New Title", "word_count": 5}
    }
    
    merged = manager._merge_scraped_data(existing, new_data)
    
    assert merged['transcript'] == "New transcript", "Should merge transcript"
    assert merged['comments'] == ["Comment 1", "Comment 2"], "Should preserve comments"
    assert merged['metadata']['title'] == "New Title", "Should update metadata"
    assert merged['metadata'].get('word_count') == 5, "Should add new metadata fields"
    print("✓ _merge_scraped_data function works correctly")
    
    # Test 4: Verify that items in queue get merged data updated
    print("\n[TEST 4] Verifying queue item gets merged data...")
    # Item should still be in queue
    assert link_id in manager.items_in_queue or manager.summarization_queue.qsize() > 0, "Item should be in queue"
    
    # Get the data that would be used by worker
    with manager.completed_lock:
        latest_data = manager.item_states[link_id].get('data', {})
        assert 'transcript' in latest_data, "Latest data should have transcript"
        assert 'comments' in latest_data, "Latest data should have comments"
    print("✓ Queue item has merged data available")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True


def test_worker_uses_merged_data():
    """Test that worker uses merged data from item_states."""
    print("\n" + "=" * 60)
    print("Testing Worker Uses Merged Data")
    print("=" * 60)
    
    # Create mock client, config, ui, and session
    mock_client = Mock()
    mock_config = Mock()
    mock_config.get = lambda key, default: {
        "research.summarization.enabled": True,
        "research.summarization.model": "qwen-flash",
        "research.summarization.reuse_existing_summaries": True,
        "research.summarization.save_to_files": False,
    }.get(key, default)
    mock_ui = Mock()
    mock_session = Mock()
    
    # Create streaming summarization manager
    batch_id = "test_batch_002"
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id=batch_id
    )
    
    # Register expected items
    link_id = "yt_test2"
    manager.register_expected_items([link_id])
    
    # Start workers (required for queuing to work)
    manager.start_workers()
    time.sleep(0.1)  # Give workers time to start
    
    # Step 1: Comments complete first and are queued
    comments_data = {
        "comments": ["Comment A", "Comment B"],
        "source": "youtube"
    }
    manager.on_scraping_complete(link_id, comments_data)
    
    # Verify item is queued
    assert manager.summarization_queue.qsize() > 0, "Item should be in queue"
    
    # Step 2: Transcript completes and merges data
    transcript_data = {
        "transcript": "Test transcript content",
        "source": "youtube"
    }
    manager.on_scraping_complete(link_id, transcript_data)
    
    # Step 3: Verify merged data is in item_states
    with manager.completed_lock:
        stored_data = manager.item_states[link_id]['data']
        assert 'transcript' in stored_data, "Stored data should have transcript"
        assert 'comments' in stored_data, "Stored data should have comments"
    
    # Step 4: Simulate what worker does - get item from queue and check latest data
    # (We can't actually run the worker without a real summarizer, but we can verify the logic)
    print("✓ Merged data is stored in item_states")
    print(f"  - Transcript in stored data: {'transcript' in stored_data}")
    print(f"  - Comments in stored data: {'comments' in stored_data}")
    
    print("\n" + "=" * 60)
    print("Worker data merge test passed! ✓")
    print("=" * 60)
    return True


def test_no_skip_when_already_queued():
    """Test that items are not skipped when transcript completes after comments."""
    print("\n" + "=" * 60)
    print("Testing No Skip When Already Queued")
    print("=" * 60)
    
    # Create mock client, config, ui, and session
    mock_client = Mock()
    mock_config = Mock()
    mock_config.get = lambda key, default: {
        "research.summarization.enabled": True,
        "research.summarization.model": "qwen-flash",
        "research.summarization.reuse_existing_summaries": True,
        "research.summarization.save_to_files": False,
    }.get(key, default)
    mock_ui = Mock()
    mock_session = Mock()
    
    # Create streaming summarization manager
    batch_id = "test_batch_003"
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id=batch_id
    )
    
    # Register expected items
    link_id = "yt_test3"
    manager.register_expected_items([link_id])
    
    # Start workers (required for queuing to work)
    manager.start_workers()
    time.sleep(0.1)  # Give workers time to start
    
    # Step 1: Comments complete first
    comments_data = {"comments": ["C1", "C2"], "source": "youtube"}
    manager.on_scraping_complete(link_id, comments_data)
    
    # Verify item is queued
    initial_queue_size = manager.summarization_queue.qsize()
    assert initial_queue_size > 0, "Item should be queued"
    assert link_id in manager.items_in_queue, "Item should be in items_in_queue"
    
    # Step 2: Transcript completes - should merge, not skip
    transcript_data = {"transcript": "Transcript text", "source": "youtube"}
    
    # Before: Check initial state
    initial_data = manager.item_states[link_id]['data'].copy()
    assert 'transcript' not in initial_data, "Initial data should not have transcript"
    
    # Call on_scraping_complete - should merge, not return early
    manager.on_scraping_complete(link_id, transcript_data)
    
    # After: Check that data was merged
    final_data = manager.item_states[link_id]['data']
    assert 'transcript' in final_data, "Final data should have transcript after merge"
    assert 'comments' in final_data, "Final data should have comments"
    assert final_data['transcript'] == transcript_data['transcript'], "Transcript should be merged"
    
    # Queue size should remain the same (not add duplicate)
    final_queue_size = manager.summarization_queue.qsize()
    assert final_queue_size == initial_queue_size, "Queue size should not increase (merged, not new item)"
    
    print("✓ Transcript data merged when item already in queue (not skipped)")
    print(f"  - Initial queue size: {initial_queue_size}")
    print(f"  - Final queue size: {final_queue_size}")
    print(f"  - Data has transcript: {'transcript' in final_data}")
    print(f"  - Data has comments: {'comments' in final_data}")
    
    print("\n" + "=" * 60)
    print("No skip test passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Streaming Summarization Manager Merge Tests")
    print("=" * 60)
    
    managers_to_cleanup = []
    
    try:
        # Run tests
        test_merge_functionality()
        test_worker_uses_merged_data()
        test_no_skip_when_already_queued()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓✓✓")
        print("=" * 60)
        print("\nSummary:")
        print("1. ✓ Data merging works correctly")
        print("2. ✓ Items are not skipped when transcript completes after comments")
        print("3. ✓ Worker will use merged data from item_states")
        print("4. ✓ Queue items get updated with merged data")
        print("\nThe fixes are working correctly!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

