"""Quick test: WebSocket connection with batchId validation."""
import asyncio
import websockets
import json
import sys
from pathlib import Path

async def test_websocket_connection():
    """Test WebSocket connection handling."""
    
    print("Testing WebSocket connection...")
    print()
    
    # Test 1: Valid batchId
    batch_id = "test_ws_123"
    ws_url = f"ws://localhost:8000/ws/{batch_id}"
    
    print(f"Test 1: Connecting with valid batchId: {batch_id}")
    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ Connected successfully")
            
            # Wait for initial message (if any)
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(message)
                print(f"✅ Received message: {data.get('type')}")
            except asyncio.TimeoutError:
                print("✅ No initial message (OK)")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure backend server is running on localhost:8000")
        return False
    
    # Test 2: Empty batchId (should be rejected by frontend, but we can test backend)
    print()
    print(f"Test 2: Testing empty batchId (backend may reject)")
    try:
        async with websockets.connect("ws://localhost:8000/ws/") as ws:
            print("⚠️  Connected with empty batchId (unexpected)")
    except Exception as e:
        print(f"✅ Correctly rejected empty batchId: {type(e).__name__}")
    
    # Test 3: Short batchId (should be rejected by frontend validation)
    print()
    print(f"Test 3: Short batchId 'ab' (frontend validation)")
    print("   This should be rejected by frontend batchId validation")
    print("   Frontend should show: '批次ID格式无效，无法连接'")
    
    print("\n" + "="*60)
    print("✅ WebSocket connection test completed!")
    print("="*60)
    print("\nNote: Frontend validation is tested in the browser.")
    print("      Navigate to ScrapingProgressPage with invalid batchId to test.")
    
    return True

if __name__ == '__main__':
    try:
        asyncio.run(test_websocket_connection())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")




