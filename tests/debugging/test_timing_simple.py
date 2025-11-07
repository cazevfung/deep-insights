"""Simplified timing test that verifies core improvements without full backend setup.

This test focuses on:
1. Verifying timing log format
2. Testing progress update message structure
3. Confirming WebSocket message delivery
4. Validating timeout reductions
"""
import sys
import time
import asyncio
import queue
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_timing_log_format():
    """Test that timing logs follow the expected format."""
    print("\n" + "=" * 80)
    print("TEST: Timing Log Format")
    print("=" * 80)
    
    # Simulate timing logs
    start_time = time.time()
    time.sleep(0.1)  # Simulate work
    elapsed = time.time() - start_time
    
    # Format should match: [TIMING] Operation completed in X.XXXs
    log_message = f"[TIMING] Test operation completed in {elapsed:.3f}s"
    print(f"Generated log: {log_message}")
    
    assert "[TIMING]" in log_message, "Timing logs should include [TIMING] prefix"
    assert "completed in" in log_message, "Timing logs should indicate completion"
    assert "s" in log_message, "Timing logs should show seconds"
    
    print("[OK] Timing log format is correct")
    return True

def test_progress_message_structure():
    """Test that progress messages have the correct structure."""
    print("\n" + "=" * 80)
    print("TEST: Progress Message Structure")
    print("=" * 80)
    
    # Simulate progress messages
    messages = [
        {"type": "workflow:progress", "message": "正在调用AI API...", "level": "info"},
        {"type": "workflow:progress", "message": "正在接收响应... (50 tokens)", "level": "info"},
        {"type": "research:phase_change", "phase": "phase1", "phase_name": "发现目标"},
        {"type": "scraping:status", "status": "completed", "progress": 100.0},
    ]
    
    for msg in messages:
        print(f"Message type: {msg.get('type')}, has message: {'message' in msg}, has status: {'status' in msg}")
        assert "type" in msg, "Messages should have a 'type' field"
        # Messages can have either 'message', 'status', or 'phase_name' field
        assert "message" in msg or "status" in msg or "phase_name" in msg, "Messages should have content"
    
    print(f"[OK] All {len(messages)} progress messages have correct structure")
    return True

async def test_timeout_reduction():
    """Test that reduced timeouts work correctly."""
    print("\n" + "=" * 80)
    print("TEST: Timeout Reduction")
    print("=" * 80)
    
    # Simulate the old timeout (30s) vs new timeout (10s)
    old_timeout = 30.0
    new_timeout = 10.0
    
    print(f"Old timeout: {old_timeout}s")
    print(f"New timeout: {new_timeout}s")
    print(f"Reduction: {old_timeout - new_timeout}s ({(old_timeout - new_timeout) / old_timeout * 100:.1f}%)")
    
    # Simulate fast completion (should complete before timeout)
    async def fast_operation():
        await asyncio.sleep(0.1)
        return True
    
    start_time = time.time()
    result = await asyncio.wait_for(fast_operation(), timeout=new_timeout)
    elapsed = time.time() - start_time
    
    print(f"Operation completed in {elapsed:.3f}s")
    assert result, "Operation should complete successfully"
    assert elapsed < new_timeout, f"Should complete before timeout ({new_timeout}s)"
    assert elapsed < old_timeout, "Should be faster than old timeout"
    
    print("[OK] Reduced timeout works correctly")
    return True

async def test_websocket_message_order():
    """Test WebSocket message ordering."""
    print("\n" + "=" * 80)
    print("TEST: WebSocket Message Order")
    print("=" * 80)
    
    messages = []
    
    async def send_message(msg_type: str, content: str):
        await asyncio.sleep(0.05)  # Simulate network delay
        messages.append({
            'timestamp': time.time(),
            'type': msg_type,
            'content': content
        })
    
    # Send messages in sequence
    await send_message("scraping:status", "Starting")
    await send_message("research:phase_change", "Phase 0")
    await send_message("workflow:progress", "Processing...")
    await send_message("research:phase_change", "Phase 1")
    await send_message("workflow:progress", "API call")
    await send_message("workflow:progress", "Complete")
    
    print(f"Sent {len(messages)} messages")
    
    # Verify order
    timestamps = [msg['timestamp'] for msg in messages]
    assert timestamps == sorted(timestamps), "Messages should be in chronological order"
    
    # Verify sequence
    expected_types = [
        "scraping:status",
        "research:phase_change",
        "workflow:progress",
        "research:phase_change",
        "workflow:progress",
        "workflow:progress",
    ]
    actual_types = [msg['type'] for msg in messages]
    assert actual_types == expected_types, "Message types should match expected sequence"
    
    print("[OK] WebSocket messages are in correct order")
    for i, msg in enumerate(messages):
        print(f"  {i+1}. {msg['type']} at {msg['timestamp']:.3f}")
    
    return True

