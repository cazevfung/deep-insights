"""
Workflow API routes.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
import platform
import subprocess
from pathlib import Path
from app.services.workflow_service import WorkflowService
from app.websocket.manager import WebSocketManager
from loguru import logger

router = APIRouter()

# Global WebSocket manager instance - will be set by main.py
websocket_manager: Optional[WebSocketManager] = None
workflow_service: Optional[WorkflowService] = None

def set_websocket_manager(manager: WebSocketManager):
    """Set the shared WebSocket manager instance."""
    global websocket_manager, workflow_service
    websocket_manager = manager
    workflow_service = WorkflowService(manager)


# Track if terminal window has been opened (only open once)
_terminal_window_opened = False

def _open_logs_terminal_window():
    """Open a terminal window to show server logs (Windows only, opens once)."""
    global _terminal_window_opened
    import os
    
    # Only open once per server session
    if _terminal_window_opened:
        return
    
    try:
        if platform.system() == "Windows":
            # Get the log file path
            project_root = Path(__file__).parent.parent.parent.parent
            log_file = project_root / "logs" / "backend.log"
            log_file.parent.mkdir(exist_ok=True, parents=True)
            
            # Create the log file if it doesn't exist
            if not log_file.exists():
                log_file.touch()
            
            # Create a batch file that tails the log file
            temp_bat = project_root / "logs" / "tail_logs.bat"
            temp_bat.parent.mkdir(exist_ok=True, parents=True)
            
            bat_content = f'''@echo off
title Research Tool Backend Server Logs
color 0F
cls
echo ============================================================
echo Research Tool Backend Server - Console Logs
echo ============================================================
echo.
echo This window shows server logs including Playwright/Chromium errors.
echo Log file: {log_file}
echo.
echo Waiting for logs to appear...
echo.
if exist "{log_file}" (
    powershell -Command "Get-Content '{log_file}' -Wait -Tail 100"
) else (
    echo Log file not found. Waiting for it to be created...
    timeout /t 2 /nobreak >nul
    if exist "{log_file}" (
        powershell -Command "Get-Content '{log_file}' -Wait -Tail 100"
    ) else (
        echo Log file still not found. Please check the server logs.
        pause
    )
)
'''
            temp_bat.write_text(bat_content, encoding='utf-8')
            
            # Launch the batch file in a new window
            # Use os.startfile() which is the proper way on Windows
            os.startfile(str(temp_bat))
            
            _terminal_window_opened = True
            logger.info("✓ Terminal window opened for viewing logs")
    except Exception as e:
        logger.warning(f"Could not open terminal window: {e}")
        # Don't fail if terminal can't be opened


class StartWorkflowRequest(BaseModel):
    batch_id: str


class StartWorkflowResponse(BaseModel):
    workflow_id: str
    batch_id: str
    status: str


@router.post("/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Start workflow for a batch.
    
    Args:
        request: Request with batch_id
        background_tasks: FastAPI background tasks
        
    Returns:
        Workflow ID and status
    """
    try:
        logger.info(f"Received workflow start request: batch_id={request.batch_id}")
        
        # Open terminal window to show logs (Windows only, first time only)
        try:
            if platform.system() == "Windows":
                _open_logs_terminal_window()
        except Exception as e:
            logger.warning(f"Could not open terminal window: {e}")
            # Don't fail the workflow if terminal can't be opened
        
        if workflow_service is None:
            logger.error("Workflow service not initialized")
            raise HTTPException(status_code=500, detail="Workflow service not initialized")
        
        batch_id = request.batch_id
        
        if not batch_id:
            logger.error("batch_id is required but not provided")
            raise HTTPException(status_code=400, detail="batch_id is required")
        
        workflow_id = f"workflow_{batch_id}"
        
        # Start workflow in background using BackgroundTasks (runs after response is sent)
        try:
            background_tasks.add_task(run_workflow_task, batch_id)
            logger.info(f"Added workflow task to background: workflow_id={workflow_id}, batch_id={batch_id}")
        except Exception as task_error:
            logger.error(f"Failed to add background task: {task_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to schedule workflow task: {str(task_error)}")
        
        logger.info(f"Workflow start request successful: workflow_id={workflow_id}, batch_id={batch_id}")
        
        # Create response object
        response = StartWorkflowResponse(
            workflow_id=workflow_id,
            batch_id=batch_id,
            status="started",
        )
        
        logger.info(f"Returning response: workflow_id={response.workflow_id}, batch_id={response.batch_id}, status={response.status}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


async def run_workflow_task(batch_id: str):
    """Background task to run workflow."""
    try:
        logger.info(f"Starting background workflow task for batch_id: {batch_id}")
        
        if workflow_service is None:
            logger.error("Workflow service is None in background task")
            return
        
        await workflow_service.run_workflow(batch_id)
        logger.info(f"Background workflow task completed for batch_id: {batch_id}")
    except Exception as e:
        logger.error(f"Workflow task error for batch_id {batch_id}: {e}", exc_info=True)
        # Try to broadcast error to WebSocket clients
        try:
            if websocket_manager is not None:
                await websocket_manager.broadcast(batch_id, {
                    "type": "error",
                    "phase": "workflow",
                    "message": f"工作流错误: {str(e)}",
                })
        except Exception as broadcast_error:
            logger.error(f"Failed to broadcast error: {broadcast_error}")


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Get workflow status.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow status
    """
    try:
        if websocket_manager is None:
            raise HTTPException(status_code=500, detail="WebSocket manager not initialized")
        if workflow_service is None:
            raise HTTPException(status_code=500, detail="Workflow service not initialized")
        
        # Extract batch_id from workflow_id
        batch_id = workflow_id.replace("workflow_", "")
        
        # Get connection count
        connection_count = websocket_manager.get_connection_count(batch_id)
        
        # Check cancellation status
        progress_service = workflow_service.progress_service
        is_cancelled = progress_service.is_cancelled(batch_id)
        cancellation_info = progress_service.get_cancellation_info(batch_id) if is_cancelled else None
        
        return {
            "workflow_id": workflow_id,
            "batch_id": batch_id,
            "status": "cancelled" if is_cancelled else ("running" if connection_count > 0 else "stopped"),
            "connections": connection_count,
            "cancelled": is_cancelled,
            "cancellation_info": cancellation_info,
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CancelWorkflowRequest(BaseModel):
    batch_id: str
    reason: Optional[str] = "User cancelled"


@router.post("/cancel")
async def cancel_workflow(request: CancelWorkflowRequest):
    """
    Cancel a running workflow.
    
    Args:
        request: Request with batch_id and optional reason
        
    Returns:
        Cancellation confirmation
    """
    try:
        batch_id = request.batch_id
        reason = request.reason or "User cancelled"
        
        if not batch_id:
            raise HTTPException(status_code=400, detail="batch_id is required")
        
        # Cancel via progress service
        await workflow_service.progress_service.cancel_batch(batch_id, reason)
        
        logger.info(f"Cancelled workflow: batch_id={batch_id}, reason={reason}")
        
        return {
            "batch_id": batch_id,
            "status": "cancelled",
            "reason": reason,
            "cancellation_info": workflow_service.progress_service.get_cancellation_info(batch_id)
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


