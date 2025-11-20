"""
FastAPI application entry point.
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.logging_setup import setup_logging

# Ensure logging configuration is consistent when the app is imported directly
setup_logging(enable_console=True)

# Initialize logger early
logger.info("Initializing FastAPI application...")

try:
    from core.config import Config
    from app.routes import ingestion, links, workflow, research, session, reports, history, exports
    from app.websocket.manager import WebSocketManager
    logger.info("✓ All modules imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import modules: {e}", exc_info=True)
    raise

app = FastAPI(
    title="Research Tool API",
    description="API for Research Tool service",
    version="0.1.0",
)

# Initialize configuration with error handling
try:
    config = Config()
    logger.info("✓ Config loaded successfully")
except Exception as e:
    logger.error(f"✗ Failed to load config: {e}", exc_info=True)
    raise

# CORS middleware - read from config
try:
    cors_config = config.get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config['allowed_origins'],
        allow_credentials=cors_config['allow_credentials'],
        allow_methods=cors_config['allow_methods'],
        allow_headers=cors_config['allow_headers'],
    )
    logger.info("✓ CORS middleware configured")
except Exception as e:
    logger.error(f"✗ Failed to configure CORS: {e}", exc_info=True)
    raise

# Initialize WebSocket manager (single shared instance)
try:
    websocket_manager = WebSocketManager()
    logger.info("✓ WebSocket manager initialized")
except Exception as e:
    logger.error(f"✗ Failed to initialize WebSocket manager: {e}", exc_info=True)
    raise

# Set shared WebSocket manager in routers
try:
    workflow.set_websocket_manager(websocket_manager)
    logger.info("✓ Workflow router configured")
except Exception as e:
    logger.error(f"✗ Failed to configure workflow router: {e}", exc_info=True)
    raise

# Include routers with error handling
try:
    app.include_router(links.router, prefix="/api/links", tags=["links"])
    app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
    app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
    app.include_router(research.router, prefix="/api/research", tags=["research"])
    app.include_router(session.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(history.router, prefix="/api/history", tags=["history"])
    app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
    logger.info("✓ All routers included successfully")
except Exception as e:
    logger.error(f"✗ Failed to include routers: {e}", exc_info=True)
    raise

# Register health endpoints BEFORE routers to ensure they're always available
@app.get("/")
async def root():
    return {"message": "Research Tool API", "version": "0.1.0"}

@app.get("/health")
async def health():
    """Health check endpoint - should respond quickly without any dependencies."""
    # This endpoint should NEVER hang - it's the simplest possible check
    return {
        "status": "healthy",
        "service": "Research Tool API",
        "version": "0.1.0"
    }

@app.get("/api/health")
async def api_health():
    """API health check endpoint - should respond quickly without any dependencies."""
    # This endpoint should NEVER hang - it's the simplest possible check
    return {
        "status": "healthy",
        "service": "Research Tool API",
        "version": "0.1.0",
        "endpoint": "/api/health"
    }

logger.info("✓ FastAPI application initialized successfully")


@app.on_event("startup")
async def startup_event():
    """Called when the application starts."""
    logger.info("=" * 60)
    logger.info("FastAPI application startup complete")
    logger.info("Server is ready to accept requests")
    logger.info("=" * 60)
    
    # Log tail window disabled - use the main uvicorn console window instead
    # The console window spawned by run_server.py contains the actual live uvicorn output
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Called when the application shuts down."""
    logger.info("FastAPI application shutting down...")


# WebSocket endpoint
@app.websocket("/ws/{batch_id}")
async def websocket_endpoint(websocket: WebSocket, batch_id: str):
    await websocket_manager.connect(websocket, batch_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
            await websocket_manager.handle_message(websocket, batch_id, data)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(websocket, batch_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)  # Changed from 8000 to 3001

