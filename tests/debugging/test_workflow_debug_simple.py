"""
Simple test script to find bugs in workflow debugging features.

This test can run without a full workflow execution.
"""
import os
import sys
from pathlib import Path

# Enable debug mode
os.environ['WORKFLOW_DEBUG'] = 'true'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# Add backend to path for app imports
sys.path.insert(0, str(project_root / "backend"))

def test_message_validation():
    """Test message validation logic."""
    print("=" * 80)
    print("Testing Message Validation")
    print("=" * 80)
    
    # Import validation function
    sys.path.insert(0, str(project_root / "backend" / "lib"))
    from workflow_direct import _validate_message, REQUIRED_FIELDS_BY_TYPE
    
    print(f"\nRequired fields schemas: {len(REQUIRED_FIELDS_BY_TYPE)} message types")
    for msg_type, fields in REQUIRED_FIELDS_BY_TYPE.items():
        print(f"  {msg_type}: {fields}")
    
    test_cases = [
        # Valid messages
        ({
            'type': 'scraping:start',
            'message': 'Test'
        }, True, 'Valid scraping:start'),
        
        ({
            'type': 'scraping:complete_link',
            'scraper': 'youtube',
            'url': 'https://test.com',
            'link_id': 'test_1',
            'status': 'success'
        }, True, 'Valid scraping:complete_link'),
        
        # Invalid messages
        ({
            'type': 'scraping:start'
            # Missing 'message'
        }, False, 'Missing required field'),
        
        ({
            'type': 'scraping:complete_link',
            'scraper': 'youtube',
            'url': 'https://test.com',
            'link_id': 'test_1',
            'status': 'invalid_status'  # Invalid status
        }, False, 'Invalid status value'),
    ]
    
    issues = []
    passed = 0
    failed = 0
    
    for message, expected_valid, description in test_cases:
        is_valid, error_msg = _validate_message(message, message.get('type', ''))
        if is_valid != expected_valid:
            issues.append(f"{description}: expected_valid={expected_valid}, got={is_valid}")
            print(f"[FAIL] {description}")
            print(f"   Expected: {expected_valid}, Got: {is_valid}")
            if error_msg:
                print(f"   Error: {error_msg}")
            failed += 1
        else:
            print(f"[PASS] {description}")
            passed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if issues:
        print(f"\nFound {len(issues)} validation issues:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("\n[PASS] All validation tests passed!")
        return True


def test_debug_mode():
    """Test that debug mode is properly configured."""
    print("\n" + "=" * 80)
    print("Testing Debug Mode Configuration")
    print("=" * 80)
    
    from backend.lib.workflow_direct import DEBUG_MODE
    from backend.app.services.workflow_service import DEBUG_MODE as WS_DEBUG_MODE
    
    print(f"\nworkflow_direct.py DEBUG_MODE: {DEBUG_MODE}")
    print(f"workflow_service.py DEBUG_MODE: {WS_DEBUG_MODE}")
    print(f"Environment WORKFLOW_DEBUG: {os.environ.get('WORKFLOW_DEBUG', 'not set')}")
    
    if DEBUG_MODE and WS_DEBUG_MODE:
        print("[PASS] Debug mode is enabled in both modules")
        return True
    else:
        print("[FAIL] Debug mode mismatch!")
        return False


def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "=" * 80)
    print("Testing Imports")
    print("=" * 80)
    
    issues = []
    
    try:
        from backend.lib.workflow_direct import (
            _validate_message,
            _safe_callback_invoke,
            run_all_scrapers_direct
        )
        print("[PASS] workflow_direct imports successful")
    except Exception as e:
        issues.append(f"workflow_direct import failed: {e}")
        print(f"[FAIL] workflow_direct import failed: {e}")
    
    try:
        # Try backend.app first
        try:
            from backend.app.services.workflow_service import WorkflowService
            print("[PASS] workflow_service imports successful (backend.app)")
        except ImportError:
            # Try app directly (if backend is in path)
            from app.services.workflow_service import WorkflowService
            print("[PASS] workflow_service imports successful (app)")
    except Exception as e:
        issues.append(f"workflow_service import failed: {e}")
        print(f"[FAIL] workflow_service import failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        from tests.test_links_loader import TestLinksLoader
        print("[PASS] TestLinksLoader import successful")
    except Exception as e:
        issues.append(f"TestLinksLoader import failed: {e}")
        print(f"[FAIL] TestLinksLoader import failed: {e}")
    
    if issues:
        print(f"\nFound {len(issues)} import issues:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("\n[PASS] All imports successful!")
        return True


def test_callback_tracking():
    """Test callback tracking structure."""
    print("\n" + "=" * 80)
    print("Testing Callback Tracking Structure")
    print("=" * 80)
    
    from backend.lib.workflow_direct import _callback_tracking, _tracking_lock
    
    print(f"\nCallback tracking structure exists: {_callback_tracking is not None}")
    print(f"Tracking lock exists: {_tracking_lock is not None}")
    
    # Test that we can add to tracking (in debug mode)
    if os.environ.get('WORKFLOW_DEBUG', 'false').lower() == 'true':
        print("[PASS] Debug mode enabled - tracking will be active")
        return True
    else:
        print("[INFO] Debug mode not enabled - tracking will be inactive")
        return True  # Not an error, just informational


def main():
    """Run all tests."""
    print("=" * 80)
    print("WORKFLOW DEBUG TEST - Simple Version")
    print("=" * 80)
    print(f"Python version: {sys.version}")
    print(f"Project root: {project_root}")
    print(f"Debug mode: {os.environ.get('WORKFLOW_DEBUG', 'not set')}")
    
    results = []
    
    # Test imports first
    import_ok = test_imports()
    results.append(("Imports", import_ok))
    
    if not import_ok:
        print("\n[FAIL] Import tests failed - cannot continue")
        return 1
    
    # Test debug mode
    debug_ok = test_debug_mode()
    results.append(("Debug Mode", debug_ok))
    
    # Test callback tracking
    tracking_ok = test_callback_tracking()
    results.append(("Callback Tracking", tracking_ok))
    
    # Test message validation
    validation_ok = test_message_validation()
    results.append(("Message Validation", validation_ok))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[PASS] All tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

