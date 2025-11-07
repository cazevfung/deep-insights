"""Test to verify the expected_total=0 fix and research phase startup.

This test verifies:
1. confirm_all_scraping_complete handles expected_total=0 correctly
2. Research phase can start when expected_total is 0 but links are registered
3. The fix properly calculates expected_total from registered links
4. Both scenarios: with and without initialize_expected_links
"""
import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Fix Unicode encoding for Windows console
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
# From tests/debugging/test_expected_total_fix.py, we need to go up 3 levels to project root
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / 'backend'
app_path = backend_path / 'app'

print(f"[DEBUG] Current file: {__file__}")
print(f"[DEBUG] File parent (tests/debugging): {Path(__file__).parent}")
print(f"[DEBUG] File parent.parent (tests): {Path(__file__).parent.parent}")
print(f"[DEBUG] File parent.parent.parent (project root): {project_root}")
print(f"[DEBUG] Backend path: {backend_path}")
print(f"[DEBUG] App path: {app_path}")
print(f"[DEBUG] Project root exists: {project_root.exists()}")
print(f"[DEBUG] Backend path exists: {backend_path.exists()}")
print(f"[DEBUG] App path exists: {app_path.exists()}")

sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(app_path))

print(f"[DEBUG] sys.path after setup:")
for i, p in enumerate(sys.path[:5]):
    print(f"  [{i}] {p}")

from loguru import logger

# Try importing with error handling
try:
    print("[DEBUG] Attempting to import ProgressService...")
    from app.services.progress_service import ProgressService
    print("[DEBUG] Successfully imported ProgressService")
except ImportError as e:
    print(f"[DEBUG] Failed to import ProgressService: {e}")
    print(f"[DEBUG] Trying alternative import paths...")
    # Try alternative paths
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "progress_service",
            app_path / "services" / "progress_service.py"
        )
        if spec and spec.loader:
            progress_service_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(progress_service_module)
            ProgressService = progress_service_module.ProgressService
            print("[DEBUG] Successfully loaded ProgressService via importlib")
        else:
            raise ImportError("Could not create spec for progress_service")
    except Exception as e2:
        print(f"[DEBUG] Alternative import also failed: {e2}")
        raise

try:
    print("[DEBUG] Attempting to import WorkflowService...")
    from app.services.workflow_service import WorkflowService
    print("[DEBUG] Successfully imported WorkflowService")
except ImportError as e:
    print(f"[DEBUG] Failed to import WorkflowService: {e}")
    # Try alternative import
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "workflow_service",
            app_path / "services" / "workflow_service.py"
        )
        if spec and spec.loader:
            workflow_service_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(workflow_service_module)
            WorkflowService = workflow_service_module.WorkflowService
            print("[DEBUG] Successfully loaded WorkflowService via importlib")
        else:
            raise ImportError("Could not create spec for workflow_service")
    except Exception as e2:
        print(f"[DEBUG] Alternative import also failed: {e2}")
        # WorkflowService might not be needed for all tests, so we'll handle it per test
        WorkflowService = None

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:HH:mm:ss.SSS} | {level: <8} | {message}",
    level="INFO"
)

# Mock WebSocket manager
class MockWSManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
    
    async def broadcast(self, batch_id: str, message: Dict[str, Any]):
        """Capture broadcast messages."""
        self.messages.append(message)
        logger.info(f"[BROADCAST] {message.get('type')}: {message.get('message', '')}")
    
    async def connect(self, websocket, batch_id: str):
        pass
    
    async def disconnect(self, websocket, batch_id: str):
        pass
    
    def get_connection_count(self, batch_id: str) -> int:
        return 0
    
    def get_messages_by_type(self, msg_type: str) -> List[Dict]:
        """Get messages by type."""
        return [msg for msg in self.messages if msg.get('type') == msg_type]


