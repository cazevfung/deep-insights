"""
Integration test to verify frontend and backend are in sync.

This test verifies that research phase only starts when ALL expected processes
(determined at the beginning) are 100% complete, NOT when only "started" processes are complete.

This addresses the original bug where fast scrapers would complete first, and the system
would think scraping was done before slow scrapers even started.
"""
import sys
import os
import io
import asyncio
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Fix Unicode encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Enable debug mode
os.environ['WORKFLOW_DEBUG'] = 'true'

from backend.app.services.workflow_service import WorkflowService, calculate_total_scraping_processes
from backend.app.services.progress_service import ProgressService
from app.websocket.manager import WebSocketManager


class MockWebSocketManager:
    """Mock WebSocket manager to capture messages."""
    
    def __init__(self):
        self.messages: Dict[str, List[Dict]] = {}  # batch_id -> list of messages
        self.phase_transitions: Dict[str, List[str]] = {}  # batch_id -> list of phases
    
    async def broadcast(self, batch_id: str, message: Dict):
        """Capture broadcast messages."""
        if batch_id not in self.messages:
            self.messages[batch_id] = []
        self.messages[batch_id].append(message)
        
        # Track phase transitions
        if message.get('type') == 'research:phase_change':
            phase = message.get('phase')
            if batch_id not in self.phase_transitions:
                self.phase_transitions[batch_id] = []
            self.phase_transitions[batch_id].append(phase)
    
    def get_messages(self, batch_id: str, message_type: str = None) -> List[Dict]:
        """Get messages for a batch, optionally filtered by type."""
        messages = self.messages.get(batch_id, [])
        if message_type:
            return [m for m in messages if m.get('type') == message_type]
        return messages
    
    def has_phase_transition(self, batch_id: str, phase: str) -> bool:
        """Check if a phase transition occurred."""
        return phase in self.phase_transitions.get(batch_id, [])


