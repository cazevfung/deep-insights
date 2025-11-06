"""
Research API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

router = APIRouter()


class UserInputRequest(BaseModel):
    type: str
    data: dict


@router.post("/user_input")
async def submit_user_input(request: UserInputRequest):
    """
    Submit user input during research phase.
    
    Args:
        request: User input request
        
    Returns:
        Success status
    """
    try:
        # This will be handled by WebSocket messages
        # For now, just acknowledge
        logger.info(f"Received user input: type={request.type}")
        
        return {
            "status": "received",
            "type": request.type,
        }
        
    except Exception as e:
        logger.error(f"Failed to process user input: {e}")
        raise HTTPException(status_code=500, detail=str(e))



