#!/usr/bin/env python
"""
Run the FastAPI server with startup validation.
"""
import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from lib.logging_setup import setup_logging


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host if host != '0.0.0.0' else '127.0.0.1', port))
            return result != 0  # Port is available if connection fails
    except Exception as e:
        logger.warning(f"Could not check port availability: {e}")
        return True  # Assume available if we can't check


def validate_startup(override_host: Optional[str] = None, override_port: Optional[int] = None):
    """Validate that required services can be initialized."""
    try:
        logger.info("Validating backend startup...")
        
        # Test config loading
        config = Config()
        logger.info("✓ Config loaded successfully")
        
        # Test backend config
        backend_config = config.get_backend_config()
        if override_host is not None:
            backend_config['host'] = override_host
        if override_port is not None:
            backend_config['port'] = override_port
        logger.info(f"✓ Backend config loaded: host={backend_config['host']}, port={backend_config['port']}")
        
        # Test importing main app (this will initialize services)
        logger.info("Testing app initialization...")
        from app.main import app
        logger.info("✓ App module imported successfully")
        
        # Check port availability
        port = backend_config['port']
        host = backend_config['host']
        if not check_port_available(host, port):
            logger.warning(f"⚠ Port {port} appears to be in use. Server may fail to start.")
            logger.warning(f"   Try stopping any existing server on port {port}")
        else:
            logger.info(f"✓ Port {port} is available")
        
        logger.info("✓ Startup validation complete")
        return True
        
    except Exception as e:
        logger.error(f"✗ Startup validation failed: {e}", exc_info=True)
        logger.error("Please check the error above and fix any configuration issues")
        return False


def ensure_console_window(args: argparse.Namespace) -> None:
    """On Windows, relaunch the script in a dedicated console unless disabled."""
    if os.name != "nt":
        return

    if args.reuse_window:
        return

    if os.environ.get("BACKEND_SERVER_CHILD") == "1":
        return

    child_env = os.environ.copy()
    child_env["BACKEND_SERVER_CHILD"] = "1"

    command = [sys.executable, str(Path(__file__).resolve())]
    if args.host:
        command += ["--host", args.host]
    if args.port is not None:
        command += ["--port", str(args.port)]

    try:
        creation_flags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
    except AttributeError:
        creation_flags = 0

    subprocess.Popen(
        command,
        cwd=str(project_root),
        env=child_env,
        creationflags=creation_flags,
    )
    print("Launching backend server in a new console window...")
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Research Tool backend server")
    parser.add_argument("--host", type=str, help="Override host to bind")
    parser.add_argument("--port", type=int, help="Override port to bind")
    parser.add_argument(
        "--reuse-window",
        action="store_true",
        help="Run the server in the current console window (skip auto-spawn on Windows)",
    )
    args = parser.parse_args()

    ensure_console_window(args)

    env_host = os.environ.get("BACKEND_HOST_OVERRIDE")
    env_port = os.environ.get("BACKEND_PORT_OVERRIDE")
    env_port_int = None
    if env_port:
        try:
            env_port_int = int(env_port)
        except ValueError:
            env_port_int = None

    override_host = args.host or env_host
    override_port = args.port if args.port is not None else env_port_int

    # Configure logging (console + file + stdlib interception)
    setup_logging(enable_console=True, console_colorize=True)
    
    logger.info("=" * 60)
    logger.info("Starting Research Tool Backend Server")
    logger.info("=" * 60)
    
    # Validate startup before running
    if not validate_startup(override_host=override_host, override_port=override_port):
        logger.error("Startup validation failed. Exiting.")
        sys.exit(1)
    
    try:
        config = Config()
        backend_config = config.get_backend_config()
        if override_host is not None:
            backend_config['host'] = override_host
        if override_port is not None:
            backend_config['port'] = override_port
        if override_port is not None:
            logger.info(f"Using overridden backend port: {backend_config['port']}")
        if override_host is not None:
            logger.info(f"Using overridden backend host: {backend_config['host']}")
        
        logger.info(f"Starting server on {backend_config['host']}:{backend_config['port']}")
        logger.info(f"Reload mode: {backend_config['reload']}")
        
        uvicorn.run(
            "app.main:app",
            host=backend_config['host'],
            port=backend_config['port'],
            reload=backend_config['reload'],
            reload_dirs=backend_config['reload_dirs'],
            log_level="info",
            log_config=None,  # Use our Loguru-based config
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)


