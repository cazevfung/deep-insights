"""Simplified Streaming Summarization Manager - Clean sequential processing."""

import json
import time
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from loguru import logger

from research.summarization.content_summarizer import ContentSummarizer


class ItemState(Enum):
    """Clear state machine for item lifecycle."""
    PENDING = auto()           # Registered, waiting for scraping
    SCRAPED = auto()           # Scraping complete, data saved
    QUEUED = auto()            # Waiting in queue for summarization
    SUMMARIZING = auto()       # AI is creating summary
    COMPLETED = auto()         # Summary complete, final JSON saved
    FAILED = auto()            # Failed after retries (terminal state)


class ItemInfo:
    """Simple container for item state and data."""
    def __init__(self, link_id: str):
        self.link_id = link_id
        self.state = ItemState.PENDING
        self.scraped_data: Optional[Dict[str, Any]] = None
        self.summary: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.retry_count: int = 0
        self.last_update: float = time.time()
    
    def update_state(self, new_state: ItemState, error: Optional[str] = None):
        """Update state with timestamp."""
        self.state = new_state
        self.last_update = time.time()
        if error:
            self.error = error
        logger.info(f"[ItemState] {self.link_id}: {new_state.name}" + (f" ({error})" if error else ""))


class StreamingSummarizationManagerV2:
    """
    Simplified streaming summarization manager.
    
    Design principles:
    1. One item, one state - no overlapping flags
    2. Sequential processing - predictable and debuggable
    3. Clear file lifecycle - scraped.json → complete.json
    4. Simple error handling - retry then fail
    5. Caller handles data merging - we only receive complete data
    """
    
    def __init__(self, client, config, ui, session, batch_id: str):
        """
        Initialize simplified summarization manager.
        
        Args:
            client: QwenStreamingClient instance
            config: Config instance
            ui: UI interface for progress updates
            session: ResearchSession instance
            batch_id: Batch identifier (e.g., "20251114_150630")
        """
        self.client = client
        self.config = config
        self.ui = ui
        self.session = session
        self.batch_id = batch_id
        
        # Initialize summarizer
        self.summarizer = ContentSummarizer(client=client, config=config, ui=ui)
        
        # Simple state tracking - one state per item
        self.items: Dict[str, ItemInfo] = {}
        self.items_lock = threading.RLock()  # Use RLock to allow reentrant acquisition
        
        # Processing queue - FIFO, items pulled by worker threads
        self.processing_queue: Queue = Queue()
        
        # Worker threads (can be >1). Keep worker_thread for backward compatibility.
        self.worker_threads: List[threading.Thread] = []
        self.worker_thread: Optional[threading.Thread] = None  # Deprecated alias
        self.worker_count = max(1, config.get("research.summarization.worker_count", 4))
        self._worker_id_counter = 0
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'total': 0,
            'scraped': 0,
            'summarized': 0,
            'reused': 0,
            'failed': 0,
            'created': 0
        }
        
        # Settings
        self.summarization_enabled = config.get("research.summarization.enabled", True)
        self.summarization_model = config.get("research.summarization.model", "qwen-flash")
        
        # File-based completion tracking
        self.use_file_based_completion = config.get(
            "research.summarization.use_file_based_completion",
            True  # Default to enabled for reliability
        )
        self.reuse_existing_summaries = config.get("research.summarization.reuse_existing_summaries", True)
        self.max_retries = config.get("research.summarization.max_retries", 3)
        
        # Batch directory for saving files and file-based completion checks
        from core.config import Config
        config_obj = Config()
        results_base_path = config_obj.get_batches_dir()
        self.batch_dir = results_base_path / f"run_{batch_id}"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[SummarizationV2] Initialized for batch {batch_id}")
        logger.info(f"[SummarizationV2] Batch directory: {self.batch_dir}")
        logger.info(f"[SummarizationV2] Summarization enabled: {self.summarization_enabled}")
    
    def register_expected_items(self, link_ids: List[str]):
        """
        Register all items we expect to process.
        
        Args:
            link_ids: List of link identifiers
        """
        with self.items_lock:
            for link_id in link_ids:
                if link_id not in self.items:
                    self.items[link_id] = ItemInfo(link_id)
                    self.stats['total'] += 1
        
        logger.info(f"[SummarizationV2] Registered {len(link_ids)} items")
    
    def on_item_scraped(self, link_id: str, data: Dict[str, Any]):
        """
        Called when scraping is COMPLETE for an item.
        
        Important: Caller must ensure data is fully merged (transcript + comments)
        before calling this method. We do NOT handle partial data or merging.
        
        Args:
            link_id: Link identifier
            data: Complete scraped data with keys:
                - source: str (e.g., "youtube")
                - metadata: dict
                - transcript: str (optional)
                - comments: list (optional)
                - summary: dict (optional, if reusing existing)
        """
        if not self.summarization_enabled:
            logger.info(f"[SummarizationV2] Summarization disabled, skipping {link_id}")
            return
        
        # Flag to track if we're reusing a summary
        should_reuse = False
        
        with self.items_lock:
            # Get or create item
            if link_id not in self.items:
                logger.warning(f"[SummarizationV2] Unexpected item {link_id}, registering now")
                self.items[link_id] = ItemInfo(link_id)
                self.stats['total'] += 1
            
            item = self.items[link_id]
            
            # Store scraped data
            item.scraped_data = data
            item.update_state(ItemState.SCRAPED)
            self.stats['scraped'] += 1
            
            # Check if summary already exists and we can reuse it
            if self.reuse_existing_summaries and data.get("summary"):
                logger.info(f"[SummarizationV2] Reusing existing summary for {link_id}")
                item.summary = data["summary"]
                item.update_state(ItemState.COMPLETED)
                self.stats['summarized'] += 1
                self.stats['reused'] += 1
                should_reuse = True
        
        # Handle reuse path outside the lock to avoid deadlock
        if should_reuse:
            # Save complete JSON immediately
            self._save_complete_json(link_id, data)
            
            # Send UI update (this acquires items_lock internally)
            self._send_ui_update(link_id, "reused", f"使用已有摘要: {link_id}")
            return
        
        # Save scraped JSON to disk
        self._save_scraped_json(link_id, data)
        
        # Add to processing queue
        with self.items_lock:
            item.update_state(ItemState.QUEUED)
        
        self.processing_queue.put(link_id)
        
        logger.info(
            f"[SummarizationV2] Queued {link_id} for summarization "
            f"(queue_size={self.processing_queue.qsize()})"
        )
        
        # Send UI update
        self._send_ui_update(link_id, "queued", f"已加入摘要队列: {link_id}")
    
    def start_worker(self):
        """Start worker threads to process the summarization queue."""
        if not self.summarization_enabled:
            logger.info("[SummarizationV2] Summarization disabled, not starting worker")
            return
        
        # Drop references to dead threads
        alive_threads = [t for t in self.worker_threads if t.is_alive()]
        dead_threads = len(self.worker_threads) - len(alive_threads)
        if dead_threads:
            logger.warning(
                f"[SummarizationV2] Cleaned up {dead_threads} dead summarization worker(s)"
            )
        self.worker_threads = alive_threads
        
        if len(self.worker_threads) >= self.worker_count:
            logger.info(
                f"[SummarizationV2] Worker pool already at capacity "
                f"({len(self.worker_threads)}/{self.worker_count})"
            )
            return
        
        threads_to_start = self.worker_count - len(self.worker_threads)
        logger.info(
            f"[SummarizationV2] Starting {threads_to_start} summarization worker(s) "
            f"(target={self.worker_count})"
        )
        
        for _ in range(threads_to_start):
            worker_id = self._next_worker_id()
            worker_thread = threading.Thread(
                target=self._worker_loop,
                name=f"SummarizationWorker-{worker_id}",
                args=(worker_id,),
                daemon=False
            )
            self.worker_threads.append(worker_thread)
            # Maintain backward-compatible reference to the first worker
            if self.worker_thread is None:
                self.worker_thread = worker_thread
            worker_thread.start()
            logger.info(f"[SummarizationV2] Worker {worker_id} started")
        
        logger.info(
            f"[SummarizationV2] Active summarization workers: "
            f"{len(self.worker_threads)}/{self.worker_count}"
        )
    
    def _next_worker_id(self) -> int:
        """Return the next worker id."""
        self._worker_id_counter += 1
        return self._worker_id_counter
    
    def _worker_loop(self, worker_id: int):
        """Worker that processes items sequentially."""
        logger.info(f"[SummarizationV2] Worker loop started (worker_id={worker_id})")
        
        while not self.shutdown_event.is_set():
            try:
                # Get next item from queue (timeout allows checking for shutdown)
                try:
                    link_id = self.processing_queue.get(timeout=0.5)
                except Empty:
                    continue
                
                # Process the item
                logger.info(f"[SummarizationV2] Processing: {link_id} (worker_id={worker_id})")
                self._process_item(link_id, worker_id=worker_id)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"[SummarizationV2] Worker error: {e}", exc_info=True)
                # Continue processing other items
                try:
                    self.processing_queue.task_done()
                except:
                    pass
        
        logger.info(f"[SummarizationV2] Worker loop finished (worker_id={worker_id})")
    
    def _process_item(self, link_id: str, worker_id: Optional[int] = None):
        """
        Process a single item - create summary and save.
        
        Steps:
        1. Update state to SUMMARIZING
        2. Call AI to create summary
        3. Save complete JSON with summary
        4. Update state to COMPLETED
        5. Send UI update
        
        If AI fails, retry up to max_retries times.
        
        Args:
            link_id: Link identifier to process
        """
        logger.info(
            f"[SummarizationV2] _process_item ENTERED for {link_id}, "
            f"thread={threading.current_thread().name}, worker_id={worker_id}"
        )
        
        # Get item and data
        logger.info(f"[SummarizationV2] Acquiring items_lock for {link_id} (thread={threading.current_thread().name})")
        with self.items_lock:
            logger.info(f"[SummarizationV2] Acquired items_lock for {link_id} (thread={threading.current_thread().name})")
            if link_id not in self.items:
                logger.error(f"[SummarizationV2] Item {link_id} not found in items dict")
                return
            
            item = self.items[link_id]
            
            if not item.scraped_data:
                logger.error(f"[SummarizationV2] No scraped data for {link_id}")
                item.update_state(ItemState.FAILED, "No scraped data")
                self.stats['failed'] += 1
                return
            
            # Update state to SUMMARIZING
            item.update_state(ItemState.SUMMARIZING)
            
            # Make a copy of data to work with outside lock
            data = item.scraped_data.copy()
        
        logger.info(f"[SummarizationV2] Released items_lock for {link_id}, data size: {len(str(data))} chars")
        
        # Send UI update - processing started
        logger.info(f"[SummarizationV2] Sending UI update for {link_id}")
        self._send_ui_update(link_id, "processing", f"正在总结: {link_id}", worker_id=worker_id)
        logger.info(f"[SummarizationV2] About to call summarizer for {link_id}")
        
        # Try to create summary (with retries)
        summary = None
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"[SummarizationV2] Creating summary for {link_id} "
                    f"(attempt {attempt}/{self.max_retries})"
                )
                
                # Call AI to create summary
                start_time = time.time()
                summary = self.summarizer.summarize_content_item(
                    link_id=link_id,
                    transcript=data.get("transcript"),
                    comments=data.get("comments"),
                    metadata=data.get("metadata")
                )
                elapsed = time.time() - start_time
                
                logger.info(
                    f"[SummarizationV2] Summary created for {link_id} "
                    f"in {elapsed:.2f}s (attempt {attempt})"
                )
                
                # Success - break retry loop
                break
                
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"[SummarizationV2] Failed to create summary for {link_id} "
                    f"(attempt {attempt}/{self.max_retries}): {e}",
                    exc_info=True
                )
                
                # If not last attempt, wait before retrying
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"[SummarizationV2] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        # Check if we got a summary
        if summary is None:
            # All retries failed
            logger.error(
                f"[SummarizationV2] Failed to create summary for {link_id} "
                f"after {self.max_retries} attempts"
            )
            
            with self.items_lock:
                item.update_state(ItemState.FAILED, f"AI failed: {last_error}")
                item.retry_count = self.max_retries
                self.stats['failed'] += 1
            
            # Send UI update - failed
            self._send_ui_update(link_id, "error", f"摘要创建失败: {link_id}", worker_id=worker_id)
            return
        
        # Success - save complete JSON
        data["summary"] = summary
        
        with self.items_lock:
            item.summary = summary
            item.scraped_data["summary"] = summary
        
        self._save_complete_json(link_id, data)
        
        # Update state to COMPLETED
        with self.items_lock:
            item.update_state(ItemState.COMPLETED)
            self.stats['summarized'] += 1
            self.stats['created'] += 1
        
        # Send UI update - completed
        transcript_markers = summary.get("transcript_summary", {}).get("total_markers", 0)
        comments_markers = summary.get("comments_summary", {}).get("total_markers", 0)
        total_markers = transcript_markers + comments_markers
        
        self._send_ui_update(
            link_id,
            "completed",
            f"总结好了: {link_id} ({total_markers} 标记)",
            worker_id=worker_id
        )
        
        # Send summaries to frontend
        self._send_summaries_to_ui(link_id, summary)
        
        logger.info(f"[SummarizationV2] ✓ Completed {link_id}")
    
    def _save_scraped_json(self, link_id: str, data: Dict[str, Any]):
        """
        Save scraped data to disk.
        
        File: {batch_id}_{SOURCE}_{link_id}_scraped.json
        
        Args:
            link_id: Link identifier
            data: Scraped data to save
        """
        try:
            filename = self._get_filename(link_id, data.get("source"), suffix="scraped")
            
            payload = {
                "batch_id": self.batch_id,
                "link_id": link_id,
                "source": data.get("source"),
                "metadata": data.get("metadata", {}),
                "transcript": data.get("transcript"),
                "comments": data.get("comments"),
                "scraped_at": time.time()
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            
            transcript_len = len(payload.get("transcript") or "")
            comments_count = len(payload.get("comments") or [])
            
            logger.info(
                f"[SummarizationV2] Saved scraped data: {filename.name} "
                f"({transcript_len} chars transcript, {comments_count} comments)"
            )
            
        except Exception as e:
            logger.error(f"[SummarizationV2] Failed to save scraped JSON for {link_id}: {e}", exc_info=True)
    
    def _save_complete_json(self, link_id: str, data: Dict[str, Any]):
        """
        Save complete data (scraped + summary) to disk.
        
        File: {batch_id}_{SOURCE}_{link_id}_complete.json
        
        Args:
            link_id: Link identifier
            data: Complete data with summary to save
        """
        try:
            filename = self._get_filename(link_id, data.get("source"), suffix="complete")
            
            payload = {
                "batch_id": self.batch_id,
                "link_id": link_id,
                "source": data.get("source"),
                "metadata": data.get("metadata", {}),
                "transcript": data.get("transcript"),
                "comments": data.get("comments"),
                "summary": data.get("summary"),
                "completed_at": time.time()
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[SummarizationV2] Saved complete data: {filename.name}")
            
        except Exception as e:
            logger.error(f"[SummarizationV2] Failed to save complete JSON for {link_id}: {e}", exc_info=True)
    
    def _get_filename(self, link_id: str, source: Optional[str], suffix: str) -> Path:
        """
        Generate filename for saving data.
        
        Format: {batch_id}_{SOURCE_PREFIX}_{link_id}_{suffix}.json
        
        Args:
            link_id: Link identifier
            source: Source type (youtube, bilibili, reddit, article)
            suffix: File suffix (scraped, complete, summary)
            
        Returns:
            Path to file
        """
        source_prefix_map = {
            "youtube": "YT",
            "bilibili": "BILI",
            "reddit": "RD",
            "article": "ARTICLE",
        }
        
        source_lower = (source or "").lower()
        source_prefix = source_prefix_map.get(source_lower, (source or "GEN").upper())
        
        filename = f"{self.batch_id}_{source_prefix}_{link_id}_{suffix}.json"
        return self.batch_dir / filename
    
    def _send_ui_update(self, link_id: str, stage: str, message: str, worker_id: Optional[int] = None):
        """
        Send progress update to UI.
        
        Args:
            link_id: Link identifier
            stage: Stage name (queued, processing, completed, error, reused)
            message: Display message
        """
        if not hasattr(self, 'ui') or not self.ui:
            return
        
        if not hasattr(self.ui, 'display_summarization_progress'):
            return
        
        # Get current stats (RLock allows reentrant acquisition if called from within another lock)
        with self.items_lock:
            completed = self.stats['summarized']
            queued = self.processing_queue.qsize()
            
            # Count items in SUMMARIZING state
            processing = sum(
                1 for item in self.items.values()
                if item.state == ItemState.SUMMARIZING
            )
            
            # Count successfully scraped items (items that reached SCRAPED state or later)
            # Failed scrapes never reach SCRAPED state and cannot be sent for summarization,
            # so we should only count successfully scraped items as the total
            total_scraped = sum(
                1 for item in self.items.values()
                if item.state.value >= ItemState.SCRAPED.value
            )
        
        # Use successfully scraped items as total for progress calculation
        # This ensures the denominator reflects only items that can actually be summarized
        total = total_scraped if total_scraped > 0 else self.stats['scraped']
        
        # Calculate progress
        if total > 0:
            progress = (completed / total) * 100
        else:
            progress = 0
        
        self.ui.display_summarization_progress(
            current_item=completed,
            total_items=total,
            link_id=link_id,
            stage=stage,
            message=f"[{completed}/{total}] {message}",
            progress=progress,
            completed_items=completed,
            processing_items=processing,
            queued_items=queued,
            worker_id=worker_id
        )
    
    def _send_summaries_to_ui(self, link_id: str, summary: Dict[str, Any]):
        """
        Send completed summaries to frontend.
        
        Args:
            link_id: Link identifier
            summary: Summary data with transcript_summary and comments_summary
        """
        if not hasattr(self, 'ui') or not self.ui:
            return
        
        if not hasattr(self.ui, 'display_summary'):
            return
        
        # Send transcript summary if exists
        transcript_summary = summary.get("transcript_summary", {})
        if transcript_summary and transcript_summary.get("total_markers", 0) > 0:
            self.ui.display_summary(
                link_id=link_id,
                summary_type="transcript",
                summary_data=transcript_summary
            )
        
        # Send comments summary if exists
        comments_summary = summary.get("comments_summary", {})
        if comments_summary and comments_summary.get("total_markers", 0) > 0:
            self.ui.display_summary(
                link_id=link_id,
                summary_type="comments",
                summary_data=comments_summary
            )
    
    def _check_file_based_completion(self) -> tuple[bool, Dict[str, bool]]:
        """
        Check completion status based on _complete.json files on disk.
        
        This is more reliable than in-memory state tracking because:
        - File existence is the ground truth (if file exists, summary was saved)
        - Can recover from crashes/restarts
        - Doesn't depend on API call tracking
        
        Returns:
            Tuple of (all_complete, file_status_dict) where:
            - all_complete: True if all expected items have _complete.json files
            - file_status_dict: Dict mapping link_id to bool (True if file exists)
        """
        if not self.use_file_based_completion:
            return False, {}
        
        file_status = {}
        all_complete = True
        
        with self.items_lock:
            expected_items = set(self.items.keys())
        
        # Check for _complete.json files for each expected item
        for link_id in expected_items:
            # Get source from item data if available
            source = None
            with self.items_lock:
                if link_id in self.items and self.items[link_id].scraped_data:
                    source = self.items[link_id].scraped_data.get("source")
            
            # Try to find _complete.json file (may have different source prefixes)
            # Format: {batch_id}_{SOURCE}_{link_id}_complete.json
            complete_file = None
            if source:
                # Try with known source first
                complete_file = self._get_filename(link_id, source, suffix="complete")
            else:
                # If source unknown, try common source prefixes
                source_prefixes = ["YT", "BILI", "RD", "ARTICLE"]
                for prefix in source_prefixes:
                    candidate = self.batch_dir / f"{self.batch_id}_{prefix}_{link_id}_complete.json"
                    if candidate.exists():
                        complete_file = candidate
                        break
            
            # If still not found, try glob pattern
            if not complete_file or not complete_file.exists():
                pattern = f"{self.batch_id}_*_{link_id}_complete.json"
                matches = list(self.batch_dir.glob(pattern))
                if matches:
                    complete_file = matches[0]
            
            # Check if file exists and has valid summary
            if complete_file and complete_file.exists():
                try:
                    with open(complete_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    # Verify file has summary field (not just empty file)
                    if file_data.get("summary"):
                        file_status[link_id] = True
                        continue
                except Exception as e:
                    logger.debug(f"[SummarizationV2] Error reading {complete_file}: {e}")
            
            # File doesn't exist or is invalid
            file_status[link_id] = False
            all_complete = False
        
        return all_complete, file_status
    
    def verify_completion_from_files(self, expected_link_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Verify completion status purely from _complete.json files on disk.
        
        This is useful for:
        - Recovery after crashes/restarts
        - Independent verification without in-memory state
        - Debugging completion issues
        
        Args:
            expected_link_ids: Optional list of link_ids to check.
                              If None, uses registered items.
        
        Returns:
            Dict mapping link_id to bool (True if _complete.json exists with valid summary)
        """
        if expected_link_ids is None:
            with self.items_lock:
                expected_link_ids = list(self.items.keys())
        
        file_status = {}
        for link_id in expected_link_ids:
            # Try to find _complete.json file
            pattern = f"{self.batch_id}_*_{link_id}_complete.json"
            matches = list(self.batch_dir.glob(pattern))
            
            if matches:
                try:
                    with open(matches[0], 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    # Verify file has summary field
                    file_status[link_id] = bool(file_data.get("summary"))
                except Exception as e:
                    logger.debug(f"[SummarizationV2] Error reading {matches[0]}: {e}")
                    file_status[link_id] = False
            else:
                file_status[link_id] = False
        
        return file_status
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until all successfully scraped items reach terminal states (COMPLETED or FAILED).
        
        Uses (summarized + failed) / successfully_scraped == 100% to determine completion.
        This avoids race conditions by checking if all items reached terminal states.
        
        Only counts items that were successfully scraped (reached SCRAPED state or later).
        Failed scrapes cannot be summarized, so they are excluded.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if all successfully scraped items are in terminal states, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self.items_lock:
                # Count successfully scraped items (reached SCRAPED state or later)
                successfully_scraped = sum(
                    1 for item in self.items.values()
                    if item.state.value >= ItemState.SCRAPED.value
                )
                
                # Count items in terminal states (COMPLETED or FAILED)
                completed = sum(
                    1 for item in self.items.values()
                    if item.state == ItemState.COMPLETED
                )
                failed = sum(
                    1 for item in self.items.values()
                    if item.state == ItemState.FAILED
                )
                
                # Use stats as fallback if counts are 0
                if successfully_scraped == 0:
                    successfully_scraped = self.stats.get('scraped', 0)
                if completed == 0:
                    completed = self.stats.get('summarized', 0)
                if failed == 0:
                    failed = self.stats.get('failed', 0)
                
                total_registered = self.stats['total']
                terminal_count = completed + failed
                
                # Check completion: (completed + failed) / successfully_scraped == 100%
                # This avoids race conditions by checking terminal states
                if successfully_scraped > 0:
                    completion_percentage = (terminal_count / successfully_scraped) * 100.0
                    is_complete = terminal_count >= successfully_scraped
                else:
                    completion_percentage = 0.0
                    is_complete = True  # No items to process
            
            if is_complete:
                logger.info(
                    f"[SummarizationV2] All successfully scraped items completed: "
                    f"{completed} summarized, {failed} failed "
                    f"({terminal_count}/{successfully_scraped} = {completion_percentage:.1f}%) "
                    f"out of {total_registered} total registered"
                )
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(
                    f"[SummarizationV2] Timeout after {timeout}s: "
                    f"{completed} summarized, {failed} failed "
                    f"({terminal_count}/{successfully_scraped} = {completion_percentage:.1f}%)"
                )
                return False
            
            # Wait before checking again
            time.sleep(0.5)
    
    def get_all_summarized_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed items with summaries.
        
        Returns:
            Dict mapping link_id to data with summaries
        """
        with self.items_lock:
            result = {}
            for link_id, item in self.items.items():
                if item.state == ItemState.COMPLETED and item.scraped_data:
                    result[link_id] = item.scraped_data
            return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dict with stats including:
            - total: Total registered items (including failed scrapes)
            - scraped: Successfully scraped items (can be summarized)
            - successfully_scraped: Count of items that reached SCRAPED state or later
            - summarized: Successfully summarized items (COMPLETED state)
            - failed: Failed summarization items (FAILED state)
            - created: New summaries created
            - reused: Existing summaries reused
        """
        with self.items_lock:
            stats = self.stats.copy()
            
            # Count successfully scraped items (items that reached SCRAPED state or later)
            successfully_scraped = sum(
                1 for item in self.items.values()
                if item.state.value >= ItemState.SCRAPED.value
            )
            
            # Count terminal states
            completed = sum(
                1 for item in self.items.values()
                if item.state == ItemState.COMPLETED
            )
            failed = sum(
                1 for item in self.items.values()
                if item.state == ItemState.FAILED
            )
            
            # Add counts (use stats as fallback if counts are 0)
            stats['successfully_scraped'] = successfully_scraped if successfully_scraped > 0 else stats.get('scraped', 0)
            stats['summarized_count'] = completed if completed > 0 else stats.get('summarized', 0)
            stats['failed_count'] = failed if failed > 0 else stats.get('failed', 0)
            
            # Calculate completion percentage to avoid race conditions
            if stats['successfully_scraped'] > 0:
                stats['completion_percentage'] = (
                    (stats['summarized_count'] + stats['failed_count']) / stats['successfully_scraped']
                ) * 100.0
                stats['is_complete'] = (stats['summarized_count'] + stats['failed_count']) >= stats['successfully_scraped']
            else:
                stats['completion_percentage'] = 100.0
                stats['is_complete'] = True

            # Backward-compatibility fields expected by legacy callers
            stats['expected_items'] = max(self.stats.get('total', 0), len(self.items))
            stats['summaries_created'] = self.stats.get('created', 0)
            stats['summaries_reused'] = self.stats.get('reused', 0)
            stats['summaries_failed'] = self.stats.get('failed', 0)
            stats['queue_size'] = self.processing_queue.qsize()
            # Ensure legacy field names are populated
            stats['scraped'] = stats.get('scraped', self.stats.get('scraped', 0))
            stats['summarized'] = stats.get('summarized', stats.get('summarized_count', 0))
            
            return stats
    
    def get_item_states(self) -> Dict[str, str]:
        """Get state of all items (for debugging)."""
        with self.items_lock:
            return {
                link_id: item.state.name
                for link_id, item in self.items.items()
            }
    
    def shutdown(self):
        """Shutdown worker and wait for completion."""
        logger.info("[SummarizationV2] Shutting down...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in list(self.worker_threads):
            if worker.is_alive():
                logger.info(f"[SummarizationV2] Waiting for {worker.name} to finish...")
                worker.join(timeout=10.0)
                if worker.is_alive():
                    logger.warning(f"[SummarizationV2] {worker.name} did not finish in time")
        
        self.worker_threads = []
        self.worker_thread = None
        
        # Log final statistics
        logger.info(
            f"[SummarizationV2] Shutdown complete: "
            f"{self.stats['created']} created, "
            f"{self.stats['reused']} reused, "
            f"{self.stats['failed']} failed"
        )