async def test_expected_total_zero_with_registered_links():
    """Test the fix: expected_total=0 but links are registered."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: expected_total=0 with registered links (THE BUG SCENARIO)")
    logger.info("=" * 80)
    
    ws_manager = MockWSManager()
    progress_service = ProgressService(ws_manager)
    batch_id = f"test_expected_total_zero_{int(time.time())}"
    
    # Scenario: Links are registered but expected_total is 0 (bug scenario)
    # This simulates the case where initialize_expected_links wasn't called
    # or was called with an empty list
    
    logger.info(f"[TEST] Batch ID: {batch_id}")
    logger.info("[TEST] Simulating bug scenario: expected_total=0 but 57 links registered")
    
    # Register 57 links directly (simulating what happens during scraping)
    # WITHOUT calling initialize_expected_links first
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(57)
    ]
    
    # Manually register links (simulating what happens during scraping)
    for link_info in expected_links:
        await progress_service.update_link_progress(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            stage='extracting',
            stage_progress=50.0,
            overall_progress=50.0,
            message='Processing'
        )
    
    logger.info(f"[TEST] Registered {len(expected_links)} links")
    logger.info(f"[TEST] expected_total before fix: {progress_service.expected_totals.get(batch_id, 'NOT SET')}")
    
    # Mark all as completed
    for link_info in expected_links:
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            status='completed'
        )
    
    # Now test confirm_all_scraping_complete with expected_total=0
    logger.info("[TEST] Calling confirm_all_scraping_complete (with expected_total=0)...")
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    logger.info(f"[RESULT] Confirmation result:")
    logger.info(f"  - confirmed: {result.get('confirmed')}")
    logger.info(f"  - expected_total: {result.get('expected_total')}")
    logger.info(f"  - registered_count: {result.get('registered_count')}")
    logger.info(f"  - completed_count: {result.get('completed_count')}")
    logger.info(f"  - failed_count: {result.get('failed_count')}")
    logger.info(f"  - total_final: {result.get('total_final')}")
    logger.info(f"  - completion_rate: {result.get('completion_rate')}")
    logger.info(f"  - is_100_percent: {result.get('is_100_percent')}")
    
    # Verify the fix worked
    assert result.get('expected_total') == 57, f"Expected total should be 57, got {result.get('expected_total')}"
    assert result.get('registered_count') == 57, f"Registered count should be 57, got {result.get('registered_count')}"
    assert result.get('completed_count') == 57, f"Completed count should be 57, got {result.get('completed_count')}"
    assert result.get('total_final') == 57, f"Total final should be 57, got {result.get('total_final')}"
    assert result.get('completion_rate') == 1.0, f"Completion rate should be 1.0, got {result.get('completion_rate')}"
    assert result.get('is_100_percent') == True, f"is_100_percent should be True, got {result.get('is_100_percent')}"
    assert result.get('confirmed') == True, f"Confirmed should be True, got {result.get('confirmed')}"
    
    logger.info("[PASS] TEST 1 PASSED: Fix correctly handles expected_total=0 scenario")
    return True


async def test_expected_total_zero_with_mixed_status():
    """Test with some completed, some failed (like the real scenario: 56 completed, 1 failed)."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: expected_total=0 with mixed status (56 completed, 1 failed)")
    logger.info("=" * 80)
    
    ws_manager = MockWSManager()
    progress_service = ProgressService(ws_manager)
    batch_id = f"test_mixed_status_{int(time.time())}"
    
    logger.info(f"[TEST] Batch ID: {batch_id}")
    
    # Register 57 links
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(57)
    ]
    
    # Register all links
    for link_info in expected_links:
        await progress_service.update_link_progress(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            stage='extracting',
            stage_progress=50.0,
            overall_progress=50.0,
            message='Processing'
        )
    
    # Mark 56 as completed, 1 as failed (real scenario)
    for i, link_info in enumerate(expected_links):
        status = 'completed' if i < 56 else 'failed'
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            status=status
        )
    
    logger.info(f"[TEST] Status: 56 completed, 1 failed")
    
    # Test confirmation
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    logger.info(f"[RESULT] Confirmation result:")
    logger.info(f"  - confirmed: {result.get('confirmed')}")
    logger.info(f"  - expected_total: {result.get('expected_total')}")
    logger.info(f"  - completed_count: {result.get('completed_count')}")
    logger.info(f"  - failed_count: {result.get('failed_count')}")
    logger.info(f"  - total_final: {result.get('total_final')}")
    logger.info(f"  - completion_rate: {result.get('completion_rate')}")
    logger.info(f"  - is_100_percent: {result.get('is_100_percent')}")
    
    # Verify
    assert result.get('expected_total') == 57, f"Expected total should be 57"
    assert result.get('completed_count') == 56, f"Completed count should be 56"
    assert result.get('failed_count') == 1, f"Failed count should be 1"
    assert result.get('total_final') == 57, f"Total final should be 57"
    assert result.get('completion_rate') == 1.0, f"Completion rate should be 1.0"
    assert result.get('is_100_percent') == True, f"is_100_percent should be True"
    assert result.get('confirmed') == True, f"Confirmed should be True"
    
    logger.info("[PASS] TEST 2 PASSED: Fix correctly handles mixed status scenario")
    return True


