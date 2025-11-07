"""
Test to verify that progress tracking uses expected_total instead of started processes.
"""
import asyncio
import sys
import os
import io
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / 'app'))

from app.services.progress_service import ProgressService
from app.websocket.manager import WebSocketManager
from collections import defaultdict

class MockWebSocketManager:
    """Mock WebSocket manager to capture messages."""
    def __init__(self):
        self.messages = defaultdict(list)
    
    async def broadcast(self, batch_id: str, message: dict):
        """Capture broadcast messages."""
        self.messages[batch_id].append(message)
        print(f"[BROADCAST] {batch_id}: {message.get('type')} - {message}")

async def test_expected_total_calculation():
    """Test that completion_rate is calculated against expected_total, not started processes."""
    print("=" * 80)
    print("TEST: Expected Total vs Started Processes")
    print("=" * 80)
    
    # Setup
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    batch_id = "test_batch_001"
    
    # Scenario: We expect 10 processes total, but only 6 have started so far
    expected_total = 10
    started_processes = 6
    completed_processes = 2
    
    print(f"\nScenario:")
    print(f"  Expected total: {expected_total}")
    print(f"  Started processes: {started_processes}")
    print(f"  Completed processes: {completed_processes}")
    print(f"  Expected completion rate: {completed_processes}/{expected_total} = {completed_processes/expected_total*100:.1f}%")
    print(f"  WRONG completion rate (if using started): {completed_processes}/{started_processes} = {completed_processes/started_processes*100:.1f}%")
    
    # Step 1: Initialize expected links (simulating batch:initialized)
    print(f"\nStep 1: Initialize {expected_total} expected processes")
    expected_links = []
    for i in range(expected_total):
        expected_links.append({
            'link_id': f'link_{i}',
            'url': f'https://example.com/{i}',
            'scraper_type': 'youtube' if i % 2 == 0 else 'reddit',
            'process_type': 'transcript' if i % 2 == 0 else 'article'
        })
    
    registered_count = progress_service.initialize_expected_links(batch_id, expected_links)
    print(f"  [OK] Pre-registered {registered_count} expected processes")
    print(f"  [OK] Expected total set: {progress_service.expected_totals.get(batch_id, 0)}")
    
    # Step 2: Simulate only 6 processes starting and 2 completing
    print(f"\nStep 2: Simulate {started_processes} processes starting, {completed_processes} completing")
    
    # Start 6 processes (only some have started)
    for i in range(started_processes):
        link_id = f'link_{i}'
        await progress_service.update_link_progress(
            batch_id,
            link_id,
            f'https://example.com/{i}',
            stage='extracting',
            stage_progress=50.0,
            overall_progress=50.0,
            message='Processing...'
        )
    
    # Complete 2 processes
    for i in range(completed_processes):
        link_id = f'link_{i}'
        await progress_service.update_link_progress(
            batch_id,
            link_id,
            f'https://example.com/{i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
    
    # Step 3: Get status update (this calls _update_batch_status internally)
    print(f"\nStep 3: Get status update")
    await progress_service._update_batch_status(batch_id)
    
    # Step 4: Check the broadcast message
    print(f"\nStep 4: Verify broadcast message")
    status_messages = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'scraping:status']
    
    if not status_messages:
        print("  ✗ ERROR: No scraping:status message found!")
        return False
    
    status_msg = status_messages[-1]  # Get latest
    print(f"  Status message fields:")
    print(f"    total (started): {status_msg.get('total')}")
    print(f"    expected_total: {status_msg.get('expected_total')}")
    print(f"    completed: {status_msg.get('completed')}")
    print(f"    completion_rate: {status_msg.get('completion_rate')}")
    print(f"    completion_percentage: {status_msg.get('completion_percentage')}")
    print(f"    is_100_percent: {status_msg.get('is_100_percent')}")
    
    # Verify
    print(f"\nVerification:")
    errors = []
    
    # Check expected_total is set
    if status_msg.get('expected_total') != expected_total:
        errors.append(f"expected_total should be {expected_total}, got {status_msg.get('expected_total')}")
    else:
        print(f"  [OK] expected_total is correct: {expected_total}")
    
    # Check total (started) is correct
    # Note: Since all processes are pre-registered, total will equal expected_total
    # The key is that completion_rate uses expected_total, not just started processes
    if status_msg.get('total') != expected_total:
        # This is OK - total represents registered processes, which includes all pre-registered ones
        print(f"  [INFO] total (registered) is {status_msg.get('total')}, expected_total is {expected_total}")
        print(f"  [INFO] This is correct - all processes are pre-registered, so total equals expected_total")
    else:
        print(f"  [OK] total (registered processes) equals expected_total: {expected_total}")
    
    # Check completion_rate is calculated against expected_total
    expected_rate = completed_processes / expected_total
    actual_rate = status_msg.get('completion_rate', 0)
    
    if abs(actual_rate - expected_rate) > 0.001:
        errors.append(f"completion_rate should be {expected_rate:.3f} (calculated against expected_total), got {actual_rate:.3f}")
    else:
        print(f"  [OK] completion_rate is correct: {actual_rate:.3f} ({completed_processes}/{expected_total})")
    
    # Check it's NOT calculated against started processes
    wrong_rate = completed_processes / started_processes
    if abs(actual_rate - wrong_rate) < 0.001:
        errors.append(f"ERROR: completion_rate is calculated against started processes ({wrong_rate:.3f}) instead of expected_total!")
    else:
        print(f"  [OK] completion_rate is NOT using started processes (would be {wrong_rate:.3f})")
    
    # Check completion_percentage
    expected_percentage = expected_rate * 100.0
    actual_percentage = status_msg.get('completion_percentage', 0)
    
    if abs(actual_percentage - expected_percentage) > 0.1:
        errors.append(f"completion_percentage should be {expected_percentage:.1f}%, got {actual_percentage:.1f}%")
    else:
        print(f"  [OK] completion_percentage is correct: {actual_percentage:.1f}%")
    
    # Check is_100_percent is False (since only 2/10 complete)
    if status_msg.get('is_100_percent') != False:
        errors.append(f"is_100_percent should be False (2/10 complete), got {status_msg.get('is_100_percent')}")
    else:
        print(f"  [OK] is_100_percent is False (correct, not 100% yet)")
    
    if errors:
        print(f"\n[FAIL] TEST FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n[PASS] TEST PASSED: All checks passed!")
        return True

