#!/usr/bin/env python
"""
Test script to diagnose LinkFormatterService initialization issues.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing LinkFormatterService initialization...")
print(f"Project root: {project_root}")
print()

try:
    print("Step 1: Testing utils.link_formatter import...")
    from utils.link_formatter import build_items, current_batch_id
    print("✓ utils.link_formatter import successful")
    print()
except Exception as e:
    print(f"✗ Failed to import utils.link_formatter: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("Step 2: Testing backend.app.services.link_formatter_service import...")
    from backend.app.services.link_formatter_service import LinkFormatterService
    print("✓ LinkFormatterService import successful")
    print()
except Exception as e:
    print(f"✗ Failed to import LinkFormatterService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("Step 3: Testing LinkFormatterService instantiation...")
    service = LinkFormatterService()
    print("✓ LinkFormatterService instantiated successfully")
    print()
except Exception as e:
    print(f"✗ Failed to instantiate LinkFormatterService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("Step 4: Testing format_links with sample URLs...")
    test_urls = ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    result = service.format_links(test_urls)
    print(f"✓ format_links executed successfully")
    print(f"  Batch ID: {result['batch_id']}")
    print(f"  Total items: {result['total']}")
    print()
except Exception as e:
    print(f"✗ Failed to format links: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All tests passed! ✓")

