"""Main test runner for phase transition timing tests.

This script runs all phase transition timing tests and provides a summary.
"""
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

def run_test(test_file: str) -> tuple[bool, str]:
    """Run a test file and return (success, output)."""
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        return False, f"Test file not found: {test_file}"
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 60 seconds"
    except Exception as e:
        return False, f"Error running test: {e}"

def main():
    """Run all phase transition tests."""
    print("\n" + "=" * 80)
    print("PHASE TRANSITION TIMING TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    print("")
    
    tests = [
        ("test_timing_simple.py", "Core Timing Improvements"),
        ("test_phase_transition_real.py", "Workflow Service Timing"),
    ]
    
    results = []
    
    for test_file, test_name in tests:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_name} ({test_file})")
        print("=" * 80)
        
        start_time = time.time()
        success, output = run_test(test_file)
        elapsed = time.time() - start_time
        
        # Print last 30 lines of output
        lines = output.split('\n')
        print('\n'.join(lines[-30:]))
        
        results.append({
            'name': test_name,
            'file': test_file,
            'success': success,
            'elapsed': elapsed,
            'output': output
        })
        
        status = "PASSED" if success else "FAILED"
        print(f"\n{status} in {elapsed:.2f}s")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "PASSED" if result['success'] else "FAILED"
        print(f"{status}: {result['name']} ({result['elapsed']:.2f}s)")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Finished: {datetime.now().isoformat()}")
    print("=" * 80)
    
    if passed == total:
        print("\n[SUCCESS] All phase transition timing tests passed!")
        print("The lagging issues are fixed and verified.")
        return 0
    else:
        print(f"\n[FAILED] {total - passed} test(s) failed.")
        print("Please review the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