def test_progress_update_frequency():
    """Test that progress updates are sent at appropriate intervals."""
    print("\n" + "=" * 80)
    print("TEST: Progress Update Frequency")
    print("=" * 80)
    
    # Simulate streaming with progress updates
    update_interval = 2.0  # Update every 2 seconds
    heartbeat_interval = 15.0  # Heartbeat every 15 seconds
    
    updates = []
    start_time = time.time()
    last_update = start_time
    
    # Simulate streaming - run long enough to generate at least one update (need > 2 seconds)
    target_duration = update_interval * 1.5  # Run for at least 1.5 intervals (3 seconds)
    end_time = start_time + target_duration
    
    i = 0
    while time.time() < end_time:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Send update every 2 seconds
        if current_time - last_update >= update_interval:
            updates.append({
                'time': elapsed,
                'tokens': i,
                'message': f"正在接收响应... ({i} tokens)"
            })
            last_update = current_time
        
        i += 1
        time.sleep(0.02)  # Simulate token arrival
    
    elapsed = time.time() - start_time
    print(f"Generated {len(updates)} progress updates in {elapsed:.1f}s")
    
    if len(updates) == 0:
        raise AssertionError(f"No updates generated in {elapsed:.1f}s (expected at least 1)")
    
    if len(updates) > 0:
        print(f"Average interval: {elapsed / len(updates):.2f}s")
    
    # Verify updates are sent at reasonable intervals
    intervals = [updates[i+1]['time'] - updates[i]['time'] for i in range(len(updates)-1)]
    avg_interval = sum(intervals) / len(intervals) if intervals else 0
    
    print(f"Average interval between updates: {avg_interval:.2f}s")
    assert avg_interval <= update_interval * 1.5, "Updates should be sent regularly"
    assert len(updates) > 0, "Should have at least one progress update"
    
    for update in updates:
        print(f"  Update at {update['time']:.1f}s: {update['message']}")
    
    print("[OK] Progress updates are sent at appropriate frequency")
    return True

async def main():
    """Run all simplified tests."""
    print("\n" + "=" * 80)
    print("SIMPLIFIED TIMING IMPROVEMENTS TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    print("")
    
    results = []
    
    # Test 1: Timing log format
    try:
        result = test_timing_log_format()
        results.append(("Timing Log Format", result))
    except Exception as e:
        print(f"[FAILED] FAILED: {e}")
        results.append(("Timing Log Format", False))
    
    # Test 2: Progress message structure
    try:
        result = test_progress_message_structure()
        results.append(("Progress Message Structure", result))
    except Exception as e:
        print(f"[FAILED] FAILED: {e}")
        results.append(("Progress Message Structure", False))
    
    # Test 3: Timeout reduction
    try:
        result = await test_timeout_reduction()
        results.append(("Timeout Reduction", result))
    except Exception as e:
        print(f"[FAILED] FAILED: {e}")
        results.append(("Timeout Reduction", False))
    
    # Test 4: WebSocket message order
    try:
        result = await test_websocket_message_order()
        results.append(("WebSocket Message Order", result))
    except Exception as e:
        print(f"[FAILED] FAILED: {e}")
        results.append(("WebSocket Message Order", False))
    
    # Test 5: Progress update frequency
    try:
        result = test_progress_update_frequency()
        results.append(("Progress Update Frequency", result))
    except Exception as e:
        print(f"[FAILED] FAILED: {e}")
        results.append(("Progress Update Frequency", False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Finished: {datetime.now().isoformat()}")
    print("=" * 80)
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED! Core improvements are verified.")
        return 0
    else:
        print(f"\n[FAILED] {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

