"""
Research API routes.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List, Union
from loguru import logger
import json

from app.routes import workflow as workflow_routes

router = APIRouter()


class UserInputRequest(BaseModel):
    type: str
    data: dict


class ConversationMessageRequest(BaseModel):
    batch_id: str
    message: str
    session_id: Optional[str] = None


class ConversationMessageResponse(BaseModel):
    status: Literal["ok", "queued", "context_required"]
    user_message_id: str
    assistant_message_id: Optional[str] = None
    reply: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    context_bundle: Optional[Dict[str, Any]] = None
    queued_reason: Optional[str] = None
    context_request_id: Optional[str] = None
    required_context: Optional[List[Dict[str, Any]]] = None


class ConversationContextSupplyItem(BaseModel):
    slot_key: Optional[str] = None
    label: Optional[str] = None
    content: str


class ConversationContextSupplyRequest(BaseModel):
    batch_id: str
    request_id: str
    items: List[ConversationContextSupplyItem]
    provided_by: Optional[str] = "user"


class SuggestedQuestionsRequest(BaseModel):
    batch_id: str
    session_id: Optional[str] = None
    conversation_context: List[Dict[str, Any]]


class SuggestedQuestionsResponse(BaseModel):
    questions: List[str]
    generated_at: str
    model_used: str


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
    workflow_service = workflow_routes.workflow_service
    websocket_manager = workflow_routes.websocket_manager

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
        context_request_id=result.context_request_id,
        required_context=result.required_context,
    )


@router.post("/conversation/context-supply", response_model=ConversationMessageResponse)
async def supply_conversation_context(request: ConversationContextSupplyRequest):
    workflow_service = workflow_routes.workflow_service
    websocket_manager = workflow_routes.websocket_manager

    if workflow_service is None or websocket_manager is None:
        raise HTTPException(status_code=500, detail="Workflow service is not initialized")

    conversation_service = workflow_service.conversation_service
    conversation_service.ensure_batch(request.batch_id)

    try:
        result = await conversation_service.supply_context(
            request.batch_id,
            request.request_id,
            [item.dict() for item in request.items],
            provided_by=request.provided_by or "user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Context supply failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to supply conversation context") from exc

    user_payload = conversation_service.get_message_payload(request.batch_id, result.user_message_id)
    if user_payload:
        await websocket_manager.broadcast(request.batch_id, {
            "type": "conversation:message",
            "message": user_payload,
        })

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
        context_request_id=result.context_request_id,
        required_context=result.required_context,
    )


@router.post("/conversation/suggest-questions", response_model=SuggestedQuestionsResponse)
async def suggest_questions(request: SuggestedQuestionsRequest):
    """
    Generate suggested follow-up questions based on conversation context and session data.
    """
    workflow_service = workflow_routes.workflow_service

    if workflow_service is None:
        raise HTTPException(status_code=500, detail="Workflow service is not initialized")

    if not request.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id is required")

    conversation_service = workflow_service.conversation_service
    conversation_service.ensure_batch(request.batch_id)

    try:
        questions, model_used = await conversation_service.generate_suggested_questions(
            request.batch_id,
            session_id=request.session_id,
            conversation_context=request.conversation_context,
        )
    except Exception as exc:
        logger.error(f"Failed to generate suggested questions: {exc}", exc_info=True)
        # Return fallback questions instead of failing
        questions = conversation_service.generate_fallback_questions(
            request.batch_id,
            session_id=request.session_id,
        )
        model_used = "fallback"

    from datetime import datetime, timezone
    return SuggestedQuestionsResponse(
        questions=questions,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_used=model_used,
    )


# Editor routes
_editor_service = None


def get_editor_service():
    """Get or create editor service instance."""
    global _editor_service
    if _editor_service is None:
        try:
            from app.services.editor_service import EditorService
            from core.config import Config
            config = Config()
            _editor_service = EditorService(config)
        except Exception as e:
            logger.error(f"Failed to initialize editor service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Editor service unavailable")
    return _editor_service


class EditorChatRequest(BaseModel):
    batch_id: str
    phase: str
    step_id: Optional[str] = None
    selected_text: str
    selected_range: Dict[str, int]
    full_context: str
    user_message: str
    conversation_history: Optional[List[Dict[str, str]]] = None


class EditorApplyRequest(BaseModel):
    batch_id: str
    phase: str
    step_id: Optional[str] = None
    selected_range: Dict[str, int]
    replacement_text: str
    # NEW: Selection metadata for field-level editing
    item_id: Optional[Union[int, str]] = None
    item_index: Optional[int] = None
    field_name: Optional[str] = None
    field_path: Optional[List[Union[str, int]]] = None


@router.post("/editor/chat")
async def editor_chat(request: EditorChatRequest):
    """Chat with AI about selected content."""
    try:
        editor_service = get_editor_service()
        
        async def generate():
            try:
                async for chunk in editor_service.chat_with_selection(
                    batch_id=request.batch_id,
                    phase=request.phase,
                    selected_text=request.selected_text,
                    full_context=request.full_context,
                    user_message=request.user_message,
                    conversation_history=request.conversation_history,
                    step_id=request.step_id
                ):
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                yield "data: {}\n\n"  # End marker
            except Exception as e:
                logger.error(f"Error in editor chat stream: {e}", exc_info=True)
                error_msg = json.dumps({'type': 'error', 'content': str(e)})
                yield f"data: {error_msg}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        logger.error(f"Editor chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editor/apply")
async def editor_apply(request: EditorApplyRequest):
    """Apply changes to phase content.
    
    For Phase 3, if a step goal is changed, automatically triggers step rerun.
    """
    try:
        editor_service = get_editor_service()
        result = await editor_service.apply_changes(
            batch_id=request.batch_id,
            phase=request.phase,
            selected_range=request.selected_range,
            replacement_text=request.replacement_text,
            step_id=request.step_id,
            # NEW: Pass metadata for field-level editing
            item_id=request.item_id,
            item_index=request.item_index,
            field_name=request.field_name,
            field_path=request.field_path
        )
    except ValueError as e:
        # NEW: User-friendly error messages for validation errors
        error_msg = str(e)
        if "array" in error_msg.lower() or "string replacement" in error_msg.lower() or "field-level editing" in error_msg.lower():
            return {
                "status": "error",
                "error": "editing_not_supported",
                "message": (
                    "This content cannot be edited using text selection. "
                    "The content is stored in a structured format. "
                    "Field-level editing support is coming soon."
                ),
                "user_message": error_msg
            }
        elif "disabled" in error_msg.lower():
            return {
                "status": "error",
                "error": "editing_disabled",
                "message": (
                    "Editing for this phase is currently disabled. "
                    "Please wait for the fix to be deployed."
                ),
                "user_message": error_msg
            }
        raise HTTPException(status_code=400, detail=error_msg)
        
        # If Phase 3 step goal was changed, trigger automatic rerun
        if (result.get('metadata', {}).get('step_rerun_required') and 
            request.phase == 'phase3'):
            step_id = result['metadata']['step_rerun_id']
            session_id = request.batch_id  # Assuming batch_id can be used as session_id
            
            # Import workflow service to trigger rerun
            from app.routes import workflow as workflow_routes
            workflow_service = workflow_routes.workflow_service
            
            if workflow_service:
                logger.info(
                    f"Phase 3 step {step_id} goal changed, triggering automatic rerun "
                    f"(old: '{result['metadata']['old_goal'][:50]}...', "
                    f"new: '{result['metadata']['new_goal'][:50]}...')"
                )
                # Trigger rerun asynchronously (don't wait for completion)
                import asyncio
                asyncio.create_task(
                    workflow_service.rerun_phase3_step(
                        batch_id=request.batch_id,
                        session_id=session_id,
                        step_id=step_id,
                        regenerate_report=True  # Regenerate report if Phase 4 is complete
                    )
                )
                result['metadata']['step_rerun_triggered'] = True
                result['metadata']['step_rerun_message'] = f"步骤 {step_id} 的目标已更改，正在自动重新执行..."
            else:
                logger.warning("Workflow service not available, cannot trigger step rerun")
                result['metadata']['step_rerun_triggered'] = False
                result['metadata']['step_rerun_message'] = "无法触发步骤重新执行（工作流服务不可用）"
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Editor apply error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
