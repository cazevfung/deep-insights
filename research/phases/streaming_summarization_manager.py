"""Streaming Summarization Manager - Processes items as they finish scraping."""

import json
import time
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Any, List, Optional, Set
from loguru import logger
from core.config import Config

from research.summarization.content_summarizer import ContentSummarizer
from research.phases.progress_tracker import ProactiveProgressTracker, ItemState


class StreamingSummarizationManager:
    """
    Manages streaming summarization pipeline.
    
    Processes items as they finish scraping, rather than waiting for all scraping to complete.
    """
    
    def __init__(self, client, config, ui, session, batch_id: str):
        """
        Initialize streaming summarization manager.
        
        Args:
            client: QwenStreamingClient instance
            config: Config instance
            ui: UI interface for progress updates
            session: ResearchSession instance
            batch_id: Batch identifier
        """
        self.client = client
        self.config = config
        self.ui = ui
        self.session = session
        self.batch_id = batch_id
        
        # Initialize summarizer
        self.summarizer = ContentSummarizer(client=client, config=config, ui=ui)
        
        # State tracking
        self.item_states: Dict[str, Dict[str, Any]] = {}  # {link_id: {'scraped': bool, 'summarized': bool, 'data': dict, 'error': str}}
        self.summarization_queue = Queue()
        self.expected_items: Set[str] = set()  # All link_ids we expect
        self.completed_lock = threading.Lock()
        
        # FIX 4: Track items being processed for cancellation support
        self.items_in_queue: Set[str] = set()  # Items currently in queue
        self.items_processing: Set[str] = set()  # Items currently being processed by workers
        self.cancelled_items: Set[str] = set()  # Items that have been cancelled
        
        # Worker pool
        self.workers: List[threading.Thread] = []
        self.num_workers = 8
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.summaries_created = 0
        self.summaries_reused = 0
        self.summaries_failed = 0
        
        # Summarization settings
        self.summarization_enabled = config.get("research.summarization.enabled", True)
        self.summarization_model = config.get("research.summarization.model", "qwen-flash")
        self.reuse_existing_summaries = config.get("research.summarization.reuse_existing_summaries", True)
        self.save_summaries_to_files = config.get("research.summarization.save_to_files", True)
        
        # Initialize proactive progress tracker
        self.progress_tracker = ProactiveProgressTracker()
        self.progress_tracker.scraping_timeout = 300.0  # 5 minutes per scraping
        self.progress_tracker.summarization_timeout = 120.0  # 2 minutes per summarization
        
        logger.info(f"[StreamingSummarizationManager] Initialized for batch {batch_id}")
        logger.info(f"[StreamingSummarizationManager] ✅ Proactive progress tracker initialized")
    
    def _get_item_display_name(self, link_id: str, item_data: Optional[Dict[str, Any]]) -> str:
        """
        Prefer showing a human-friendly title if metadata provides one.
        Falls back to the raw link_id when no title information exists.
        """
        if not isinstance(item_data, dict):
            return link_id
        
        metadata = item_data.get("metadata")
        title_candidates = []
        if isinstance(metadata, dict):
            title_candidates.extend([
                metadata.get("title"),
                metadata.get("video_title"),
                metadata.get("page_title"),
                metadata.get("name"),
            ])
        
        title_candidates.extend([
            item_data.get("title"),
            item_data.get("name"),
        ])
        
        for candidate in title_candidates:
            if isinstance(candidate, str):
                title = candidate.strip()
                if title:
                    return title
        
        return link_id
    
    def register_expected_items(self, link_ids: List[str]):
        """
        Register all link_ids we expect to process.
        
        Args:
            link_ids: List of all link_ids that will be scraped
        """
        self.expected_items = set(link_ids)
        with self.completed_lock:
            for link_id in link_ids:
                self.item_states[link_id] = {
                    'scraped': False,
                    'summarized': False,
                    'data': None,
                    'error': None
                }
                # Register in proactive progress tracker
                self.progress_tracker.register_item(link_id)
                self.progress_tracker.update_state(
                    link_id,
                    ItemState.PENDING,
                    "Registered, waiting for scraping to start"
                )
        logger.info(f"[StreamingSummarizationManager] Registered {len(link_ids)} expected items")
    
    def _get_progress_counts(self) -> Dict[str, int]:
        """
        Get current progress counts for all items.
        
        Returns:
            Dictionary with 'completed', 'processing', 'queued', and 'total' counts
        """
        with self.completed_lock:
            completed = sum(1 for state in self.item_states.values() if state.get('summarized', False))
            processing = len(self.items_processing)
            queued = len(self.items_in_queue)
            total = len(self.expected_items)
            return {
                'completed': completed,
                'processing': processing,
                'queued': queued,
                'total': total
            }
    
    def _calculate_progress(self, completed: int, processing: int, total: int) -> float:
        """
        Calculate progress percentage accounting for both completed and processing items.
        
        Uses partial progress (50% for processing items) to give a more accurate
        representation of work being done.
        
        Args:
            completed: Number of completed items
            processing: Number of items currently being processed
            total: Total number of items
            
        Returns:
            Progress percentage (0-100)
        """
        if total == 0:
            return 0.0
        
        # Count processing items as partial progress (50% each)
        # This gives a more accurate representation of work being done
        partial_progress = (completed + (processing * 0.5)) / total * 100
        
        # Ensure progress never exceeds 100%
        return min(100.0, partial_progress)
    
    def _save_summary_to_file(self, link_id: str, data: Dict[str, Any]) -> None:
        """
        Persist the completed summary for an item to a JSON file on disk.
        
        This gives us a clear, durable marker that an item has fully completed
        its lifecycle (scraped + summarized) and makes debugging much easier.
        
        File format:
            {batch_id}_{SOURCE}_{link_id}_summary.json
        
        The payload includes transcript, comments, metadata, and the summary.
        """
        try:
            # Use configured batches directory
            config = Config()
            results_base_path = config.get_batches_dir()
            batch_dir = results_base_path / f"run_{self.batch_id}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            
            source = (data.get("source") or "").lower()
            source_prefix_map = {
                "youtube": "YT",
                "bilibili": "BILI",
                "reddit": "RD",
                "article": "ARTICLE",
            }
            type_prefix = source_prefix_map.get(source, (source or "GEN").upper())
            
            summary_filename = batch_dir / f"{self.batch_id}_{type_prefix}_{link_id}_summary.json"
            
            payload = {
                "batch_id": self.batch_id,
                "link_id": link_id,
                "source": source,
                "metadata": data.get("metadata") or {},
                "transcript": data.get("transcript"),
                "comments": data.get("comments"),
                "summary": data.get("summary"),
            }
            
            with open(summary_filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            
            transcript_len = len(payload.get("transcript") or "")
            comments_obj = payload.get("comments") or []
            comments_count = len(comments_obj) if isinstance(comments_obj, list) else 0
            logger.info(
                f"[StreamingSummarizationManager] ✅ Item completed for {link_id}: "
                f"summary saved to {summary_filename.name} "
                f"({transcript_len} chars transcript, {comments_count} comments)"
            )
        except Exception as e:
            logger.error(
                f"[StreamingSummarizationManager] ✗ Failed to save summary for {link_id}: {e}",
                exc_info=True,
            )
    
    def _merge_scraped_data(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge scraped data from multiple sources (transcript + comments).
        
        When transcript and comments complete separately, this merges them into
        a single data structure with both transcript and comments.
        
        Args:
            existing_data: Existing scraped data (may be from comments or transcript)
            new_data: New scraped data (may be from transcript or comments)
            
        Returns:
            Merged data with both transcript and comments
        """
        merged = existing_data.copy() if existing_data else {}
        
        # Merge transcript (prefer new data if both exist, but merge if one is empty)
        if new_data.get('transcript'):
            if not merged.get('transcript') or len(merged.get('transcript', '')) < len(new_data.get('transcript', '')):
                merged['transcript'] = new_data['transcript']
        elif existing_data and existing_data.get('transcript'):
            merged['transcript'] = existing_data['transcript']
        
        # Merge comments (prefer new data if both exist, but merge if one is empty)
        if new_data.get('comments'):
            if not merged.get('comments') or len(merged.get('comments', [])) < len(new_data.get('comments', [])):
                merged['comments'] = new_data['comments']
        elif existing_data and existing_data.get('comments'):
            merged['comments'] = existing_data['comments']
        
        # Merge metadata (prefer new data, but keep existing if new is missing fields)
        if new_data.get('metadata'):
            if not merged.get('metadata'):
                merged['metadata'] = {}
            merged['metadata'].update(new_data['metadata'])
            # Keep existing metadata fields if new data doesn't have them
            if existing_data and existing_data.get('metadata'):
                for key, value in existing_data['metadata'].items():
                    if key not in merged['metadata'] or not merged['metadata'][key]:
                        merged['metadata'][key] = value
        elif existing_data and existing_data.get('metadata'):
            merged['metadata'] = existing_data['metadata']
        
        # Merge source (prefer new if both exist)
        if new_data.get('source'):
            merged['source'] = new_data['source']
        elif existing_data and existing_data.get('source'):
            merged['source'] = existing_data['source']
        
        # Merge summary if exists
        if new_data.get('summary'):
            merged['summary'] = new_data['summary']
        elif existing_data and existing_data.get('summary'):
            merged['summary'] = existing_data['summary']
        
        return merged
    
    def on_scraping_complete(self, link_id: str, data: Dict[str, Any]):
        """
        Called when an item finishes scraping.
        
        FIX 6: Merges data when transcript/comments complete separately.
        When transcript completes after comments (or vice versa), merges the new data
        with existing data instead of skipping.
        
        FIX LOCK CONTENTION: Minimized critical section to only hold lock when modifying shared state.
        UI updates and logging are moved outside the lock to prevent blocking other threads/workers.
        
        Args:
            link_id: Link identifier
            data: Scraped data for this item
        """
        # FIX LOCK CONTENTION: Split into multiple small critical sections instead of one giant lock
        # This allows workers to process items concurrently with new items being queued
        
        # CRITICAL SECTION 1: Check if item is already being processed/queued and merge if needed
        should_queue = False
        should_send_reused_ui = False
        with self.completed_lock:
            # Check if already being processed
            if link_id in self.items_processing:
                # Item is being processed - merge data and update stored state
                # The worker will use the updated data when it finishes
                logger.info(f"[StreamingSummarizationManager] {link_id} is being processed, merging data")
                existing_data = self.item_states.get(link_id, {}).get('data', {})
                merged_data = self._merge_scraped_data(existing_data, data)
                self.item_states[link_id]['data'] = merged_data
                logger.info(f"[StreamingSummarizationManager] ✓ Merged data for {link_id} (worker will use updated data)")
                return
            
            if link_id in self.items_in_queue:
                # Item is in queue but not processed yet - merge data and update stored state
                # The worker will use the merged data when it processes the item
                logger.info(f"[StreamingSummarizationManager] {link_id} is in queue, merging data with existing")
                existing_data = self.item_states.get(link_id, {}).get('data', {})
                merged_data = self._merge_scraped_data(existing_data, data)
                self.item_states[link_id]['data'] = merged_data
                logger.info(f"[StreamingSummarizationManager] ✓ Merged data for {link_id} (queue item will use updated data)")
                return
            
            if link_id in self.cancelled_items:
                logger.info(f"[StreamingSummarizationManager] {link_id} was cancelled, skipping")
                return
            
            if link_id not in self.item_states:
                logger.warning(f"[StreamingSummarizationManager] Received unexpected link_id: {link_id}")
                # Add it anyway
                self.item_states[link_id] = {
                    'scraped': False,
                    'summarized': False,
                    'data': None,
                    'error': None
                }
            
            # Check if already summarized
            if self.item_states[link_id].get('summarized', False):
                logger.debug(f"[StreamingSummarizationManager] {link_id} already summarized, skipping")
                return
            
            # Mark as scraped and store data
            self.item_states[link_id]['scraped'] = True
            self.item_states[link_id]['data'] = data
            
            # Check if summary already exists
            if self.reuse_existing_summaries and data.get("summary"):
                logger.debug(f"[StreamingSummarizationManager] Reusing existing summary for {link_id}")
                self.item_states[link_id]['summarized'] = True
                self.summaries_reused += 1
                should_send_reused_ui = True
                # Don't return yet - send UI update outside the lock
            else:
                # Mark as in queue before adding
                self.items_in_queue.add(link_id)
                should_queue = True
        
        # END CRITICAL SECTION 1 - Lock released!
        
        # FIX THREAD STARVATION: Give other threads (especially workers) a chance to acquire the lock
        # Without this, the workflow thread immediately re-acquires the lock and starves workers
        time.sleep(0.001)  # 1ms is enough for thread scheduler to switch
        
        # Handle reused summary UI update (outside lock)
        if should_send_reused_ui:
            if hasattr(self, 'ui') and self.ui:
                # Get counts in a separate critical section
                with self.completed_lock:
                    counts = self._get_progress_counts()
                    effective_progress = self._calculate_progress(
                        counts['completed'],
                        counts['processing'],
                        counts['total']
                    )
                
                if hasattr(self.ui, 'display_summarization_progress'):
                    item_display_name = self._get_item_display_name(link_id, data)
                    self.ui.display_summarization_progress(
                        current_item=counts['completed'],
                        total_items=counts['total'],
                        link_id=link_id,
                        stage="reused",
                        message=f"使用已有摘要 [{counts['completed']}/{counts['total']}]: {item_display_name}",
                        progress=effective_progress,
                        completed_items=counts['completed'],
                        processing_items=counts['processing'],
                        queued_items=counts['queued'],
                    )
            return
        
        # If not queueing, we're done
        if not should_queue:
            return
        
        # Check workers WITHOUT lock (w.is_alive() is thread-safe)
        active_workers = [w for w in self.workers if w.is_alive()]
        if not active_workers:
            logger.error(
                f"[StreamingSummarizationManager] ⚠️ No active workers running! Cannot process {link_id}. "
                f"Total workers: {len(self.workers)}, Active: 0. "
                f"Worker status: {[(w.name, w.is_alive()) for w in self.workers]}"
            )
            # Remove from queue set if no workers
            with self.completed_lock:
                self.items_in_queue.discard(link_id)
            
            # Try to restart workers if they all died
            logger.info(f"[StreamingSummarizationManager] Attempting to restart workers...")
            self.start_workers()
            
            # Check again
            active_workers = [w for w in self.workers if w.is_alive()]
            if not active_workers:
                logger.error(f"[StreamingSummarizationManager] Failed to restart workers. Item {link_id} cannot be processed.")
                return
            logger.info(f"[StreamingSummarizationManager] Workers restarted successfully. {len(active_workers)} active.")
        elif len(active_workers) < self.num_workers:
            # Check for dead workers
            dead_workers = [w for w in self.workers if not w.is_alive()]
            logger.warning(
                f"[StreamingSummarizationManager] Some workers have died! "
                f"Active: {len(active_workers)}/{self.num_workers}. "
                f"Dead workers: {[w.name for w in dead_workers]}"
            )
        
        # Queue the item (NO LOCK - queue.put() is thread-safe)
        self.summarization_queue.put((link_id, data))
        
        queue_size = self.summarization_queue.qsize()
        num_active_workers = len([w for w in self.workers if w.is_alive()])
        logger.info(
            f"[StreamingSummarizationManager] ✓ Queued {link_id} for summarization "
            f"(queue_size={queue_size}, active_workers={num_active_workers})"
        )
        
        # Send UI update to show item was queued (outside lock)
        if hasattr(self, 'ui') and self.ui:
            # Get counts in a separate critical section
            with self.completed_lock:
                scraped_count = sum(1 for state in self.item_states.values() if state.get('scraped', False))
                summarized_count = sum(1 for state in self.item_states.values() if state.get('summarized', False))
                pending_count = scraped_count - summarized_count
                counts = self._get_progress_counts()
                effective_progress = self._calculate_progress(
                    counts['completed'],
                    counts['processing'],
                    counts['total']
                )
            
            if hasattr(self.ui, 'display_summarization_progress'):
                item_display_name = self._get_item_display_name(link_id, data)
                self.ui.display_summarization_progress(
                    current_item=counts['completed'],
                    total_items=counts['total'],
                    link_id=link_id,
                    stage="queued",
                    message=f"已加入摘要队列 [{counts['completed']}/{counts['total']}]: {item_display_name} (队列中: {queue_size} 项, 等待中: {pending_count} 项)",
                    progress=effective_progress,
                    completed_items=counts['completed'],
                    processing_items=counts['processing'],
                    queued_items=counts['queued'],
                )
        
        # Update progress tracker LAST (after all locks and UI updates)
        # This prevents lock contention with workers
        transcript_len = len(data.get('transcript', '')) if data.get('transcript') else 0
        comments_count = len(data.get('comments', [])) if data.get('comments') else 0
        self.progress_tracker.update_state(
            link_id,
            ItemState.SCRAPED,
            f"Scraped: {transcript_len} chars transcript, {comments_count} comments"
        )
        if should_queue:
            self.progress_tracker.update_state(
                link_id,
                ItemState.QUEUED,
                "Queued for AI summarization"
            )
    
    def start_workers(self):
        """Start worker pool to process summarization queue."""
        if not self.summarization_enabled:
            logger.info("[StreamingSummarizationManager] Summarization disabled, skipping worker start")
            return
        
        logger.info(f"[StreamingSummarizationManager] Starting {self.num_workers} summarization workers")
        
        for i in range(self.num_workers):
            worker_thread = threading.Thread(
                target=self._worker,
                args=(i + 1,),
                name=f"StreamingSummarizationWorker-{i+1}",
                daemon=False
            )
            worker_thread.start()
            self.workers.append(worker_thread)
            logger.info(f"[StreamingSummarizationManager] Started worker {i+1}")
        
        # Start proactive progress monitoring
        self.progress_tracker.start_monitoring()
        logger.info("[StreamingSummarizationManager] 🚀 Proactive progress monitoring started")
    
    def _worker(self, worker_id: int):
        """Worker thread that processes summarization tasks from queue."""
        logger.info(f"[StreamingSummarizationManager] Worker {worker_id} started")
        worker_summaries_created = 0
        idle_iterations = 0
        last_heartbeat_log = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Get next task from queue (with timeout to allow checking for shutdown)
                try:
                    link_id, data = self.summarization_queue.get(timeout=0.1)
                    logger.info(
                        f"[StreamingSummarizationManager] ✓ Worker {worker_id} got item from queue: {link_id}, "
                        f"queue_size={self.summarization_queue.qsize()}, "
                        f"data_keys={list(data.keys()) if isinstance(data, dict) else 'not_dict'}"
                    )
                    idle_iterations = 0  # Reset idle counter when we get work
                except Empty:
                    # FIX RACE #6: Add periodic heartbeat logging to diagnose worker stalls
                    idle_iterations += 1
                    # Log heartbeat every 50 iterations (5 seconds) when idle
                    if idle_iterations % 50 == 0:
                        queue_size = self.summarization_queue.qsize()
                        logger.info(
                            f"[StreamingSummarizationManager] 💓 Worker {worker_id} heartbeat: "
                            f"idle for {idle_iterations} iterations (~{idle_iterations * 0.1:.1f}s), "
                            f"queue_size={queue_size}"
                        )
                        last_heartbeat_log = idle_iterations
                    continue
                
                # DEBUG: Log before attempting to acquire lock
                logger.info(f"[StreamingSummarizationManager] 🔒 Worker {worker_id} attempting to acquire lock for {link_id}")
                
                # FIX 4: Check if item was cancelled
                with self.completed_lock:
                    logger.info(f"[StreamingSummarizationManager] ✅ Worker {worker_id} acquired lock for {link_id}")
                    if link_id in self.cancelled_items:
                        logger.info(f"[StreamingSummarizationManager] Worker {worker_id} skipping {link_id} (cancelled)")
                        self.items_in_queue.discard(link_id)
                        self.summarization_queue.task_done()
                        continue
                    
                    # FIX 6: Use latest merged data from item_states instead of queue data
                    # The queue might have incomplete data (e.g., just comments), but item_states
                    # will have the merged data (comments + transcript) after on_scraping_complete
                    # merges data when transcript/comments complete separately
                    if link_id in self.item_states:
                        latest_data = self.item_states[link_id].get('data', {})
                        if latest_data:
                            # Use latest merged data instead of queue data
                            data = latest_data
                            logger.debug(f"[StreamingSummarizationManager] Worker {worker_id} using merged data for {link_id}")
                    
                    # FIX 5: Mark as processing and remove from queue set
                    if link_id in self.items_in_queue:
                        self.items_in_queue.remove(link_id)
                    self.items_processing.add(link_id)
                    
                    logger.info(f"[StreamingSummarizationManager] 🔓 Worker {worker_id} releasing lock for {link_id}")
                # Lock released here!
                
                # Update progress tracker NOW (after lock released)
                self.progress_tracker.update_state(
                    link_id,
                    ItemState.SUMMARIZING,
                    f"Worker {worker_id} acquired lock and starting processing"
                )
                self.progress_tracker.assign_worker(link_id, worker_id)
                
                logger.info(f"[StreamingSummarizationManager] ⚙️ Worker {worker_id} processing: {link_id}")
                
                # Send UI update to show processing started
                if hasattr(self, 'ui') and self.ui:
                    total_items = len(self.expected_items)
                    summarized_count = sum(1 for state in self.item_states.values() if state.get('summarized', False))
                    queue_size = self.summarization_queue.qsize()
                    
                    if hasattr(self.ui, 'display_summarization_progress'):
                        counts = self._get_progress_counts()
                        effective_progress = self._calculate_progress(
                            counts['completed'],
                            counts['processing'],
                            counts['total']
                        )
                        item_display_name = self._get_item_display_name(link_id, data)
                        self.ui.display_summarization_progress(
                            current_item=counts['completed'],
                            total_items=counts['total'],
                            link_id=link_id,
                            stage="processing",
                            message=f"正在总结 [{counts['completed']}/{counts['total']}]: {item_display_name} (Worker {worker_id})",
                            progress=effective_progress,
                            completed_items=counts['completed'],
                            processing_items=counts['processing'],
                            queued_items=counts['queued'],
                            worker_id=worker_id,
                        )
                
                # Check if already summarized (race condition protection)
                with self.completed_lock:
                    # FIX: Check if link_id exists in item_states before accessing
                    # If it doesn't exist, initialize it (defensive programming)
                    if link_id not in self.item_states:
                        logger.warning(
                            f"[StreamingSummarizationManager] Worker {worker_id} received unexpected link_id: {link_id}. "
                            f"Initializing item_state. Expected items: {list(self.expected_items)[:5]}..."
                        )
                        self.item_states[link_id] = {
                            'scraped': True,  # It was scraped if it's in the queue
                            'summarized': False,
                            'data': data,  # Use data from queue
                            'error': None
                        }
                    
                    # Now safely check if already summarized
                    if self.item_states[link_id].get('summarized', False):
                        logger.debug(f"[StreamingSummarizationManager] Worker {worker_id} skipping {link_id} (already summarized)")
                        self.items_processing.discard(link_id)
                        self.summarization_queue.task_done()
                        continue
                    
                    # FIX 6: Get latest merged data right before processing
                    # This ensures we use the most up-to-date data even if transcript/comments
                    # completed separately and data was merged after item was queued
                    if link_id in self.item_states:
                        latest_merged_data = self.item_states[link_id].get('data', {})
                        if latest_merged_data:
                            # Use latest merged data (may have transcript + comments merged)
                            data = latest_merged_data
                            transcript_len = len(data.get('transcript', '')) if data.get('transcript') else 0
                            comments_count = len(data.get('comments', [])) if data.get('comments') else 0
                            logger.info(
                                f"[StreamingSummarizationManager] Worker {worker_id} using latest merged data for {link_id}: "
                                f"{transcript_len} chars transcript, {comments_count} comments"
                            )
                
                # FIX 6: Final check - get latest merged data RIGHT BEFORE summarization
                # This handles race condition where transcript completes while worker is processing
                with self.completed_lock:
                    if link_id in self.item_states:
                        final_merged_data = self.item_states[link_id].get('data', {})
                        if final_merged_data:
                            # Compare to see if data was updated
                            old_transcript_len = len(data.get('transcript', '')) if data.get('transcript') else 0
                            new_transcript_len = len(final_merged_data.get('transcript', '')) if final_merged_data.get('transcript') else 0
                            old_comments_count = len(data.get('comments', [])) if data.get('comments') else 0
                            new_comments_count = len(final_merged_data.get('comments', [])) if final_merged_data.get('comments') else 0
                            
                            # If data was updated (e.g., transcript was merged), use the latest
                            if new_transcript_len > old_transcript_len or new_comments_count > old_comments_count:
                                data = final_merged_data
                                logger.info(
                                    f"[StreamingSummarizationManager] Worker {worker_id} updated data for {link_id} right before summarization: "
                                    f"{new_transcript_len} chars transcript (was {old_transcript_len}), "
                                    f"{new_comments_count} comments (was {old_comments_count})"
                                )
                
                # Create summary
                try:
                    # Update progress: About to call AI
                    self.progress_tracker.record_progress(
                        link_id,
                        f"Worker {worker_id} calling AI API"
                    )
                    
                    api_start_time = time.time()
                    logger.info(f"[StreamingSummarizationManager] 🤖 Worker {worker_id} [TIMING] Starting AI summarization for {link_id}")
                    
                    summary = self.summarizer.summarize_content_item(
                        link_id=link_id,
                        transcript=data.get("transcript"),
                        comments=data.get("comments"),
                        metadata=data.get("metadata")
                    )
                    
                    api_elapsed = time.time() - api_start_time
                    logger.info(f"[StreamingSummarizationManager] ✅ Worker {worker_id} [TIMING] AI summarization completed in {api_elapsed:.3f}s for {link_id}")
                    
                    # Update progress: AI completed
                    self.progress_tracker.record_progress(
                        link_id,
                        f"Worker {worker_id} AI completed in {api_elapsed:.1f}s, saving results"
                    )
                    
                    # Update state
                    with self.completed_lock:
                        # FIX 4: Check if cancelled during processing
                        if link_id in self.cancelled_items:
                            logger.info(f"[StreamingSummarizationManager] Worker {worker_id} {link_id} was cancelled during processing")
                            self.items_processing.discard(link_id)
                            self.summarization_queue.task_done()
                            continue
                        
                        data["summary"] = summary
                        self.item_states[link_id]['data'] = data
                        self.item_states[link_id]['summarized'] = True
                        self.items_processing.discard(link_id)  # FIX 4: Remove from processing set
                        worker_summaries_created += 1
                        self.summaries_created += 1
                    
                    # Log summary stats
                    transcript_markers = summary.get("transcript_summary", {}).get("total_markers", 0)
                    comments_markers = summary.get("comments_summary", {}).get("total_markers", 0)
                    logger.info(
                        f"[StreamingSummarizationManager] Worker {worker_id} created summary for {link_id}: "
                        f"{transcript_markers} transcript markers, {comments_markers} comment markers"
                    )
                    
                    # Persist completed item summary to disk so we have a clear lifecycle marker
                    # (scraped → summarized → summary JSON saved).
                    try:
                        logger.info(f"[StreamingSummarizationManager] 💾 Worker {worker_id} saving summary to file for {link_id}")
                        self._save_summary_to_file(link_id, data)
                        logger.info(f"[StreamingSummarizationManager] ✅ Worker {worker_id} saved summary file for {link_id}")
                    except Exception as e:
                        # Errors are already logged inside _save_summary_to_file
                        logger.error(f"[StreamingSummarizationManager] ❌ Worker {worker_id} failed to save summary file for {link_id}: {e}")
                        pass
                    
                    # Send progress update
                    if hasattr(self, 'ui') and self.ui:
                        total_items = len(self.expected_items)
                        summarized_count = sum(1 for state in self.item_states.values() if state['summarized'])
                        
                        if hasattr(self.ui, 'display_summarization_progress'):
                            counts = self._get_progress_counts()
                            effective_progress = self._calculate_progress(
                                counts['completed'],
                                counts['processing'],
                                counts['total']
                            )
                            item_display_name = self._get_item_display_name(link_id, data)
                            self.ui.display_summarization_progress(
                                current_item=counts['completed'],
                                total_items=counts['total'],
                                link_id=link_id,
                                stage="completed",
                                message=f"总结好了 [{counts['completed']}/{counts['total']}]: {item_display_name} ({transcript_markers + comments_markers} 标记, Worker {worker_id})",
                                progress=effective_progress,
                                completed_items=counts['completed'],
                                processing_items=counts['processing'],
                                queued_items=counts['queued'],
                                worker_id=worker_id,
                            )
                        
                        # Send summaries to frontend
                        transcript_summary = summary.get("transcript_summary", {})
                        if transcript_summary and transcript_summary.get("total_markers", 0) > 0:
                            if hasattr(self.ui, 'display_summary'):
                                self.ui.display_summary(
                                    link_id=link_id,
                                    summary_type="transcript",
                                    summary_data=transcript_summary
                                )
                        
                        comments_summary = summary.get("comments_summary", {})
                        if comments_summary and comments_summary.get("total_markers", 0) > 0:
                            if hasattr(self.ui, 'display_summary'):
                                self.ui.display_summary(
                                    link_id=link_id,
                                    summary_type="comments",
                                    summary_data=comments_summary
                                )
                    
                    # Update progress tracker: Item completed successfully
                    self.progress_tracker.update_state(
                        link_id,
                        ItemState.COMPLETED,
                        f"Worker {worker_id} completed successfully ({transcript_markers + comments_markers} markers)"
                    )
                
                except Exception as e:
                    logger.error(f"[StreamingSummarizationManager] Worker {worker_id} failed to summarize {link_id}: {e}", exc_info=True)
                    
                    # Update progress tracker: Item failed
                    self.progress_tracker.record_error(link_id, str(e))
                    self.progress_tracker.update_state(
                        link_id,
                        ItemState.FAILED,
                        f"Worker {worker_id} failed: {str(e)[:100]}"
                    )
                    
                    # Mark as failed but still summarized (so we can complete)
                    with self.completed_lock:
                        # FIX 4: Check if cancelled during processing
                        if link_id in self.cancelled_items:
                            logger.info(f"[StreamingSummarizationManager] Worker {worker_id} {link_id} was cancelled during error handling")
                            self.items_processing.discard(link_id)
                            self.summarization_queue.task_done()
                            continue
                        
                        error_summary = {
                            "transcript_summary": {},
                            "comments_summary": {},
                            "created_at": None,
                            "model_used": self.summarization_model,
                            "error": str(e)
                        }
                        data["summary"] = error_summary
                        self.item_states[link_id]['data'] = data
                        self.item_states[link_id]['summarized'] = True
                        self.item_states[link_id]['error'] = str(e)
                        self.items_processing.discard(link_id)  # FIX 4: Remove from processing set
                        self.summaries_failed += 1
                    
                    # Send error update
                    if hasattr(self, 'ui') and self.ui:
                        counts = self._get_progress_counts()
                        
                        if hasattr(self.ui, 'display_summarization_progress'):
                            effective_progress = self._calculate_progress(
                                counts['completed'],
                                counts['processing'],
                                counts['total']
                            )
                            item_display_name = self._get_item_display_name(link_id, data)
                            self.ui.display_summarization_progress(
                                current_item=counts['completed'],
                                total_items=counts['total'],
                                link_id=link_id,
                                stage="error",
                                message=f"摘要创建失败 [{counts['completed']}/{counts['total']}]: {item_display_name} (Worker {worker_id})",
                                progress=effective_progress,
                                completed_items=counts['completed'],
                                processing_items=counts['processing'],
                                queued_items=counts['queued'],
                                worker_id=worker_id,
                            )
                
                # Mark task as done
                logger.info(f"[StreamingSummarizationManager] ✔️ Worker {worker_id} completed item {link_id}, marking task_done")
                self.summarization_queue.task_done()
            
            except Exception as e:
                logger.error(
                    f"[StreamingSummarizationManager] Worker {worker_id} unexpected error processing item: {e}. "
                    f"link_id={link_id if 'link_id' in locals() else 'unknown'}, "
                    f"queue_size={self.summarization_queue.qsize()}, "
                    f"items_in_queue={len(self.items_in_queue)}, "
                    f"items_processing={len(self.items_processing)}",
                    exc_info=True
                )
                # Don't break the worker loop - continue processing other items
                # Only break on critical errors that can't be recovered from
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    break
                # Mark task as done even if there was an error to prevent queue blocking
                try:
                    self.summarization_queue.task_done()
                except Exception:
                    pass  # Ignore if task_done fails
                continue  # Continue processing instead of breaking
        
        logger.info(f"[StreamingSummarizationManager] Worker {worker_id} finished, created {worker_summaries_created} summaries")
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until all items are scraped AND summarized.
        
        FIX 3: Now waits for actual worker thread completion, not just state flags.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
            
        Returns:
            True if all items completed, False if timeout
        """
        start_time = time.time()
        
        logger.info(f"[StreamingSummarizationManager] Waiting for completion of {len(self.expected_items)} items")
        
        # FIX 3: First wait for queue to be empty (all tasks dequeued)
        logger.info("[StreamingSummarizationManager] Waiting for summarization queue to be empty...")
        queue_empty_timeout = timeout * 0.3 if timeout else None  # Use 30% of timeout for queue
        queue_start = time.time()
        
        while True:
            queue_size = self.summarization_queue.qsize()
            if queue_size == 0:
                logger.info("[StreamingSummarizationManager] Queue is empty, all tasks dequeued")
                break
            
            if queue_empty_timeout and (time.time() - queue_start) > queue_empty_timeout:
                logger.warning(f"[StreamingSummarizationManager] Queue not empty after {queue_empty_timeout}s (size={queue_size})")
                break
            
            time.sleep(0.1)
        
        # FIX 3: Wait for all workers to be idle (actually finished processing)
        logger.info("[StreamingSummarizationManager] Waiting for all workers to finish processing...")
        worker_timeout = timeout * 0.7 if timeout else None  # Use 70% of timeout for workers
        worker_start = time.time()
        
        while True:
            active_workers = [w for w in self.workers if w.is_alive()]
            idle_workers = []
            
            # Check if workers are actually idle (not processing)
            for worker in active_workers:
                # Workers are idle when they're waiting for queue items
                # We can't directly check this, but we can check if queue is empty
                # and workers have been alive for a while without new tasks
                if self.summarization_queue.qsize() == 0:
                    # Queue is empty, workers should be idle
                    idle_workers.append(worker)
            
            # If all workers are idle or no active workers, check state flags
            if len(active_workers) == 0 or len(idle_workers) == len(active_workers):
                with self.completed_lock:
                    # Check completion status
                    all_scraped = all(
                        self.item_states.get(link_id, {}).get('scraped', False)
                        for link_id in self.expected_items
                    )
                    all_summarized = all(
                        self.item_states.get(link_id, {}).get('summarized', False)
                        for link_id in self.expected_items
                    )
                    
                    scraped_count = sum(1 for state in self.item_states.values() if state.get('scraped', False))
                    summarized_count = sum(1 for state in self.item_states.values() if state.get('summarized', False))
                    
                    if all_scraped and all_summarized:
                        logger.info(
                            f"[StreamingSummarizationManager] All items completed: "
                            f"{scraped_count}/{len(self.expected_items)} scraped, "
                            f"{summarized_count}/{len(self.expected_items)} summarized"
                        )
                        # FIX 3: Final verification - wait a bit more to ensure workers are truly done
                        time.sleep(0.2)
                        return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"[StreamingSummarizationManager] Timeout waiting for completion")
                return False
            
            if worker_timeout and (time.time() - worker_start) > worker_timeout:
                logger.warning(f"[StreamingSummarizationManager] Worker timeout after {worker_timeout}s")
                # Check state flags as fallback
                with self.completed_lock:
                    all_scraped = all(
                        self.item_states.get(link_id, {}).get('scraped', False)
                        for link_id in self.expected_items
                    )
                    all_summarized = all(
                        self.item_states.get(link_id, {}).get('summarized', False)
                        for link_id in self.expected_items
                    )
                    if all_scraped and all_summarized:
                        logger.warning("[StreamingSummarizationManager] State flags indicate completion, but workers may still be active")
                        return True
                return False
            
            # Wait a bit before checking again
            time.sleep(0.2)
    
    def get_all_summarized_data(self) -> Dict[str, Any]:
        """
        Get all data with summaries attached.
        
        Returns:
            Dict mapping link_id to data with summaries
        """
        with self.completed_lock:
            result = {}
            for link_id, state in self.item_states.items():
                if state.get('summarized', False) and state.get('data'):
                    result[link_id] = state['data']
            return result
    
    def cancel_item(self, link_id: str):
        """
        FIX 4: Cancel an in-progress summarization for a link.
        
        This is called when scraping restarts for an item that's already
        being summarized, to prevent duplicate processing.
        
        Args:
            link_id: Link identifier to cancel
        """
        with self.completed_lock:
            if link_id in self.cancelled_items:
                logger.debug(f"[StreamingSummarizationManager] {link_id} already cancelled")
                return
            
            self.cancelled_items.add(link_id)
            self.items_in_queue.discard(link_id)
            self.items_processing.discard(link_id)
            
            logger.info(f"[StreamingSummarizationManager] Cancelled summarization for {link_id}")
    
    def shutdown(self):
        """Shutdown worker pool and wait for completion."""
        logger.info("[StreamingSummarizationManager] Shutting down workers")
        
        # Stop proactive progress monitoring
        self.progress_tracker.stop_monitoring()
        logger.info("[StreamingSummarizationManager] 🛑 Proactive progress monitoring stopped")
        
        self.shutdown_event.set()
        
        # Wait for all workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)
        
        # Wait for queue to be empty
        self.summarization_queue.join()
        
        logger.info(
            f"[StreamingSummarizationManager] Shutdown complete: "
            f"{self.summaries_created} created, {self.summaries_reused} reused, {self.summaries_failed} failed"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about processing."""
        with self.completed_lock:
            scraped_count = sum(1 for state in self.item_states.values() if state.get('scraped', False))
            summarized_count = sum(1 for state in self.item_states.values() if state.get('summarized', False))
            
            return {
                'expected_items': len(self.expected_items),
                'scraped': scraped_count,
                'summarized': summarized_count,
                'summaries_created': self.summaries_created,
                'summaries_reused': self.summaries_reused,
                'summaries_failed': self.summaries_failed,
                'queue_size': self.summarization_queue.qsize()
            }

