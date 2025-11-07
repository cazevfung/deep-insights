"""
Comprehensive test to verify:
1. Frontend and backend are in sync using expected_total value
2. Research phase starts based on confirmation that 100% of expected_total is completed (success or fail)
"""
import asyncio
import sys
import os
import io
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / 'app'))

from app.services.workflow_service import WorkflowService, calculate_total_scraping_processes
from app.services.progress_service import ProgressService
from app.websocket.manager import WebSocketManager

class MockWebSocketManager:
    """Mock WebSocket manager to capture messages."""
    def __init__(self):
        self.messages = defaultdict(list)
        self.broadcast_calls = []
    
    async def broadcast(self, batch_id: str, message: dict):
        """Capture broadcast messages."""
        self.messages[batch_id].append(message)
        self.broadcast_calls.append((batch_id, message))
        if message.get('type') in ['batch:initialized', 'scraping:status', 'scraping:100_percent_complete', 'research:start']:
            print(f"[BROADCAST] {batch_id}: {message.get('type')}")
            if message.get('type') == 'batch:initialized':
                print(f"  expected_total: {message.get('expected_total')}")
            elif message.get('type') == 'scraping:status':
                print(f"  expected_total: {message.get('expected_total')}, completed: {message.get('completed')}, failed: {message.get('failed')}, completion_rate: {message.get('completion_rate')}, is_100_percent: {message.get('is_100_percent')}")
            elif message.get('type') == 'scraping:100_percent_complete':
                print(f"  expected_total: {message.get('expected_total')}, completed: {message.get('completed')}, failed: {message.get('failed')}")

