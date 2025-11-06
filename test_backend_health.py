#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to diagnose backend health endpoint issues.
"""
import sys
import io
from pathlib import Path
import urllib.request
import urllib.error
import json
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_health_endpoint():
    """Test the health endpoint directly."""
    print("=" * 60)
    print("Backend Health Endpoint Test")
    print("=" * 60)
    print()
    
    # Test 1: Root health endpoint
    print("Test 1: Testing root health endpoint...")
    try:
        response = urllib.request.urlopen("http://localhost:3001/health", timeout=5)
        content = response.read().decode('utf-8')
        print(f"Response status: {response.status}")
        print(f"Response content: {content[:200]}...")
        try:
            data = json.loads(content)
            print(f"[OK] Root health endpoint works: {data}")
        except json.JSONDecodeError:
            print(f"[ERROR] Root health endpoint returned non-JSON: {content[:200]}")
    except Exception as e:
        print(f"[FAILED] Root health endpoint failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 2: Links health endpoint
    print("Test 2: Testing /api/links/health endpoint...")
    try:
        response = urllib.request.urlopen("http://localhost:3001/api/links/health", timeout=5)
        data = json.loads(response.read().decode('utf-8'))
        print(f"[OK] Links health endpoint works: {data}")
        if data.get('status') == 'ok':
            print("[OK] LinkFormatterService is initialized correctly")
        else:
            print(f"[ERROR] LinkFormatterService error: {data.get('message')}")
    except urllib.error.HTTPError as e:
        print(f"[FAILED] HTTP Error {e.code}: {e.reason}")
        try:
            error_content = e.read().decode('utf-8')
            print(f"  Error response: {error_content[:500]}")
            try:
                error_data = json.loads(error_content)
                print(f"  Error details: {error_data}")
            except:
                pass
        except:
            pass
    except urllib.error.URLError as e:
        print(f"[FAILED] Connection error: {e}")
        print("  This usually means the server is not responding or not running")
    except Exception as e:
        print(f"[FAILED] Links health endpoint failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 3: Direct import test
    print("Test 3: Testing direct import of LinkFormatterService...")
    try:
        from backend.app.services.link_formatter_service import LinkFormatterService
        service = LinkFormatterService()
        print("[OK] LinkFormatterService can be imported and instantiated")
    except Exception as e:
        print(f"[FAILED] LinkFormatterService import failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 4: Check if routes are registered
    print("Test 4: Testing route registration...")
    try:
        from backend.app.main import app
        routes = [route.path for route in app.routes]
        print(f"[OK] App loaded. Found {len(routes)} routes")
        health_routes = [r for r in routes if 'health' in r]
        if health_routes:
            print(f"  Health routes: {health_routes}")
        else:
            print("  [WARNING] No health routes found!")
        links_routes = [r for r in routes if 'links' in r]
        if links_routes:
            print(f"  Links routes: {links_routes}")
        else:
            print("  [WARNING] No links routes found!")
    except Exception as e:
        print(f"[FAILED] Failed to load app: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_health_endpoint()
