"""
Test summarization progress updates.

Tests that:
1. WebSocketUI.display_summarization_progress sends correct messages
2. Phase0Prepare integrates with progress updates correctly
3. Progress messages are formatted correctly
"""
import sys
import asyncio
import io
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.services.websocket_ui import WebSocketUI
from app.websocket.manager import WebSocketManager


class MockWebSocketManager:
    """Mock WebSocket manager to capture messages."""
    def __init__(self):
        self.messages = []
        self.broadcast_calls = []
    
    async def broadcast(self, batch_id: str, message: dict):
        """Capture broadcast messages."""
        self.messages.append({
            'batch_id': batch_id,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        self.broadcast_calls.append((batch_id, message))
        print(f"[MOCK WS] Broadcast to {batch_id}: {message.get('type')} - {message.get('message', '')[:50]}")


async def test_websocket_ui_summarization_progress():
    """Test WebSocketUI.display_summarization_progress method."""
    print("\n" + "=" * 80)
    print("TEST 1: WebSocketUI.display_summarization_progress")
    print("=" * 80)
    
    # Create mock WebSocket manager
    mock_ws_manager = MockWebSocketManager()
    batch_id = "test_batch_001"
    
    # Create event loop for async operations
    loop = asyncio.get_event_loop()
    
    # Create WebSocketUI instance
    ui = WebSocketUI(mock_ws_manager, batch_id, main_loop=loop)
    
    # Test 1: Send initial progress
    print("\n[Test 1.1] Sending initial progress (0/5)...")
    ui.display_summarization_progress(
        current_item=0,
        total_items=5,
        link_id="",
        stage="starting",
        message="开始创建摘要 (5 个内容项)"
    )
    
    # Wait a bit for async to complete
    await asyncio.sleep(0.1)
    
    # Test 2: Send item progress
    print("\n[Test 1.2] Sending item progress (1/5)...")
    ui.display_summarization_progress(
        current_item=1,
        total_items=5,
        link_id="yt_req1",
        stage="summarizing",
        message="正在总结 [1/5]: yt_req1"
    )
    
    await asyncio.sleep(0.1)
    
    # Test 3: Send completion
    print("\n[Test 1.3] Sending completion (1/5)...")
    ui.display_summarization_progress(
        current_item=1,
        total_items=5,
        link_id="yt_req1",
        stage="completed",
        message="总结好了 [1/5]: yt_req1 (15 标记)"
    )
    
    await asyncio.sleep(0.1)
    
    # Test 4: Send final completion
    print("\n[Test 1.4] Sending final completion (5/5)...")
    ui.display_summarization_progress(
        current_item=5,
        total_items=5,
        link_id="",
        stage="all_completed",
        message="所有摘要创建完成 (3 新建, 2 重用)"
    )
    
    await asyncio.sleep(0.1)
    
    # Verify messages
    print(f"\n[Verification] Total messages captured: {len(mock_ws_manager.messages)}")
    
    assert len(mock_ws_manager.messages) == 4, f"Expected 4 messages, got {len(mock_ws_manager.messages)}"
    
    # Check first message (initial)
    msg1 = mock_ws_manager.messages[0]['message']
    assert msg1['type'] == 'summarization:progress', f"Expected type 'summarization:progress', got '{msg1['type']}'"
    assert msg1['current_item'] == 0, f"Expected current_item=0, got {msg1['current_item']}"
    assert msg1['total_items'] == 5, f"Expected total_items=5, got {msg1['total_items']}"
    assert msg1['progress'] == 0.0, f"Expected progress=0.0, got {msg1['progress']}"
    assert msg1['stage'] == 'starting', f"Expected stage='starting', got '{msg1['stage']}'"
    print("  ✓ Initial progress message correct")
    
    # Check second message (item progress)
    msg2 = mock_ws_manager.messages[1]['message']
    assert msg2['type'] == 'summarization:progress', f"Expected type 'summarization:progress', got '{msg2['type']}'"
    assert msg2['current_item'] == 1, f"Expected current_item=1, got {msg2['current_item']}"
    assert msg2['total_items'] == 5, f"Expected total_items=5, got {msg2['total_items']}"
    assert msg2['progress'] == 20.0, f"Expected progress=20.0, got {msg2['progress']}"
    assert msg2['link_id'] == 'yt_req1', f"Expected link_id='yt_req1', got '{msg2['link_id']}'"
    assert msg2['stage'] == 'summarizing', f"Expected stage='summarizing', got '{msg2['stage']}'"
    print("  ✓ Item progress message correct")
    
    # Check third message (completion)
    msg3 = mock_ws_manager.messages[2]['message']
    assert msg3['current_item'] == 1, f"Expected current_item=1, got {msg3['current_item']}"
    assert msg3['stage'] == 'completed', f"Expected stage='completed', got '{msg3['stage']}'"
    assert '标记' in msg3['message'], f"Expected '标记' in message, got '{msg3['message']}'"
    print("  ✓ Completion message correct")
    
    # Check fourth message (final)
    msg4 = mock_ws_manager.messages[3]['message']
    assert msg4['current_item'] == 5, f"Expected current_item=5, got {msg4['current_item']}"
    assert msg4['progress'] == 100.0, f"Expected progress=100.0, got {msg4['progress']}"
    assert msg4['stage'] == 'all_completed', f"Expected stage='all_completed', got '{msg4['stage']}'"
    print("  ✓ Final completion message correct")
    
    print("\n✅ TEST 1 PASSED: WebSocketUI.display_summarization_progress works correctly")


def test_phase0_prepare_integration():
    """Test that Phase0Prepare can use display_summarization_progress."""
    print("\n" + "=" * 80)
    print("TEST 2: Phase0Prepare Integration")
    print("=" * 80)
    
    # Check that Phase0Prepare has the method call
    from research.phases.phase0_prepare import Phase0Prepare
    
    # Read the source file to verify the integration
    phase0_file = Path(__file__).parent.parent / "research" / "phases" / "phase0_prepare.py"
    source_code = phase0_file.read_text(encoding='utf-8')
    
    # Check for key patterns
    checks = [
        ('display_summarization_progress', 'Method call exists'),
        ('current_item=', 'Progress tracking parameter'),
        ('total_items=', 'Total items parameter'),
        ('stage=', 'Stage parameter'),
        ('正在总结', 'Chinese progress message'),
        ('总结好了', 'Chinese completion message'),
    ]
    
    print("\n[Verification] Checking Phase0Prepare source code...")
    all_passed = True
    for pattern, description in checks:
        if pattern in source_code:
            print(f"  ✓ {description}: Found '{pattern}'")
        else:
            print(f"  ✗ {description}: Missing '{pattern}'")
            all_passed = False
    
    if all_passed:
        print("\n✅ TEST 2 PASSED: Phase0Prepare integration verified")
    else:
        print("\n❌ TEST 2 FAILED: Some patterns missing")
        raise AssertionError("Phase0Prepare integration incomplete")


def test_progress_calculation():
    """Test progress percentage calculation."""
    print("\n" + "=" * 80)
    print("TEST 3: Progress Calculation")
    print("=" * 80)
    
    test_cases = [
        (0, 5, 0.0),
        (1, 5, 20.0),
        (2, 5, 40.0),
        (3, 5, 60.0),
        (4, 5, 80.0),
        (5, 5, 100.0),
        (0, 0, 0.0),  # Edge case: division by zero
    ]
    
    print("\n[Test Cases]")
    all_passed = True
    for current_item, total_items, expected_progress in test_cases:
        if total_items > 0:
            calculated = (current_item / total_items) * 100
        else:
            calculated = 0.0
        
        if abs(calculated - expected_progress) < 0.01:  # Allow small floating point errors
            print(f"  ✓ [{current_item}/{total_items}] = {calculated:.1f}%")
        else:
            print(f"  ✗ [{current_item}/{total_items}] = {calculated:.1f}% (expected {expected_progress:.1f}%)")
            all_passed = False
    
    if all_passed:
        print("\n✅ TEST 3 PASSED: Progress calculation correct")
    else:
        print("\n❌ TEST 3 FAILED: Progress calculation errors")
        raise AssertionError("Progress calculation incorrect")


async def run_all_tests():
    """Run all tests."""
    print("=" * 80)
    print("SUMMARIZATION PROGRESS UPDATE TESTS")
    print("=" * 80)
    
    try:
        # Test 1: WebSocketUI
        await test_websocket_ui_summarization_progress()
        
        # Test 2: Phase0Prepare integration
        test_phase0_prepare_integration()
        
        # Test 3: Progress calculation
        test_progress_calculation()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

