"""
Scraping Control Center - Centralized task management with dynamic worker pool.

This module implements a centralized control center that maintains a constant
pool of active workers (default 8) and dynamically assigns tasks from a unified
queue. When a worker completes, it immediately picks up the next task, ensuring
maximum efficiency and resource utilization.
"""
import sys
import time
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from threading import Lock, Event, Thread
from typing import Dict, List, Optional, Callable, Any, Type
from pathlib import Path
import json
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import scrapers
from scrapers.base_scraper import BaseScraper
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.youtube_comments_scraper import YouTubeCommentsScraper
from scrapers.bilibili_scraper import BilibiliScraper
from scrapers.bilibili_comments_scraper import BilibiliCommentsScraper
from scrapers.article_scraper import ArticleScraper
from scrapers.reddit_scraper import RedditScraper
import json


def _save_single_result(result: Dict[str, Any], batch_id: str, scraper_name: str, link_type: str) -> Optional[Path]:
    """
    Save a single scraping result to JSON file immediately.
    
    This function saves results incrementally as each item completes,
    rather than waiting for the entire batch to finish.
    
    Args:
        result: Single extraction result dictionary
        batch_id: Batch ID
        scraper_name: Name of scraper (for filename)
        link_type: Type of links (for filename)
    
    Returns:
        Path to saved file if successful, None otherwise
    """
    if not result or not result.get('success'):
        return None
    
    # Create output directory structure
    output_dir = Path(__file__).parent.parent.parent / "tests" / "results"
    output_dir.mkdir(exist_ok=True, parents=True)
    batch_folder = output_dir / f"run_{batch_id}"
    batch_folder.mkdir(exist_ok=True)  # Create batch folder if it doesn't exist
    
    # Comments scrapers need special handling - they accumulate comments
    # For now, we'll save individual comment files per link_id
    if scraper_name in ['youtubecomments', 'bilibilicomments']:
        # For comments, save individual files per link_id
        # Format: {batch_id}_{TYPE}_{link_id}_cmts.json or {batch_id}_{TYPE}_{link_id}_cmt.json
        type_prefix = 'YT' if scraper_name == 'youtubecomments' else 'BILI'
        suffix = 'cmts' if scraper_name == 'youtubecomments' else 'cmt'
        link_id = result.get('link_id', 'unknown')
        filename = batch_folder / f"{batch_id}_{type_prefix}_{link_id}_{suffix}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            # FIX 2: Verify file is written and readable
            if _verify_file_written(filename):
                logger.debug(f"[{scraper_name}] Saved and verified result file: {filename.name}")
                return filename
            else:
                logger.error(f"[{scraper_name}] File {filename.name} was not written correctly")
                return None
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")
            return None
    else:
        # Transcript/article scrapers save one file per link
        # Filename format: {batch_id}_{TYPE}_{link_id}_{suffix}.json
        type_prefix_map = {
            'youtube': 'YT',
            'bilibili': 'BILI',
            'article': 'AR',
            'reddit': 'RD',
        }
        type_prefix = type_prefix_map.get(link_type, link_type.upper()[:4])
        
        suffix_map = {
            'youtube': 'tsct',
            'bilibili': 'tsct',
            'article': 'tsct',
            'reddit': 'tsct',
        }
        suffix = suffix_map.get(link_type, 'tsct')
        
        link_id = result.get('link_id', 'unknown')
        filename = batch_folder / f"{batch_id}_{type_prefix}_{link_id}_{suffix}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            # FIX 2: Verify file is written and readable
            if _verify_file_written(filename):
                logger.debug(f"[{scraper_name}] Saved and verified result file: {filename.name}")
                return filename
            else:
                logger.error(f"[{scraper_name}] File {filename.name} was not written correctly")
                return None
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")
            return None


def _verify_file_written(filename: Path, max_retries: int = 5, retry_delay: float = 0.1) -> bool:
    """
    Verify that a file has been fully written to disk.
    
    Args:
        filename: Path to the file to verify
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        True if file exists and is readable, False otherwise
    """
    import time
    
    for attempt in range(max_retries):
        try:
            # Check if file exists
            if not filename.exists():
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                logger.warning(f"File {filename} does not exist after {attempt + 1} attempts")
                return False
            
            # Try to open and read the file to ensure it's fully written
            with open(filename, 'r', encoding='utf-8') as f:
                # Try to parse as JSON to ensure it's complete
                json.load(f)
            
            # File exists and is valid JSON
            return True
        except (IOError, OSError, json.JSONDecodeError) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            logger.warning(f"File {filename} verification failed after {attempt + 1} attempts: {e}")
            return False
    
    return False


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class WorkerState(Enum):
    """Worker state enumeration."""
    IDLE = 'idle'
    PROCESSING = 'processing'
    TERMINATED = 'terminated'


