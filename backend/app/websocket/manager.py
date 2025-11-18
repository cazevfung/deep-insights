"""
WebSocket manager for real-time progress updates.
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import asyncio
import os
from loguru import logger


class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self, max_buffer_size: Optional[int] = None):
        """
        Initialize WebSocket manager.
        
        Args:
            max_buffer_size: Maximum messages to buffer per batch. If None, will try to read from:
                1. Environment variable WEBSOCKET_BUFFER_SIZE
                2. Config file (web.websocket.max_buffer_size)
                3. Default: 1000 (increased from 100 to handle large batches)
        """
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.batch_rooms: Dict[str, Set[str]] = {}  # batch_id -> connection_ids
        # Store WebSocketUI instances for user input delivery
        self._ui_instances: Dict[str, 'WebSocketUI'] = {}  # batch_id -> WebSocketUI
        # Message buffer for messages sent before clients connect
        self._message_buffer: Dict[str, list] = {}  # batch_id -> list of messages
        
        # Determine buffer size from various sources
        if max_buffer_size is not None:
            self._max_buffer_size = max_buffer_size
        else:
            # Try environment variable first
            env_buffer_size = os.environ.get('WEBSOCKET_BUFFER_SIZE')
            if env_buffer_size:
                try:
                    self._max_buffer_size = int(env_buffer_size)
                except ValueError:
                    logger.warning(f"Invalid WEBSOCKET_BUFFER_SIZE value: {env_buffer_size}, using default")
                    self._max_buffer_size = 1000
            else:
                # Try config file
                try:
                    from core.config import Config
                    config = Config()
                    self._max_buffer_size = config.get('web.websocket.max_buffer_size', 1000)
                except Exception:
                    # Default to 1000 (increased from 100 to handle large batches with many progress updates)
                    self._max_buffer_size = 1000
        
        logger.info(f"WebSocket manager initialized with buffer size: {self._max_buffer_size}")
        self._conversation_service: Optional['ConversationContextService'] = None
    
    def register_ui(self, batch_id: str, ui: 'WebSocketUI'):
        """Register a WebSocketUI instance for a batch."""
        from app.services.websocket_ui import WebSocketUI
        self._ui_instances[batch_id] = ui
        logger.debug(f"Registered WebSocketUI for batch_id: {batch_id}")
    
    def unregister_ui(self, batch_id: str):
        """Unregister a WebSocketUI instance for a batch."""
        if batch_id in self._ui_instances:
            del self._ui_instances[batch_id]
            logger.debug(f"Unregistered WebSocketUI for batch_id: {batch_id}")

    def set_conversation_service(self, service: 'ConversationContextService'):
        """Attach conversation context service for conversational feedback."""
        self._conversation_service = service
    
    async def connect(self, websocket: WebSocket, batch_id: str):
        """Connect a WebSocket client."""
        await websocket.accept()
        
        connection_id = id(websocket)
        
        if batch_id not in self.active_connections:
            self.active_connections[batch_id] = set()
        
        self.active_connections[batch_id].add(websocket)
        
        if batch_id not in self.batch_rooms:
            self.batch_rooms[batch_id] = set()
        
        self.batch_rooms[batch_id].add(str(connection_id))
        
        # Log connection state for debugging
        total_connections = len(self.active_connections[batch_id])
        logger.info(f"WebSocket connected: batch_id={batch_id}, connection_id={connection_id}, total_connections={total_connections}")
        logger.debug(f"Active connections keys after connect: {list(self.active_connections.keys())}")
        logger.debug(f"Connections for batch {batch_id}: {len(self.active_connections.get(batch_id, []))}")
        
        # If UI instance exists for this batch, log it (but don't re-register - it's already registered)
        if batch_id in self._ui_instances:
            logger.debug(f"UI instance already registered for batch_id: {batch_id}, connection will be able to deliver user input")
        
        # Send welcome message
        await self.send_to_client(websocket, {
            "type": "connected",
            "batch_id": batch_id,
            "message": "WebSocket connected successfully",
        })
        
        # Send buffered messages if any
        if batch_id in self._message_buffer and self._message_buffer[batch_id]:
            buffered_count = len(self._message_buffer[batch_id])
            logger.info(f"Sending {buffered_count} buffered messages to new client for batch {batch_id}")
            # Create a copy of the buffer to iterate over
            buffered_messages = list(self._message_buffer[batch_id])
            sent_count = 0
            for buffered_message in buffered_messages:
                try:
                    await self.send_to_client(websocket, buffered_message)
                    sent_count += 1
                    logger.debug(f"Sent buffered message type {buffered_message.get('type')} to client")
                except Exception as e:
                    logger.error(f"Failed to send buffered message type {buffered_message.get('type')}: {e}")
            logger.info(f"Sent {sent_count}/{buffered_count} buffered messages to client for batch {batch_id}")
            # Clear buffer after sending
            self._message_buffer[batch_id] = []
        elif batch_id in self._message_buffer:
            logger.debug(f"No buffered messages for batch {batch_id} (buffer exists but is empty)")
        else:
            logger.debug(f"No message buffer for batch {batch_id}")
    
    async def disconnect(self, websocket: WebSocket, batch_id: str):
        """Disconnect a WebSocket client."""
        connection_id = id(websocket)
        
        if batch_id in self.active_connections:
            self.active_connections[batch_id].discard(websocket)
            
            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]
        
        if batch_id in self.batch_rooms:
            self.batch_rooms[batch_id].discard(str(connection_id))
            
            if not self.batch_rooms[batch_id]:
                del self.batch_rooms[batch_id]
        
        logger.info(f"WebSocket disconnected: batch_id={batch_id}, connection_id={connection_id}")
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
    
    async def broadcast(self, batch_id: str, message: dict):
        """Broadcast message to all clients in a batch room."""
        # Debug: Log connection state
        has_connections = batch_id in self.active_connections and len(self.active_connections[batch_id]) > 0
        logger.debug(f"Broadcast check: batch_id={batch_id}, has_connections={has_connections}, active_connections keys={list(self.active_connections.keys())}")
        
        # If no active connections, buffer the message
        if not has_connections:
            # Buffer message for later delivery
            if batch_id not in self._message_buffer:
                self._message_buffer[batch_id] = []
            
            # Implement FIFO buffer: remove oldest messages if buffer is full
            buffer = self._message_buffer[batch_id]
            if len(buffer) >= self._max_buffer_size:
                # Remove oldest message(s) to make room
                # For very high-frequency messages, remove multiple old ones to reduce churn
                removed_count = max(1, len(buffer) - self._max_buffer_size + 1)
                removed_messages = buffer[:removed_count]
                buffer = buffer[removed_count:]
                self._message_buffer[batch_id] = buffer
                logger.warning(
                    f"Message buffer full for batch {batch_id}, removed {removed_count} oldest message(s) "
                    f"(types: {[m.get('type') for m in removed_messages[:3]]})"
                )
            
            buffer.append(message)
            logger.debug(f"Buffered message type {message.get('type')} for batch {batch_id} (buffer size: {len(buffer)})")
            
            logger.debug(f"No active connections for batch_id: {batch_id}, message type: {message.get('type')} (buffered)")
            return
        
        connection_count = len(self.active_connections[batch_id])
        logger.debug(f"Broadcasting message type {message.get('type')} to {connection_count} client(s) for batch {batch_id}")
        
        disconnected = set()
        
        # Iterate over a copy of the set to avoid "Set changed size during iteration" error
        for websocket in list(self.active_connections[batch_id]):
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
                logger.debug(f"Successfully sent message type {message.get('type')} to client")
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}", exc_info=True)
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket, batch_id)
    
    async def handle_message(self, websocket: WebSocket, batch_id: str, data: str):
        """Handle incoming message from client."""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            logger.info(f"Received message: type={message_type}, batch_id={batch_id}")
            
            # Handle different message types
            if message_type == "ping":
                await self.send_to_client(websocket, {"type": "pong"})
            elif message_type == "workflow:start":
                # Workflow start is handled by the workflow route
                pass
            elif message_type == "research:user_input":
                # Handle user input response
                prompt_id = message.get("prompt_id")
                response = message.get("response", "")
                
                logger.info(f"Received user input message: batch_id={batch_id}, prompt_id={prompt_id}, response={response[:50] if response else 'empty'}")
                
                if not prompt_id:
                    logger.error(f"User input message missing prompt_id: batch_id={batch_id}, message={message}")
                    await self.send_to_client(websocket, {
                        "type": "error",
                        "message": "User input message missing prompt_id",
                    })
                    return
                
                if batch_id not in self._ui_instances:
                    logger.error(f"User input received but no UI instance registered for batch_id: {batch_id}. Registered batches: {list(self._ui_instances.keys())}")
                    await self.send_to_client(websocket, {
                        "type": "error",
                        "message": f"No UI instance registered for batch {batch_id}",
                    })
                    return
                
                ui = self._ui_instances[batch_id]
                # Deliver response to waiting prompt_user() call with retry logic
                try:
                    ui.deliver_user_input(prompt_id, response)
                    logger.info(f"Successfully delivered user input for prompt_id: {prompt_id}, batch_id: {batch_id}")
                    if self._conversation_service:
                        conversation_results = await self._conversation_service.resolve_procedural_prompt(
                            batch_id,
                            prompt_id,
                            response,
                        )
                        for conversation_result in conversation_results:
                            user_payload = self._conversation_service.get_message_payload(
                                batch_id, conversation_result.user_message_id
                            )
                            if user_payload:
                                await self.broadcast(batch_id, {
                                    "type": "conversation:message",
                                    "message": user_payload,
                                })
                            if conversation_result.assistant_message_id:
                                assistant_payload = self._conversation_service.get_message_payload(
                                    batch_id, conversation_result.assistant_message_id
                                )
                                if assistant_payload:
                                    await self.broadcast(batch_id, {
                                        "type": "conversation:message",
                                        "message": assistant_payload,
                                    })
                except Exception as e:
                    logger.error(f"Failed to deliver user input for prompt_id: {prompt_id}, batch_id: {batch_id}: {e}", exc_info=True)
                    await self.send_to_client(websocket, {
                        "type": "error",
                        "message": f"Failed to deliver user input: {str(e)}",
                    })
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            await self.send_to_client(websocket, {
                "type": "error",
                "message": f"Failed to process message: {str(e)}",
            })
    
    def get_connection_count(self, batch_id: str) -> int:
        """Get number of active connections for a batch."""
        return len(self.active_connections.get(batch_id, set()))