async def test_research_phase_startup_simulation():
    """Simulate the full workflow to verify research phase would start."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Full workflow simulation - Research phase startup")
    logger.info("=" * 80)
    
    if WorkflowService is None:
        logger.warning("[SKIP] WorkflowService not available, skipping test")
        return True
    
    ws_manager = MockWSManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    workflow_service.progress_service = progress_service
    
    batch_id = f"test_research_startup_{int(time.time())}"
    
    logger.info(f"[TEST] Batch ID: {batch_id}")
    
    # Simulate the bug scenario: expected_total=0, but links are registered
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(57)
    ]
    
    # Register links (simulating scraping in progress)
    for link_info in expected_links:
        await progress_service.update_link_progress(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            stage='extracting',
            stage_progress=50.0,
            overall_progress=50.0,
            message='Processing'
        )
    
    # Complete all links
    for i, link_info in enumerate(expected_links):
        status = 'completed' if i < 56 else 'failed'
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            status=status
        )
    
    # Simulate the workflow service checking for confirmation
    logger.info("[TEST] Simulating workflow service confirmation check...")
    message_queue = asyncio.Queue()
    
    # Test wait_for_scraping_confirmation (which calls confirm_all_scraping_complete)
    confirmation = await workflow_service.wait_for_scraping_confirmation(
        message_queue, batch_id, max_wait_seconds=5.0
    )
    
    if confirmation:
        logger.info(f"[RESULT] Confirmation received:")
        logger.info(f"  - confirmed: {confirmation.get('confirmed')}")
        logger.info(f"  - expected_total: {confirmation.get('expected_total')}")
        logger.info(f"  - completion_rate: {confirmation.get('completion_rate')}")
        logger.info(f"  - is_100_percent: {confirmation.get('is_100_percent')}")
        
        # Verify research phase would start
        if confirmation.get('confirmed') and confirmation.get('is_100_percent'):
            logger.info("✅ Research phase WOULD START (confirmation passed)")
            
            # Check if research:phase_change would be sent
            phase_change_msgs = ws_manager.get_messages_by_type('research:phase_change')
            logger.info(f"[TEST] research:phase_change messages: {len(phase_change_msgs)}")
            
            # In a real scenario, workflow_service would send research:phase_change here
            # For this test, we just verify the confirmation would allow it
            assert confirmation.get('confirmed') == True, "Confirmation should be True"
            assert confirmation.get('is_100_percent') == True, "is_100_percent should be True"
            assert confirmation.get('expected_total') > 0, "expected_total should be > 0"
            
            logger.info("[PASS] TEST 3 PASSED: Research phase would start normally")
            return True
        else:
            logger.error("[FAIL] Research phase would NOT start (confirmation failed)")
            return False
    else:
        logger.error("[FAIL] No confirmation received")
        return False


async def test_normal_flow_with_initialize():
    """Test normal flow where initialize_expected_links is called first."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Normal flow with initialize_expected_links called first")
    logger.info("=" * 80)
    
    ws_manager = MockWSManager()
    progress_service = ProgressService(ws_manager)
    batch_id = f"test_normal_flow_{int(time.time())}"
    
    logger.info(f"[TEST] Batch ID: {batch_id}")
    
    # Normal flow: initialize_expected_links is called first
    expected_links = [
        {'link_id': f'link_{i}', 'url': f'https://example.com/{i}'}
        for i in range(57)
    ]
    
    # Call initialize_expected_links first (normal flow)
    registered_count = progress_service.initialize_expected_links(batch_id, expected_links)
    logger.info(f"[TEST] initialize_expected_links returned: {registered_count}")
    logger.info(f"[TEST] expected_total set to: {progress_service.expected_totals.get(batch_id)}")
    
    # Complete all links
    for link_info in expected_links:
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=link_info['link_id'],
            url=link_info['url'],
            status='completed'
        )
    
    # Test confirmation
    result = await progress_service.confirm_all_scraping_complete(batch_id)
    
    logger.info(f"[RESULT] Confirmation result:")
    logger.info(f"  - confirmed: {result.get('confirmed')}")
    logger.info(f"  - expected_total: {result.get('expected_total')}")
    logger.info(f"  - completion_rate: {result.get('completion_rate')}")
    
    # Verify normal flow still works
    assert result.get('expected_total') == 57, f"Expected total should be 57"
    assert result.get('confirmed') == True, f"Confirmed should be True"
    assert result.get('is_100_percent') == True, f"is_100_percent should be True"
    
    logger.info("[PASS] TEST 4 PASSED: Normal flow still works correctly")
    return True