@dataclass
class ScrapingTask:
    """Represents a single scraping task."""
    task_id: str
    link_id: str
    url: str
    link_type: str  # 'youtube', 'bilibili', 'article', 'reddit'
    scraper_type: str  # 'youtube', 'youtubecomments', 'bilibili', 'bilibilicomments', 'article', 'reddit'
    batch_id: str
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class Worker:
    """Represents a worker thread."""
    worker_id: str
    thread: Optional[Thread] = None
    current_task: Optional[ScrapingTask] = None
    state: WorkerState = WorkerState.IDLE
    scraper_instance: Optional[BaseScraper] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class TaskQueueManager:
    """Manages the unified task queue."""
    
    def __init__(self):
        self._queue: Queue = Queue()
        self._lock = Lock()
        self._total_added = 0
        self._total_processed = 0
    
    def add_task(self, task: ScrapingTask) -> None:
        """Add a task to the queue."""
        with self._lock:
            self._queue.put(task)
            self._total_added += 1
            logger.debug(f"Task {task.task_id} added to queue (queue_size={self._queue.qsize()})")
    
    def add_tasks(self, tasks: List[ScrapingTask]) -> None:
        """Add multiple tasks to the queue."""
        with self._lock:
            for task in tasks:
                self._queue.put(task)
                self._total_added += 1
            logger.debug(f"Added {len(tasks)} tasks to queue (queue_size={self._queue.qsize()})")
    
    def get_next_task(self, timeout: float = 0.1) -> Optional[ScrapingTask]:
        """Get the next task from the queue (thread-safe)."""
        try:
            task = self._queue.get(timeout=timeout)
            with self._lock:
                self._total_processed += 1
            return task
        except Empty:
            return None
    
    def get_nowait(self) -> Optional[ScrapingTask]:
        """Get the next task from the queue without blocking (thread-safe)."""
        try:
            task = self._queue.get_nowait()
            with self._lock:
                self._total_processed += 1
            return task
        except Empty:
            return None
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def return_task(self, task: ScrapingTask) -> None:
        """
        Return a task to the queue (for retry after validation failure).
        
        This is used when a task is dequeued but found to be invalid
        (e.g., already completed). The task is returned to the end of the queue.
        """
        with self._lock:
            self._queue.put(task)
            # Adjust processed count since we're putting it back
            self._total_processed = max(0, self._total_processed - 1)
    
    def get_statistics(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._lock:
            return {
                'queue_size': self._queue.qsize(),
                'total_added': self._total_added,
                'total_processed': self._total_processed,
                'pending': self._total_added - self._total_processed
            }


class ScraperFactory:
    """Factory for creating scraper instances based on link type."""
    
    # Map link types to scraper classes
    # v3: Only transcript scrapers are active; comment scrapers removed from map.
    SCRAPER_MAP: Dict[str, Dict[str, Type[BaseScraper]]] = {
        'youtube': {
            'youtube': YouTubeScraper,
        },
        'bilibili': {
            'bilibili': BilibiliScraper,
        },
        'article': {
            'article': ArticleScraper,
        },
        'reddit': {
            'reddit': RedditScraper,
        },
    }
    
    @classmethod
    def create_scraper(
        cls,
        scraper_type: str,
        progress_callback: Optional[Callable[[dict], None]] = None,
        cancellation_checker: Optional[Callable[[], bool]] = None,
        **kwargs
    ) -> BaseScraper:
        """
        Create a scraper instance based on scraper type.
        
        Args:
            scraper_type: Type of scraper ('youtube', 'youtubecomments', etc.)
            progress_callback: Optional progress callback
            cancellation_checker: Optional cancellation checker
            **kwargs: Additional scraper-specific parameters
        
        Returns:
            Scraper instance
        """
        # Find the scraper class
        scraper_class = None
        for link_type, scrapers in cls.SCRAPER_MAP.items():
            if scraper_type in scrapers:
                scraper_class = scrapers[scraper_type]
                break
        
        if scraper_class is None:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        
        # Create scraper instance with callbacks
        scraper_kwargs = kwargs.copy()
        if progress_callback:
            scraper_kwargs['progress_callback'] = progress_callback
        if cancellation_checker:
            scraper_kwargs['cancellation_checker'] = cancellation_checker
        
        logger.debug(f"Creating scraper: {scraper_type} with kwargs: {scraper_kwargs}")
        return scraper_class(**scraper_kwargs)
    
    @classmethod
    def get_scraper_config(cls, link_type: str, scraper_type: str) -> Dict[str, Any]:
        """Get default configuration for a scraper type."""
        # Default configurations
        configs = {
            'youtube': {'headless': False},
            'bilibili': {},
            'article': {'headless': True},
            'reddit': {'headless': False},
        }
        return configs.get(scraper_type, {})


class TaskStateTracker:
    """Thread-safe task state tracker."""
    
    def __init__(self):
        self._lock = Lock()
        self._tasks: Dict[str, ScrapingTask] = {}
    
    def add_task(self, task: ScrapingTask) -> None:
        """Add a task to the tracker."""
        with self._lock:
            self._tasks[task.task_id] = task
    
    def update_task_state(
        self,
        task_id: str,
        status: TaskStatus,
        **kwargs
    ) -> None:
        """Update task state (thread-safe)."""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                for key, value in kwargs.items():
                    setattr(task, key, value)
    
    def get_task_state(self, task_id: str) -> Optional[ScrapingTask]:
        """Get task state (thread-safe)."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScrapingTask]:
        """Get all tasks (thread-safe)."""
        with self._lock:
            return list(self._tasks.values())
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics (thread-safe)."""
        with self._lock:
            stats = {
                'pending': sum(1 for t in self._tasks.values()
                              if t.status == TaskStatus.PENDING),
                'processing': sum(1 for t in self._tasks.values()
                                if t.status == TaskStatus.PROCESSING),
                'completed': sum(1 for t in self._tasks.values()
                                if t.status == TaskStatus.COMPLETED),
                'failed': sum(1 for t in self._tasks.values()
                             if t.status == TaskStatus.FAILED),
                'cancelled': sum(1 for t in self._tasks.values()
                               if t.status == TaskStatus.CANCELLED),
                'total': len(self._tasks),
            }
            return stats


class ScrapingControlCenter:
    """
    Centralized control center for managing scraping tasks with dynamic worker pool.
    
    Maintains a constant pool of active workers (default 8) and dynamically assigns
    tasks from a unified queue. When a worker completes, it immediately picks up
    the next task, ensuring maximum efficiency.
    """
    
    def __init__(
        self,
        worker_pool_size: int = 8,
        progress_callback: Optional[Callable[[dict], None]] = None,
        cancellation_checker: Optional[Callable[[], bool]] = None,
        **scraper_kwargs
    ):
        """
        Initialize the control center.
        
        Args:
            worker_pool_size: Number of parallel workers (default: 8)
            progress_callback: Optional progress callback function
            cancellation_checker: Optional cancellation checker function
            **scraper_kwargs: Additional scraper configuration
        """
        self.worker_pool_size = worker_pool_size
        self.progress_callback = progress_callback
        self.cancellation_checker = cancellation_checker
        self.scraper_kwargs = scraper_kwargs
        
        # Core components
        self.task_queue = TaskQueueManager()
        self.state_tracker = TaskStateTracker()
        self.scraper_factory = ScraperFactory()
        
        # Worker management
        self.workers: Dict[str, Worker] = {}
        self.assignment_lock = Lock()  # CRITICAL: Protects task assignment
        self._lock_holder = None  # Track which worker is holding the lock (for debugging)
        self._lock_holder_lock = Lock()  # Protects _lock_holder
        self.shutdown_event = Event()
        self.race_condition_count = 0
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_task(self, task: ScrapingTask) -> None:
        """Add a task to the queue and tracker."""
        # Only add tasks that are in PENDING state
        # If a task is already COMPLETED or FAILED, don't add it to the queue
        if task.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            logger.warning(
                f"Skipping task {task.task_id} (link_id={task.link_id}) - "
                f"status is {task.status}, not PENDING"
            )
            # Still add to tracker for tracking purposes, but not to queue
            self.state_tracker.add_task(task)
            return
        
        self.state_tracker.add_task(task)
        self.task_queue.add_task(task)
    
    def add_tasks(self, tasks: List[ScrapingTask]) -> None:
        """Add multiple tasks."""
        valid_tasks = []
        for task in tasks:
            # Only add tasks that are in PENDING state
            if task.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                logger.warning(
                    f"Skipping task {task.task_id} (link_id={task.link_id}) - "
                    f"status is {task.status}, not PENDING"
                )
                # Still add to tracker for tracking purposes
                self.state_tracker.add_task(task)
            else:
                valid_tasks.append(task)
                self.state_tracker.add_task(task)
        
        # Only add valid tasks to queue
        if valid_tasks:
            self.task_queue.add_tasks(valid_tasks)
    
    def _maybe_start_additional_worker(self) -> bool:
        """
        V3: Dynamically start an additional worker if:
        1. There are tasks in queue
        2. There are unstarted workers
        3. We haven't reached the max pool size
        
        Must be called while holding assignment_lock.
        
        Returns:
            True if a new worker was started, False otherwise
        """
        # Count active workers (those with threads)
        active_workers = sum(1 for w in self.workers.values() if w.thread is not None)
        
        # Count tasks in queue
        queue_size = self.task_queue.get_queue_size()
        
        # If we have work and available slots, start a new worker
        if queue_size > 0 and active_workers < self.worker_pool_size:
            # Find first unstarted worker
            for worker_id, worker in self.workers.items():
                if worker.thread is None:
                    # Start this worker
                    thread = Thread(
                        target=self._worker_loop,
                        args=(worker_id,),
                        name=f"ScrapingWorker-{worker_id}",
                        daemon=False
                    )
                    worker.thread = thread
                    thread.start()
                    logger.info(
                        f"✨ [V3] Started additional worker {worker_id} "
                        f"(active: {active_workers+1}/{self.worker_pool_size}, queue: {queue_size})"
                    )
                    return True
        
        return False
    
    def _assign_task_to_worker(self, worker_id: str) -> bool:
        """
        Atomically assign a task to a worker.
        
        CRITICAL: This method MUST be called while holding assignment_lock.
        It does NOT acquire the lock itself to avoid deadlocks when called
        from within _handle_worker_completion.
        
        Returns:
            True if task was assigned, False if no tasks available
        """
        # NOTE: Lock is NOT acquired here - caller must hold assignment_lock
        # Check if worker is actually idle (double-check pattern)
        worker = self.workers[worker_id]
        if worker.state != WorkerState.IDLE:
            return False  # Worker already has a task
        
        # Check if queue has tasks
        if self.task_queue.is_empty():
            return False  # No tasks available
        
        # FIX 1: Check task state BEFORE dequeuing to prevent re-entry
        # We need to peek at tasks without removing them, but Queue doesn't support peek
        # So we'll use a retry loop: dequeue, check, and REMOVE invalid tasks (don't return to queue)
        max_retries = 50  # Increased to handle more invalid tasks
        retry_count = 0
        invalid_tasks_removed = 0
        
        while retry_count < max_retries:
            # Get task from queue (atomic operation)
            task = self.task_queue.get_nowait()
            if task is None:
                if invalid_tasks_removed > 0:
                    logger.warning(
                        f"[WORKER-{worker_id}] Queue emptied after removing {invalid_tasks_removed} invalid tasks. "
                        f"Remaining queue size: {self.task_queue.get_queue_size()}"
                    )
                return False  # Queue was emptied
            
            # CRITICAL: Verify task is still in pending state BEFORE processing
            # This prevents reprocessing of failed/completed tasks
            current_task = self.state_tracker.get_task_state(task.task_id)
            if current_task:
                if current_task.status == TaskStatus.FAILED:
                    # Task already failed - remove it permanently (don't reprocess, don't return to queue)
                    self.race_condition_count += 1
                    invalid_tasks_removed += 1
                    logger.warning(
                        f"[RACE_DETECTED] Task {task.task_id} (link_id={task.link_id}) already FAILED - "
                        f"removing from queue permanently. Total races: {self.race_condition_count}, "
                        f"Invalid removed: {invalid_tasks_removed}"
                    )
                    # Don't return to queue - task is effectively removed
                    retry_count += 1
                    continue
                elif current_task.status == TaskStatus.COMPLETED:
                    # Task already completed - remove it permanently (don't reprocess, don't return to queue)
                    self.race_condition_count += 1
                    invalid_tasks_removed += 1
                    logger.warning(
                        f"[RACE_DETECTED] Task {task.task_id} (link_id={task.link_id}) already COMPLETED - "
                        f"removing from queue permanently. Total races: {self.race_condition_count}, "
                        f"Invalid removed: {invalid_tasks_removed}"
                    )
                    # Don't return to queue - task is effectively removed
                    retry_count += 1
                    continue
                elif current_task.status != TaskStatus.PENDING:
                    # Task is in an unexpected state (PROCESSING, CANCELLED, etc.)
                    # If PROCESSING, it might be assigned to another worker - return to queue
                    # If CANCELLED or other states, remove it
                    if current_task.status == TaskStatus.PROCESSING:
                        # Task is being processed by another worker - return to queue
                        self.race_condition_count += 1
                        logger.debug(
                            f"[RACE_DETECTED] Task {task.task_id} (link_id={task.link_id}) is PROCESSING "
                            f"(assigned to {current_task.assigned_worker_id}) - returning to queue. "
                            f"Total races: {self.race_condition_count}"
                        )
                        self.task_queue.return_task(task)
                        retry_count += 1
                        continue
                    else:
                        # Other invalid states - remove permanently (don't return to queue)
                        self.race_condition_count += 1
                        invalid_tasks_removed += 1
                        logger.warning(
                            f"[RACE_DETECTED] Task {task.task_id} (link_id={task.link_id}) in invalid state "
                            f"{current_task.status} - removing from queue. Total races: {self.race_condition_count}, "
                            f"Invalid removed: {invalid_tasks_removed}"
                        )
                        # Don't return to queue - task is effectively removed
                        retry_count += 1
                        continue
            
            # Task is valid (PENDING or not tracked yet) - proceed with assignment
            # Atomically update task state and assign to worker
            task.status = TaskStatus.PROCESSING
            task.assigned_worker_id = worker_id
            task.started_at = datetime.now()
            
            # Update worker state
            worker.current_task = task
            worker.state = WorkerState.PROCESSING
            
            # Update state tracker
            self.state_tracker.update_task_state(
                task.task_id,
                TaskStatus.PROCESSING,
                assigned_worker_id=worker_id,
                started_at=task.started_at
            )
            
            if invalid_tasks_removed > 0:
                logger.info(
                    f"[WORKER-{worker_id}] Task {task.task_id} (link_id={task.link_id}) assigned after "
                    f"removing {invalid_tasks_removed} invalid tasks"
                )
            else:
                logger.debug(f"Task {task.task_id} assigned to worker {worker_id}")
            return True
        
        # FIX RACE #5: If we've exhausted retries, check if queue only contains invalid tasks
        queue_size = self.task_queue.get_queue_size()
        logger.error(
            f"[WORKER-{worker_id}] ⚠️ Exhausted retries ({max_retries}) trying to assign task! "
            f"Removed {invalid_tasks_removed} invalid tasks. "
            f"Remaining queue size: {queue_size}. "
            f"This indicates the queue may be stuck with invalid tasks."
        )
        
        # CRITICAL FIX: If queue still has items, check if they're all invalid
        # If so, remove them all to unblock workers
        if queue_size > 0:
            logger.warning(
                f"[WORKER-{worker_id}] Queue has {queue_size} items remaining. "
                f"Checking if all are invalid and removing them..."
            )
            
            # Remove all invalid tasks from queue
            remaining_invalid = 0
            valid_tasks_found = []
            temp_tasks = []
            
            # Dequeue all remaining tasks to check their states
            while True:
                try:
                    temp_task = self.task_queue.get_nowait()
                    if temp_task:
                        temp_tasks.append(temp_task)
                    else:
                        break
                except Empty:
                    break
            
            # Check each task and only return valid ones to queue
            for temp_task in temp_tasks:
                task_state = self.state_tracker.get_task_state(temp_task.task_id)
                if task_state:
                    # Check if task is invalid (FAILED, COMPLETED, or CANCELLED)
                    if task_state.status in (TaskStatus.FAILED, TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                        remaining_invalid += 1
                        logger.debug(
                            f"[WORKER-{worker_id}] Removing invalid task {temp_task.task_id} "
                            f"(status={task_state.status}) from queue permanently"
                        )
                        # Don't return to queue - task is removed
                    elif task_state.status == TaskStatus.PROCESSING:
                        # Task is being processed by another worker - return to queue
                        valid_tasks_found.append(temp_task)
                        logger.debug(
                            f"[WORKER-{worker_id}] Returning PROCESSING task {temp_task.task_id} "
                            f"to queue (assigned to {task_state.assigned_worker_id})"
                        )
                    elif task_state.status == TaskStatus.PENDING:
                        # Valid pending task - return to queue
                        valid_tasks_found.append(temp_task)
                        logger.debug(
                            f"[WORKER-{worker_id}] Returning valid PENDING task {temp_task.task_id} to queue"
                        )
                    else:
                        # Unknown state - remove it
                        remaining_invalid += 1
                        logger.warning(
                            f"[WORKER-{worker_id}] Removing task {temp_task.task_id} "
                            f"with unknown status {task_state.status}"
                        )
                else:
                    # Task not tracked - assume it's valid (new task)
                    valid_tasks_found.append(temp_task)
                    logger.debug(
                        f"[WORKER-{worker_id}] Returning untracked task {temp_task.task_id} to queue (assuming valid)"
                    )
            
            # Return only valid tasks to queue
            for valid_task in valid_tasks_found:
                self.task_queue.return_task(valid_task)
            
            if remaining_invalid > 0:
                logger.warning(
                    f"[WORKER-{worker_id}] Cleaned up {remaining_invalid} invalid tasks from queue. "
                    f"Returned {len(valid_tasks_found)} valid tasks. "
                    f"New queue size: {self.task_queue.get_queue_size()}"
                )
            
            # If we removed all tasks and queue is now empty, return False
            if len(valid_tasks_found) == 0:
                logger.info(
                    f"[WORKER-{worker_id}] All remaining tasks were invalid. Queue is now empty. "
                    f"Workers can proceed to completion."
                )
                return False
        
        return False
    
    def _handle_worker_completion(
        self,
        worker_id: str,
        task: ScrapingTask,
        result: Dict[str, Any]
    ) -> None:
        """
        Handle worker completion atomically.
        
        CRITICAL: This operation is protected by assignment_lock to ensure
        atomic completion + immediate task replacement.
        """
        logger.info(f"🔍 [WORKER-{worker_id}] _handle_worker_completion ENTERED for task {task.task_id}, success={result.get('success')}")
        try:
            lock_wait_start = time.time()
            logger.info(f"🔒 [WORKER-{worker_id}] About to acquire lock for task {task.task_id}")
            with self.assignment_lock:  # CRITICAL: Atomic completion + replacement
                lock_wait_time = time.time() - lock_wait_start
                if lock_wait_time > 0.1:  # Log if we waited more than 100ms
                    logger.warning(f"⏱️ [WORKER-{worker_id}] Waited {lock_wait_time:.3f}s to acquire lock for task {task.task_id}")
                
                logger.info(f"✅ [WORKER-{worker_id}] Acquired lock in _handle_worker_completion for task {task.task_id}")
                
                # FIX RACE #1: Check if task is already completed INSIDE the lock
                # This prevents multiple workers from both seeing the task as incomplete
                # and then both sending completion messages
                current_task_state = self.state_tracker.get_task_state(task.task_id)
                is_duplicate = current_task_state and current_task_state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                if is_duplicate:
                    logger.warning(
                        f"⚠️ [WORKER-{worker_id}] Task {task.task_id} already {current_task_state.status.name} (duplicate completion detected). "
                        f"Skipping state update and message sending. Will only reset worker to idle and try to assign new task."
                    )
                    # Still reset worker state to idle so it can pick up new tasks
                    worker = self.workers[worker_id]
                    worker.current_task = None
                    worker.state = WorkerState.IDLE
                    
                    # Try to assign a new task immediately
                    new_task_assigned = self._assign_task_to_worker(worker_id)
                    if new_task_assigned:
                        new_task = self.workers[worker_id].current_task
                        logger.info(
                            f"[WORKER-{worker_id}] Assigned new task {new_task.task_id} after duplicate completion "
                            f"(queue_size={self.task_queue.get_queue_size()})"
                        )
                    
                    # Return early - don't send any messages or update state
                    return
                
                # Update task state (this is the first completion since we checked above)
                task_status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
                task.status = task_status
                task.completed_at = datetime.now()
                task.result = result
                if not result.get('success'):
                    task.error = result.get('error')
                
                # Update worker state to idle
                worker = self.workers[worker_id]
                worker.current_task = None
                worker.state = WorkerState.IDLE
                # Increment counters for this completion
                if result.get('success'):
                    worker.tasks_completed += 1
                else:
                    worker.tasks_failed += 1
                
                # Update state tracker (idempotent)
                self.state_tracker.update_task_state(
                    task.task_id,
                    task_status,
                    completed_at=task.completed_at,
                    result=result,
                    error=task.error
                )
                
                logger.info(
                    f"[WORKER-{worker_id}] Completed task {task.task_id} "
                    f"(success={result.get('success')}, "
                    f"total_completed={worker.tasks_completed}, total_failed={worker.tasks_failed})"
                )
            
            # FIX RACE #3 (IMPROVED): Save file BEFORE assigning new task AND before sending completion message
            # This ensures:
            # 1. The JSON file exists before workflow_service tries to load it
            # 2. The JSON file exists before we start a new scraper (prevents resource contention)
            # 3. Worker is idle and ready for either: new scraper OR letting summarization proceed
            logger.info(f"💾 [WORKER-{worker_id}] Saving result file for task {task.task_id} before assigning new work")
            file_saved = False
            if result.get('success'):
                try:
                    saved_file = _save_single_result(result, task.batch_id, task.scraper_type, task.link_type)
                    if saved_file:
                        file_saved = True
                        logger.info(f"✅ [WORKER-{worker_id}] File saved successfully: {saved_file.name}")
                    else:
                        logger.warning(f"⚠️ [WORKER-{worker_id}] File save returned None for task {task.task_id}")
                except Exception as save_error:
                    logger.error(
                        f"❌ [WORKER-{worker_id}] Error saving result for task {task.task_id}: {save_error}",
                        exc_info=True
                    )
            
            # Send completion message AFTER file is saved
            logger.info(f"📤 [WORKER-{worker_id}] Preparing to send completion message for task {task.task_id} (file_saved={file_saved})")
            if self.progress_callback:
                try:
                    # Determine status and message
                    status = 'success' if result.get('success') else 'failed'
                    word_count = result.get('word_count', 0)
                    error_msg = result.get('error') or task.error
                    
                    if status == 'success':
                        message_text = f"Completed: {word_count} words extracted"
                    else:
                        message_text = f"Failed: {error_msg}" if error_msg else "Failed: Unknown error"
                    
                    # Send scraping:complete_link message (based on task_id, not link_id)
                    completion_message = {
                        'type': 'scraping:complete_link',
                        'batch_id': task.batch_id,
                        'link_id': task.link_id,
                        'url': task.url,
                        'status': status,
                        'message': message_text,
                        'scraper': task.scraper_type,
                        'worker_id': worker_id,
                        'word_count': word_count,
                        'error': error_msg if status == 'failed' else None,
                        'metadata': {
                            'source': task.scraper_type,
                            'task_id': task.task_id,  # Include task_id for tracking
                            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                            'file_saved': file_saved  # Indicate if file was saved
                        }
                    }
                    
                    logger.info(
                        f"📤 [WORKER-{worker_id}] Sending completion message for task {task.task_id}: "
                        f"status={status}, link_id={task.link_id}, batch_id={task.batch_id}, "
                        f"word_count={word_count}, scraper={task.scraper_type}"
                    )
                    
                    self.progress_callback(completion_message)
                    logger.info(
                        f"✅ [WORKER-{worker_id}] Completion message sent successfully for task {task.task_id}"
                    )
                except Exception as callback_error:
                    logger.error(
                        f"❌ [WORKER-{worker_id}] Error sending completion message for task {task.task_id}: {callback_error}",
                        exc_info=True
                    )
            else:
                logger.warning(f"⚠️ [WORKER-{worker_id}] No progress_callback set! Cannot send completion message for task {task.task_id}")
            
            # NOW assign new task AFTER file saved + completion message sent
            # This ensures proper sequencing: scrape done → JSON saved → completion confirmed → new scraper starts
            with self.assignment_lock:
                # V3: Try to start an additional worker if needed
                self._maybe_start_additional_worker()
                
                # Assign new task to current worker
                new_task_assigned = self._assign_task_to_worker(worker_id)
                if new_task_assigned:
                    new_task = self.workers[worker_id].current_task
                    logger.info(
                        f"[WORKER-{worker_id}] Assigned new task {new_task.task_id} after completing {task.task_id} "
                        f"(queue_size={self.task_queue.get_queue_size()})"
                    )
                else:
                    queue_size = self.task_queue.get_queue_size()
                    logger.info(
                        f"[WORKER-{worker_id}] No new task available after completing {task.task_id} "
                        f"(queue_size={queue_size})"
                    )
                    
        except Exception as e:
            logger.error(
                f"❌ [WORKER-{worker_id}] CRITICAL ERROR in completion handler for task {task.task_id}: {e}",
                exc_info=True
            )
            logger.error(
                f"❌ [WORKER-{worker_id}] Task details: task_id={task.task_id}, link_id={task.link_id}, "
                f"batch_id={task.batch_id}, worker_current_task={self.workers[worker_id].current_task.task_id if self.workers[worker_id].current_task else None}"
            )
            # Try to at least reset worker state to prevent deadlock
            try:
                with self.assignment_lock:
                    worker = self.workers[worker_id]
                    worker.current_task = None
                    worker.state = WorkerState.IDLE
            except Exception as reset_error:
                logger.error(f"[WORKER-{worker_id}] Failed to reset worker state: {reset_error}", exc_info=True)
    
    def _process_task(self, worker_id: str, task: ScrapingTask) -> Dict[str, Any]:
        """
        Process a single task.
        
        This runs outside the lock for performance.
        """
        worker = self.workers[worker_id]
        scraper = None
        
        try:
            # Create scraper instance for this task
            scraper_config = self.scraper_factory.get_scraper_config(
                task.link_type,
                task.scraper_type
            )
            scraper_config.update(self.scraper_kwargs)
            
            # Create progress callback wrapper
            def progress_wrapper(message: dict):
                if self.progress_callback:
                    # Add control center context
                    message['worker_id'] = worker_id
                    message['queue_position'] = self.task_queue.get_queue_size()
                    message['batch_id'] = task.batch_id
                    message['link_id'] = task.link_id
                    message['url'] = task.url
                    
                    # Add type field if missing (scraper progress messages don't have it)
                    if 'type' not in message:
                        message['type'] = 'scraping:progress'
                    
                    self.progress_callback(message)
            
            scraper = self.scraper_factory.create_scraper(
                task.scraper_type,
                progress_callback=progress_wrapper,
                cancellation_checker=self.cancellation_checker,
                **scraper_config
            )
            
            worker.scraper_instance = scraper
            
            # Send start_link message to notify that this task has started
            if self.progress_callback:
                try:
                    start_message = {
                        'type': 'scraping:start_link',
                        'batch_id': task.batch_id,
                        'link_id': task.link_id,
                        'url': task.url,
                        'scraper': task.scraper_type,
                        'worker_id': worker_id,
                        'message': f'Starting {task.scraper_type} extraction'
                    }
                    self.progress_callback(start_message)
                    logger.debug(
                        f"[WORKER-{worker_id}] Sent start_link message for task {task.task_id}: "
                        f"link_id={task.link_id}"
                    )
                except Exception as callback_error:
                    logger.warning(
                        f"[WORKER-{worker_id}] Error sending start_link message for task {task.task_id}: {callback_error}"
                    )
            
            # Extract content
            logger.info(
                f"[WORKER-{worker_id}] Processing task {task.task_id}: "
                f"{task.url} (link_id={task.link_id}, type={task.scraper_type})"
            )
            
            result = scraper.extract(task.url, batch_id=task.batch_id, link_id=task.link_id)
            
            logger.info(
                f"[WORKER-{worker_id}] Scraper.extract() returned for task {task.task_id}: "
                f"success={result.get('success')}, word_count={result.get('word_count', 0)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"[WORKER-{worker_id}] Error processing task {task.task_id}: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'url': task.url,
                'link_id': task.link_id,
                'batch_id': task.batch_id,
                'error': str(e),
                'word_count': 0
            }
        finally:
            # Cleanup scraper
            if scraper:
                try:
                    scraper.close()
                    worker.scraper_instance = None
                except Exception as e:
                    logger.warning(f"[WORKER-{worker_id}] Error closing scraper: {e}")
    
    def _worker_loop(self, worker_id: str) -> None:
        """
        Worker main loop with race condition protection.
        
        This loop continuously checks for tasks to process. Tasks can be assigned either:
        1. By the loop itself (when worker is idle and queue has tasks)
        2. By _handle_worker_completion (when a task completes and a new one is immediately assigned)
        """
        logger.info(f"[WORKER-{worker_id}] Worker started")
        
        while not self.shutdown_event.is_set():
            # Check for cancellation
            if self.cancellation_checker and self.cancellation_checker():
                logger.info(f"[WORKER-{worker_id}] Cancellation detected, stopping")
                break
            
            # Get worker reference (fast check, no lock)
            worker = self.workers[worker_id]
            
            # CRITICAL: Check if worker already has a task assigned (could be assigned by _handle_worker_completion)
            # This ensures we process tasks assigned externally, not just tasks we assign ourselves
            if worker.state == WorkerState.PROCESSING and worker.current_task is not None:
                # Worker has a task assigned - process it
                task = worker.current_task
                try:
                    logger.info(f"[WORKER-{worker_id}] Starting to process task {task.task_id} (link_id={task.link_id}, type={task.scraper_type})")
                    result = self._process_task(worker_id, task)
                    logger.debug(f"[WORKER-{worker_id}] Task {task.task_id} processing complete, result success={result.get('success')}")
                    logger.info(f"🔍 [WORKER-{worker_id}] About to call _handle_worker_completion for task {task.task_id}")
                    try:
                        self._handle_worker_completion(worker_id, task, result)
                        logger.info(f"✅ [WORKER-{worker_id}] _handle_worker_completion returned successfully for task {task.task_id}")
                    except Exception as completion_ex:
                        logger.error(
                            f"❌ [WORKER-{worker_id}] Exception in _handle_worker_completion for task {task.task_id}: {completion_ex}",
                            exc_info=True
                        )
                    logger.debug(f"[WORKER-{worker_id}] Completion handler finished for task {task.task_id}")
                    # After completion, loop will continue and check for new task
                    continue
                except Exception as e:
                    logger.error(f"[WORKER-{worker_id}] Unexpected error processing task {task.task_id}: {e}", exc_info=True)
                    try:
                        self._handle_worker_completion(worker_id, task, {
                            'success': False,
                            'error': str(e),
                            'url': task.url,
                            'link_id': task.link_id,
                            'batch_id': task.batch_id,
                            'word_count': 0
                        })
                    except Exception as completion_error:
                        logger.error(f"[WORKER-{worker_id}] Error in completion handler: {completion_error}", exc_info=True)
                        # Manually reset worker state to prevent deadlock
                        with self.assignment_lock:
                            worker.state = WorkerState.IDLE
                            worker.current_task = None
                    continue
            
            # Worker is idle - try to get a task (atomic operation with lock)
            if worker.state == WorkerState.IDLE:
                # FIX RACE #4: Add periodic logging to help diagnose worker stalls
                # Log worker state every 10 iterations when idle
                if not hasattr(worker, '_idle_iterations'):
                    worker._idle_iterations = 0
                worker._idle_iterations += 1
                
                if worker._idle_iterations % 10 == 0:
                    queue_size = self.task_queue.get_queue_size()
                    stats = self.state_tracker.get_statistics()
                    logger.info(
                        f"[WORKER-{worker_id}] Still idle after {worker._idle_iterations} iterations. "
                        f"Queue size: {queue_size}, "
                        f"Tasks: pending={stats['pending']}, processing={stats['processing']}, "
                        f"completed={stats['completed']}, failed={stats['failed']}"
                    )
                
                with self.assignment_lock:
                    task_assigned = self._assign_task_to_worker(worker_id)
                
                if task_assigned:
                    # Task was assigned - reset idle counter and process in next iteration
                    worker._idle_iterations = 0
                    continue
                else:
                    # No tasks available, wait a bit before checking again
                    time.sleep(0.1)
                    continue
            else:
                # Worker is in an unexpected state (shouldn't happen, but handle gracefully)
                logger.warning(f"[WORKER-{worker_id}] Worker in unexpected state: {worker.state}, sleeping...")
                time.sleep(0.1)
                continue
        
        # Mark worker as terminated
        with self.assignment_lock:
            self.workers[worker_id].state = WorkerState.TERMINATED
        
        logger.info(f"[WORKER-{worker_id}] Worker terminated")
    
    def start(self) -> None:
        """
        Start the control center and worker pool.
        
        V3 WORKFLOW: Start workers one at a time to avoid resource stampede.
        Each worker will naturally pick up a task when ready, creating a gradual ramp-up.
        """
        if self.start_time:
            logger.warning("Control center already started")
            return
        
        self.start_time = datetime.now()
        logger.info(
            f"Starting control center with {self.worker_pool_size} workers "
            f"(queue_size={self.task_queue.get_queue_size()})"
        )
        
        # V3: Start with ONLY 1 worker initially
        # Additional workers will be started dynamically as needed
        initial_workers = min(1, self.worker_pool_size)
        
        for i in range(initial_workers):
            worker_id = f"worker_{i+1}"
            worker = Worker(worker_id=worker_id)
            self.workers[worker_id] = worker
            
            # Create and start thread
            thread = Thread(
                target=self._worker_loop,
                args=(worker_id,),
                name=f"ScrapingWorker-{worker_id}",
                daemon=False
            )
            worker.thread = thread
            thread.start()
            logger.info(f"Started worker {i+1}")
        
        # Create remaining workers but DON'T start them yet
        for i in range(initial_workers, self.worker_pool_size):
            worker_id = f"worker_{i+1}"
            worker = Worker(worker_id=worker_id)
            worker.state = WorkerState.IDLE  # Mark as available but not started
            self.workers[worker_id] = worker
            logger.info(f"Worker {i+1} created (not started yet)")
        
        logger.info(f"Control center started: {initial_workers}/{self.worker_pool_size} workers active initially")
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
        
        Returns:
            True if all tasks completed, False if timeout
        """
        start_wait = time.time()
        
        while True:
            # Check if all tasks are done
            stats = self.state_tracker.get_statistics()
            queue_stats = self.task_queue.get_statistics()
            
            pending = stats['pending'] + stats['processing']
            
            if pending == 0 and queue_stats['queue_size'] == 0:
                # All tasks completed
                self.end_time = datetime.now()
                logger.info("All tasks completed")
                return True
            
            # Check timeout
            if timeout and (time.time() - start_wait) > timeout:
                logger.warning(f"Wait timeout after {timeout}s (pending={pending})")
                return False
            
            # Check for cancellation
            if self.cancellation_checker and self.cancellation_checker():
                logger.info("Cancellation detected during wait")
                return False
            
            time.sleep(0.5)  # Check every 500ms
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """
        Shutdown the control center.
        
        Args:
            wait: Wait for workers to finish current tasks
            timeout: Maximum time to wait for workers
        """
        logger.info("Shutting down control center...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        if wait:
            # Wait for all workers to finish
            start_time = time.time()
            for worker_id, worker in self.workers.items():
                if worker.thread and worker.thread.is_alive():
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    if remaining > 0:
                        worker.thread.join(timeout=remaining)
                    else:
                        logger.warning(f"Worker {worker_id} did not terminate in time")
        
        self.end_time = datetime.now()
        logger.info("Control center shut down")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        queue_stats = self.task_queue.get_statistics()
        state_stats = self.state_tracker.get_statistics()
        
        # Worker statistics
        worker_stats = {
            'idle': sum(1 for w in self.workers.values()
                       if w.state == WorkerState.IDLE),
            'processing': sum(1 for w in self.workers.values()
                            if w.state == WorkerState.PROCESSING),
            'terminated': sum(1 for w in self.workers.values()
                            if w.state == WorkerState.TERMINATED),
            'total_completed': sum(w.tasks_completed for w in self.workers.values()),
            'total_failed': sum(w.tasks_failed for w in self.workers.values()),
        }
        
        # Timing
        elapsed = None
        if self.start_time:
            end = self.end_time or datetime.now()
            elapsed = (end - self.start_time).total_seconds()
        
        return {
            'queue': queue_stats,
            'tasks': state_stats,
            'workers': worker_stats,
            'race_conditions_detected': self.race_condition_count,
            'elapsed_seconds': elapsed,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }

