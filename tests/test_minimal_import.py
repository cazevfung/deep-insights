"""Minimal test to check basic imports."""
import sys
from pathlib import Path
import time

print("Starting import test...")
start_time = time.time()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add backend directory to path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

print(f"Step 1: Testing Config import (at {time.time() - start_time:.2f}s)...")
try:
    from core.config import Config
    config = Config()
    print(f"  ✓ Config OK (at {time.time() - start_time:.2f}s)")
except Exception as e:
    print(f"  ✗ Config failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\nStep 2: Testing direct workflow service import (at {time.time() - start_time:.2f}s)...")
print("  (This might hang if there's an issue...)")

try:
    # Try importing directly
    import importlib
    module = importlib.import_module('app.services.news_summary_workflow_service')
    print(f"  ✓ Module imported (at {time.time() - start_time:.2f}s)")
    
    Service = getattr(module, 'NewsSummaryWorkflowService')
    print(f"  ✓ Service class found (at {time.time() - start_time:.2f}s)")
    
    # Try initializing
    print(f"  Initializing service (at {time.time() - start_time:.2f}s)...")
    service = Service(config)
    print(f"  ✓ Service initialized (at {time.time() - start_time:.2f}s)")
    
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n✓ All tests passed! (total time: {time.time() - start_time:.2f}s)")

