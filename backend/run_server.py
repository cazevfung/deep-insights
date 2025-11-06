#!/usr/bin/env python
"""
Run the FastAPI server with startup validation.
"""
import uvicorn
import socket
import sys
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config


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


def validate_startup():
    """Validate that required services can be initialized."""
    try:
        logger.info("Validating backend startup...")
        
        # Test config loading
        config = Config()
        logger.info("✓ Config loaded successfully")
        
        # Test backend config
        backend_config = config.get_backend_config()
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


if __name__ == "__main__":
    # Configure logging
    logger.remove()  # Remove default handler
    
    # Log to stderr (console) - this will show in the terminal window
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Also log to a file for debugging
    log_file = Path(__file__).parent.parent / "logs" / "backend.log"
    log_file.parent.mkdir(exist_ok=True, parents=True)
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # More verbose in file
        rotation="10 MB",
        retention="7 days"
    )
    
    logger.info("=" * 60)
    logger.info("Starting Research Tool Backend Server")
    logger.info("=" * 60)
    
    # Validate startup before running
    if not validate_startup():
        logger.error("Startup validation failed. Exiting.")
        sys.exit(1)
    
    try:
        config = Config()
        backend_config = config.get_backend_config()
        
        logger.info(f"Starting server on {backend_config['host']}:{backend_config['port']}")
        logger.info(f"Reload mode: {backend_config['reload']}")
        
        uvicorn.run(
            "app.main:app",
            host=backend_config['host'],
            port=backend_config['port'],
            reload=backend_config['reload'],
            reload_dirs=backend_config['reload_dirs'],
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)