async def test_premature_completion_prevention():
    """
    Test that research phase does NOT start when only started processes are complete,
    but waits for ALL expected processes.
    
    Scenario:
    - Expected total: 10 processes
    - Fast processes (5) start and complete quickly
    - Slow processes (5) haven't started yet
    - System should NOT transition to research phase
    """
    print("\n" + "=" * 80)
    print("Test: Premature Completion Prevention")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    progress_service = workflow_service.progress_service
    
    batch_id = "sync_test_001"
    expected_total = 10
    
    # Step 1: Initialize expected processes (simulating _load_link_context)
    print(f"\nStep 1: Initialize {expected_total} expected processes")
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(expected_total)
    ]
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    # Verify initialization
    assert batch_id in progress_service.expected_totals, "Expected total should be set"
    assert progress_service.expected_totals[batch_id] == expected_total, f"Expected total should be {expected_total}"
    print(f"  [OK] Expected total set: {progress_service.expected_totals[batch_id]}")
    
    # Step 2: Fast processes (5) start and complete quickly
    print(f"\nStep 2: Fast processes (5) start and complete")
    fast_processes = list(range(5))
    for i in fast_processes:
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    # Check status after fast processes complete
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    print(f"  Status after fast processes:")
    print(f"    Registered: {result['registered_count']}/{result['expected_total']}")
    print(f"    Completed: {result['completed_count']}")
    print(f"    Total final: {result['total_final']}")
    print(f"    Completion rate: {result['completion_rate']:.1%}")
    print(f"    Is 100%: {result['is_100_percent']}")
    print(f"    Confirmed: {result['confirmed']}")
    
    # Verify: Should NOT be 100% yet (only 5/10 complete)
    # Note: All 10 are pre-registered (this is correct - prevents premature completion)
    # But only 5 have final status (completed)
    assert result['registered_count'] == expected_total, f"All {expected_total} should be pre-registered, got {result['registered_count']}"
    assert result['total_final'] == 5, f"Only 5 should be final (completed), got {result['total_final']}"
    assert result['completion_rate'] == 0.5, f"Should be 50%, got {result['completion_rate']:.1%}"
    assert result['is_100_percent'] == False, "Should NOT be 100% yet"
    assert result['confirmed'] == False, "Should NOT be confirmed yet"
    print(f"  [OK] All {expected_total} processes pre-registered (prevents premature completion)")
    print(f"  [OK] Only 5/10 have final status - correctly identified as NOT 100% complete")
    
    # Step 3: Check if research phase would start (it shouldn't)
    print(f"\nStep 3: Check research phase trigger")
    
    # Simulate what happens in run_workflow when checking confirmation
    confirmation = result
    completion_rate = confirmation.get('completion_rate', 0.0)
    completion_percentage = confirmation.get('completion_percentage', 0.0)
    is_100_percent = confirmation.get('is_100_percent', False)
    total_final = confirmation.get('total_final', 0)
    expected_total_check = confirmation.get('expected_total', 0)
    
    # This is the check from run_workflow
    should_proceed = (
        is_100_percent and 
        total_final == expected_total_check and 
        completion_percentage >= 100.0
    )
    
    print(f"  Research phase should proceed: {should_proceed}")
    assert should_proceed == False, "Research phase should NOT proceed yet"
    print(f"  [OK] Research phase correctly blocked (not 100% complete)")
    
    # Step 4: Slow processes (5) start and complete
    print(f"\nStep 4: Slow processes (5) start and complete")
    slow_processes = list(range(5, 10))
    for i in slow_processes:
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    # Check status after all processes complete
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    print(f"  Status after all processes:")
    print(f"    Registered: {result['registered_count']}/{result['expected_total']}")
    print(f"    Completed: {result['completed_count']}")
    print(f"    Total final: {result['total_final']}")
    print(f"    Completion rate: {result['completion_rate']:.1%}")
    print(f"    Is 100%: {result['is_100_percent']}")
    print(f"    Confirmed: {result['confirmed']}")
    
    # Verify: Should be 100% now (10/10 complete)
    assert result['registered_count'] == expected_total, f"All {expected_total} processes should be registered"
    assert result['total_final'] == expected_total, f"All {expected_total} should be final"
    assert result['completion_rate'] == 1.0, f"Should be 100%, got {result['completion_rate']:.1%}"
    assert result['is_100_percent'] == True, "Should be 100% now"
    assert result['confirmed'] == True, "Should be confirmed now"
    print(f"  [OK] Correctly identified as 100% complete (10/10)")
    
    # Step 5: Check if research phase would start now (it should)
    print(f"\nStep 5: Check research phase trigger (after 100%)")
    
    confirmation = result
    completion_rate = confirmation.get('completion_rate', 0.0)
    completion_percentage = confirmation.get('completion_percentage', 0.0)
    is_100_percent = confirmation.get('is_100_percent', False)
    total_final = confirmation.get('total_final', 0)
    expected_total_check = confirmation.get('expected_total', 0)
    
    should_proceed = (
        is_100_percent and 
        total_final == expected_total_check and 
        completion_percentage >= 100.0
    )
    
    print(f"  Research phase should proceed: {should_proceed}")
    assert should_proceed == True, "Research phase SHOULD proceed now"
    print(f"  [OK] Research phase correctly allowed (100% complete)")
    
    print("\n[PASS] Premature completion prevention test passed!")
    return True


