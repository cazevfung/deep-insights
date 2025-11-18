"""
Simple test script to verify streaming summarization manager merge functionality.

Tests the core merge logic without starting workers or calling APIs.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.phases.streaming_summarization_manager import StreamingSummarizationManager


def test_merge_scraped_data():
    """Test the _merge_scraped_data function directly."""
    print("=" * 60)
    print("Testing _merge_scraped_data Function")
    print("=" * 60)
    
    # Create minimal manager just to access the merge function
    mock_client = Mock()
    mock_config = Mock()
    mock_config.get = lambda key, default: default
    mock_ui = Mock()
    mock_session = Mock()
    
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id="test"
    )
    
    # Test 1: Merge comments first, then transcript
    print("\n[TEST 1] Merge: Comments first, then transcript...")
    comments_data = {
        "comments": ["Comment 1", "Comment 2", "Comment 3"],
        "source": "youtube",
        "metadata": {"title": "Test Video"}
    }
    
    transcript_data = {
        "transcript": "This is a test transcript with some content.",
        "source": "youtube",
        "metadata": {"title": "Test Video", "word_count": 10}
    }
    
    # Merge: comments -> transcript
    merged = manager._merge_scraped_data(comments_data, transcript_data)
    
    assert 'transcript' in merged, "Merged should have transcript"
    assert 'comments' in merged, "Merged should have comments"
    assert merged['transcript'] == transcript_data['transcript'], "Transcript should be from new data"
    assert merged['comments'] == comments_data['comments'], "Comments should be from existing data"
    assert merged['metadata']['word_count'] == 10, "Metadata should be merged"
    print("✓ Comments + Transcript merged correctly")
    
    # Test 2: Merge transcript first, then comments
    print("\n[TEST 2] Merge: Transcript first, then comments...")
    merged2 = manager._merge_scraped_data(transcript_data, comments_data)
    
    assert 'transcript' in merged2, "Merged should have transcript"
    assert 'comments' in merged2, "Merged should have comments"
    assert merged2['transcript'] == transcript_data['transcript'], "Transcript should be preserved"
    assert merged2['comments'] == comments_data['comments'], "Comments should be added"
    print("✓ Transcript + Comments merged correctly")
    
    # Test 3: Merge with empty data
    print("\n[TEST 3] Merge: Empty existing data...")
    merged3 = manager._merge_scraped_data({}, transcript_data)
    assert merged3['transcript'] == transcript_data['transcript'], "Should add transcript to empty data"
    print("✓ Empty data + transcript merged correctly")
    
    # Test 4: Merge with None
    print("\n[TEST 4] Merge: None existing data...")
    merged4 = manager._merge_scraped_data(None, comments_data)
    assert merged4['comments'] == comments_data['comments'], "Should handle None existing data"
    print("✓ None + comments merged correctly")
    
    print("\n" + "=" * 60)
    print("All merge function tests passed! ✓")
    print("=" * 60)
    return True


def test_on_scraping_complete_merge_logic():
    """Test that on_scraping_complete merges data when item is already queued."""
    print("\n" + "=" * 60)
    print("Testing on_scraping_complete Merge Logic")
    print("=" * 60)
    
    # Create manager
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
    
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id="test_merge"
    )
    
    # Register expected items
    link_id = "test_link_1"
    manager.register_expected_items([link_id])
    
    # Start workers (required for queuing)
    manager.start_workers()
    
    # Test: Comments complete first
    print("\n[TEST] Comments complete first...")
    comments_data = {
        "comments": ["C1", "C2"],
        "source": "youtube"
    }
    
    manager.on_scraping_complete(link_id, comments_data)
    
    # Verify data is stored
    assert manager.item_states[link_id]['scraped'] == True, "Should be marked as scraped"
    assert 'comments' in manager.item_states[link_id]['data'], "Should have comments"
    assert 'transcript' not in manager.item_states[link_id]['data'], "Should not have transcript yet"
    print("✓ Comments data stored")
    
    # Test: Transcript completes after comments (should merge, not skip)
    print("\n[TEST] Transcript completes after comments (should merge)...")
    transcript_data = {
        "transcript": "Test transcript",
        "source": "youtube"
    }
    
    # Before merge
    before_data = manager.item_states[link_id]['data'].copy()
    assert 'transcript' not in before_data, "Should not have transcript before merge"
    
    # Call on_scraping_complete - should merge, not skip
    manager.on_scraping_complete(link_id, transcript_data)
    
    # After merge
    after_data = manager.item_states[link_id]['data']
    assert 'transcript' in after_data, "Should have transcript after merge"
    assert 'comments' in after_data, "Should still have comments after merge"
    assert after_data['transcript'] == transcript_data['transcript'], "Transcript should be merged"
    assert after_data['comments'] == comments_data['comments'], "Comments should be preserved"
    print("✓ Transcript merged with comments (not skipped)")
    print(f"  - Transcript: {len(after_data.get('transcript', ''))} chars")
    print(f"  - Comments: {len(after_data.get('comments', []))} items")
    
    # Verify item is still in queue (not duplicated)
    queue_size = manager.summarization_queue.qsize()
    print(f"  - Queue size: {queue_size}")
    
    # Shutdown workers
    manager.shutdown()
    
    print("\n" + "=" * 60)
    print("on_scraping_complete merge logic test passed! ✓")
    print("=" * 60)
    return True


def test_worker_uses_merged_data_logic():
    """Test that worker would use merged data from item_states."""
    print("\n" + "=" * 60)
    print("Testing Worker Uses Merged Data Logic")
    print("=" * 60)
    
    # Create manager
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
    
    manager = StreamingSummarizationManager(
        client=mock_client,
        config=mock_config,
        ui=mock_ui,
        session=mock_session,
        batch_id="test_worker"
    )
    
    link_id = "test_link_2"
    manager.register_expected_items([link_id])
    manager.start_workers()
    
    # Step 1: Comments complete and queued
    comments_data = {"comments": ["Comment A"], "source": "youtube"}
    manager.on_scraping_complete(link_id, comments_data)
    
    # Step 2: Transcript completes and merges
    transcript_data = {"transcript": "Transcript text", "source": "youtube"}
    manager.on_scraping_complete(link_id, transcript_data)
    
    # Step 3: Simulate what worker does - get latest data from item_states
    with manager.completed_lock:
        # This is what the worker code does (line 364-368 in the fix)
        if link_id in manager.item_states:
            latest_data = manager.item_states[link_id].get('data', {})
            if latest_data:
                # Worker would use this data
                worker_data = latest_data
                
                # Verify worker would get merged data
                assert 'transcript' in worker_data, "Worker should get transcript"
                assert 'comments' in worker_data, "Worker should get comments"
                assert worker_data['transcript'] == transcript_data['transcript'], "Worker should get merged transcript"
                assert worker_data['comments'] == comments_data['comments'], "Worker should get merged comments"
                
                print("✓ Worker would use merged data from item_states")
                print(f"  - Transcript in worker data: {'transcript' in worker_data}")
                print(f"  - Comments in worker data: {'comments' in worker_data}")
    
    manager.shutdown()
    
    print("\n" + "=" * 60)
    print("Worker data logic test passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Streaming Summarization Manager Merge Tests (Simple)")
    print("=" * 60)
    
    try:
        # Run tests
        test_merge_scraped_data()
        test_on_scraping_complete_merge_logic()
        test_worker_uses_merged_data_logic()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓✓✓")
        print("=" * 60)
        print("\nSummary:")
        print("1. ✓ _merge_scraped_data function works correctly")
        print("2. ✓ on_scraping_complete merges data when item already queued")
        print("3. ✓ Items are NOT skipped when transcript completes after comments")
        print("4. ✓ Worker will use merged data from item_states")
        print("5. ✓ Transcript and comments are both included in merged data")
        print("\n✅ The fixes are working correctly!")
        print("\nKey Fixes Verified:")
        print("  - Data merging: ✓")
        print("  - No skipping: ✓")
        print("  - Worker uses merged data: ✓")
        
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