async def test_frontend_backend_sync():
    """Test 1: Verify frontend and backend are in sync using expected_total."""
    print("=" * 80)
    print("TEST 1: Frontend-Backend Sync with expected_total")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    workflow_service.progress_service = progress_service
    
    batch_id = "test_sync_001"
    
    # Simulate link context
    context = {
        'youtube': [
            {'link_id': 'yt1', 'url': 'https://youtube.com/watch?v=1'},
            {'link_id': 'yt2', 'url': 'https://youtube.com/watch?v=2'},
        ],
        'article': [
            {'link_id': 'art1', 'url': 'https://example.com/article1'},
        ]
    }
    
    # Calculate expected total
    totals = calculate_total_scraping_processes(context)
    expected_total = totals['expected_total']  # Should be 5 (2 YouTube × 2 + 1 Article)
    
    print(f"\nScenario:")
    print(f"  YouTube links: 2 (each = 2 processes)")
    print(f"  Article links: 1 (each = 1 process)")
    print(f"  Expected total: {expected_total}")
    
    # Simulate workflow initialization
    workflow_service.link_context[batch_id] = context
    workflow_service.batch_totals[batch_id] = {
        'expected_total': expected_total,
        'total_processes': expected_total,  # Deprecated but kept
        'total_links': 3,
        'breakdown': totals['breakdown'],
    }
    
    # Pre-register expected processes
    all_processes = [
        {'link_id': 'yt1', 'url': 'https://youtube.com/watch?v=1', 'scraper_type': 'youtube', 'process_type': 'transcript'},
        {'link_id': 'yt1_comments', 'url': 'https://youtube.com/watch?v=1', 'scraper_type': 'youtubecomments', 'process_type': 'comments'},
        {'link_id': 'yt2', 'url': 'https://youtube.com/watch?v=2', 'scraper_type': 'youtube', 'process_type': 'transcript'},
        {'link_id': 'yt2_comments', 'url': 'https://youtube.com/watch?v=2', 'scraper_type': 'youtubecomments', 'process_type': 'comments'},
        {'link_id': 'art1', 'url': 'https://example.com/article1', 'scraper_type': 'article', 'process_type': 'article'},
    ]
    
    registered = progress_service.initialize_expected_links(batch_id, all_processes)
    print(f"\nPre-registered {registered} processes")
    
    # Send batch:initialized
    await ws_manager.broadcast(batch_id, {
        'type': 'batch:initialized',
        'batch_id': batch_id,
        'expected_total': expected_total,
        'total_processes': expected_total,
    })
    
    # Send initial status
    await progress_service._update_batch_status(batch_id)
    
    # Verify messages
    batch_init = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'batch:initialized']
    status_msgs = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'scraping:status']
    
    errors = []
    
    # Check batch:initialized
    if batch_init:
        init_msg = batch_init[-1]
        if init_msg.get('expected_total') != expected_total:
            errors.append(f"batch:initialized expected_total mismatch: expected {expected_total}, got {init_msg.get('expected_total')}")
        else:
            print(f"\n[OK] batch:initialized has correct expected_total: {init_msg.get('expected_total')}")
    else:
        errors.append("No batch:initialized message found")
    
    # Check scraping:status
    if status_msgs:
        status_msg = status_msgs[-1]
        if status_msg.get('expected_total') != expected_total:
            errors.append(f"scraping:status expected_total mismatch: expected {expected_total}, got {status_msg.get('expected_total')}")
        else:
            print(f"[OK] scraping:status has correct expected_total: {status_msg.get('expected_total')}")
    else:
        errors.append("No scraping:status message found")
    
    if errors:
        print(f"\n[FAIL] Errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"\n[PASS] Frontend and backend are in sync using expected_total!")
    return True

async def test_100_percent_completion_trigger():
    """Test 2: Verify research phase starts only when 100% of expected_total is completed."""
    print("\n" + "=" * 80)
    print("TEST 2: Research Phase Trigger at 100% Completion")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    workflow_service.progress_service = progress_service
    
    batch_id = "test_100_percent_001"
    expected_total = 6  # 3 YouTube links × 2 processes each
    
    # Initialize expected links
    all_processes = [
        {'link_id': f'yt{i}', 'url': f'https://youtube.com/watch?v={i}', 'scraper_type': 'youtube', 'process_type': 'transcript'}
        for i in range(1, 4)
    ] + [
        {'link_id': f'yt{i}_comments', 'url': f'https://youtube.com/watch?v={i}', 'scraper_type': 'youtubecomments', 'process_type': 'comments'}
        for i in range(1, 4)
    ]
    
    registered = progress_service.initialize_expected_links(batch_id, all_processes)
    progress_service.expected_totals[batch_id] = expected_total
    
    print(f"\nScenario:")
    print(f"  Expected total: {expected_total}")
    print(f"  Registered processes: {registered}")
    
    # Test Case 2.1: NOT 100% - should NOT trigger research
    print(f"\n--- Test Case 2.1: 4/6 completed (NOT 100%) ---")
    for i in range(1, 3):  # Complete first 2 YouTube transcripts and comments (4 processes)
        await progress_service.update_link_progress(
            batch_id,
            f'yt{i}',
            f'https://youtube.com/watch?v={i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
        await progress_service.update_link_progress(
            batch_id,
            f'yt{i}_comments',
            f'https://youtube.com/watch?v={i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
    
    await progress_service._update_batch_status(batch_id)
    
    # Check confirmation
    confirmation = await progress_service.confirm_all_scraping_complete(batch_id)
    is_100_percent = confirmation.get('is_100_percent', False)
    total_final = confirmation.get('total_final', 0)
    
    print(f"  Completed: {confirmation.get('completed_count', 0)}")
    print(f"  Failed: {confirmation.get('failed_count', 0)}")
    print(f"  Total final: {total_final}")
    print(f"  Expected total: {expected_total}")
    print(f"  is_100_percent: {is_100_percent}")
    print(f"  confirmed: {confirmation.get('confirmed', False)}")
    
    if is_100_percent or confirmation.get('confirmed'):
        print(f"  [FAIL] Should NOT be 100% yet (4/6 completed)")
        return False
    else:
        print(f"  [OK] Correctly NOT at 100% (4/6 completed)")
    
    # Test Case 2.2: 100% with all success - should trigger research
    print(f"\n--- Test Case 2.2: 6/6 completed (100% success) ---")
    # Complete remaining 2 processes
    await progress_service.update_link_progress(
        batch_id,
        'yt3',
        'https://youtube.com/watch?v=3',
        stage='completed',
        stage_progress=100.0,
        overall_progress=100.0,
        message='Completed'
    )
    await progress_service.update_link_progress(
        batch_id,
        'yt3_comments',
        'https://youtube.com/watch?v=3',
        stage='completed',
        stage_progress=100.0,
        overall_progress=100.0,
        message='Completed'
    )
    
    await progress_service._update_batch_status(batch_id)
    
    confirmation = await progress_service.confirm_all_scraping_complete(batch_id)
    is_100_percent = confirmation.get('is_100_percent', False)
    total_final = confirmation.get('total_final', 0)
    confirmed = confirmation.get('confirmed', False)
    
    print(f"  Completed: {confirmation.get('completed_count', 0)}")
    print(f"  Failed: {confirmation.get('failed_count', 0)}")
    print(f"  Total final: {total_final}")
    print(f"  Expected total: {expected_total}")
    print(f"  is_100_percent: {is_100_percent}")
    print(f"  confirmed: {confirmed}")
    
    if not (is_100_percent and total_final == expected_total and confirmed):
        print(f"  [FAIL] Should be 100% complete and confirmed")
        return False
    else:
        print(f"  [OK] Correctly at 100% and confirmed (6/6 completed)")
    
    # Test Case 2.3: 100% with some failures - should still trigger research
    print(f"\n--- Test Case 2.3: 6/6 completed (4 success, 2 failed) ---")
    batch_id_2 = "test_100_percent_002"
    expected_total_2 = 6
    
    all_processes_2 = [
        {'link_id': f'yt{i}', 'url': f'https://youtube.com/watch?v={i}', 'scraper_type': 'youtube', 'process_type': 'transcript'}
        for i in range(1, 4)
    ] + [
        {'link_id': f'yt{i}_comments', 'url': f'https://youtube.com/watch?v={i}', 'scraper_type': 'youtubecomments', 'process_type': 'comments'}
        for i in range(1, 4)
    ]
    
    registered_2 = progress_service.initialize_expected_links(batch_id_2, all_processes_2)
    progress_service.expected_totals[batch_id_2] = expected_total_2
    
    # Complete 4 processes successfully
    for i in range(1, 3):
        await progress_service.update_link_progress(
            batch_id_2,
            f'yt{i}',
            f'https://youtube.com/watch?v={i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
        await progress_service.update_link_progress(
            batch_id_2,
            f'yt{i}_comments',
            f'https://youtube.com/watch?v={i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
    
    # Fail 2 processes - stage='failed' automatically sets error status
    # The error message goes in the 'message' parameter
    await progress_service.update_link_progress(
        batch_id_2,
        'yt3',
        'https://youtube.com/watch?v=3',
        stage='failed',
        stage_progress=0.0,
        overall_progress=0.0,
        message='Failed: Test failure'
    )
    await progress_service.update_link_progress(
        batch_id_2,
        'yt3_comments',
        'https://youtube.com/watch?v=3',
        stage='failed',
        stage_progress=0.0,
        overall_progress=0.0,
        message='Failed: Test failure'
    )
    
    await progress_service._update_batch_status(batch_id_2)
    
    confirmation_2 = await progress_service.confirm_all_scraping_complete(batch_id_2)
    is_100_percent_2 = confirmation_2.get('is_100_percent', False)
    total_final_2 = confirmation_2.get('total_final', 0)
    confirmed_2 = confirmation_2.get('confirmed', False)
    
    print(f"  Completed: {confirmation_2.get('completed_count', 0)}")
    print(f"  Failed: {confirmation_2.get('failed_count', 0)}")
    print(f"  Total final: {total_final_2}")
    print(f"  Expected total: {expected_total_2}")
    print(f"  is_100_percent: {is_100_percent_2}")
    print(f"  confirmed: {confirmed_2}")
    
    if not (is_100_percent_2 and total_final_2 == expected_total_2 and confirmed_2):
        print(f"  [FAIL] Should be 100% complete even with failures (6/6 final status)")
        return False
    else:
        print(f"  [OK] Correctly at 100% and confirmed (4 success + 2 failed = 6/6 final)")
    
    print(f"\n[PASS] Research phase correctly triggers at 100% completion!")
    return True

async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST: Frontend-Backend Sync & 100% Completion Trigger")
    print("=" * 80)
    
    test1_passed = await test_frontend_backend_sync()
    test2_passed = await test_100_percent_completion_trigger()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Frontend-Backend Sync): {'PASS' if test1_passed else 'FAIL'}")
    print(f"Test 2 (100% Completion Trigger): {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        return 0
    else:
        print("\n[FAILURE] SOME TESTS FAILED!")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

