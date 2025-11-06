#!/usr/bin/env python
"""
Kill hung backend processes on port 3001.
"""
import sys
import subprocess
import socket
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config

def kill_backend():
    """Kill processes using port 3001."""
    try:
        config = Config()
        backend_config = config.get_backend_config()
        port = backend_config['port']
        
        print(f"Finding processes using port {port}...")
        
        # Use netstat to find processes using the port (Windows)
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Find lines with the port
            lines = result.stdout.split('\n')
            pids = []
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) > 0:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.append(pid)
            
            if not pids:
                print(f"   No processes found using port {port}")
                print("   Backend may not be running")
                return False
            
            print(f"   Found {len(pids)} process(es) using port {port}: {', '.join(pids)}")
            
            # Kill each process
            for pid in pids:
                print(f"   Killing process {pid}...")
                try:
                    subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                    print(f"   ✓ Killed process {pid}")
                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Failed to kill process {pid}: {e}")
                    return False
            
            print(f"   ✓ All processes killed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error running netstat: {e}")
            return False
        except FileNotFoundError:
            print("   ❌ netstat not found (this script requires Windows)")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Killing Backend Processes")
    print("=" * 60)
    success = kill_backend()
    if success:
        print("\n✓ Backend processes killed. You can now restart the backend:")
        print("  python backend/run_server.py")
    else:
        print("\n❌ Failed to kill backend processes")
        print("You may need to manually kill the process or restart your computer")
    sys.exit(0 if success else 1)

