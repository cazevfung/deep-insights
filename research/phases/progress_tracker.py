"""Proactive Progress Tracker - Actively monitors and drives item processing."""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from enum import Enum
from loguru import logger


class ItemState(Enum):
    """States an item can be in."""
    PENDING = "pending"          # Waiting to be scraped
    SCRAPING = "scraping"        # Being scraped
    SCRAPED = "scraped"          # Scraped, waiting for summarization
    QUEUED = "queued"            # Queued for summarization
    SUMMARIZING = "summarizing"  # Being summarized
    COMPLETED = "completed"      # Fully done
    FAILED = "failed"            # Failed at some stage


@dataclass
class ItemProgress:
    """Tracks progress of a single item through the pipeline."""
    link_id: str
    state: ItemState = ItemState.PENDING
    
    # Timestamps for each stage
    created_at: datetime = field(default_factory=datetime.now)
    scraping_started_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    queued_at: Optional[datetime] = None
    summarization_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Progress tracking
    last_progress_update: datetime = field(default_factory=datetime.now)
    progress_message: str = ""
    worker_id: Optional[int] = None
    
    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0
    
    def update_progress(self, message: str):
        """Update progress with a new message."""
        self.last_progress_update = datetime.now()
        self.progress_message = message
        logger.debug(f"[ProgressTracker] {self.link_id}: {message}")
    
    def time_in_current_state(self) -> float:
        """Get seconds spent in current state."""
        return (datetime.now() - self.last_progress_update).total_seconds()
    
    def is_stalled(self, timeout_seconds: float) -> bool:
        """Check if item has been in current state too long."""
        return self.time_in_current_state() > timeout_seconds