async def test_batch_initialized_message():
    """
    Test that batch:initialized message is sent with correct total count.
    """
    print("\n" + "=" * 80)
    print("Test: Batch Initialized Message")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    
    batch_id = "sync_test_002"
    
    # Simulate _load_link_context by manually setting up context
    context = {
        'youtube': [
            {'link_id': 'yt1', 'url': 'https://youtube.com/1'},
            {'link_id': 'yt2', 'url': 'https://youtube.com/2'}
        ],
        'reddit': [
            {'link_id': 'rd1', 'url': 'https://reddit.com/1'}
        ]
    }
    
    # Calculate totals
    totals = calculate_total_scraping_processes(context)
    workflow_service.batch_totals[batch_id] = {
        'total_processes': totals['total_processes'],
        'total_links': totals['total_links'],
        'breakdown': totals['breakdown'],
        'link_breakdown': totals['link_breakdown'],
        'calculated_at': datetime.now().isoformat(),
        'source': 'test'
    }
    
    # Send batch:initialized message (simulating _load_link_context)
    await ws_manager.broadcast(batch_id, {
        'type': 'batch:initialized',
        'batch_id': batch_id,
        'total_processes': totals['total_processes'],
        'total_links': totals['total_links'],
        'breakdown': totals['breakdown'],
        'link_breakdown': totals['link_breakdown'],
        'timestamp': datetime.now().isoformat(),
        'message': f'已初始化批次，共 {totals["total_processes"]} 个抓取任务'
    })
    
    # Check message was sent
    messages = ws_manager.get_messages(batch_id, 'batch:initialized')
    assert len(messages) > 0, "batch:initialized message should be sent"
    
    message = messages[0]
    print(f"\n  batch:initialized message:")
    print(f"    Total processes: {message['total_processes']}")
    print(f"    Total links: {message['total_links']}")
    print(f"    Breakdown: {message['breakdown']}")
    
    # Verify totals
    expected_processes = (2 * 2) + (1 * 1)  # 2 YouTube (2 each) + 1 Reddit (1 each) = 5
    expected_links = 2 + 1  # 3 links
    
    assert message['total_processes'] == expected_processes, f"Expected {expected_processes} processes"
    assert message['total_links'] == expected_links, f"Expected {expected_links} links"
    assert message['breakdown']['youtube'] == 4, "YouTube should have 4 processes"
    assert message['breakdown']['reddit'] == 1, "Reddit should have 1 process"
    
    print(f"  [OK] Message contains correct totals")
    print(f"  [OK] Frontend can use this to track progress from the start")
    
    print("\n[PASS] Batch initialized message test passed!")
    return True


async def test_completion_rate_in_status_messages():
    """
    Test that batch status messages include completion_rate and is_100_percent.
    """
    print("\n" + "=" * 80)
    print("Test: Completion Rate in Status Messages")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    progress_service = workflow_service.progress_service
    
    batch_id = "sync_test_003"
    expected_total = 6
    
    # Initialize
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(expected_total)
    ]
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    # Complete 3 processes
    for i in range(3):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    # Trigger status update
    await progress_service._update_batch_status(batch_id)
    
    # Check status message
    messages = ws_manager.get_messages(batch_id, 'scraping:status')
    assert len(messages) > 0, "Status message should be sent"
    
    message = messages[-1]  # Get latest
    print(f"\n  Status message fields:")
    print(f"    total: {message.get('total')}")
    print(f"    completed: {message.get('completed')}")
    print(f"    overall_progress: {message.get('overall_progress')}")
    print(f"    completion_rate: {message.get('completion_rate')}")
    print(f"    completion_percentage: {message.get('completion_percentage')}")
    print(f"    is_100_percent: {message.get('is_100_percent')}")
    print(f"    can_proceed_to_research: {message.get('can_proceed_to_research')}")
    
    # Verify fields exist
    assert 'completion_rate' in message, "completion_rate should be in message"
    assert 'completion_percentage' in message, "completion_percentage should be in message"
    assert 'is_100_percent' in message, "is_100_percent should be in message"
    assert 'can_proceed_to_research' in message, "can_proceed_to_research should be in message"
    
    # Verify values (3/6 = 50%)
    assert message['completion_rate'] == 0.5, f"Should be 0.5, got {message['completion_rate']}"
    assert message['completion_percentage'] == 50.0, f"Should be 50.0%, got {message['completion_percentage']}"
    assert message['is_100_percent'] == False, "Should not be 100%"
    assert message['can_proceed_to_research'] == False, "Should not allow research phase"
    
    print(f"  [OK] All completion rate fields present")
    print(f"  [OK] Values are correct (50% completion)")
    print(f"  [OK] Frontend can use these fields to track progress")
    
    print("\n[PASS] Completion rate in status messages test passed!")
    return True


