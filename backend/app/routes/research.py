"""
Research API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from loguru import logger

from app.routes.workflow import workflow_service, websocket_manager

router = APIRouter()


class UserInputRequest(BaseModel):
    type: str
    data: dict


class ConversationMessageRequest(BaseModel):
    batch_id: str
    message: str
    session_id: Optional[str] = None


class ConversationMessageResponse(BaseModel):
    status: Literal["ok", "queued"]
    user_message_id: str
    assistant_message_id: Optional[str] = None
    reply: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    context_bundle: Optional[Dict[str, Any]] = None
    queued_reason: Optional[str] = None


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


@router.post("/conversation", response_model=ConversationMessageResponse)
async def send_conversation_message(request: ConversationMessageRequest):
    """
    Handle right-column conversation messages with contextual feedback.
    """
    if workflow_service is None or websocket_manager is None:
        raise HTTPException(status_code=500, detail="Workflow service is not initialized")

    if not request.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id is required")

    conversation_service = workflow_service.conversation_service
    conversation_service.ensure_batch(request.batch_id)

    try:
        result = await conversation_service.handle_user_message(
            request.batch_id,
            request.message,
            session_id=request.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Conversation handling failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate conversation response") from exc

    user_payload = conversation_service.get_message_payload(request.batch_id, result.user_message_id)
    if user_payload:
        await websocket_manager.broadcast(request.batch_id, {
            "type": "conversation:message",
            "message": user_payload,
        })

    assistant_payload = None
    if result.status == "ok" and result.assistant_message_id:
        assistant_payload = conversation_service.get_message_payload(request.batch_id, result.assistant_message_id)
        if assistant_payload:
            await websocket_manager.broadcast(request.batch_id, {
                "type": "conversation:message",
                "message": assistant_payload,
            })

    return ConversationMessageResponse(
        status=result.status,
        user_message_id=result.user_message_id,
        assistant_message_id=result.assistant_message_id,
        reply=result.reply,
        metadata=result.metadata,
        context_bundle=result.context_bundle,
        queued_reason=result.queued_reason,
    )