class ProactiveProgressTracker:
    """
    Proactively monitors and drives item processing.
    
    Instead of passively waiting for things to happen, this tracker:
    1. Actively monitors what SHOULD be happening
    2. Detects when items are stalled
    3. Proactively triggers next steps when capacity is available
    4. Reports real-time progress
    """
    
    def __init__(self):
        self.items: Dict[str, ItemProgress] = {}
        self.lock = threading.Lock()
        
        # Monitoring thread
        self.monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Configuration
        self.scraping_timeout = 300.0  # 5 minutes per scraping
        self.summarization_timeout = 120.0  # 2 minutes per summarization
        self.check_interval = 1.0  # Check every second
        
        # Callbacks for proactive actions
        self.on_item_stalled = None  # Called when item is stalled
        self.on_capacity_available = None  # Called when workers are free
    
    def start_monitoring(self):
        """Start the proactive monitoring thread."""
        if self.monitor_thread is not None:
            logger.warning("[ProgressTracker] Monitoring already started")
            return
        
        self.shutdown_event.clear()
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="ProgressMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("[ProgressTracker] 🚀 Started proactive monitoring")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if self.monitor_thread is None:
            return
        
        self.shutdown_event.set()
        self.monitor_thread.join(timeout=5.0)
        self.monitor_thread = None
        logger.info("[ProgressTracker] 🛑 Stopped monitoring")
    
    def register_item(self, link_id: str) -> ItemProgress:
        """Register a new item to track."""
        with self.lock:
            if link_id in self.items:
                logger.warning(f"[ProgressTracker] Item {link_id} already registered")
                return self.items[link_id]
            
            item = ItemProgress(link_id=link_id)
            self.items[link_id] = item
            logger.info(f"[ProgressTracker] 📝 Registered {link_id} for tracking")
            return item
    
    def update_state(self, link_id: str, new_state: ItemState, message: str = ""):
        """Update item state proactively."""
        with self.lock:
            if link_id not in self.items:
                logger.warning(f"[ProgressTracker] Updating unknown item: {link_id}")
                self.register_item(link_id)
            
            item = self.items[link_id]
            old_state = item.state
            item.state = new_state
            item.update_progress(message or f"State changed: {old_state.value} → {new_state.value}")
            
            # Update timestamps
            now = datetime.now()
            if new_state == ItemState.SCRAPING:
                item.scraping_started_at = now
            elif new_state == ItemState.SCRAPED:
                item.scraped_at = now
            elif new_state == ItemState.QUEUED:
                item.queued_at = now
            elif new_state == ItemState.SUMMARIZING:
                item.summarization_started_at = now
            elif new_state == ItemState.COMPLETED:
                item.completed_at = now
            elif new_state == ItemState.FAILED:
                item.failed_at = now
            
            logger.info(
                f"[ProgressTracker] 🔄 {link_id}: {old_state.value} → {new_state.value} "
                f"(time in previous state: {item.time_in_current_state():.1f}s)"
            )
    
    def assign_worker(self, link_id: str, worker_id: int):
        """Record that a worker is processing this item."""
        with self.lock:
            if link_id in self.items:
                self.items[link_id].worker_id = worker_id
                logger.info(f"[ProgressTracker] 👷 Worker {worker_id} assigned to {link_id}")
    
    def record_progress(self, link_id: str, message: str):
        """Record progress update (heartbeat)."""
        with self.lock:
            if link_id in self.items:
                self.items[link_id].update_progress(message)
    
    def record_error(self, link_id: str, error: str):
        """Record an error for an item."""
        with self.lock:
            if link_id in self.items:
                item = self.items[link_id]
                item.error = error
                item.state = ItemState.FAILED
                item.failed_at = datetime.now()
                logger.error(f"[ProgressTracker] ❌ {link_id} failed: {error}")
    
    def get_status_summary(self) -> Dict:
        """Get current status of all items."""
        with self.lock:
            return {
                "total": len(self.items),
                "by_state": {
                    state.value: sum(1 for item in self.items.values() if item.state == state)
                    for state in ItemState
                },
                "stalled": [
                    {
                        "link_id": item.link_id,
                        "state": item.state.value,
                        "time_in_state": item.time_in_current_state(),
                        "worker_id": item.worker_id,
                        "message": item.progress_message
                    }
                    for item in self.items.values()
                    if self._is_item_stalled(item)
                ]
            }
    
    def _is_item_stalled(self, item: ItemProgress) -> bool:
        """Check if item is stalled based on its state."""
        if item.state == ItemState.SCRAPING:
            return item.is_stalled(self.scraping_timeout)
        elif item.state in (ItemState.QUEUED, ItemState.SUMMARIZING):
            return item.is_stalled(self.summarization_timeout)
        return False
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread."""
        logger.info("[ProgressTracker] 🔍 Monitoring loop started")
        
        iteration = 0
        while not self.shutdown_event.is_set():
            try:
                iteration += 1
                
                # Check for stalled items every iteration
                stalled_items = []
                with self.lock:
                    for item in self.items.values():
                        if self._is_item_stalled(item):
                            stalled_items.append(item)
                
                # Report stalled items
                if stalled_items:
                    for item in stalled_items:
                        logger.warning(
                            f"[ProgressTracker] ⚠️ STALLED: {item.link_id} in state {item.state.value} "
                            f"for {item.time_in_current_state():.1f}s (worker: {item.worker_id})"
                        )
                        if self.on_item_stalled:
                            self.on_item_stalled(item)
                
                # Log status summary every 10 seconds
                if iteration % 10 == 0:
                    summary = self.get_status_summary()
                    logger.info(
                        f"[ProgressTracker] 📊 Status: "
                        f"Total={summary['total']}, "
                        f"Scraping={summary['by_state'].get('scraping', 0)}, "
                        f"Queued={summary['by_state'].get('queued', 0)}, "
                        f"Summarizing={summary['by_state'].get('summarizing', 0)}, "
                        f"Completed={summary['by_state'].get('completed', 0)}, "
                        f"Stalled={len(summary['stalled'])}"
                    )
                
                # Check if we have capacity for more work
                with self.lock:
                    active_summarization = sum(
                        1 for item in self.items.values()
                        if item.state == ItemState.SUMMARIZING
                    )
                    queued_items = sum(
                        1 for item in self.items.values()
                        if item.state == ItemState.QUEUED
                    )
                
                if active_summarization < 8 and queued_items > 0:
                    # We have idle workers and items waiting
                    logger.info(
                        f"[ProgressTracker] 💡 CAPACITY AVAILABLE: "
                        f"{8 - active_summarization} workers free, {queued_items} items queued"
                    )
                    if self.on_capacity_available:
                        self.on_capacity_available(8 - active_summarization, queued_items)
                
                # Sleep between checks
                self.shutdown_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"[ProgressTracker] Error in monitoring loop: {e}", exc_info=True)
                time.sleep(1.0)  # Back off on errors
        
        logger.info("[ProgressTracker] 🔍 Monitoring loop stopped")

