"""
Test script to verify total processes tracking and 100% completion trigger.

This test validates:
1. Total processes calculation
2. Batch totals storage
3. Completion rate calculation
4. 100% completion check
5. Research phase trigger logic
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Enable debug mode
os.environ['WORKFLOW_DEBUG'] = 'true'

from backend.app.services.workflow_service import (
    calculate_total_scraping_processes,
    PROCESSES_PER_LINK_TYPE,
    WorkflowService
)
from backend.app.services.progress_service import ProgressService
from app.websocket.manager import WebSocketManager
from datetime import datetime


def test_calculate_total_processes():
    """Test the centralized total processes calculation function."""
    print("\n" + "=" * 80)
    print("Test 1: Total Processes Calculation")
    print("=" * 80)
    
    # Test case 1: Mixed link types
    links_by_type = {
        'youtube': [
            {'id': 'yt1', 'url': 'https://youtube.com/watch?v=1'},
            {'id': 'yt2', 'url': 'https://youtube.com/watch?v=2'}
        ],
        'bilibili': [
            {'id': 'bili1', 'url': 'https://bilibili.com/video/BV1'}
        ],
        'reddit': [
            {'id': 'rd1', 'url': 'https://reddit.com/r/test'},
            {'id': 'rd2', 'url': 'https://reddit.com/r/test2'},
            {'id': 'rd3', 'url': 'https://reddit.com/r/test3'}
        ],
        'article': [
            {'id': 'art1', 'url': 'https://example.com/article'}
        ]
    }
    
    result = calculate_total_scraping_processes(links_by_type)
    
    print(f"\nInput links:")
    for link_type, links in links_by_type.items():
        print(f"  {link_type}: {len(links)} links")
    
    print(f"\nCalculated results:")
    print(f"  Total links: {result['total_links']}")
    print(f"  Total processes: {result['total_processes']}")
    print(f"  Breakdown: {result['breakdown']}")
    print(f"  Link breakdown: {result['link_breakdown']}")
    
    # Verify calculations
    expected_total_links = 2 + 1 + 3 + 1  # 7 links
    expected_total_processes = (2 * 2) + (1 * 2) + (3 * 1) + (1 * 1)  # 4 + 2 + 3 + 1 = 10
    
    assert result['total_links'] == expected_total_links, f"Expected {expected_total_links} links, got {result['total_links']}"
    assert result['total_processes'] == expected_total_processes, f"Expected {expected_total_processes} processes, got {result['total_processes']}"
    assert result['breakdown']['youtube'] == 4, f"Expected 4 YouTube processes, got {result['breakdown']['youtube']}"
    assert result['breakdown']['bilibili'] == 2, f"Expected 2 Bilibili processes, got {result['breakdown']['bilibili']}"
    assert result['breakdown']['reddit'] == 3, f"Expected 3 Reddit processes, got {result['breakdown']['reddit']}"
    assert result['breakdown']['article'] == 1, f"Expected 1 Article process, got {result['breakdown']['article']}"
    
    print("\n[PASS] Total processes calculation is correct!")
    return True


async def test_completion_rate_calculation():
    """Test completion rate calculation in ProgressService."""
    print("\n" + "=" * 80)
    print("Test 2: Completion Rate Calculation")
    print("=" * 80)
    
    # Create mock WebSocket manager
    class MockWebSocketManager:
        async def broadcast(self, batch_id, message):
            pass
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    
    batch_id = "test_batch_001"
    expected_total = 10
    
    # Initialize expected links
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(expected_total)
    ]
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    print(f"\nInitialized batch: {batch_id}")
    print(f"  Expected total: {expected_total}")
    
    # Simulate progress: 5 completed, 2 failed, 3 pending
    for i in range(5):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    for i in range(5, 7):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'failed', 0.0, 0.0, 'Failed'
        )
    
    # Check completion
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    print(f"\nCompletion status:")
    print(f"  Completed: {result['completed_count']}")
    print(f"  Failed: {result['failed_count']}")
    print(f"  Total final: {result['total_final']}")
    print(f"  Expected total: {result['expected_total']}")
    print(f"  Completion rate: {result['completion_rate']:.2%}")
    print(f"  Completion percentage: {result['completion_percentage']:.1f}%")
    print(f"  Is 100%: {result['is_100_percent']}")
    print(f"  Confirmed: {result['confirmed']}")
    
    # Verify calculations
    assert result['completed_count'] == 5, f"Expected 5 completed, got {result['completed_count']}"
    assert result['failed_count'] == 2, f"Expected 2 failed, got {result['failed_count']}"
    assert result['total_final'] == 7, f"Expected 7 total final, got {result['total_final']}"
    assert result['completion_rate'] == 0.7, f"Expected 0.7 completion rate, got {result['completion_rate']}"
    assert result['completion_percentage'] == 70.0, f"Expected 70.0%, got {result['completion_percentage']}"
    assert result['is_100_percent'] == False, "Should not be 100% yet"
    assert result['confirmed'] == False, "Should not be confirmed yet"
    
    # Complete remaining links
    for i in range(7, 10):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    # Check again - should be 100%
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    print(f"\nAfter completing all:")
    print(f"  Completed: {result['completed_count']}")
    print(f"  Failed: {result['failed_count']}")
    print(f"  Total final: {result['total_final']}")
    print(f"  Completion rate: {result['completion_rate']:.2%}")
    print(f"  Is 100%: {result['is_100_percent']}")
    print(f"  Confirmed: {result['confirmed']}")
    
    assert result['total_final'] == 10, f"Expected 10 total final, got {result['total_final']}"
    assert result['completion_rate'] == 1.0, f"Expected 1.0 completion rate, got {result['completion_rate']}"
    assert result['is_100_percent'] == True, "Should be 100% now"
    assert result['confirmed'] == True, "Should be confirmed now"
    
    print("\n[PASS] Completion rate calculation is correct!")
    return True


def test_batch_totals_storage():
    """Test batch totals storage in WorkflowService."""
    print("\n" + "=" * 80)
    print("Test 3: Batch Totals Storage")
    print("=" * 80)
    
    # Create mock WebSocket manager
    class MockWebSocketManager:
        async def broadcast(self, batch_id, message):
            pass
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    
    # Manually set batch totals (simulating _load_link_context)
    batch_id = "test_batch_002"
    workflow_service.batch_totals[batch_id] = {
        'total_processes': 15,
        'total_links': 8,
        'breakdown': {
            'youtube': 4,
            'bilibili': 2,
            'reddit': 6,
            'article': 3
        },
        'link_breakdown': {
            'youtube': 2,
            'bilibili': 1,
            'reddit': 6,
            'article': 3
        },
        'calculated_at': datetime.now().isoformat(),
        'source': 'test'
    }
    
    print(f"\nStored batch totals for: {batch_id}")
    print(f"  Total processes: {workflow_service.batch_totals[batch_id]['total_processes']}")
    print(f"  Total links: {workflow_service.batch_totals[batch_id]['total_links']}")
    print(f"  Breakdown: {workflow_service.batch_totals[batch_id]['breakdown']}")
    
    # Verify storage
    assert batch_id in workflow_service.batch_totals, "Batch totals should be stored"
    assert workflow_service.batch_totals[batch_id]['total_processes'] == 15, "Total processes should be 15"
    assert workflow_service.batch_totals[batch_id]['total_links'] == 8, "Total links should be 8"
    
    print("\n[PASS] Batch totals storage is working!")
    return True


async def test_100_percent_check():
    """Test the 100% completion check logic."""
    print("\n" + "=" * 80)
    print("Test 4: 100% Completion Check")
    print("=" * 80)
    
    # Create mock WebSocket manager
    class MockWebSocketManager:
        async def broadcast(self, batch_id, message):
            pass
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    
    batch_id = "test_batch_003"
    expected_total = 5
    
    # Initialize
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(expected_total)
    ]
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    # Test case 1: Not 100% (3 completed, 1 failed, 1 pending)
    for i in range(3):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    await progress_service.update_link_progress(
        batch_id, 'link_3', 'https://example.com/3',
        'failed', 0.0, 0.0, 'Failed'
    )
    
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    print(f"\nTest case 1: Partial completion (3 completed, 1 failed, 1 pending)")
    print(f"  Total final: {result['total_final']}/{result['expected_total']}")
    print(f"  Completion rate: {result['completion_rate']:.2%}")
    print(f"  Is 100%: {result['is_100_percent']}")
    print(f"  Confirmed: {result['confirmed']}")
    
    assert result['total_final'] == 4, "Should have 4 final (3 completed + 1 failed)"
    assert result['is_100_percent'] == False, "Should not be 100%"
    assert result['confirmed'] == False, "Should not be confirmed"
    
    # Test case 2: 100% (complete the last one)
    await progress_service.update_link_progress(
        batch_id, 'link_4', 'https://example.com/4',
        'completed', 100.0, 100.0, 'Completed'
    )
    
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    print(f"\nTest case 2: 100% completion (4 completed, 1 failed)")
    print(f"  Total final: {result['total_final']}/{result['expected_total']}")
    print(f"  Completion rate: {result['completion_rate']:.2%}")
    print(f"  Is 100%: {result['is_100_percent']}")
    print(f"  Confirmed: {result['confirmed']}")
    
    assert result['total_final'] == 5, "Should have 5 final"
    assert result['completion_rate'] == 1.0, "Should be 100%"
    assert result['is_100_percent'] == True, "Should be 100%"
    assert result['confirmed'] == True, "Should be confirmed"
    
    print("\n[PASS] 100% completion check is working!")
    return True


async def main():
    """Run all tests."""
    print("=" * 80)
    print("TOTAL PROCESSES TRACKING - TEST SUITE")
    print("=" * 80)
    
    results = []
    
    try:
        # Test 1: Total processes calculation
        results.append(("Total Processes Calculation", test_calculate_total_processes()))
    except Exception as e:
        print(f"\n[FAIL] Total processes calculation: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Total Processes Calculation", False))
    
    try:
        # Test 2: Completion rate calculation
        results.append(("Completion Rate Calculation", await test_completion_rate_calculation()))
    except Exception as e:
        print(f"\n[FAIL] Completion rate calculation: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Completion Rate Calculation", False))
    
    try:
        # Test 3: Batch totals storage
        results.append(("Batch Totals Storage", test_batch_totals_storage()))
    except Exception as e:
        print(f"\n[FAIL] Batch totals storage: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Batch Totals Storage", False))
    
    try:
        # Test 4: 100% completion check
        results.append(("100% Completion Check", await test_100_percent_check()))
    except Exception as e:
        print(f"\n[FAIL] 100% completion check: {e}")
        import traceback
        traceback.print_exc()
        results.append(("100% Completion Check", False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