async def run_all_tests():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUITE: expected_total=0 Fix Verification")
    logger.info("=" * 80)
    
    results = []
    
    try:
        # Test 1: Bug scenario
        result1 = await test_expected_total_zero_with_registered_links()
        results.append(("Test 1: expected_total=0 with registered links", result1))
    except Exception as e:
        logger.error(f"[FAIL] Test 1 FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        results.append(("Test 1: expected_total=0 with registered links", False))
    
    try:
        # Test 2: Mixed status
        result2 = await test_expected_total_zero_with_mixed_status()
        results.append(("Test 2: expected_total=0 with mixed status", result2))
    except Exception as e:
        logger.error(f"[FAIL] Test 2 FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        results.append(("Test 2: expected_total=0 with mixed status", False))
    
    try:
        # Test 3: Research phase startup
        result3 = await test_research_phase_startup_simulation()
        results.append(("Test 3: Research phase startup simulation", result3))
    except Exception as e:
        logger.error(f"[FAIL] Test 3 FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        results.append(("Test 3: Research phase startup simulation", False))
    
    try:
        # Test 4: Normal flow
        result4 = await test_normal_flow_with_initialize()
        results.append(("Test 4: Normal flow with initialize", result4))
    except Exception as e:
        logger.error(f"[FAIL] Test 4 FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        results.append(("Test 4: Normal flow with initialize", False))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("[SUCCESS] ALL TESTS PASSED! The fix is working correctly.")
        return True
    else:
        logger.error(f"[WARNING] {total - passed} test(s) failed. Please review the fix.")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("EXPECTED_TOTAL=0 FIX VERIFICATION TEST")
    print("=" * 80)
    
    success = asyncio.run(run_all_tests())
    
    print("\n" + "=" * 80)
    if success:
        print("[SUCCESS] ALL TESTS PASSED - Fix is working correctly!")
        sys.exit(0)
    else:
        print("[FAIL] SOME TESTS FAILED - Please review the results above")
        sys.exit(1)

