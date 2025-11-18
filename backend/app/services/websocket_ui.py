"""
WebSocket UI adapter for DeepResearchAgent.
"""
from typing import Optional, TYPE_CHECKING, Dict, Any
import asyncio
import threading
import queue
from datetime import datetime
from app.websocket.manager import WebSocketManager
from loguru import logger

if TYPE_CHECKING:
    from app.services.conversation_service import ConversationContextService


class WebSocketUI:
    """Adapter to convert DeepResearchAgent UI calls to WebSocket events."""
    
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        batch_id: str,
        main_loop: Optional[asyncio.AbstractEventLoop] = None,
        conversation_service: Optional["ConversationContextService"] = None,
    ):
        self.ws_manager = websocket_manager
        self.batch_id = batch_id
        self.stream_buffers: dict[str, str] = {}
        # Track the last sent position for each stream to prevent duplicate sends
        self._stream_sent_positions: dict[str, int] = {}
        self.main_loop = main_loop
        self.conversation_service = conversation_service
        self._loop_lock = threading.Lock()
        # User input response queue - maps prompt_id to response queue
        self._user_input_queues: dict[str, queue.Queue] = {}
        self._prompt_counter = 0
        self._prompt_lock = threading.Lock()
        # Message queue for retry when loop is temporarily unavailable
        self._pending_messages: queue.Queue = queue.Queue()
        self._retry_thread: Optional[threading.Thread] = None
        self._retry_thread_lock = threading.Lock()
        if self.conversation_service:
            self.conversation_service.ensure_batch(batch_id)
    
    def _get_main_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """
        Get the main event loop, trying multiple strategies.
        
        Priority:
        1. Stored main_loop reference (works from worker threads)
        2. Current running loop (only works in async context)
        """
        # Always try stored reference first (works from worker threads)
        # IMPORTANT: Don't check is_running() from worker threads - it may return False
        # even though the loop is running in the main thread. Just check if it's closed.
        if self.main_loop is not None:
            try:
                # Only check if loop is closed, not if it's running
                # is_running() can return False when called from a different thread
                if not self.main_loop.is_closed():
                    return self.main_loop
            except (RuntimeError, AttributeError):
                # Loop might be closed or in invalid state
                pass
        
        # Fallback: Try to get the current event loop (only works in async context, not worker threads)
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_closed():
                return loop
        except RuntimeError:
            pass
        
        return None
    
    def _schedule_coroutine(self, coro):
        """
        Schedule a coroutine to run on the main event loop from any thread.
        
        If loop is unavailable, queues the coroutine for retry.
        """
        loop = self._get_main_loop()
        
        if loop is not None:
            # We have a running loop, schedule the coroutine
            try:
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                # Don't wait for completion to avoid blocking worker threads
                return future
            except Exception as e:
                logger.warning(f"Failed to schedule coroutine on main loop: {e}, queuing for retry")
                # Queue for retry instead of failing
                self._queue_message_for_retry(coro)
                return None
        else:
            # No running loop available - queue for retry
            logger.debug("No event loop available, queuing message for retry")
            self._queue_message_for_retry(coro)
            return None
    
    def _queue_message_for_retry(self, coro):
        """Queue a coroutine for retry when loop becomes available."""
        try:
            self._pending_messages.put_nowait(coro)
            # Start retry thread if not already running
            self._start_retry_thread()
        except queue.Full:
            logger.warning("Message queue full, dropping message")
        except Exception as e:
            logger.error(f"Failed to queue message for retry: {e}")
    
    def _start_retry_thread(self):
        """Start background thread to retry pending messages."""
        with self._retry_thread_lock:
            if self._retry_thread is not None and self._retry_thread.is_alive():
                return  # Already running
            
            def retry_worker():
                """Background worker to retry pending messages."""
                while True:
                    try:
                        # Wait for message with timeout
                        coro = self._pending_messages.get(timeout=1.0)
                        
                        # Try to send it
                        loop = self._get_main_loop()
                        if loop is not None:
                            try:
                                asyncio.run_coroutine_threadsafe(coro, loop)
                            except Exception as e:
                                logger.warning(f"Retry failed: {e}, re-queuing message")
                                # Re-queue if it fails
                                try:
                                    self._pending_messages.put_nowait(coro)
                                except queue.Full:
                                    logger.error("Failed to re-queue message, dropping")
                        else:
                            # No loop yet, re-queue
                            try:
                                self._pending_messages.put_nowait(coro)
                            except queue.Full:
                                logger.error("Message queue full during retry, dropping")
                        
                        # Mark task as done
                        self._pending_messages.task_done()
                    except queue.Empty:
                        # Timeout - check if we should continue
                        continue
                    except Exception as e:
                        logger.error(f"Error in retry worker: {e}")
            
            self._retry_thread = threading.Thread(target=retry_worker, daemon=True)
            self._retry_thread.start()
    
    def display_message(self, message: str, level: str = "info"):
        """Send message via WebSocket."""
        coro = self._send_message(message, level)
        self._schedule_coroutine(coro)
    
    async def _send_message(self, message: str, level: str):
        """Async helper to send message."""
        try:
            payload = {
                "type": "workflow:progress",
                "message": message,
                "level": level,
            }
            logger.debug(f"Broadcasting message to batch {self.batch_id}: {message[:100]}")
            await self.ws_manager.broadcast(self.batch_id, payload)
            logger.debug(f"Successfully broadcast message to batch {self.batch_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast message to batch {self.batch_id}: {e}", exc_info=True)
    
    def display_header(self, title: str):
        """Display a section header and notify phase change if applicable."""
        self.display_message(f"\n{'=' * 60}\n  {title}\n{'=' * 60}\n", "info")
        
        # Auto-detect phase transitions from header titles
        title_lower = title.lower()
        if "phase 0: 数据准备" in title or "phase 0: data preparation" in title_lower:
            self.notify_phase_change("phase0", "阶段0: 数据准备")
        elif "phase 0.5" in title or "phase 0.5" in title_lower:
            self.notify_phase_change("phase0.5", "阶段0.5: 角色生成")
        elif "phase 1: 生成研究目标" in title or "phase 1: discover" in title_lower:
            self.notify_phase_change("phase1", "阶段1: 发现")
        elif "phase 2: 综合" in title or "phase 2:" in title_lower or "phase 2: synthesize" in title_lower:
            self.notify_phase_change("phase2", "阶段2: 综合")
        elif "phase 3: 执行" in title or "phase 3: execute" in title_lower or "phase 3: 执行研究计划" in title:
            self.notify_phase_change("phase3", "阶段3: 执行")
        elif "phase 4: 生成最终报告" in title or "phase 4: 最终综合" in title or "phase 4: final" in title_lower:
            self.notify_phase_change("phase4", "阶段4: 最终综合")
    
    def display_progress(self, status: dict):
        """Display progress information."""
        progress = status.get("progress_percentage", 0)
        current_step = status.get("current_step_id")
        current_goal = status.get("current_step_goal", "")
        
        message = f"[进度: {progress:.1f}%]"
        if current_step:
            message += f" 步骤 {current_step}: {current_goal[:50]}..."
        
        self.display_message(message, "info")
    
    def display_stream(self, token: str, stream_id: str, reasoning_content: str = "None", content: str = "None"):
        """Stream token via WebSocket.
        
        Per Alibaba Cloud SSE standard, tokens are incremental deltas.
        Position tracking ensures each piece is only sent once to prevent duplication.
        
        Args:
            token: Token text (legacy, for backward compatibility)
            stream_id: Stream identifier
            reasoning_content: Reasoning/thinking content (Qwen protocol)
            content: Regular response content (Qwen protocol)
        """
        if not stream_id:
            logger.warning("display_stream called without stream_id; defaulting to 'default'")
            stream_id = "default"
        
        # Get current buffer and last sent position
        existing = self.stream_buffers.get(stream_id, "")
        last_sent_pos = self._stream_sent_positions.get(stream_id, 0)
        
        # Append delta token to buffer (SSE sends incremental chunks)
        new_buffer = existing + token
        
        # Extract only the content that hasn't been sent yet
        # This prevents duplicates if the same token is received multiple times
        unsent_content = new_buffer[last_sent_pos:]
        
        # Check if we have new reasoning_content or content to send
        # Even if unsent_content is empty, we should send if reasoning_content or content is not "None"
        has_reasoning = reasoning_content != "None" and len(reasoning_content) > 0
        has_content = content != "None" and len(content) > 0
        has_new_token = len(unsent_content) > 0
        
        # Debug logging to detect duplicate sends
        logger.debug(f"📤 display_stream: stream_id={stream_id}, token_len={len(token)}, unsent_len={len(unsent_content)}, reasoning={reasoning_content[:20] if reasoning_content != 'None' else 'None'}, content={content[:20] if content != 'None' else 'None'}, has_reasoning={has_reasoning}, has_content={has_content}")
        
        # Only skip if we have no new content AND no reasoning/content to send
        if not has_new_token and not has_reasoning and not has_content:
            # No new content to send, skip
            logger.debug(f"⏭️ Skipping - no new content for {stream_id}")
            return
        
        # Update buffer and sent position (only if we have new token content)
        if has_new_token:
            self.stream_buffers[stream_id] = new_buffer
            self._stream_sent_positions[stream_id] = len(new_buffer)
        
        # Send the unsent content (or empty string if no new token) with Qwen protocol fields
        # The frontend will use reasoning_content and content fields if they're not "None"
        coro = self._send_stream_token(unsent_content if has_new_token else "", stream_id, reasoning_content, content)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.append_stream_token(self.batch_id, stream_id, unsent_content)
    
    async def _send_stream_token(self, token: str, stream_id: str, reasoning_content: str = "None", content: str = "None"):
        """Async helper to send stream token following Qwen SSE protocol.
        
        Protocol:
        - 若reasoning_content不为 None，content 为 None，则当前处于思考阶段
        - 若reasoning_content为 None，content 不为 None，则当前处于回复阶段
        - 若两者均为 None，则阶段与前一包一致
        """
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:stream_token",
                "stream_id": stream_id,
                "reasoning_content": reasoning_content,
                "content": content,
                # Keep token for backward compatibility
                "token": token,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast stream token: {e}")

    def notify_stream_start(self, stream_id: str, phase: Optional[str] = None, metadata: Optional[dict] = None):
        """Notify frontend that a new token stream has started."""
        if not stream_id:
            logger.warning("notify_stream_start called without stream_id; defaulting to 'default'")
            stream_id = "default"
        # Reset buffer and sent position for this stream
        self.stream_buffers[stream_id] = ""
        self._stream_sent_positions[stream_id] = 0
        coro = self._send_stream_start(stream_id, phase, metadata)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.start_stream(self.batch_id, stream_id, phase, metadata)

    async def _send_stream_start(self, stream_id: str, phase: Optional[str], metadata: Optional[dict]):
        """Async helper to send stream start notification."""
        try:
            payload = {
                "type": "research:stream_start",
                "stream_id": stream_id,
                "phase": phase,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }
            await self.ws_manager.broadcast(self.batch_id, payload)
        except Exception as e:
            logger.error(f"Failed to broadcast stream start: {e}")

    def notify_stream_end(self, stream_id: str, phase: Optional[str] = None, metadata: Optional[dict] = None):
        """Notify frontend that the current token stream has finished."""
        if not stream_id:
            logger.warning("notify_stream_end called without stream_id; defaulting to 'default'")
            stream_id = "default"
        coro = self._send_stream_end(stream_id, phase, metadata)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.end_stream(self.batch_id, stream_id)

    async def _send_stream_end(self, stream_id: str, phase: Optional[str], metadata: Optional[dict]):
        """Async helper to send stream end notification."""
        try:
            payload = {
                "type": "research:stream_end",
                "stream_id": stream_id,
                "phase": phase,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }
            await self.ws_manager.broadcast(self.batch_id, payload)
        except Exception as e:
            logger.error(f"Failed to broadcast stream end: {e}")

    def clear_stream_buffer(self, stream_id: Optional[str] = None):
        """Clear the streaming buffer."""
        if stream_id is None:
            self.stream_buffers.clear()
            self._stream_sent_positions.clear()
        else:
            self.stream_buffers.pop(stream_id, None)
            self._stream_sent_positions.pop(stream_id, None)
    
    def get_stream_buffer(self, stream_id: Optional[str] = None) -> str:
        """Get current stream buffer contents."""
        if stream_id is None:
            # Return latest buffer if available (for backward compatibility)
            if not self.stream_buffers:
                return ""
            last_stream_id = next(reversed(self.stream_buffers))
            return self.stream_buffers.get(last_stream_id, "")
        return self.stream_buffers.get(stream_id, "")
    
    def display_json_update(self, stream_id: str, json_data: Dict[str, Any], is_complete: bool = False):
        """
        Send structured JSON update to frontend for real-time display.
        
        Args:
            stream_id: Stream identifier
            json_data: Parsed JSON data (may be partial)
            is_complete: Whether the JSON object is complete
        """
        if not stream_id:
            logger.warning("display_json_update called without stream_id; defaulting to 'default'")
            stream_id = "default"
        coro = self._send_json_update(stream_id, json_data, is_complete)
        self._schedule_coroutine(coro)
    
    async def _send_json_update(self, stream_id: str, json_data: Dict[str, Any], is_complete: bool):
        """Async helper to send JSON update."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:json_update",
                "stream_id": stream_id,
                "json_data": json_data,
                "is_complete": is_complete,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to broadcast JSON update: {e}")
    
    def notify_phase_change(self, phase: str, phase_name: str = None):
        """Notify frontend of phase transition."""
        phase_names = {
            "scraping": "抓取进度",
            "research": "研究代理",
            "phase0": "阶段0: 数据准备",
            "phase0.5": "阶段0.5: 角色生成",
            "phase1": "阶段1: 发现",
            "phase2": "阶段2: 综合",
            "phase3": "阶段3: 执行",
            "phase4": "阶段4: 最终综合",
        }
        
        display_name = phase_name or phase_names.get(phase, phase)
        
        coro = self._send_phase_change(phase, display_name)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.record_phase_change(self.batch_id, phase, display_name)
    
    async def _send_phase_change(self, phase: str, phase_name: str):
        """Async helper to send phase change notification."""
        try:
            # Fix: Frontend expects 'research:phase_change', not 'phase:changed'
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:phase_change",
                "phase": phase,
                "phase_name": phase_name,
                "message": f"进入阶段: {phase_name}",
            })
        except Exception as e:
            logger.error(f"Failed to broadcast phase change: {e}")
    
    def prompt_user(self, prompt: str, choices: Optional[list] = None) -> str:
        """
        Request user input via WebSocket.
        
        This is a blocking operation that waits for user response.
        Returns the user's response or empty string if timeout/error.
        """
        # Generate unique prompt ID
        with self._prompt_lock:
            self._prompt_counter += 1
            prompt_id = f"{self.batch_id}_{self._prompt_counter}_{datetime.now().timestamp()}"
        
        logger.info(f"Requesting user input: prompt_id={prompt_id}, prompt={prompt[:100]}, choices={choices}")
        
        # Create response queue for this prompt
        response_queue = queue.Queue(maxsize=1)  # Limit queue size to prevent buildup
        self._user_input_queues[prompt_id] = response_queue
        if self.conversation_service:
            self.conversation_service.record_procedural_prompt(self.batch_id, prompt_id, prompt, choices or [])
        
        # Send prompt to frontend with retry logic
        coro = self._send_user_prompt(prompt, choices, prompt_id)
        future = self._schedule_coroutine(coro)
        
        # Give some time for the prompt to be sent before waiting
        import time
        time.sleep(0.1)  # Small delay to ensure prompt is sent
        
        # Wait for response indefinitely - research should pause until user responds
        try:
            logger.info(f"Waiting for user response for prompt_id: {prompt_id} (will wait indefinitely)")
            response = response_queue.get()  # No timeout - wait indefinitely for user input
            logger.info(f"Received user response for prompt_id: {prompt_id}, response: {response[:50] if response else '(empty)'}")
            return response
        except queue.Empty:
            # This should never happen without a timeout, but handle it gracefully
            logger.error(f"Unexpected queue.Empty for prompt_id: {prompt_id}")
            return ""
        except Exception as e:
            logger.error(f"Error waiting for user input for prompt_id: {prompt_id}: {e}", exc_info=True)
            return ""
        finally:
            # Clean up queue
            if prompt_id in self._user_input_queues:
                del self._user_input_queues[prompt_id]
                logger.debug(f"Cleaned up prompt queue for prompt_id: {prompt_id}")
    
    def deliver_user_input(self, prompt_id: str, response: str):
        """
        Deliver user input response to waiting prompt_user() call.
        
        This is called by the WebSocket manager when it receives user input.
        """
        if prompt_id in self._user_input_queues:
            try:
                self._user_input_queues[prompt_id].put_nowait(response)
                logger.info(f"Successfully delivered user input for prompt_id: {prompt_id}, response: {response[:50]}")
            except queue.Full:
                logger.error(f"Response queue full for prompt_id: {prompt_id}")
                # Try to clear and retry once
                try:
                    # Clear the queue and try again
                    while not self._user_input_queues[prompt_id].empty():
                        try:
                            self._user_input_queues[prompt_id].get_nowait()
                        except queue.Empty:
                            break
                    self._user_input_queues[prompt_id].put_nowait(response)
                    logger.info(f"Retried and delivered user input for prompt_id: {prompt_id}")
                except Exception as e:
                    logger.error(f"Failed to retry delivery for prompt_id: {prompt_id}, error: {e}")
        else:
            available_prompts = list(self._user_input_queues.keys())
            logger.warning(
                f"No waiting prompt found for prompt_id: {prompt_id}. Available prompts: {available_prompts}"
            )

            # Try loose matching based on containing strings (legacy behaviour)
            matching_prompts = [
                pid for pid in available_prompts if prompt_id in pid or pid in prompt_id
            ]

            # If still no match, attempt prefix-based matching that ignores the timestamp suffix
            if not matching_prompts and "_" in prompt_id:
                prompt_prefix = prompt_id.rsplit("_", 1)[0]
                matching_prompts = [
                    pid for pid in available_prompts if pid.startswith(prompt_prefix)
                ]

            if matching_prompts:
                # Prefer the most recent-looking prompt id (lexicographically highest)
                target_prompt_id = sorted(matching_prompts)[-1]
                logger.info(
                    f"Found {len(matching_prompts)} potentially matching prompts, using {target_prompt_id}"
                )
                try:
                    self._user_input_queues[target_prompt_id].put_nowait(response)
                    logger.info(
                        f"Delivered user input to fallback prompt: {target_prompt_id} (original id: {prompt_id})"
                    )
                except Exception as e:
                    logger.error(f"Failed to deliver to matching prompt {target_prompt_id}: {e}")
            else:
                logger.error(
                    f"Unable to deliver user input because no matching prompt_id was found for {prompt_id}"
                )
    
    async def _send_user_prompt(self, prompt: str, choices: Optional[list], prompt_id: Optional[str] = None):
        """Async helper to send user prompt."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:user_input_required",
                "prompt": prompt,
                "choices": choices,
                "prompt_id": prompt_id,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast user prompt: {e}")
    
    def display_goals(self, goals: list):
        """Display research goals for user selection."""
        coro = self._send_goals(goals)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.record_goals(self.batch_id, goals)
    
    async def _send_goals(self, goals: list):
        """Async helper to send goals."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:goals",
                "goals": goals,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast goals: {e}")
    
    def confirm_plan(self, plan: dict) -> bool:
        """Confirm research plan."""
        coro = self._send_plan_confirmation(plan)
        self._schedule_coroutine(coro)
        
        # For now, return True (auto-confirm)
        # In production, this would wait for user response
        return True
    
    async def _send_plan_confirmation(self, plan: dict):
        """Async helper to send plan confirmation."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:plan_confirmation",
                "plan": plan,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast plan confirmation: {e}")
    
    def display_synthesized_goal(self, synthesized_goal: dict):
        """Display the synthesized comprehensive topic."""
        coro = self._send_synthesized_goal(synthesized_goal)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.record_synthesized_goal(self.batch_id, synthesized_goal)
    
    async def _send_synthesized_goal(self, synthesized_goal: dict):
        """Async helper to send synthesized goal."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:synthesized_goal",
                "synthesized_goal": synthesized_goal,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast synthesized goal: {e}")
    
    def display_plan(self, plan: list):
        """Display research plan."""
        # Use confirm_plan since it already exists and sends the plan
        # But we also add a separate display method for clarity
        coro = self._send_plan(plan)
        self._schedule_coroutine(coro)
        if self.conversation_service:
            self.conversation_service.record_plan(self.batch_id, plan)
    
    async def _send_plan(self, plan: list):
        """Async helper to send plan."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "research:plan",
                "plan": plan,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast plan: {e}")
    
    def display_report(self, report: str, save_path: Optional[str] = None):
        """Display final report."""
        coro = self._send_report(report, save_path)
        self._schedule_coroutine(coro)
    
    async def _send_report(self, report: str, save_path: Optional[str] = None):
        """Async helper to send report."""
        try:
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "phase4:report_ready",
                "report": report,
                "save_path": save_path,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast report: {e}")
    
    def display_step_complete(self, step_data: dict):
        """Display step completion with JSON results."""
        coro = self._send_step_complete(step_data)
        self._schedule_coroutine(coro)
    
    async def _send_step_complete(self, step_data: dict):
        """Async helper to send step completion."""
        try:
            from datetime import datetime
            await self.ws_manager.broadcast(self.batch_id, {
                "type": "phase3:step_complete",
                "stepData": {
                    "step_id": step_data.get("step_id"),
                    "findings": step_data.get("findings", {}),
                    "insights": step_data.get("insights", ""),
                    "confidence": step_data.get("confidence", 0.0),
                    "timestamp": step_data.get("timestamp", datetime.now().isoformat()),
                }
            })
        except Exception as e:
            logger.error(f"Failed to broadcast step complete: {e}")
    
    def display_summarization_progress(
        self,
        current_item: int,
        total_items: int,
        link_id: str,
        stage: str,
        message: str,
        progress: Optional[float] = None,
        completed_items: Optional[int] = None,
        processing_items: Optional[int] = None,
        queued_items: Optional[int] = None,
        worker_id: Optional[int] = None,
    ):
        """
        Send summarization progress update.
        
        Args:
            current_item: Current item count (for backward compatibility)
            total_items: Total items count
            link_id: Link identifier
            stage: Current stage (queued, processing, completed, error, reused)
            message: Status message
            progress: Progress percentage (0-100). If None, calculated from current_item/total_items
            completed_items: Number of completed items (optional)
            processing_items: Number of items currently being processed (optional)
            queued_items: Number of items in queue (optional)
            worker_id: Worker ID processing current item (optional)
        """
        # Calculate progress if not provided (backward compatibility)
        if progress is None:
            progress = (current_item / total_items) * 100 if total_items > 0 else 0
        
        coro = self._send_summarization_progress(
            current_item, total_items, link_id, stage, message, progress,
            completed_items, processing_items, queued_items, worker_id
        )
        self._schedule_coroutine(coro)
    
    async def _send_summarization_progress(
        self,
        current_item: int,
        total_items: int,
        link_id: str,
        stage: str,
        message: str,
        progress: float,
        completed_items: Optional[int] = None,
        processing_items: Optional[int] = None,
        queued_items: Optional[int] = None,
        worker_id: Optional[int] = None,
    ):
        """Async helper to send summarization progress."""
        try:
            payload = {
                "type": "summarization:progress",
                "batch_id": self.batch_id,
                # EXISTING fields (keep for backward compatibility)
                "current_item": current_item,
                "total_items": total_items,
                "link_id": link_id,
                "stage": stage,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
            
            # NEW optional fields (only include if not None)
            if completed_items is not None:
                payload["completed_items"] = completed_items
            if processing_items is not None:
                payload["processing_items"] = processing_items
            if queued_items is not None:
                payload["queued_items"] = queued_items
            if worker_id is not None:
                payload["worker_id"] = worker_id
            
            logger.debug(f"Broadcasting summarization progress to batch {self.batch_id}: {message}")
            await self.ws_manager.broadcast(self.batch_id, payload)
        except Exception as e:
            logger.error(f"Failed to broadcast summarization progress to batch {self.batch_id}: {e}", exc_info=True)
    
    def display_summary(self, link_id: str, summary_type: str, summary_data: dict):
        """
        Send summary data to frontend.
        
        Args:
            link_id: Link identifier for the content item
            summary_type: Type of summary ("transcript" or "comments")
            summary_data: Summary data (already flattened for UI)
        """
        coro = self._send_summary(link_id, summary_type, summary_data)
        self._schedule_coroutine(coro)
    
    async def _send_summary(self, link_id: str, summary_type: str, summary_data: dict):
        """Async helper to send summary data."""
        try:
            payload = {
                "type": "phase0:summary",
                "batch_id": self.batch_id,
                "link_id": link_id,
                "summary_type": summary_type,  # "transcript" or "comments"
                "summary": summary_data,  # Flattened summary data
                "timestamp": datetime.now().isoformat()
            }
            logger.debug(f"Broadcasting summary to batch {self.batch_id}: {summary_type} for {link_id}")
            await self.ws_manager.broadcast(self.batch_id, payload)
        except Exception as e:
            logger.error(f"Failed to broadcast summary to batch {self.batch_id}: {e}", exc_info=True)