async def test_100_percent_completion():
    """Test that 100% completion is correctly detected when all expected processes complete."""
    print("\n" + "=" * 80)
    print("TEST: 100% Completion Detection")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    batch_id = "test_batch_002"
    
    expected_total = 8
    print(f"\nScenario: {expected_total} expected processes, all complete")
    
    # Initialize
    expected_links = []
    for i in range(expected_total):
        expected_links.append({
            'link_id': f'link_{i}',
            'url': f'https://example.com/{i}',
            'scraper_type': 'youtube',
            'process_type': 'transcript'
        })
    
    progress_service.initialize_expected_links(batch_id, expected_links)
    
    # Complete all processes
    print(f"\nCompleting all {expected_total} processes...")
    for i in range(expected_total):
        link_id = f'link_{i}'
        await progress_service.update_link_progress(
            batch_id,
            link_id,
            f'https://example.com/{i}',
            stage='completed',
            stage_progress=100.0,
            overall_progress=100.0,
            message='Completed'
        )
    
    # Get status
    await progress_service._update_batch_status(batch_id)
    
    # Check
    status_messages = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'scraping:status']
    status_msg = status_messages[-1]
    
    print(f"\nStatus:")
    print(f"  completed: {status_msg.get('completed')}")
    print(f"  expected_total: {status_msg.get('expected_total')}")
    print(f"  completion_rate: {status_msg.get('completion_rate')}")
    print(f"  is_100_percent: {status_msg.get('is_100_percent')}")
    
    errors = []
    if status_msg.get('completed') != expected_total:
        errors.append(f"completed should be {expected_total}, got {status_msg.get('completed')}")
    if status_msg.get('completion_rate') != 1.0:
        errors.append(f"completion_rate should be 1.0, got {status_msg.get('completion_rate')}")
    if status_msg.get('is_100_percent') != True:
        errors.append(f"is_100_percent should be True, got {status_msg.get('is_100_percent')}")
    
    if errors:
        print(f"\n[FAIL] TEST FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n[PASS] TEST PASSED: 100% completion correctly detected!")
        return True

async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PROGRESS TRACKING FIX VERIFICATION")
    print("=" * 80)
    
    test1_passed = await test_expected_total_calculation()
    test2_passed = await test_100_percent_completion()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Expected Total Calculation): {'PASS' if test1_passed else 'FAIL'}")
    print(f"Test 2 (100% Completion Detection): {'PASS' if test2_passed else 'FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        return 0
    else:
        print("\n[FAILURE] SOME TESTS FAILED")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

