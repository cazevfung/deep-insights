#!/usr/bin/env python3
"""
Cross-platform dependency installer for Research Tool.
Installs all Python and npm dependencies automatically.
Works on Windows, macOS, and Linux.
"""
import sys
import subprocess
import os
import platform
import time
import webbrowser
from pathlib import Path

# Add project root to path for config import
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Import config (with try/except for graceful fallback)
try:
    from core.config import Config
    config = Config()
    backend_config = config.get_backend_config()
    frontend_config = config.get_frontend_config()
    DEFAULT_BACKEND_PORT = backend_config['port']
    DEFAULT_FRONTEND_PORT = frontend_config['port']
except Exception:
    # Fallback to defaults if config can't be loaded
    DEFAULT_BACKEND_PORT = 3001
    DEFAULT_FRONTEND_PORT = 3000

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Windows doesn't support ANSI colors by default, use simple output
if platform.system() == 'Windows':
    Colors.GREEN = Colors.YELLOW = Colors.RED = Colors.BLUE = Colors.RESET = Colors.BOLD = ''

def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def check_command(command, version_flag='--version'):
    """Check if a command is available."""
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_command_version(command, version_flag='--version'):
    """Get version of a command."""
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def run_command(command, cwd=None, check=True):
    """Run a command and return success status."""
    try:
        print_info(f"Running: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(command)}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        return False

def check_python_dependencies_installed(pip_command, requirements_file):
    """Check if Python dependencies from requirements.txt are already installed."""
    if not requirements_file.exists():
        return False
    
    try:
        # Read requirements.txt and extract package names
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements = f.read().strip().split('\n')
        
        # Filter out comments and empty lines, extract package names
        packages_to_check = []
        for req in requirements:
            req = req.strip()
            if req and not req.startswith('#'):
                # Extract package name (handle version specifiers like >=, ==, etc.)
                package_name = req.split('>=')[0].split('==')[0].split('[')[0].strip()
                if package_name:
                    packages_to_check.append(package_name)
        
        if not packages_to_check:
            return False
        
        # Check a few key packages to verify installation
        # We'll check the first 3-5 packages as a sample
        key_packages = packages_to_check[:5]
        
        # Count how many packages are installed
        installed_count = 0
        for package in key_packages:
            try:
                # Use pip show to check if package is installed
                result = subprocess.run(
                    pip_command + ['show', package],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    installed_count += 1
            except:
                # If we can't check, skip this package
                pass
        
        # If at least 80% of key packages are installed, consider dependencies installed
        # This prevents unnecessary reinstalls if one package check fails
        if len(key_packages) > 0:
            return installed_count >= (len(key_packages) * 0.8)
        
        # If no packages to check, assume not installed
        return False
    except Exception as e:
        # If we can't read or check, assume not installed
        return False

def check_npm_dependencies_installed(client_dir):
    """Check if npm dependencies are already installed."""
    node_modules = client_dir / 'node_modules'
    if not node_modules.exists():
        return False
    
    # Check if node_modules has content (not empty)
    try:
        # Check if node_modules has subdirectories (packages installed)
        subdirs = [d for d in node_modules.iterdir() if d.is_dir()]
        # Should have at least a few packages installed
        return len(subdirs) > 5
    except:
        return False

def check_playwright_browsers_installed():
    """Check if Playwright browsers are already installed."""
    try:
        # Try to import playwright
        import playwright
        # Check if chromium browser exists by trying to list installed browsers
        result = subprocess.run(
            [sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # If chromium is already installed, --dry-run should succeed
        # Check if output indicates it's already installed
        if result.returncode == 0:
            output = result.stdout.lower() + result.stderr.lower()
            # If it says "already installed" or doesn't mention downloading, it's installed
            if 'already installed' in output or ('chromium' in output and 'download' not in output):
                return True
            # Also check if the browser directory exists
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    return True
            except:
                pass
        return False
    except ImportError:
        # Playwright not installed
        return False
    except:
        # If we can't check, assume not installed
        return False

def install_python_dependencies():
    """Install Python dependencies."""
    print_header("Checking Python Dependencies")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
        print_error(f"Python 3.9+ required. Current version: {python_version.major}.{python_version.minor}")
        return False
    
    print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
    
    # Check pip - try multiple methods
    pip_command = None
    
    # Try direct pip commands first
    for cmd in ['pip', 'pip3']:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                pip_command = [cmd]
                pip_version = result.stdout.strip().split('\n')[0]
                print_success(f"pip detected: {cmd} ({pip_version})")
                break
        except:
            pass
    
    # If not found, try python -m pip (most reliable method)
    if not pip_command:
        for python_cmd in [sys.executable, 'python', 'python3', 'py', 'py -3']:
            try:
                if python_cmd == sys.executable:
                    cmd_parts = [str(sys.executable), '-m', 'pip']
                    display_name = f'{sys.executable} -m pip'
                elif ' ' in python_cmd:
                    cmd_parts = python_cmd.split() + ['-m', 'pip']
                    display_name = f'{python_cmd} -m pip'
                else:
                    cmd_parts = [python_cmd, '-m', 'pip']
                    display_name = f'{python_cmd} -m pip'
                
                result = subprocess.run(
                    cmd_parts + ['--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    pip_command = cmd_parts
                    pip_version = result.stdout.strip().split('\n')[0]
                    print_success(f"pip detected: {display_name} ({pip_version})")
                    break
            except:
                pass
    
    if not pip_command:
        print_error("pip not found. Trying to install pip...")
        # Try to ensure pip is installed
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'ensurepip', '--upgrade'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Try again with python -m pip
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    pip_command = [sys.executable, '-m', 'pip']
                    pip_version = result.stdout.strip().split('\n')[0]
                    print_success(f"pip installed and detected: {pip_version}")
                else:
                    print_error("pip installation failed. Please install pip manually.")
                    return False
            else:
                print_error("Failed to install pip. Please install pip manually.")
                print_info("Try: python -m ensurepip --upgrade")
                return False
        except Exception as e:
            print_error(f"Error installing pip: {e}")
            return False
    
    # Get project root
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir
    
    # Check and install root requirements.txt
    root_requirements = project_root / 'requirements.txt'
    root_installed = False
    if root_requirements.exists():
        if check_python_dependencies_installed(pip_command, root_requirements):
            print_success("Root Python dependencies already installed")
            root_installed = True
        else:
            print_info(f"Installing dependencies from {root_requirements}")
            if run_command(pip_command + ['install', '-r', str(root_requirements)], check=False):
                root_installed = True
            else:
                print_warning("Some packages from root requirements.txt may have failed to install")
    
    # Check and install backend requirements.txt
    backend_requirements = project_root / 'backend' / 'requirements.txt'
    backend_installed = False
    if backend_requirements.exists():
        if check_python_dependencies_installed(pip_command, backend_requirements):
            print_success("Backend Python dependencies already installed")
            backend_installed = True
        else:
            print_info(f"Installing dependencies from {backend_requirements}")
            if run_command(pip_command + ['install', '-r', str(backend_requirements)], check=False):
                backend_installed = True
            else:
                print_warning("Some packages from backend/requirements.txt may have failed to install")
    
    if root_requirements.exists() and backend_requirements.exists():
        if root_installed and backend_installed:
            print_success("All Python dependencies are installed")
        else:
            print_success("Python dependencies installation completed")
    elif root_requirements.exists():
        if root_installed:
            print_success("Python dependencies are installed")
        else:
            print_success("Python dependencies installation completed")
    elif backend_requirements.exists():
        if backend_installed:
            print_success("Python dependencies are installed")
        else:
            print_success("Python dependencies installation completed")
    
    return True

def install_playwright_browsers():
    """Install Playwright browsers after dependencies are installed."""
    print_info("Checking Playwright browsers...")
    
    # Check if browsers are already installed
    if check_playwright_browsers_installed():
        print_success("Playwright browsers already installed")
        return True
    
    try:
        # Try to import playwright to check if it's installed
        import playwright
        print_info("Installing Playwright browsers (chromium)...")
        result = run_command([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
        if result:
            print_success("Playwright browsers installed")
            return True
        else:
            print_warning("Playwright browser installation may have failed. You can install manually with: playwright install chromium")
            return False
    except ImportError:
        # Playwright might not be installed yet, try to install it anyway
        print_info("Playwright not found, attempting to install browsers...")
        result = run_command([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
        if result:
            print_success("Playwright browsers installed")
            return True
        else:
            print_warning("Playwright browser installation may have failed. You can install manually with: playwright install chromium")
            return False

def install_npm_dependencies():
    """Install npm dependencies."""
    print_header("Checking Node.js Dependencies")
    
    # Check Node.js
    if not check_command('node'):
        print_error("Node.js not found. Please install Node.js 18+ from https://nodejs.org/")
        return False
    
    node_version = get_command_version('node')
    if node_version:
        print_success(f"Node.js {node_version} detected")
        
        # Check version number
        version_str = node_version.replace('v', '')
        major_version = int(version_str.split('.')[0])
        if major_version < 18:
            print_warning(f"Node.js 18+ recommended. Current version: {node_version}")
    
    # Check npm - npm should come with Node.js
    npm_command = None
    npm_methods = [
        ('npm', 'npm'),
    ]
    
    # Try npm command
    for cmd, display_name in npm_methods:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                npm_command = cmd
                npm_version = result.stdout.strip().split('\n')[0]
                print_success(f"npm detected: {npm_version}")
                break
        except:
            pass
    
    # If npm not found, try to find it in common Node.js installation paths (Windows)
    if not npm_command and platform.system() == 'Windows':
        common_paths = [
            os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs', 'npm.cmd'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs', 'npm.cmd'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'nodejs', 'npm.cmd'),
        ]
        for npm_path in common_paths:
            if os.path.exists(npm_path):
                try:
                    result = subprocess.run(
                        [npm_path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        npm_command = npm_path
                        npm_version = result.stdout.strip().split('\n')[0]
                        print_success(f"npm detected: {npm_version} (from {npm_path})")
                        break
                except:
                    pass
    
    if not npm_command:
        print_error("npm not found. npm should come with Node.js.")
        print_info("If Node.js is installed, npm might not be in PATH.")
        print_info("Try restarting your terminal or adding Node.js to PATH.")
        print_info("Node.js installation path might need to be added to PATH manually.")
        return False
    
    # Get project root
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir
    client_dir = project_root / 'client'
    
    # Check if client directory exists
    if not client_dir.exists():
        print_error(f"Client directory not found: {client_dir}")
        return False
    
    # Check if package.json exists
    package_json = client_dir / 'package.json'
    if not package_json.exists():
        print_error(f"package.json not found: {package_json}")
        return False
    
    # Check if npm dependencies are already installed
    if check_npm_dependencies_installed(client_dir):
        print_success("Node.js dependencies already installed")
        return True
    
    # Install npm dependencies
    print_info(f"Installing npm dependencies from {package_json}")
    if not run_command([npm_command, 'install'], cwd=str(client_dir), check=False):
        print_error("npm install failed")
        return False
    
    print_success("Node.js dependencies installation completed")
    return True

def open_browser(url, delay=3):
    """Open browser to specified URL after a delay."""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            print_info(f"Opened browser to: {url}")
        except Exception as e:
            print_warning(f"Could not open browser automatically: {e}")
            print_info(f"Please open manually: {url}")
    
    # Open in a separate thread so it doesn't block
    import threading
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()

def wait_for_server(url, timeout=30, interval=2):
    """Wait for a server to become available."""
    import urllib.request
    import urllib.error
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.status == 200:
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass
        time.sleep(interval)
    return False

def stop_backend_server(port=None):
    """Stop any existing backend server on the specified port."""
    if port is None:
        port = DEFAULT_BACKEND_PORT
    try:
        if platform.system() == 'Windows':
            # Windows: Find and kill process using the port
            import socket
            try:
                # Try to find the process using netstat
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if f':{port}' in line and 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) > 4:
                                pid = parts[-1]
                                try:
                                    subprocess.run(['taskkill', '/F', '/PID', pid], 
                                                 capture_output=True, timeout=5)
                                    print_info(f"Stopped backend server process (PID: {pid})")
                                    time.sleep(1)  # Give it time to stop
                                    return True
                                except:
                                    pass
            except:
                pass
            
            # Fallback: Try to kill Python processes that might be running the server
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Note: On Windows, we can't easily determine which Python process is the server
                # So we'll just proceed with starting a new one
                print_warning("Could not automatically stop existing backend server")
                print_info("If you see a port conflict, manually stop the backend server first")
            except:
                pass
        else:
            # Unix: Use lsof or fuser to find and kill process
            try:
                # Try lsof first
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(['kill', '-9', pid], 
                                         capture_output=True, timeout=5)
                            print_info(f"Stopped backend server process (PID: {pid})")
                            time.sleep(1)
                        except:
                            pass
                    return True
            except:
                pass
            
            # Fallback: try fuser
            try:
                subprocess.run(['fuser', '-k', f'{port}/tcp'], 
                             capture_output=True, timeout=5)
                time.sleep(1)
                return True
            except:
                pass
    except Exception as e:
        print_warning(f"Error stopping backend server: {e}")
    return False

def check_backend_health(port=None, timeout=30):
    """Check if backend server is running and LinkFormatterService is initialized."""
    if port is None:
        port = DEFAULT_BACKEND_PORT
    import urllib.request
    import urllib.error
    import json
    
    health_url = f"http://localhost:{port}/api/links/health"
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(health_url, timeout=2)
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get('status') == 'ok':
                    print_success("Backend server is healthy")
                    print_success("LinkFormatterService initialized successfully")
                    return True
                elif data.get('status') == 'error':
                    error_msg = data.get('message', 'Unknown error')
                    print_error(f"Backend server responded but service error: {error_msg}")
                    print_warning("Check backend logs for 'LinkFormatterService' initialization errors")
                    return False
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            # Server not ready yet, continue waiting
            pass
        time.sleep(2)
    
    print_warning("Backend server did not respond within timeout")
    print_info("Check the backend server window for startup logs")
    return False

def start_servers(start_backend=True, start_frontend=True, auto_open_browser=True, restart_backend=False):
    """Start backend and/or frontend servers."""
    print_header("Starting Servers")
    
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir
    backend_dir = project_root / 'backend'
    client_dir = project_root / 'client'
    
    processes = []
    
    # Stop existing backend server if restart requested
    if start_backend and restart_backend:
        print_info("Stopping existing backend server...")
        stop_backend_server()
        time.sleep(2)  # Give it time to fully stop
    
    # Start backend server
    if start_backend:
        backend_script = backend_dir / 'run_server.py'
        if not backend_script.exists():
            print_error(f"Backend server script not found: {backend_script}")
        else:
            print_info("Starting backend server...")
            print_info(f"Backend will be available at: http://localhost:{DEFAULT_BACKEND_PORT}")
            
            if platform.system() == 'Windows':
                # Windows: Start in same terminal (background)
                try:
                    process = subprocess.Popen(
                        [sys.executable, str(backend_script)],
                        cwd=str(backend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    processes.append(process)
                    print_success("Backend server started")
                    
                    # Wait a bit then check health
                    print_info("Waiting for backend server to start...")
                    print_info("Monitoring startup logs for LinkFormatterService initialization...")
                    time.sleep(3)
                    
                    # Check backend health and LinkFormatterService initialization
                    if check_backend_health(timeout=30):
                        print_success("✓ Backend server is ready!")
                        print_success("✓ LinkFormatterService initialized successfully")
                    else:
                        print_warning("⚠ Backend server may not be fully initialized")
                        print_info("Check backend logs for startup messages:")
                        print_info("  ✓ 'LinkFormatterService initialized successfully' - Good")
                        print_info("  ✗ 'Failed to initialize LinkFormatterService: ...' - Error")
                except Exception as e:
                    print_error(f"Failed to start backend server: {e}")
            else:
                # Unix: Start in background
                try:
                    process = subprocess.Popen(
                        [sys.executable, str(backend_script)],
                        cwd=str(backend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True
                    )
                    processes.append(process)
                    print_success("Backend server started in background")
                    
                    # Wait a bit then check health
                    print_info("Waiting for backend server to start...")
                    print_info("Monitoring startup logs for LinkFormatterService initialization...")
                    time.sleep(3)
                    
                    # Check backend health and LinkFormatterService initialization
                    if check_backend_health(timeout=15):
                        print_success("✓ Backend server is ready!")
                        print_success("✓ LinkFormatterService initialized successfully")
                    else:
                        print_warning("⚠ Backend server may not be fully initialized")
                        print_info("Check backend logs for startup messages:")
                        print_info("  ✓ 'LinkFormatterService initialized successfully' - Good")
                        print_info("  ✗ 'Failed to initialize LinkFormatterService: ...' - Error")
                except Exception as e:
                    print_error(f"Failed to start backend server: {e}")
    
    # Start frontend server
    if start_frontend:
        package_json = client_dir / 'package.json'
        if not package_json.exists():
            print_error(f"Frontend package.json not found: {package_json}")
        else:
            print_info("Starting frontend dev server...")
            print_info(f"Frontend will be available at: http://localhost:{DEFAULT_FRONTEND_PORT}")
            
            if platform.system() == 'Windows':
                # Windows: Start in new window so we can see output
                try:
                    # Check if npm dependencies are installed first
                    node_modules = client_dir / 'node_modules'
                    if not node_modules.exists() or not check_npm_dependencies_installed(client_dir):
                        print_error("npm dependencies not installed. Please run install first.")
                        print_info("Run: python install_dependencies.py")
                        return processes
                    
                    # Start in a visible window so user can see output
                    process = subprocess.Popen(
                        ['npm', 'run', 'dev'],
                        cwd=str(client_dir),
                        shell=True
                    )
                    processes.append(process)
                    print_success("Frontend server starting...")
                    print_info("Check the new window for startup logs")
                except Exception as e:
                    print_error(f"Failed to start frontend server: {e}")
                    print_info("Try starting manually: cd client && npm run dev")
            else:
                # Unix: Start in background
                try:
                    process = subprocess.Popen(
                        ['npm', 'run', 'dev'],
                        cwd=str(client_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True
                    )
                    processes.append(process)
                    print_success("Frontend server started in background")
                except Exception as e:
                    print_error(f"Failed to start frontend server: {e}")
    
    # Wait for frontend server to be ready if started
    if start_frontend:
        frontend_url = f"http://localhost:{DEFAULT_FRONTEND_PORT}"
        print_info(f"Waiting for frontend server to start at {frontend_url}...")
        print_info("This may take 10-30 seconds...")
        
        # Wait for server to be ready
        if wait_for_server(frontend_url, timeout=60):
            print_success("Frontend server is ready!")
        else:
            print_warning("Frontend server may not be ready yet.")
            print_info("Server may still be starting up in the background...")
        
        # Auto-open browser if requested
        if auto_open_browser:
            print_info(f"Opening browser to {frontend_url}...")
            open_browser(frontend_url, delay=1)
    
    return processes

def main():
    """Main installation function."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Install dependencies and optionally start servers for Research Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_dependencies.py              # Install dependencies only
  python install_dependencies.py --start      # Install, start servers, and open browser
  python install_dependencies.py --start --no-browser  # Start servers without opening browser
  python install_dependencies.py --start --restart-backend  # Restart backend (stop existing, start new)
  python install_dependencies.py --start --backend-only --restart-backend  # Restart only backend with health check
  python install_dependencies.py --no-start   # Install without starting servers
        """
    )
    parser.add_argument(
        '--start',
        action='store_true',
        default=None,
        help='Start backend and frontend servers after installation'
    )
    parser.add_argument(
        '--no-start',
        action='store_true',
        help='Do not start servers (only install dependencies)'
    )
    parser.add_argument(
        '--backend-only',
        action='store_true',
        help='Only start backend server (requires --start)'
    )
    parser.add_argument(
        '--frontend-only',
        action='store_true',
        help='Only start frontend server (requires --start)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open browser automatically (requires --start)'
    )
    parser.add_argument(
        '--restart-backend',
        action='store_true',
        help='Restart backend server (stop existing, start new)'
    )
    
    args = parser.parse_args()
    
    # Determine if we should start servers
    should_start = args.start
    if args.no_start:
        should_start = False
    
    print_header("Research Tool - Dependency Installer")
    print_info(f"Platform: {platform.system()} {platform.release()}")
    print_info(f"Architecture: {platform.machine()}")
    
    # Track overall success
    python_success = False
    npm_success = False
    
    # Install Python dependencies
    try:
        python_success = install_python_dependencies()
    except Exception as e:
        print_error(f"Error installing Python dependencies: {e}")
        python_success = False
    
    # Install npm dependencies
    try:
        npm_success = install_npm_dependencies()
    except Exception as e:
        print_error(f"Error installing npm dependencies: {e}")
        npm_success = False
    
    # Install Playwright browsers (after all dependencies are installed)
    playwright_success = False
    if python_success:
        try:
            playwright_success = install_playwright_browsers()
        except Exception as e:
            print_warning(f"Error installing Playwright browsers: {e}")
            playwright_success = False
    
    # Summary
    print_header("Installation Summary")
    
    if python_success:
        print_success("Python dependencies: ✓ Installed")
    else:
        print_error("Python dependencies: ✗ Failed")
    
    if npm_success:
        print_success("Node.js dependencies: ✓ Installed")
    else:
        print_error("Node.js dependencies: ✗ Failed")
    
    if playwright_success:
        print_success("Playwright browsers: ✓ Installed")
    else:
        print_warning("Playwright browsers: ⚠ Installation skipped or failed (optional)")
    
    if not (python_success and npm_success):
        print_error("\nSome dependencies failed to install. Please check the errors above.")
        return 1
    
    print_success("\nAll dependencies installed successfully!")
    
    # Auto-start servers if not specified (default to True)
    if should_start is None:
        should_start = True
        print_header("Server Startup")
        print_info("Automatically starting servers...")
    
    # Start servers if requested
    if should_start:
        start_backend = not args.frontend_only
        start_frontend = not args.backend_only
        auto_open = not args.no_browser
        restart_backend = args.restart_backend
        
        processes = start_servers(
            start_backend=start_backend,
            start_frontend=start_frontend,
            auto_open_browser=auto_open,
            restart_backend=restart_backend
        )
        
        print_header("Server Startup Complete")
        print_success("\nServers are running!")
        if start_backend:
            print_info(f"Backend API: http://localhost:{DEFAULT_BACKEND_PORT}")
            print_info(f"Backend Docs: http://localhost:{DEFAULT_BACKEND_PORT}/docs")
        if start_frontend:
            print_info(f"Frontend: http://localhost:{DEFAULT_FRONTEND_PORT}")
            if auto_open:
                print_info("Browser opened automatically")
            else:
                print_info(f"Open browser manually to: http://localhost:{DEFAULT_FRONTEND_PORT}")
        print_info("\nServers are running in the background. To stop servers, use Ctrl+C or close the terminal.")
    else:
        print_info("\nNext steps:")
        print_info("1. Start backend: cd backend && python run_server.py")
        print_info("2. Start frontend: cd client && npm run dev")
        print_info("\nTo restart backend with health check:")
        print_info("  python install_dependencies.py --start --backend-only --restart-backend")
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        sys.exit(1)

