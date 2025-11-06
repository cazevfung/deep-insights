"""
Simplified workflow service using proven test functions.

This service uses the working code from tests/ folder directly,
with WebSocket progress callbacks for real-time updates.
"""
from typing import Dict, Optional
from pathlib import Path
import sys
import asyncio
import queue
import time
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import working test functions via backend.lib
from backend.lib import (
    run_all_scrapers,
    run_all_scrapers_direct,  # Direct execution with progress callbacks
    verify_scraper_results,
    run_research_agent,
)
from app.websocket.manager import WebSocketManager
from app.services.progress_service import ProgressService
from app.services.websocket_ui import WebSocketUI


def _run_scrapers_in_thread(progress_callback, batch_id, cancellation_checker=None):
    """
    Wrapper function to run scrapers in a thread with proper Playwright initialization.
    
    This ensures Playwright/Chromium can be launched properly when called from asyncio.to_thread().
    The function runs in a separate thread, so Playwright can initialize its browser process.
    
    Args:
        progress_callback: Progress callback function
        batch_id: Batch ID
        cancellation_checker: Optional function that returns True if cancelled
        
    Returns:
        Result dictionary from run_all_scrapers_direct
    """
    try:
        # Ensure we're in a proper thread context
        import threading
        import os
        current_thread = threading.current_thread()
        logger.info(f"Running scrapers in thread: {current_thread.name} (ID: {current_thread.ident})")
        
        # Log environment info for debugging
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Python executable: {sys.executable}")
        logger.debug(f"Thread name: {current_thread.name}")
        
        # Ensure Playwright can find its browser
        # Check if PLAYWRIGHT_BROWSERS_PATH is set
        playwright_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        if playwright_path:
            logger.debug(f"PLAYWRIGHT_BROWSERS_PATH: {playwright_path}")
        else:
            logger.debug("PLAYWRIGHT_BROWSERS_PATH not set (using default)")
        
        # Run the scrapers - Playwright will initialize in this thread
        logger.info(f"Starting scrapers execution in thread...")
        result = run_all_scrapers_direct(
            progress_callback=progress_callback,
            batch_id=batch_id,
            cancellation_checker=cancellation_checker
        )
        
        logger.info(f"Scrapers completed in thread: {current_thread.name}")
        return result
        
    except Exception as e:
        logger.error(f"Error running scrapers in thread: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


class WorkflowService:
    """
    Simplified workflow service using proven test functions.
    
    This service directly uses the working code from tests/ folder,
    with progress callbacks for real-time WebSocket updates.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.progress_service = ProgressService(websocket_manager)
        # Track link context for progress callbacks
        # Maps batch_id -> scraper_type -> list of {link_id, url}
        self.link_context: Dict[str, Dict[str, list]] = {}
    
    async def _load_link_context(self, batch_id: str):
        """
        Load link context from TestLinksLoader for this batch_id.
        Also pre-registers all expected links in the progress service to ensure accurate total count.
        
        Args:
            batch_id: Batch ID to load links for
        """
        try:
            from tests.test_links_loader import TestLinksLoader
            loader = TestLinksLoader()
            
            # Verify batch_id matches
            loader_batch_id = loader.get_batch_id()
            if loader_batch_id != batch_id:
                logger.warning(f"Batch ID mismatch: loader has {loader_batch_id}, expected {batch_id}")
            
            # Build link context mapping: scraper_type -> list of {link_id, url}
            context: Dict[str, list] = {}
            all_expected_processes = []  # Collect all expected PROCESSES (not just links)
            
            for link_type in ['youtube', 'bilibili', 'reddit', 'article']:
                links = loader.get_links(link_type)
                link_list = [
                    {'link_id': link['id'], 'url': link['url']}
                    for link in links
                ]
                context[link_type] = link_list
                
                # Count expected processes based on link type:
                # - YouTube: transcript + comments = 2 processes per link
                # - Bilibili: transcript + comments = 2 processes per link
                # - Reddit: 1 process per link
                # - Article: 1 process per link
                if link_type in ['youtube', 'bilibili']:
                    # Each link generates 2 processes (transcript + comments)
                    for link_info in link_list:
                        # Transcript process
                        all_expected_processes.append({
                            'link_id': link_info['link_id'],
                            'url': link_info['url'],
                            'scraper_type': link_type,  # 'youtube' or 'bilibili'
                            'process_type': 'transcript'
                        })
                        # Comments process (use modified link_id to avoid collision)
                        all_expected_processes.append({
                            'link_id': f"{link_info['link_id']}_comments",
                            'url': link_info['url'],
                            'scraper_type': f'{link_type}comments',  # 'youtubecomments' or 'bilibilicomments'
                            'process_type': 'comments'
                        })
                else:
                    # Reddit and Article: 1 process per link
                    for link_info in link_list:
                        all_expected_processes.append({
                            'link_id': link_info['link_id'],
                            'url': link_info['url'],
                            'scraper_type': link_type,
                            'process_type': 'transcript'  # or 'article'/'reddit'
                        })
            
            self.link_context[batch_id] = context
            total_links = sum(len(links) for links in context.values())
            total_processes = len(all_expected_processes)
            logger.info(f"Loaded link context for batch {batch_id}: {total_links} links → {total_processes} expected processes")
            
            # Pre-register all expected processes in progress service
            # This ensures total count is accurate from the start, preventing premature completion
            registered_count = self.progress_service.initialize_expected_links(batch_id, all_expected_processes)
            logger.info(f"Pre-registered {registered_count} expected processes in progress tracker for batch {batch_id}")
            
            # Send initial batch status update with correct total
            await self.progress_service._update_batch_status(batch_id)
            
        except Exception as e:
            logger.error(f"Failed to load link context: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Initialize empty context
            self.link_context[batch_id] = {}
    
    def _normalize_scraper_type(self, scraper_type: str) -> str:
        """
        Normalize scraper type to match link types in TestLinksLoader.
        
        Args:
            scraper_type: Scraper type from class name (e.g., 'youtubecomments', 'bilibilicomments')
            
        Returns:
            Normalized type (e.g., 'youtube', 'bilibili')
        """
        # Map comments scrapers to their base types
        if scraper_type == 'youtubecomments':
            return 'youtube'
        elif scraper_type == 'bilibilicomments':
            return 'bilibili'
        # Other types match directly
        return scraper_type
    
    def _find_link_info(self, batch_id: str, scraper_type: str, link_id: Optional[str] = None, url: Optional[str] = None):
        """
        Find link_id and url from context or provided parameters.
        
        Args:
            batch_id: Batch ID
            scraper_type: Scraper type (e.g., 'bilibili', 'youtube', 'youtubecomments')
            link_id: Optional link_id from progress message
            url: Optional url from progress message
            
        Returns:
            Tuple of (link_id, url) or (None, None) if not found
        """
        # If both provided, use them
        if link_id and url:
            return link_id, url
        
        # Normalize scraper type to match link types
        normalized_type = self._normalize_scraper_type(scraper_type)
        
        # Try to find from context
        if batch_id in self.link_context:
            links = self.link_context[batch_id].get(normalized_type, [])
            
            # If link_id provided, find matching url
            if link_id:
                for link in links:
                    if link['link_id'] == link_id:
                        return link_id, link['url']
            
            # If url provided, find matching link_id
            if url:
                for link in links:
                    if link['url'] == url:
                        return link['link_id'], url
            
            # If neither provided, try first link of this type
            if links:
                return links[0]['link_id'], links[0]['url']
        
        # Fallback: generate link_id from scraper_type
        if not link_id:
            link_id = f"{scraper_type}_unknown"
        if not url:
            url = f"unknown_{scraper_type}_url"
        
        return link_id, url
    
    def _create_progress_callback(self, batch_id: str, message_queue: queue.Queue):
        """
        Create a sync progress callback that converts scraper format to ProgressService format.
        
        Args:
            batch_id: Batch ID for messages
            message_queue: Queue to put messages in
            
        Returns:
            Sync callback function
        """
        def progress_callback(message: dict):
            """Sync callback that converts and queues messages."""
            try:
                message_type = message.get('type', '')
                scraper_type = message.get('scraper', 'unknown')
                
                logger.info(f"[WorkflowService] Progress callback received: type={message_type}, scraper={scraper_type}, keys={list(message.keys())}")
                
                # Handle different message types from workflow_direct.py
                if message_type == 'scraping:start_link':
                    # Link just started - set stage based on scraper type
                    stage = 'loading'  # Initial stage for all scrapers
                    progress = 0.0
                    message_text = message.get('message', '')
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # For comments scrapers, append '_comments' to link_id to match pre-registered IDs
                    if scraper_type in ['youtubecomments', 'bilibilicomments']:
                        if callback_link_id and not callback_link_id.endswith('_comments'):
                            callback_link_id = f"{callback_link_id}_comments"
                    
                    logger.info(f"[WorkflowService] Processing scraping:start_link - stage={stage}, link_id={callback_link_id}, url={callback_url}, scraper={scraper_type}")
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # Apply _comments suffix for comments scrapers after finding link info
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                callback_link_id = f"{callback_link_id}_comments"
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type
                        }
                    }
                    message_queue.put_nowait(converted_message)
                    return  # Done processing this message
                    
                elif message_type == 'scraping:complete_link':
                    # Link completed (success or failed)
                    status = message.get('status', 'unknown')
                    if status == 'success':
                        stage = 'completed'
                        progress = 100.0
                    else:
                        stage = 'failed'
                        progress = 0.0
                    
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # For comments scrapers, append '_comments' to link_id to match pre-registered IDs
                    if scraper_type in ['youtubecomments', 'bilibilicomments']:
                        if callback_link_id and not callback_link_id.endswith('_comments'):
                            callback_link_id = f"{callback_link_id}_comments"
                    
                    logger.info(f"[WorkflowService] Processing scraping:complete_link - status={status}, stage={stage}, link_id={callback_link_id}, scraper={scraper_type}")
                    
                    # Extract error message from the message or error field
                    error_msg = message.get('error') or (message.get('message', '').split(' - ')[-1] if ' - ' in message.get('message', '') else None)
                    message_text = message.get('message', '')
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # Apply _comments suffix for comments scrapers after finding link info
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                callback_link_id = f"{callback_link_id}_comments"
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type
                        }
                    }
                    message_queue.put_nowait(converted_message)
                    
                    # Update link status for both success and failed links
                    # This ensures frontend receives completion notifications
                    if status == 'success':
                        # Queue a status update for successful links
                        status_message = {
                            'action': 'update_link_status',
                            'batch_id': callback_batch_id,
                            'link_id': callback_link_id,
                            'url': callback_url,
                            'status': 'completed',
                            'error': None,
                            'metadata': {
                                'bytes_downloaded': bytes_downloaded,
                                'total_bytes': total_bytes,
                                'source': scraper_type
                            }
                        }
                        try:
                            message_queue.put_nowait(status_message)
                        except queue.Full:
                            pass
                    elif status == 'failed':
                        # Queue a status update for failed links
                        status_message = {
                            'action': 'update_link_status',
                            'batch_id': callback_batch_id,
                            'link_id': callback_link_id,
                            'url': callback_url,
                            'status': 'failed',
                            'error': error_msg or message_text
                        }
                        try:
                            message_queue.put_nowait(status_message)
                        except queue.Full:
                            pass
                    return  # Done processing this message
                    
                elif message_type in ['scraping:start', 'scraping:discover', 'scraping:complete', 'scraping:start_type']:
                    # Batch-level messages - don't convert to link progress, just broadcast
                    # These don't have link_id/url, so skip progress conversion
                    logger.info(f"[WorkflowService] Handling batch-level message: {message_type}")
                    try:
                        # Broadcast directly (these are handled by the frontend)
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for batch-level messages
                
                elif message_type == 'scraping:verify_completion':
                    # Request from scraping service to verify and send confirmation
                    # This is called after scraping:complete to ensure all processes are done
                    logger.info(f"[WorkflowService] Verifying scraping completion for batch {batch_id}")
                    try:
                        # Schedule async verification (can't await in sync callback)
                        # We'll queue a special action that the async processor will handle
                        message_queue.put_nowait({
                            'action': 'verify_completion',
                            'batch_id': batch_id
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further - async handler will verify
                
                elif message_type == 'scraping:all_complete_confirmed':
                    # Confirmation signal - broadcast and mark as received
                    logger.info(f"[WorkflowService] Received scraping completion confirmation for batch {batch_id}")
                    try:
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for confirmation messages
                
                elif message_type.startswith('research:'):
                    # Research-related messages are batch-level, not link-level
                    # Don't convert to link progress - broadcast directly
                    logger.info(f"[WorkflowService] Handling research message: {message_type}")
                    try:
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for research messages
                    
                else:
                    # Direct progress report from scraper (has stage field)
                    # Or unknown message type - log it for debugging
                    if not message_type:
                        logger.warning(f"[WorkflowService] Received message without type field: {list(message.keys())}")
                    else:
                        logger.info(f"[WorkflowService] Handling unknown message type: {message_type}")
                    
                    stage = message.get('stage', 'unknown')
                    progress = message.get('progress', 0.0)
                    message_text = message.get('message', '')
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # For comments scrapers, append '_comments' to link_id to match pre-registered IDs
                    if scraper_type in ['youtubecomments', 'bilibilicomments']:
                        if callback_link_id and not callback_link_id.endswith('_comments'):
                            callback_link_id = f"{callback_link_id}_comments"
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # Apply _comments suffix for comments scrapers after finding link info
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                callback_link_id = f"{callback_link_id}_comments"
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type
                        }
                    }
                    message_queue.put_nowait(converted_message)
            except queue.Full:
                logger.warning(f"Progress queue full, dropping message: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Error in progress callback: {e}", exc_info=True)
        
        return progress_callback
    
    async def wait_for_scraping_confirmation(
        self,
        progress_queue: queue.Queue,
        batch_id: str,
        max_wait_seconds: float = 5.0,
        check_interval: float = 0.5
    ) -> Dict:
        """
        Wait for scraping:all_complete_confirmed signal from scraping service.
        
        Args:
            progress_queue: Queue to check for confirmation message
            batch_id: Batch ID to wait for
            max_wait_seconds: Maximum time to wait (default: 60 seconds)
            check_interval: Time between checks (default: 0.5 seconds)
            
        Returns:
            Dict with confirmation details if received, or None if timeout
        """
        start_time = time.time()
        last_log_time = 0
        logger.info(f"Waiting for scraping completion confirmation for batch {batch_id}...")
        
        # Also check progress service directly as fallback
        confirmation_received = False
        confirmation_data = None
        
        while time.time() - start_time < max_wait_seconds:
            # Check queue for confirmation message
            try:
                # Peek at queue without removing items
                queue_items = []
                temp_items = []
                while True:
                    try:
                        item = progress_queue.get_nowait()
                        temp_items.append(item)
                        if item.get('action') == 'broadcast':
                            message = item.get('message', {})
                            if message.get('type') == 'scraping:all_complete_confirmed':
                                confirmation_received = True
                                confirmation_data = message
                                logger.info(f"Received scraping completion confirmation for batch {batch_id}")
                        queue_items.append(item)
                    except queue.Empty:
                        break
                
                # Put items back
                for item in queue_items:
                    try:
                        progress_queue.put_nowait(item)
                    except queue.Full:
                        pass
                
                if confirmation_received:
                    break
            except Exception as e:
                logger.debug(f"Error checking queue for confirmation: {e}")
            
            # Fallback: Check progress service directly
            if not confirmation_received:
                try:
                    confirmation_result = await self.progress_service.confirm_all_scraping_complete(batch_id)
                    if confirmation_result.get('confirmed'):
                        confirmation_received = True
                        confirmation_data = {
                            'type': 'scraping:all_complete_confirmed',
                            'batch_id': batch_id,
                            **confirmation_result
                        }
                        logger.info(f"Confirmed scraping completion via direct check for batch {batch_id}")
                        break
                except Exception as e:
                    logger.debug(f"Error checking completion directly: {e}")
            
            # Log progress periodically
            elapsed = time.time() - start_time
            if int(elapsed) > last_log_time:
                last_log_time = int(elapsed)
                pending_count = self.progress_service.get_pending_links_count(batch_id)
                logger.debug(
                    f"Waiting for confirmation: elapsed={elapsed:.1f}s, "
                    f"pending_links={pending_count}, queue_size={progress_queue.qsize()}"
                )
            
            await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        
        if confirmation_received and confirmation_data:
            logger.info(
                f"Scraping completion confirmed for batch {batch_id} after {elapsed:.2f}s: "
                f"{confirmation_data.get('completed_count', 0)} completed, "
                f"{confirmation_data.get('failed_count', 0)} failed out of "
                f"{confirmation_data.get('expected_total', 0)} expected"
            )
            return confirmation_data
        else:
            # Timeout - check final status
            logger.warning(
                f"Timeout waiting for scraping confirmation after {elapsed:.2f}s for batch {batch_id}. "
                f"Checking final status..."
            )
            confirmation_result = await self.progress_service.confirm_all_scraping_complete(batch_id)
            if confirmation_result.get('confirmed'):
                logger.info(f"Scraping completion confirmed via final check for batch {batch_id}")
                return {
                    'type': 'scraping:all_complete_confirmed',
                    'batch_id': batch_id,
                    **confirmation_result
                }
            else:
                logger.warning(
                    f"Scraping completion NOT confirmed for batch {batch_id}: "
                    f"{confirmation_result.get('registered_count', 0)}/{confirmation_result.get('expected_total', 0)} registered, "
                    f"{confirmation_result.get('completed_count', 0)} completed, "
                    f"{confirmation_result.get('failed_count', 0)} failed"
                )
                return None
    
    async def _wait_for_status_updates(
        self,
        message_queue: queue.Queue,
        batch_id: str,
        max_wait_seconds: float = 30.0,
        check_interval: float = 0.2
    ) -> bool:
        """
        Wait for all queued status updates to be processed.
        
        Args:
            message_queue: Queue to check for remaining messages
            batch_id: Batch ID to check status for
            max_wait_seconds: Maximum time to wait (default: 30 seconds)
            check_interval: Time between checks (default: 0.2 seconds)
            
        Returns:
            True if all links have final status, False if timeout
        """
        start_time = time.time()
        last_log_time = 0
        logger.info(f"Waiting for status updates to complete for batch {batch_id}...")
        
        while time.time() - start_time < max_wait_seconds:
            # Check if queue is empty (or has only non-status messages)
            queue_empty = True
            queue_size = 0
            try:
                # Check queue size (approximate)
                queue_size = message_queue.qsize()
                if queue_size > 0:
                    # Check if there are status update messages
                    # We can't peek, so we'll check by trying to get one
                    # But we'll put it back if it's not a status update
                    try:
                        test_message = message_queue.get_nowait()
                        if test_message.get('action') in ['update_link_progress', 'update_link_status']:
                            # Put it back - it's a status update that needs processing
                            message_queue.put_nowait(test_message)
                            queue_empty = False
                        else:
                            # Put it back - it's not a status update
                            message_queue.put_nowait(test_message)
                            queue_empty = True
                    except queue.Empty:
                        queue_empty = True
                else:
                    queue_empty = True
            except Exception as e:
                logger.warning(f"Error checking queue: {e}")
                queue_empty = True
            
            # Check if all links have final status
            all_final = self.progress_service.all_links_have_final_status(batch_id)
            
            if queue_empty and all_final:
                elapsed = time.time() - start_time
                logger.info(f"All status updates processed in {elapsed:.2f}s for batch {batch_id}")
                return True
            
            # Log progress periodically (every second)
            elapsed = time.time() - start_time
            if int(elapsed) > last_log_time:
                last_log_time = int(elapsed)
                pending_count = self.progress_service.get_pending_links_count(batch_id)
                logger.debug(f"Waiting for status updates: queue_size={queue_size}, pending_links={pending_count}, elapsed={elapsed:.1f}s")
            
            await asyncio.sleep(check_interval)
        
        # Timeout - check final status
        elapsed = time.time() - start_time
        pending_count = self.progress_service.get_pending_links_count(batch_id)
        all_final = self.progress_service.all_links_have_final_status(batch_id)
        
        if all_final:
            logger.info(f"All status updates processed (after timeout) in {elapsed:.2f}s for batch {batch_id}")
            return True
        else:
            logger.warning(f"Timeout waiting for status updates after {elapsed:.2f}s for batch {batch_id}: {pending_count} links still pending")
            # Force update batch status to ensure frontend has latest state
            await self.progress_service._update_batch_status(batch_id)
            return False
    
    async def _process_progress_queue(self, message_queue: queue.Queue, batch_id: str):
        """
        Process messages from queue and call ProgressService.
        
        Args:
            message_queue: Queue to poll for messages
            batch_id: Batch ID for broadcasting
        """
        max_retries = 3
        retry_delay = 0.5
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            try:
                # Try to get message (non-blocking)
                try:
                    message = message_queue.get_nowait()
                    consecutive_errors = 0  # Reset error counter on success
                    
                    # Check if this is a ProgressService update action
                    if message.get('action') == 'update_link_progress':
                        # Retry logic for progress updates
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Call ProgressService.update_link_progress()
                                await self.progress_service.update_link_progress(
                                    batch_id=message['batch_id'],
                                    link_id=message['link_id'],
                                    url=message['url'],
                                    stage=message['stage'],
                                    stage_progress=message['stage_progress'],
                                    overall_progress=message['overall_progress'],
                                    message=message['message'],
                                    metadata=message.get('metadata')
                                )
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Progress update failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Progress update failed after {max_retries} attempts: {e}")
                                    # Don't re-queue to avoid infinite loops - log and move on
                    
                    elif message.get('action') == 'update_link_status':
                        # Retry logic for status updates
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Call ProgressService.update_link_status()
                                await self.progress_service.update_link_status(
                                    batch_id=message['batch_id'],
                                    link_id=message['link_id'],
                                    url=message['url'],
                                    status=message['status'],
                                    error=message.get('error'),
                                    metadata=message.get('metadata')
                                )
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Status update failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Status update failed after {max_retries} attempts: {e}")
                                    # Don't re-queue to avoid infinite loops - log and move on
                    
                    elif message.get('action') == 'verify_completion':
                        # Verify scraping completion and send confirmation signal
                        verify_batch_id = message.get('batch_id', batch_id)
                        logger.info(f"Verifying scraping completion for batch {verify_batch_id}")
                        try:
                            # Wait a bit for any pending status updates
                            await asyncio.sleep(0.5)
                            
                            # Verify completion
                            confirmation_result = await self.progress_service.confirm_all_scraping_complete(verify_batch_id)
                            
                            # Send confirmation signal
                            confirmation_message = {
                                'type': 'scraping:all_complete_confirmed',
                                'batch_id': verify_batch_id,
                                **confirmation_result
                            }
                            
                            # Broadcast confirmation
                            await self.ws_manager.broadcast(verify_batch_id, confirmation_message)
                            
                            # Also queue it for the wait_for_scraping_confirmation to pick up
                            try:
                                message_queue.put_nowait({
                                    'action': 'broadcast',
                                    'message': confirmation_message
                                })
                            except queue.Full:
                                pass
                            
                            logger.info(
                                f"Sent scraping completion confirmation for batch {verify_batch_id}: "
                                f"confirmed={confirmation_result.get('confirmed')}"
                            )
                        except Exception as e:
                            logger.error(f"Error verifying completion for batch {verify_batch_id}: {e}", exc_info=True)
                    
                    elif message.get('action') == 'broadcast':
                        # Broadcast batch-level messages directly
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Broadcast the nested message
                                await self.ws_manager.broadcast(batch_id, message.get('message', message))
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Broadcast failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Broadcast failed after {max_retries} attempts: {e}")
                    
                    else:
                        # Retry logic for other messages (with type field)
                        if 'type' in message:
                            retry_count = 0
                            success = False
                            
                            while retry_count < max_retries and not success:
                                try:
                                    # Broadcast messages with type field directly
                                    await self.ws_manager.broadcast(batch_id, message)
                                    success = True
                                except Exception as e:
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        logger.warning(f"Broadcast failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                        await asyncio.sleep(retry_delay)
                                    else:
                                        logger.error(f"Broadcast failed after {max_retries} attempts: {e}")
                        else:
                            # Skip messages without type or action (internal messages)
                            # Also skip messages with action that aren't handled above
                            if message.get('action'):
                                logger.debug(f"Skipping unhandled action message: {message.get('action')}, keys: {list(message.keys())}")
                            else:
                                logger.debug(f"Skipping message without type or action: {message.keys()}")
                        
                except queue.Empty:
                    # No message, wait a bit
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error processing progress queue (consecutive errors: {consecutive_errors}): {e}")
                
                # If too many consecutive errors, wait longer before retrying
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), waiting longer before retry")
                    await asyncio.sleep(1.0)
                    consecutive_errors = 0  # Reset after waiting
                else:
                    await asyncio.sleep(0.1)
    
    async def run_workflow(self, batch_id: str) -> Dict:
        """
        Run full workflow using proven test functions with progress updates.
        
        Args:
            batch_id: Batch ID to process
            
        Returns:
            Result dictionary from the workflow
        """
        try:
            # Check for cancellation before starting
            if self.progress_service.is_cancelled(batch_id):
                logger.info(f"Batch {batch_id} was cancelled before workflow started")
                return {'success': False, 'error': 'Cancelled by user'}
            
            # Load link context for this batch
            await self._load_link_context(batch_id)
            
            # Create progress queue for thread-safe communication
            progress_queue = queue.Queue()
            progress_callback = self._create_progress_callback(batch_id, progress_queue)
            
            # Start progress processor task
            progress_task = asyncio.create_task(
                self._process_progress_queue(progress_queue, batch_id)
            )
            
            try:
                # Step 1: Run all scrapers (using proven test function)
                logger.info(f"Starting scrapers for batch: {batch_id}")
                
                # Notify frontend that we're in scraping phase
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:phase_change",
                    "phase": "scraping",
                    "phase_name": "抓取进度",
                    "message": "开始抓取内容",
                })
                
                # Check cancellation before scraping
                if self.progress_service.is_cancelled(batch_id):
                    logger.info(f"Batch {batch_id} was cancelled before scraping")
                    return {'success': False, 'error': 'Cancelled by user'}
                
                # Use direct execution to pass progress callbacks to scrapers
                # Run in thread pool - Playwright needs to be initialized in the thread
                # Note: Playwright browser processes are created in the thread, so this should work
                scrapers_result = await asyncio.to_thread(
                    _run_scrapers_in_thread,
                    progress_callback=progress_callback,
                    batch_id=batch_id,
                    cancellation_checker=lambda: self.progress_service.is_cancelled(batch_id)
                )
                
                # Check cancellation after scraping
                if self.progress_service.is_cancelled(batch_id):
                    logger.info(f"Batch {batch_id} was cancelled during scraping")
                    cancellation_info = self.progress_service.get_cancellation_info(batch_id)
                    return {
                        'success': False,
                        'error': 'Cancelled by user',
                        'cancellation_info': cancellation_info
                    }
                
                if not scrapers_result.get("success"):
                    logger.error(f"Scrapers failed: {scrapers_result}")
                    raise Exception("Scrapers failed")
                
                logger.info(f"Scraping complete: {scrapers_result.get('passed', 0)}/{scrapers_result.get('total', 0)} succeeded")
                
                # Wait for all status updates to be processed before transitioning
                # This ensures all links have final status before research phase starts
                logger.info(f"Waiting for status updates to complete for batch {batch_id}...")
                status_wait_start = time.time()
                all_status_complete = await self._wait_for_status_updates(progress_queue, batch_id, max_wait_seconds=30.0)
                status_wait_elapsed = time.time() - status_wait_start
                logger.info(f"Status updates wait completed in {status_wait_elapsed:.2f}s for batch {batch_id}")
                
                # Force a final batch status update to ensure frontend has accurate state
                await self.progress_service._update_batch_status(batch_id)
                
                # CRITICAL: Wait for explicit confirmation signal from scraping service
                # This ensures all expected processes (not just started ones) are complete
                logger.info(f"Waiting for scraping completion confirmation for batch {batch_id}...")
                confirmation = await self.wait_for_scraping_confirmation(progress_queue, batch_id, max_wait_seconds=60.0)
                
                if not confirmation or not confirmation.get('confirmed'):
                    # Confirmation not received or not confirmed
                    if confirmation:
                        logger.error(
                            f"Scraping completion NOT confirmed for batch {batch_id}: "
                            f"Expected {confirmation.get('expected_total', 0)}, "
                            f"Registered {confirmation.get('registered_count', 0)}, "
                            f"Completed {confirmation.get('completed_count', 0)}, "
                            f"Failed {confirmation.get('failed_count', 0)}, "
                            f"Pending {confirmation.get('pending_count', 0)}, "
                            f"In Progress {confirmation.get('in_progress_count', 0)}"
                        )
                        if confirmation.get('non_final_statuses'):
                            logger.error(f"Non-final statuses: {confirmation.get('non_final_statuses')}")
                    else:
                        logger.error(f"Scraping completion confirmation timeout for batch {batch_id}")
                    
                    # Don't proceed to research phase - this is a critical error
                    raise Exception(
                        f"Scraping completion not confirmed for batch {batch_id}. "
                        f"Cannot proceed to research phase until all expected processes complete."
                    )
                
                logger.info(
                    f"Scraping completion CONFIRMED for batch {batch_id}: "
                    f"{confirmation.get('completed_count', 0)} completed, "
                    f"{confirmation.get('failed_count', 0)} failed out of "
                    f"{confirmation.get('expected_total', 0)} expected processes"
                )
                
                # Step 2: Verify scraper results (using proven test function)
                logger.info(f"Verifying scraper results for batch: {batch_id}")
                
                verified = await asyncio.to_thread(
                    verify_scraper_results,
                    batch_id,
                    progress_callback=progress_callback
                )
                
                if not verified:
                    await self.ws_manager.broadcast(batch_id, {
                        "type": "error",
                        "phase": "verification",
                        "message": "抓取结果验证失败",
                    })
                    raise Exception("Scraper results verification failed")
                
                # Step 3: Run research agent (using proven test function)
                logger.info(f"Starting research agent for batch: {batch_id}")
                
                # NOW send phase change (after all scraping status is finalized)
                # This ensures frontend has received all status updates before Research Agent tab appears
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:phase_change",
                    "phase": "research",
                    "phase_name": "研究代理",
                    "message": "开始研究阶段",
                })
                
                # Create UI with WebSocket callbacks and main event loop reference
                main_loop = asyncio.get_running_loop()
                ui = WebSocketUI(self.ws_manager, batch_id, main_loop=main_loop)
                
                # Register UI instance with WebSocket manager for user input delivery
                self.ws_manager.register_ui(batch_id, ui)
                
                # Notify UI that research is starting
                ui.notify_phase_change("research", "研究代理")
                
                # Run research agent with progress callbacks
                result = await asyncio.to_thread(
                    run_research_agent,
                    batch_id,
                    ui=ui,
                    progress_callback=progress_callback
                )
                
                if not result:
                    raise Exception("Research agent failed")
                
                await self.ws_manager.broadcast(batch_id, {
                    "type": "workflow:complete",
                    "batch_id": batch_id,
                    "result": result,
                })
                
                return result
                
            finally:
                # Unregister UI instance when workflow completes
                self.ws_manager.unregister_ui(batch_id)
                # Cancel progress processor (will finish processing remaining messages)
                progress_task.cancel()
                try:
                    await asyncio.wait_for(progress_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                # Process any remaining messages (only broadcast if they have a 'type' field)
                # Skip ALL internal action messages (update_link_progress, update_link_status, etc.)
                while True:
                    try:
                        message = progress_queue.get_nowait()
                        # Only broadcast messages with 'type' field (WebSocket messages)
                        # Skip ALL internal action messages - they should be processed by ProgressService, not broadcast
                        if message.get('action') in ['update_link_progress', 'update_link_status']:
                            # These are internal messages - skip them (they should have been processed already)
                            logger.debug(f"Skipping internal action message in cleanup: {message.get('action')}")
                            continue
                        elif 'type' in message:
                            await self.ws_manager.broadcast(batch_id, message)
                        elif message.get('action') == 'broadcast':
                            # Handle broadcast action messages
                            await self.ws_manager.broadcast(batch_id, message.get('message', message))
                    except queue.Empty:
                        break
            
        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            error_message = str(e)
            
            # Provide more detailed error messages
            if "Research agent failed" in error_message or "prompt_user" in error_message.lower():
                detailed_message = f"工作流错误: 研究代理失败 - 可能是用户输入超时或连接问题。错误详情: {error_message}"
            else:
                detailed_message = f"工作流错误: {error_message}"
            
            await self.ws_manager.broadcast(batch_id, {
                "type": "error",
                "phase": "workflow",
                "message": detailed_message,
            })
            raise