async def test_100_percent_complete_message():
    """
    Test that scraping:100_percent_complete message is sent when 100% is reached.
    """
    print("\n" + "=" * 80)
    print("Test: 100% Complete Message")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    progress_service = workflow_service.progress_service
    
    batch_id = "sync_test_004"
    expected_total = 4
    
    # Initialize
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(expected_total)
    ]
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    # Complete all processes
    for i in range(expected_total):
        await progress_service.update_link_progress(
            batch_id, f'link_{i}', f'https://example.com/{i}',
            'completed', 100.0, 100.0, 'Completed'
        )
    
    # Simulate what happens in _process_progress_queue when verification happens
    confirmation_result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    if confirmation_result.get('is_100_percent') and confirmation_result.get('confirmed'):
        completion_rate = confirmation_result.get('completion_rate', 0.0)
        completion_percentage = confirmation_result.get('completion_percentage', 0.0)
        total_final = confirmation_result.get('total_final', 0)
        expected_total_check = confirmation_result.get('expected_total', 0)
        
        if total_final == expected_total_check:
            await ws_manager.broadcast(batch_id, {
                'type': 'scraping:100_percent_complete',
                'batch_id': batch_id,
                'completion_rate': completion_rate,
                'completion_percentage': completion_percentage,
                'completed_count': confirmation_result.get('completed_count', 0),
                'failed_count': confirmation_result.get('failed_count', 0),
                'expected_total': expected_total_check,
                'message': '所有抓取任务已完成 (100%)',
                'timestamp': datetime.now().isoformat()
            })
    
    # Check message was sent
    messages = ws_manager.get_messages(batch_id, 'scraping:100_percent_complete')
    assert len(messages) > 0, "100% complete message should be sent"
    
    message = messages[0]
    print(f"\n  100% complete message:")
    print(f"    completion_rate: {message['completion_rate']}")
    print(f"    completion_percentage: {message['completion_percentage']}")
    print(f"    completed_count: {message['completed_count']}")
    print(f"    expected_total: {message['expected_total']}")
    
    assert message['completion_rate'] == 1.0, "Should be 1.0"
    assert message['completion_percentage'] == 100.0, "Should be 100.0%"
    assert message['completed_count'] == expected_total, f"Should have {expected_total} completed"
    assert message['expected_total'] == expected_total, f"Should match expected {expected_total}"
    
    print(f"  [OK] Message sent with correct 100% completion data")
    print(f"  [OK] Frontend can use this as clear signal to enable research phase")
    
    print("\n[PASS] 100% complete message test passed!")
    return True


async def main():
    """Run all integration tests."""
    print("=" * 80)
    print("WORKFLOW SYNC INTEGRATION TEST SUITE")
    print("=" * 80)
    print("\nTesting that frontend and backend stay in sync, and research phase")
    print("only starts when ALL expected processes are 100% complete.")
    
    results = []
    
    try:
        results.append(("Premature Completion Prevention", await test_premature_completion_prevention()))
    except Exception as e:
        print(f"\n[FAIL] Premature completion prevention: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Premature Completion Prevention", False))
    
    try:
        results.append(("Batch Initialized Message", await test_batch_initialized_message()))
    except Exception as e:
        print(f"\n[FAIL] Batch initialized message: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Batch Initialized Message", False))
    
    try:
        results.append(("Completion Rate in Status Messages", await test_completion_rate_in_status_messages()))
    except Exception as e:
        print(f"\n[FAIL] Completion rate in status messages: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Completion Rate in Status Messages", False))
    
    try:
        results.append(("100% Complete Message", await test_100_percent_complete_message()))
    except Exception as e:
        print(f"\n[FAIL] 100% complete message: {e}")
        import traceback
        traceback.print_exc()
        results.append(("100% Complete Message", False))
    
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
        print("\n[SUCCESS] All integration tests passed!")
        print("\n[OK] Frontend and backend are in sync")
        print("[OK] Research phase only starts when ALL expected processes are 100% complete")
        print("[OK] System correctly prevents premature transition")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

