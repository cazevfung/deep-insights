"""
Progress tracking service for scraping operations.
"""
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
from app.websocket.manager import WebSocketManager


class ProgressService:
    """Centralized progress tracking and broadcasting service."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        """
        Initialize progress service.
        
        Args:
            websocket_manager: WebSocket manager for broadcasting updates
        """
        self.ws_manager = websocket_manager
        # In-memory state tracking (could be persisted to JSON/DB later)
        self.link_states: Dict[str, Dict] = {}  # batch_id -> link_id -> state
        # Expected total count per batch (set during initialization, never changes)
        self.expected_totals: Dict[str, int] = {}  # batch_id -> expected total count
        # Cancellation tracking
        self.cancellation_flags: Dict[str, bool] = {}  # batch_id -> cancelled
        self.cancellation_info: Dict[str, Dict] = {}  # batch_id -> cancellation details
        # Progress update throttling (to avoid overwhelming UI/WebSocket)
        self.last_update_time: Dict[str, float] = {}  # (batch_id, link_id) -> timestamp
        # Load throttling config from config file or use defaults
        self._load_throttling_config()
        # Grace period for completion confirmation (wait for async operations to finish)
        self.completion_grace_period = 3.0  # Seconds to wait after last progress update before confirming
    
    def _load_throttling_config(self):
        """Load throttling configuration from config file or environment variables."""
        import os
        # Default values (more conservative to reduce message frequency)
        self.min_update_interval = 0.5  # Minimum seconds between updates (2 updates/sec max, increased from 0.2)
        self.progress_change_threshold = 2.0  # Minimum progress change to trigger update (2%, increased from 1%)
        
        try:
            from core.config import Config
            config = Config()
            websocket_config = config.get('web', {}).get('websocket', {})
            
            # Load from config file
            self.min_update_interval = websocket_config.get('min_update_interval', self.min_update_interval)
            self.progress_change_threshold = websocket_config.get('progress_change_threshold', self.progress_change_threshold)
        except Exception:
            pass
        
        # Environment variable overrides
        env_interval = os.environ.get('WEBSOCKET_UPDATE_INTERVAL')
        if env_interval:
            try:
                self.min_update_interval = float(env_interval)
            except ValueError:
                pass
        
        env_threshold = os.environ.get('WEBSOCKET_PROGRESS_THRESHOLD')
        if env_threshold:
            try:
                self.progress_change_threshold = float(env_threshold)
            except ValueError:
                pass
        
        logger.info(f"Progress throttling: interval={self.min_update_interval}s, threshold={self.progress_change_threshold}%")
    
    def initialize_expected_links(self, batch_id: str, expected_links: list):
        """
        Pre-register all expected links for a batch before scraping starts.
        This ensures the total count is accurate from the start, preventing premature completion.
        
        Args:
            batch_id: Batch ID
            expected_links: List of dicts with 'link_id' and 'url' keys
        """
        if batch_id not in self.link_states:
            self.link_states[batch_id] = {}
        
        registered_count = 0
        for link_info in expected_links:
            link_id = link_info.get('link_id')
            url = link_info.get('url')
            
            if not link_id or not url:
                logger.warning(f"Skipping invalid link info: {link_info}")
                continue
            
            # Only register if not already registered (don't overwrite existing state)
            if link_id not in self.link_states[batch_id]:
                self.link_states[batch_id][link_id] = {
                    'url': url,
                    'status': 'pending',
                    # Don't set started_at yet - it will be set when link actually starts
                }
                registered_count += 1
        
        # Store expected total count (this is the "goal" number, never changes)
        # If links were already registered, use the total count of all links (new + existing)
        total_links_count = len(self.link_states[batch_id])
        if registered_count == 0 and total_links_count > 0:
            # All links were already registered - use total count as expected
            logger.warning(
                f"initialize_expected_links called for batch {batch_id} but all {total_links_count} links were already registered. "
                f"Using total count as expected_total."
            )
            self.expected_totals[batch_id] = total_links_count
            return total_links_count
        elif registered_count == 0 and total_links_count == 0:
            # Empty list provided - this is an error condition
            logger.error(
                f"initialize_expected_links called for batch {batch_id} with empty or invalid link list. "
                f"This will cause expected_total to be 0, which may prevent research phase from starting."
            )
            self.expected_totals[batch_id] = 0
            return 0
        else:
            # Normal case: new links registered
            self.expected_totals[batch_id] = registered_count
            logger.info(f"Pre-registered {registered_count} expected links for batch {batch_id} (expected total: {registered_count})")
            return registered_count
    
    def _get_or_recover_expected_total(self, batch_id: str, *, minimum: int = 0) -> int:
        """
        Retrieve expected_total for a batch, recovering from registered data when needed.

        Args:
            batch_id: Batch identifier
            minimum: Optional lower bound to enforce (e.g., completed_count)

        Returns:
            Expected total for the batch (may be recovered from registered links)
        """
        stored = self.expected_totals.get(batch_id)

        if stored is not None and stored > 0 and stored >= minimum:
            return stored

        links = self.link_states.get(batch_id, {})
        recovered = max(len(links), minimum)

        if recovered > 0:
            if stored in (None, 0):
                logger.warning(
                    f"[RECOVER] expected_total missing or zero for batch '{batch_id}'. "
                    f"Recovering value from registered links (count={recovered})."
                )
            elif recovered > stored:
                logger.warning(
                    f"[RECOVER] expected_total {stored} too low for batch '{batch_id}'. "
                    f"Adjusting to {recovered} based on registered links."
                )

            self.expected_totals[batch_id] = recovered
            return recovered

        # No registered data to recover from; keep stored value (0 or None)
        if minimum > 0 and stored not in (None, 0):
            adjusted = max(stored, minimum)
            if adjusted != stored:
                logger.warning(
                    f"[RECOVER] Raising expected_total for batch '{batch_id}' from {stored} to {adjusted} "
                    f"to satisfy minimum requirement ({minimum})."
                )
                self.expected_totals[batch_id] = adjusted
            return adjusted

        return stored or 0

    def _normalize_status(self, status: str) -> str:
        """
        Normalize status format to kebab-case for frontend compatibility.
        
        Args:
            status: Status value (may be snake_case or kebab-case)
            
        Returns:
            Normalized status in kebab-case format
        """
        # Convert snake_case to kebab-case
        if status == 'in_progress':
            return 'in-progress'
        # 'completed' and 'failed' are already correct, but ensure consistency
        return status
    
    async def update_link_progress(
        self,
        batch_id: str,
        link_id: str,
        url: str,
        stage: str,
        stage_progress: float,
        overall_progress: float,
        message: str,
        metadata: Optional[dict] = None
    ):
        """
        Update link progress and broadcast to WebSocket.
        
        Args:
            batch_id: Batch ID
            link_id: Link ID
            url: Link URL
            stage: Current stage name (e.g., "downloading", "transcribing")
            stage_progress: Progress within current stage (0.0-100.0)
            overall_progress: Overall progress for this link (0.0-100.0)
            message: Human-readable status message
            metadata: Additional data (bytes_downloaded, total_bytes, etc.)
        """
        # Update in-memory state
        if batch_id not in self.link_states:
            self.link_states[batch_id] = {}
        
        # CRITICAL: Only update pre-registered entries - do NOT create new ones dynamically
        # This ensures total count is based on expected processes, not started ones
        if link_id not in self.link_states[batch_id]:
            # Check if this batch has expected totals set (pre-registration happened)
            if batch_id in self.expected_totals:
                logger.warning(
                    f"Attempted to update progress for unregistered link_id '{link_id}' in batch '{batch_id}'. "
                    f"Expected total: {self.expected_totals[batch_id]}, Registered: {len(self.link_states[batch_id])}. "
                    f"This may indicate a link_id format mismatch (e.g., missing '_comments' suffix)."
                )
                # Don't create new entry - return early to prevent dynamic registration
                return
            else:
                # No pre-registration happened (legacy behavior for backwards compatibility)
                logger.warning(f"No pre-registration for batch '{batch_id}', creating entry dynamically (legacy mode)")
                self.link_states[batch_id][link_id] = {
                    'url': url,
                    'status': 'pending',
                    'started_at': datetime.now().isoformat(),
                }
        else:
            # Link was pre-registered, update started_at if it wasn't set
            if not self.link_states[batch_id][link_id].get('started_at'):
                self.link_states[batch_id][link_id]['started_at'] = datetime.now().isoformat()
        
        state = self.link_states[batch_id][link_id]
        
        # Get old progress before updating (for throttling check)
        old_overall_progress = state.get('overall_progress', 0)
        
        state['current_stage'] = stage
        state['stage_progress'] = stage_progress
        state['overall_progress'] = overall_progress
        state['status_message'] = message
        state['updated_at'] = datetime.now().isoformat()
        
        # Set status based on stage and progress
        # If stage is 'completed' and progress is 100%, mark as completed
        # If stage is 'failed', mark as failed
        # Otherwise, set to 'in-progress' (but preserve existing 'completed' or 'failed' status)
        # CRITICAL: Once a link is 'completed' or 'failed', never change it back to 'in-progress'
        current_status = state.get('status', 'pending')
        normalized_current = self._normalize_status(current_status)
        
        # Protect against overwriting final states
        if normalized_current == 'completed':
            # Link is already completed - do NOT overwrite with progress updates
            # Only allow explicit status update via update_link_status
            logger.debug(
                f"[ProgressService] Link {link_id} already completed, ignoring progress update "
                f"(stage={stage}, progress={overall_progress})"
            )
            return  # Exit early - don't modify completed status
        elif normalized_current == 'failed':
            # Link is already failed - do NOT overwrite
            logger.debug(
                f"[ProgressService] Link {link_id} already failed, ignoring progress update "
                f"(stage={stage}, progress={overall_progress})"
            )
            return  # Exit early - don't modify failed status
        
        # Now safe to update status based on stage/progress
        if stage == 'completed' and overall_progress >= 100.0:
            state['status'] = 'completed'
            state['completed_at'] = datetime.now().isoformat()
            logger.info(f"✅ [ProgressService] Link {link_id} marked as completed (stage={stage}, progress={overall_progress})")
        elif stage == 'failed':
            state['status'] = 'failed'
            state['overall_progress'] = 0.0
            logger.warning(f"❌ [ProgressService] Link {link_id} marked as failed (stage={stage})")
        else:
            # Update to 'in-progress' only if not already in a final state
            state['status'] = 'in-progress'  # Use kebab-case for frontend compatibility
        
        if metadata:
            state['bytes_downloaded'] = metadata.get('bytes_downloaded')
            state['total_bytes'] = metadata.get('total_bytes')
            state['source'] = metadata.get('source')
        
        # Throttle updates: only broadcast if enough time has passed or progress changed significantly
        import time
        update_key = f"{batch_id}:{link_id}"
        current_time = time.time()
        last_time = self.last_update_time.get(update_key, 0)
        progress_changed = abs(overall_progress - old_overall_progress) >= self.progress_change_threshold
        time_elapsed = current_time - last_time >= self.min_update_interval
        
        # CRITICAL: Always track timestamp for race condition detection, even if throttled
        # This ensures confirm_all_scraping_complete can detect recent async activity
        self.last_update_time[update_key] = current_time
        
        # Broadcast if significant change (1%+) or minimum time elapsed (throttling)
        if progress_changed or time_elapsed or overall_progress >= 100:
            await self.ws_manager.broadcast(batch_id, {
                'type': 'scraping:item_progress',
                'link_id': link_id,
                'url': url,
                'stage': stage,
                'stage_progress': stage_progress,
                'overall_progress': overall_progress,
                'message': message,
                'metadata': metadata or {},
                'timestamp': datetime.now().isoformat()
            })
            logger.debug(f"Progress update: batch={batch_id}, link={link_id}, stage={stage}, progress={overall_progress:.1f}%")
        
        # Update batch-level status periodically (every 5% change or completion)
        if int(overall_progress) % 5 == 0 or overall_progress >= 100:
            await self._update_batch_status(batch_id)
    
    async def update_link_status(
        self,
        batch_id: str,
        link_id: str,
        url: str,
        status: str,  # 'in-progress', 'completed', 'failed' (accepts both formats)
        error: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """
        Update link status and broadcast.
        
        Args:
            batch_id: Batch ID
            link_id: Link ID
            url: Link URL
            status: New status (will be normalized to kebab-case)
            error: Error message if failed
            metadata: Additional metadata (word_count, etc.)
        """
        # Normalize status to kebab-case for consistency
        normalized_status = self._normalize_status(status)
        
        # Update state
        if batch_id not in self.link_states:
            self.link_states[batch_id] = {}
        
        # CRITICAL: Only update pre-registered entries - do NOT create new ones dynamically
        if link_id not in self.link_states[batch_id]:
            # Check if this batch has expected totals set (pre-registration happened)
            if batch_id in self.expected_totals:
                # Log all registered link_ids for debugging
                registered_ids = list(self.link_states[batch_id].keys())
                logger.error(
                    f"❌ CRITICAL: Attempted to update status for unregistered link_id '{link_id}' in batch '{batch_id}'. "
                    f"Expected total: {self.expected_totals[batch_id]}, Registered: {len(self.link_states[batch_id])}. "
                    f"Status being set: {status}. "
                    f"This may indicate a link_id format mismatch (e.g., missing '_comments' suffix). "
                    f"Registered link_ids: {registered_ids[:10]}{'...' if len(registered_ids) > 10 else ''}"
                )
                # Don't create new entry - return early to prevent dynamic registration
                return
            else:
                # No pre-registration happened (legacy behavior for backwards compatibility)
                logger.warning(f"No pre-registration for batch '{batch_id}', creating entry dynamically (legacy mode)")
                self.link_states[batch_id][link_id] = {
                    'url': url,
                    'started_at': datetime.now().isoformat(),
                }
        
        state = self.link_states[batch_id][link_id]
        old_status = state.get('status', 'unknown')
        old_normalized = self._normalize_status(old_status)
        
        # CRITICAL: Protect against changing from 'completed' back to any other status
        if old_normalized == 'completed' and normalized_status != 'completed':
            logger.error(
                f"❌ CRITICAL: Attempted to change link_id '{link_id}' from 'completed' to '{normalized_status}' "
                f"in batch '{batch_id}'. This is a bug - completed status should never be overwritten. "
                f"Rejecting status change."
            )
            return  # Exit early - don't overwrite completed status
        
        # CRITICAL: Protect against changing from 'failed' back to 'in-progress' or 'pending'
        # (Allow changing failed -> completed in case of retry, but log it)
        if old_normalized == 'failed' and normalized_status in ['in-progress', 'pending']:
            logger.warning(
                f"⚠️ Attempted to change link_id '{link_id}' from 'failed' to '{normalized_status}' "
                f"in batch '{batch_id}'. Rejecting status change (failed links should not be retried without explicit reset)."
            )
            return  # Exit early - don't overwrite failed status
        
        # Safe to update status
        state['status'] = normalized_status  # Store normalized status
        state['updated_at'] = datetime.now().isoformat()
        
        if normalized_status == 'completed':
            state['completed_at'] = datetime.now().isoformat()
            state['overall_progress'] = 100.0
            state['stage_progress'] = 100.0
            logger.info(
                f"✅ [ProgressService] Updated link_id '{link_id}' status: {old_status} -> {normalized_status} "
                f"(batch={batch_id}, word_count={metadata.get('word_count', 0) if metadata else 'N/A'})"
            )
        elif normalized_status == 'failed':
            state['error_message'] = error
            state['overall_progress'] = 0.0
            logger.warning(
                f"❌ [ProgressService] Updated link_id '{link_id}' status: {old_status} -> {normalized_status} "
                f"(batch={batch_id}, error={error})"
            )
        else:
            logger.debug(
                f"[ProgressService] Updated link_id '{link_id}' status: {old_status} -> {normalized_status} "
                f"(batch={batch_id})"
            )
        
        if metadata:
            state.update(metadata)
        
        # Broadcast with normalized status
        await self.ws_manager.broadcast(batch_id, {
            'type': 'scraping:item_update',
            'link_id': link_id,
            'url': url,
            'status': normalized_status,  # Send normalized status to frontend
            'error': error,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        
        # Always update batch status on status change
        await self._update_batch_status(batch_id)
    
    async def _update_batch_status(self, batch_id: str):
        """Calculate and broadcast batch-level status."""
        if batch_id not in self.link_states:
            return
        
        links = self.link_states[batch_id]
        
        # Get expected total (set at initialization) - this is the actual target
        expected_total = self._get_or_recover_expected_total(batch_id)
        total_registered = len(links)
        
        # Log if expected_total is not set (for debugging)
        if expected_total == 0 and batch_id in self.expected_totals:
            logger.warning(f"Expected total is 0 for batch {batch_id} (this should not happen if initialize_expected_links was called)")
        elif expected_total == 0:
            logger.debug(f"Expected total not set yet for batch {batch_id} (will use registered count as fallback)")
        
        # Use expected_total for completion rate calculation (the actual target)
        # Fall back to registered count if expected_total not set yet
        total_for_calculation = expected_total if expected_total > 0 else total_registered
        
        # CRITICAL: Do NOT overwrite expected total - if len(links) > expected_total, it indicates a bug
        # (e.g., link_id format mismatch causing duplicate registrations)
        if expected_total > 0 and total_registered > expected_total:
            logger.error(
                f"CRITICAL: Expected total ({expected_total}) is less than registered links ({total_registered}) for batch '{batch_id}'. "
                f"This indicates a bug - likely link_id format mismatches causing duplicate registrations. "
                f"NOT overwriting expected total. Please investigate link_id mapping."
            )
            # Log all registered link_ids for debugging
            registered_ids = list(links.keys())
            logger.debug(f"Registered link_ids: {registered_ids}")
            # Use expected total (don't overwrite) - this ensures we wait for all expected processes
            # The extra registered links are likely duplicates that should be fixed
        # Count with normalized status (handle both old snake_case and new kebab-case)
        completed = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'completed')
        failed = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'failed')
        in_progress = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'in-progress')
        
        # DEBUG: Track completed count changes to detect decreases
        if not hasattr(self, '_last_completed_count'):
            self._last_completed_count = {}
        last_completed = self._last_completed_count.get(batch_id, completed)
        if completed < last_completed:
            logger.error(
                f"❌ CRITICAL: Completed count DECREASED for batch {batch_id}: {last_completed} -> {completed}. "
                f"This indicates a bug - completed status should never decrease. "
                f"Total registered: {total_registered}, Failed: {failed}, InProgress: {in_progress}"
            )
            # Log all link statuses for debugging
            for link_id, state in links.items():
                status = self._normalize_status(state.get('status', 'pending'))
                logger.debug(f"  Link {link_id}: status={status}, stage={state.get('current_stage', 'N/A')}")
        self._last_completed_count[batch_id] = completed
        
        # Calculate overall progress and completion rate using expected_total
        # CRITICAL: Only mark as 100% complete if we have a valid expected_total
        # and all expected tasks are actually completed/failed
        if total_for_calculation > 0:
            overall_progress = ((completed + failed) / total_for_calculation) * 100.0
            completion_rate = (completed + failed) / total_for_calculation
            # Only set is_100_percent to True if:
            # 1. We have a valid expected_total (not 0, not None)
            # 2. All expected tasks are completed or failed
            # This prevents premature phase 0 start when expected_total is not set correctly
            if expected_total > 0:
                # Use integer comparison to avoid floating point precision issues
                is_100_percent = (completed + failed) >= expected_total
            else:
                # No valid expected_total - cannot determine if 100% complete
                is_100_percent = False
                logger.warning(
                    f"Cannot determine 100% completion for batch {batch_id}: expected_total={expected_total}, "
                    f"completed={completed}, failed={failed}, total_registered={total_registered}"
                )
        else:
            overall_progress = 0.0
            completion_rate = 0.0
            is_100_percent = False
        
        # Build items list with normalized status
        items = []
        for link_id, state in links.items():
            # Normalize status before sending to frontend
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            items.append({
                'link_id': link_id,
                'url': state.get('url', ''),
                'status': normalized_status,  # Send normalized status to frontend
                'current_stage': state.get('current_stage'),
                'stage_progress': state.get('stage_progress', 0),
                'overall_progress': state.get('overall_progress', 0),
                'status_message': state.get('status_message'),
                'error': state.get('error_message'),
                'started_at': state.get('started_at'),
                'completed_at': state.get('completed_at'),
            })
        
        # Broadcast - ALWAYS include expected_total, even if 0 (frontend needs to know it's not set yet)
        # Force expected_total to be an integer (not None) - use 0 if not set
        # Never broadcast 0 if we have registered links - fall back to registered count
        fallback_total = total_registered if total_registered > 0 else 0
        expected_total_value = int(expected_total) if expected_total and expected_total > 0 else fallback_total
        if expected_total_value > 0 and self.expected_totals.get(batch_id) != expected_total_value:
            logger.debug(
                f"[RECOVER] Syncing expected_total for batch {batch_id}: "
                f"stored={self.expected_totals.get(batch_id)}, broadcast={expected_total_value}"
            )
            self.expected_totals[batch_id] = expected_total_value
        
        status_message = {
            'type': 'scraping:status',
            'batch_id': batch_id,
            'total': total_registered,  # Keep for backward compatibility (started processes count)
            'expected_total': expected_total_value,  # ALWAYS include - even if 0 (frontend will handle it)
            'completed': completed,
            'failed': failed,
            'inProgress': in_progress,
            'overall_progress': overall_progress,
            'completion_rate': completion_rate,  # 0.0 to 1.0 (calculated against expected_total)
            'completion_percentage': overall_progress,  # Same as overall_progress, but explicit
            'is_100_percent': is_100_percent,  # boolean flag
            'can_proceed_to_research': is_100_percent,  # explicit flag for research phase
            'items': items,
            'timestamp': datetime.now().isoformat()
        }
        
        # CRITICAL: Verify expected_total is actually in the message
        if 'expected_total' not in status_message:
            logger.error(f"CRITICAL ERROR: expected_total missing from status_message dict! Keys: {list(status_message.keys())}")
        elif status_message['expected_total'] is None:
            logger.error(f"CRITICAL ERROR: expected_total is None in status_message! Setting to 0.")
            status_message['expected_total'] = 0
        
        # Debug log if expected_total is 0
        if expected_total == 0:
            logger.warning(
                f"Sending scraping:status with expected_total=0 for batch {batch_id}. "
                f"This means initialize_expected_links hasn't been called yet or failed. "
                f"Registered links: {total_registered}"
            )
        
        # CRITICAL DEBUG: Log the actual message being sent
        logger.info(
            f"[DEBUG] Broadcasting scraping:status for batch {batch_id}: "
            f"expected_total={status_message.get('expected_total')}, "
            f"total={status_message.get('total')}, "
            f"message_keys={list(status_message.keys())}"
        )
        
        # CRITICAL: Double-check expected_total is in the message before sending
        if 'expected_total' not in status_message:
            logger.error(f"❌ CRITICAL: expected_total MISSING from status_message! Adding it now. Keys: {list(status_message.keys())}")
            status_message['expected_total'] = expected_total_value
        
        # Log the actual JSON that will be sent (first 500 chars)
        import json
        message_json = json.dumps(status_message, ensure_ascii=False)
        logger.info(f"[DEBUG] Message JSON (first 500 chars): {message_json[:500]}")
        
        await self.ws_manager.broadcast(batch_id, status_message)
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Get current batch status."""
        if batch_id not in self.link_states:
            return None
        
        links = self.link_states[batch_id]
        
        # Use expected total if available, otherwise fall back to current count
        total = self.expected_totals.get(batch_id, len(links))
        if total < len(links):
            total = len(links)
            self.expected_totals[batch_id] = total
        
        # Count with normalized status (handle both old snake_case and new kebab-case)
        completed = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'completed')
        failed = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'failed')
        in_progress = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'in-progress')
        
        overall_progress = ((completed + failed) / total * 100.0) if total > 0 else 0.0
        
        items = []
        for link_id, state in links.items():
            # Normalize status before returning
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            items.append({
                'link_id': link_id,
                'url': state.get('url', ''),
                'status': normalized_status,  # Return normalized status
                'current_stage': state.get('current_stage'),
                'stage_progress': state.get('stage_progress', 0),
                'overall_progress': state.get('overall_progress', 0),
                'status_message': state.get('status_message'),
                'error': state.get('error_message'),
                'started_at': state.get('started_at'),
                'completed_at': state.get('completed_at'),
                'source': state.get('source'),
                'word_count': state.get('word_count'),
            })
        
        return {
            'batch_id': batch_id,
            'total': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'overall_progress': overall_progress,
            'links': items
        }
    
    def _calculate_overall_progress(self, source: str, stage: str, stage_progress: float) -> float:
        """
        Calculate overall progress based on source type and current stage.
        
        Different sources have different stages:
        - YouTube: loading → extracting → completed (0% → 100%)
        - Bilibili: loading → downloading (0-50%) → converting (50-60%) → 
                   uploading (60-70%) → transcribing (70-95%) → completed (100%)
        - Article: loading → extracting → completed (0% → 100%)
        """
        stage_weights = {
            'youtube': {
                'loading': (0, 20),
                'extracting': (20, 100),
                'completed': (100, 100)
            },
            'bilibili': {
                'loading': (0, 5),
                'downloading': (5, 50),
                'converting': (50, 60),
                'uploading': (60, 70),
                'transcribing': (70, 95),
                'completed': (100, 100)
            },
            'article': {
                'loading': (0, 20),
                'extracting': (20, 100),
                'completed': (100, 100)
            },
            'reddit': {
                'loading': (0, 20),
                'extracting': (20, 100),
                'completed': (100, 100)
            }
        }
        
        weights = stage_weights.get(source, {'unknown': (0, 100)})
        stage_range = weights.get(stage, (0, 100))
        
        # Interpolate within stage range
        min_progress, max_progress = stage_range
        range_size = max_progress - min_progress
        overall = min_progress + (range_size * stage_progress / 100.0)
        
        return min(100.0, max(0.0, overall))
    
    def is_cancelled(self, batch_id: str) -> bool:
        """Check if batch is cancelled."""
        return self.cancellation_flags.get(batch_id, False)
    
    async def cancel_batch(self, batch_id: str, reason: str = "User cancelled"):
        """
        Cancel a batch operation.
        
        Args:
            batch_id: Batch ID to cancel
            reason: Reason for cancellation
        """
        self.cancellation_flags[batch_id] = True
        
        # Record cancellation info with current state
        cancellation_info = {
            'cancelled_at': datetime.now().isoformat(),
            'reason': reason,
            'state_at_cancellation': self.get_batch_status(batch_id) or {}
        }
        self.cancellation_info[batch_id] = cancellation_info
        
        # Force kill all Playwright browser processes immediately
        try:
            import platform
            import subprocess
            
            logger.info(f"Force killing all Playwright browser processes for batch {batch_id}...")
            
            if platform.system() == 'Windows':
                # Windows: Use PowerShell to find and kill Playwright Chrome processes
                try:
                    # PowerShell command to find and kill Playwright Chrome processes
                    ps_command = '''
                        $ErrorActionPreference = 'SilentlyContinue'
                        Get-Process -Name chrome,chromium -ErrorAction SilentlyContinue | 
                        Where-Object { $_.Path -like '*ms-playwright*' -or $_.Path -like '*playwright*' } | 
                        Stop-Process -Force -ErrorAction SilentlyContinue
                    '''
                    result = subprocess.run(
                        ['powershell', '-Command', ps_command],
                        capture_output=True,
                        timeout=10
                    )
                    # More aggressive: kill chrome processes with specific command line args
                    # This targets Playwright processes more specifically
                    ps_command2 = '''
                        $ErrorActionPreference = 'SilentlyContinue'
                        Get-WmiObject Win32_Process -Filter "name='chrome.exe'" | 
                        Where-Object { $_.CommandLine -like '*ms-playwright*' -or $_.CommandLine -like '*--remote-debugging-port*' } | 
                        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
                    '''
                    subprocess.run(
                        ['powershell', '-Command', ps_command2],
                        capture_output=True,
                        timeout=10
                    )
                    logger.info("Force killed Playwright browser processes on Windows")
                except Exception as e:
                    logger.warning(f"Could not force kill browser processes: {e}")
            else:
                # Linux/Mac: Use pkill
                try:
                    subprocess.run(['pkill', '-f', 'playwright.*chromium'], capture_output=True, timeout=5)
                    subprocess.run(['pkill', '-f', 'ms-playwright'], capture_output=True, timeout=5)
                    logger.info("Force killed Playwright browser processes on Unix")
                except Exception as e:
                    logger.warning(f"Could not force kill browser processes: {e}")
        except Exception as e:
            logger.warning(f"Error force killing browser processes: {e}")
        
        # Broadcast cancellation to all clients
        await self.ws_manager.broadcast(batch_id, {
            'type': 'scraping:cancelled',
            'batch_id': batch_id,
            'reason': reason,
            'state': cancellation_info['state_at_cancellation'],
            'timestamp': cancellation_info['cancelled_at']
        })
        
        logger.info(f"Batch {batch_id} cancelled: {reason}")
    
    def get_cancellation_info(self, batch_id: str) -> Optional[Dict]:
        """Get cancellation information for a batch."""
        return self.cancellation_info.get(batch_id)
    
    def all_links_have_final_status(self, batch_id: str) -> bool:
        """
        Check if all expected links in a batch have final status (completed or failed).
        Uses expected total count to ensure we check all links, not just started ones.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            True if all expected links have final status, False otherwise
        """
        if batch_id not in self.link_states:
            return False
        
        links = self.link_states[batch_id]
        
        # Get expected total (should be set during initialization)
        expected_total = self.expected_totals.get(batch_id)
        if expected_total is not None:
            # If we have an expected total, ensure we have that many links registered
            if len(links) < expected_total:
                logger.debug(f"Only {len(links)} links registered, but expected {expected_total} - not all links have started yet")
                return False
        
        if not links:
            return False
        
        # Check that all registered links have final status
        for link_id, state in links.items():
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            # Check if status is final (completed or failed)
            if normalized_status not in ['completed', 'failed']:
                # Also check if stage is completed and progress is 100% (might not have status updated yet)
                current_stage = state.get('current_stage')
                overall_progress = state.get('overall_progress', 0)
                if not (current_stage == 'completed' and overall_progress >= 100.0):
                    logger.debug(f"Link {link_id} does not have final status: status={normalized_status}, stage={current_stage}, progress={overall_progress}")
                    return False
        
        # If we have expected total and all registered links are final, verify we have all expected links
        if expected_total is not None and len(links) < expected_total:
            logger.debug(f"Only {len(links)} links have final status, but expected {expected_total} total links")
            return False
        
        return True
    
    def get_pending_links_count(self, batch_id: str) -> int:
        """
        Get count of links that don't have final status yet.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            Number of links without final status
        """
        if batch_id not in self.link_states:
            return 0
        
        links = self.link_states[batch_id]
        pending = 0
        
        for link_id, state in links.items():
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            if normalized_status not in ['completed', 'failed']:
                # Also check if stage is completed and progress is 100% (might not have status updated yet)
                current_stage = state.get('current_stage')
                overall_progress = state.get('overall_progress', 0)
                if not (current_stage == 'completed' and overall_progress >= 100.0):
                    pending += 1
        
        return pending
    
    async def confirm_all_scraping_complete(self, batch_id: str) -> Dict:
        """
        Verify that all expected scraping processes are complete.
        This method checks that all expected processes (based on expected_totals) have final status.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            Dict with verification details:
            - confirmed: bool (True if all expected processes have final status)
            - expected_total: int
            - registered_count: int (actual registered processes)
            - completed_count: int
            - failed_count: int
            - pending_count: int
            - missing_processes: List[str] (link_ids that are expected but not registered)
            - timestamp: str (ISO format)
        """
        if batch_id not in self.link_states:
            return {
                'confirmed': False,
                'expected_total': 0,
                'registered_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'pending_count': 0,
                'missing_processes': [],
                'error': 'Batch not found in link_states',
                'timestamp': datetime.now().isoformat()
            }
        
        links = self.link_states[batch_id]
        stored_expected_total = self.expected_totals.get(batch_id)
        expected_total = stored_expected_total if stored_expected_total not in (None, 0) else 0
        registered_count = len(links)

        # Fallback: if we have registered links but no stored expected total, adopt the registered count
        if expected_total == 0 and registered_count > 0:
            if stored_expected_total in (None, 0):
                logger.warning(
                    f"expected_total is {stored_expected_total if stored_expected_total is not None else 'None'} for batch '{batch_id}', "
                    f"but {registered_count} links are registered. Using registered count as expected total."
                )
            expected_total = registered_count

        # Guard: if registered count somehow exceeds stored expected total, align totals to prevent false negatives
        elif expected_total > 0 and registered_count > expected_total:
            logger.warning(
                f"Registered count {registered_count} exceeds expected total {expected_total} for batch '{batch_id}'. "
                f"Adjusting expected total to registered count to maintain consistency."
            )
            expected_total = registered_count

        # Count statuses
        completed_count = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'completed')
        failed_count = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'failed')
        in_progress_count = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'in-progress')
        pending_count = sum(1 for l in links.values() if self._normalize_status(l.get('status', 'pending')) == 'pending')

        total_final = completed_count + failed_count

        # Absolute fallback: if expected_total is still zero (or less) but we have real results,
        # promote the larger of registered_count and total_final as the expected total.
        fallback_floor = max(registered_count, total_final)
        if expected_total <= 0 and fallback_floor > 0:
            adjusted_total = fallback_floor
            logger.warning(
                f"Expected total remained {expected_total} for batch '{batch_id}' despite {registered_count} registered links "
                f"and {total_final} final entries. Adopting {adjusted_total} as expected total."
            )
            expected_total = adjusted_total
        elif expected_total < fallback_floor:
            expected_total = self._get_or_recover_expected_total(
                batch_id, minimum=fallback_floor
            )
        elif expected_total > 0 and total_final > expected_total:
            logger.warning(
                f"Final count {total_final} exceeds expected total {expected_total} for batch '{batch_id}'. "
                f"Adjusting expected total to {total_final}."
            )
            expected_total = total_final

        # Persist any new total so future checks stay consistent
        if expected_total > 0 and expected_total != self.expected_totals.get(batch_id):
            self.expected_totals[batch_id] = expected_total

        # Check if all expected processes are registered
        missing_processes = []
        if expected_total > 0 and registered_count < expected_total:
            # Some expected processes haven't been registered yet
            # We can't identify which ones are missing without tracking expected link_ids
            # So we'll just report the count difference
            missing_count = expected_total - registered_count
            missing_processes = [f"missing_{i}" for i in range(missing_count)]

        # Check if all registered processes have final status
        all_have_final_status = True
        non_final_statuses = []
        for link_id, state in links.items():
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            if normalized_status not in ['completed', 'failed']:
                # Also check if stage is completed and progress is 100% (might not have status updated yet)
                current_stage = state.get('current_stage')
                overall_progress = state.get('overall_progress', 0)
                if not (current_stage == 'completed' and overall_progress >= 100.0):
                    all_have_final_status = False
                    non_final_statuses.append({
                        'link_id': link_id,
                        'status': normalized_status,
                        'stage': current_stage,
                        'progress': overall_progress
                    })
        
        # Calculate completion rate (always use non-zero denominator when data exists)
        effective_expected_total = expected_total if expected_total > 0 else fallback_floor
        completion_rate = (total_final / effective_expected_total) if effective_expected_total > 0 else 0.0
        is_100_percent = completion_rate >= 1.0  # Allow for floating point precision

        if effective_expected_total == 0:
            logger.error(
                f"[CONFIRM] expected_total remains {expected_total} for batch '{batch_id}' "
                f"after reconciliation. registered_count={registered_count}, total_final={total_final}, "
                f"completed={completed_count}, failed={failed_count}, pending={pending_count}, "
                f"stored_expected_total={stored_expected_total}"
            )
            if links:
                logger.error(
                    f"[CONFIRM] Link states snapshot for batch '{batch_id}': "
                    f"{ {link_id: { 'status': self._normalize_status(state.get('status', 'pending')), 'overall_progress': state.get('overall_progress'), 'current_stage': state.get('current_stage') } for link_id, state in list(links.items())[:10]} }"
                )
        
        # Determine the final expected_total to use in result and confirmation logic
        result_expected_total = expected_total if expected_total > 0 else effective_expected_total
        
        # Check for recent progress activity (race condition detection)
        # Some scrapers have async operations that continue after extract() returns
        # We need to wait a grace period after last progress update before confirming
        import time
        current_time = time.time()
        recent_activity_link_ids = []
        grace_period_expired = True
        
        for link_id, state in links.items():
            update_key = f"{batch_id}:{link_id}"
            last_update = self.last_update_time.get(update_key, 0)
            time_since_update = current_time - last_update if last_update > 0 else float('inf')
            
            # If this item is marked as completed but had progress updates recently,
            # it might still have async operations running
            normalized_status = self._normalize_status(state.get('status', 'pending'))
            if normalized_status in ['completed', 'failed']:
                if time_since_update < self.completion_grace_period:
                    grace_period_expired = False
                    recent_activity_link_ids.append({
                        'link_id': link_id,
                        'time_since_update': round(time_since_update, 2),
                        'status': normalized_status
                    })
        
        # Enhanced confirmation check: all expected processes registered AND all have final status 
        # AND 100% completion AND grace period expired (no recent async activity)
        expected_goal = result_expected_total
        confirmed = (
            expected_goal > 0 and
            registered_count >= expected_goal and
            all_have_final_status and
            is_100_percent and
            total_final == expected_goal and  # Explicit equality check
            grace_period_expired  # Wait for async operations to finish
        )
        
        # Detailed logging for debugging
        logger.info(f"[CONFIRM] Checking completion for batch {batch_id}")
        logger.info(
            f"[CONFIRM] Expected total: {result_expected_total}, Registered: {registered_count}, "
            f"Completed: {completed_count}, Failed: {failed_count}, "
            f"In Progress: {in_progress_count}, Pending: {pending_count}"
        )
        if non_final_statuses:
            logger.warning(f"[CONFIRM] Non-final statuses for batch {batch_id}: {non_final_statuses}")
        
        if recent_activity_link_ids:
            logger.info(
                f"[CONFIRM] Recent activity detected for {len(recent_activity_link_ids)} items in batch '{batch_id}': "
                f"{[item['link_id'] for item in recent_activity_link_ids[:5]]}. "
                f"Waiting grace period ({self.completion_grace_period}s) before confirming completion."
            )

        result = {
            'confirmed': confirmed,
            'completion_rate': completion_rate,  # 0.0 to 1.0
            'completion_percentage': completion_rate * 100.0,  # 0.0 to 100.0
            'is_100_percent': is_100_percent,
            'expected_total': result_expected_total,
            'registered_count': registered_count,
            'completed_count': completed_count,
            'failed_count': failed_count,
            'total_final': total_final,  # completed + failed
            'pending_count': pending_count,
            'in_progress_count': in_progress_count,
            'missing_processes': missing_processes,
            'non_final_statuses': non_final_statuses if not confirmed else [],
            'recent_activity': recent_activity_link_ids if not confirmed else [],
            'grace_period_expired': grace_period_expired,
            'timestamp': datetime.now().isoformat()
        }
        
        completion_percentage = completion_rate * 100.0
        
        if confirmed:
            logger.info(
                f"Scraping completion CONFIRMED (100%) for batch '{batch_id}': "
                f"{completion_percentage:.1f}% ({total_final}/{result_expected_total}) - "
                f"{completed_count} completed, {failed_count} failed, "
                f"grace period expired: {grace_period_expired}"
            )
        else:
            reason_parts = []
            if registered_count < expected_goal:
                reason_parts.append(f"registered ({registered_count}) < expected ({expected_goal})")
            if not all_have_final_status:
                reason_parts.append(f"non-final statuses: {len(non_final_statuses)}")
            if not is_100_percent:
                reason_parts.append(f"completion rate: {completion_percentage:.1f}% < 100%")
            if total_final != expected_goal:
                reason_parts.append(f"total_final ({total_final}) != expected ({expected_goal})")
            if not grace_period_expired:
                reason_parts.append(f"recent activity: {len(recent_activity_link_ids)} items")
            
            logger.info(
                f"Scraping completion NOT confirmed for batch '{batch_id}': "
                f"{completion_percentage:.1f}% ({total_final}/{result_expected_total}), "
                f"Reasons: {', '.join(reason_parts) if reason_parts else 'unknown'}"
            )
            if non_final_statuses:
                logger.debug(f"Non-final statuses: {non_final_statuses}")
            if recent_activity_link_ids:
                logger.debug(f"Recent activity: {recent_activity_link_ids}")
        
        return result