"""Adapter to integrate V2 manager into existing workflow with data merging."""

from typing import Dict, Any, List
from loguru import logger

from research.phases.streaming_summarization_manager_v2 import StreamingSummarizationManagerV2
from backend.app.services.data_merger import DataMerger


class StreamingSummarizationAdapter:
    """
    Adapter that wraps V2 manager and handles data merging.
    
    This provides a V1-compatible interface while using V2 internally:
    - Accepts on_scraping_complete() calls (V1 style)
    - Merges transcript + comments internally
    - Routes complete data to V2's on_item_scraped()
    
    This allows drop-in replacement of V1 with V2 in workflow_service.py
    """
    
    def __init__(self, client, config, ui, session, batch_id: str):
        """
        Initialize adapter with V2 manager and data merger.
        
        Args:
            client: QwenStreamingClient instance
            config: Config instance
            ui: UI interface
            session: ResearchSession instance
            batch_id: Batch identifier
        """
        # Track source types to determine if item needs merging
        self.item_sources: Dict[str, str] = {}  # {link_id: 'youtube'|'bilibili'|'reddit'|'article'}
        
        # Create V2 manager
        self.manager_v2 = StreamingSummarizationManagerV2(
            client=client,
            config=config,
            ui=ui,
            session=session,
            batch_id=batch_id
        )
        
        # Create data merger with callback to V2 and source types
        self.data_merger = DataMerger(
            completion_callback=self._on_data_complete,
            source_types=self.item_sources  # Pass reference to source types dict
        )
        
        logger.info(f"[StreamingSummarizationAdapter] Initialized for batch {batch_id}")
    
    def register_expected_items(self, link_ids: List[str], sources: Dict[str, str] = None):
        """
        Register expected items.
        
        Args:
            link_ids: List of link identifiers
            sources: Optional dict mapping link_id to source type
        """
        # Register with V2 manager
        self.manager_v2.register_expected_items(link_ids)
        
        # Store source types if provided
        if sources:
            self.item_sources.update(sources)
            logger.info(
                f"[StreamingSummarizationAdapter] Updated item_sources with {len(sources)} types. "
                f"Sample: {dict(list(sources.items())[:3])}"
            )
        else:
            logger.warning("[StreamingSummarizationAdapter] No source types provided!")
        
        logger.info(
            f"[StreamingSummarizationAdapter] Registered {len(link_ids)} items. "
            f"Total source_types: {len(self.item_sources)}"
        )
    
    def start_workers(self):
        """Start V2 worker (singular, not plural)."""
        self.manager_v2.start_worker()
        logger.info("[StreamingSummarizationAdapter] Started V2 worker")
    
    def on_scraping_complete(self, link_id: str, data: Dict[str, Any]):
        """
        Called when scraping completes (V1-compatible interface).
        
        This method:
        1. Determines if item is transcript, comments, or single-part
        2. Routes to data merger for merging (if needed)
        3. Data merger will call _on_data_complete() when ready
        
        Args:
            link_id: Link identifier (may have _comments suffix)
            data: Scraped data
        """
        # v3: Comment scraping has been removed. All items are treated as single-part.
        # We still normalize base_link_id for safety, but we don't special-case comments anymore.
        base_link_id = link_id
        if link_id.endswith('_comments'):
            base_link_id = link_id[:-9]  # Remove '_comments'
        
        # Determine source type (for logging only)
        source = data.get('source', '').lower()
        if not source and base_link_id in self.item_sources:
            source = self.item_sources[base_link_id]
        
        logger.info(
            f"[StreamingSummarizationAdapter] Routing {link_id} as single-part item: "
            f"base_id={base_link_id}, source={source}, "
            f"available_sources={list(self.item_sources.keys())[:5]}"
        )
        
        # Send directly as a single-part item to DataMerger / V2
        self.data_merger.on_single_item_complete(base_link_id, data)
    
    def _on_data_complete(self, link_id: str, merged_data: Dict[str, Any]):
        """
        Called by data merger when item is complete.
        
        This routes the complete, merged data to V2 manager.
        
        Args:
            link_id: Link identifier
            merged_data: Complete merged data with transcript + comments
        """
        logger.info(f"[StreamingSummarizationAdapter] Routing complete data to V2: {link_id}")
        
        try:
            self.manager_v2.on_item_scraped(link_id, merged_data)
        except Exception as e:
            logger.error(f"[StreamingSummarizationAdapter] Error routing to V2 for {link_id}: {e}", exc_info=True)
    
    def wait_for_completion(self, timeout: float = None) -> bool:
        """
        Wait for all items to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all completed, False if timeout
        """
        return self.manager_v2.wait_for_completion(timeout=timeout)
    
    def get_all_summarized_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed items with summaries."""
        return self.manager_v2.get_all_summarized_data()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.manager_v2.get_statistics()
        
        # Add merger statistics
        stats['merger_pending'] = len(self.data_merger.get_pending_items())
        stats['merger_completed'] = self.data_merger.get_completed_count()
        
        return stats
    
    def shutdown(self):
        """Shutdown manager and cleanup."""
        self.manager_v2.shutdown()
        self.data_merger.reset()
        logger.info("[StreamingSummarizationAdapter] Shutdown complete")
    
    # V1-compatible properties for workflow_service.py compatibility
    @property
    def workers(self):
        """Compatibility: Return list with single worker."""
        if getattr(self.manager_v2, "worker_threads", None):
            return [w for w in self.manager_v2.worker_threads if w is not None]
        if self.manager_v2.worker_thread:
            return [self.manager_v2.worker_thread]
        return []
    
    @property
    def summarization_queue(self):
        """Compatibility: Return V2 processing queue."""
        return self.manager_v2.processing_queue
    
    @property
    def items_in_queue(self):
        """Compatibility: Return empty set (V2 doesn't track this separately)."""
        return set()
    
    @property
    def items_processing(self):
        """Compatibility: Return items in SUMMARIZING state."""
        from research.phases.streaming_summarization_manager_v2 import ItemState
        with self.manager_v2.items_lock:
            return {
                link_id for link_id, item in self.manager_v2.items.items()
                if item.state == ItemState.SUMMARIZING
            }
    
    @property
    def expected_items(self):
        """Compatibility: Return all registered items."""
        with self.manager_v2.items_lock:
            return set(self.manager_v2.items.keys())
    
    @property
    def item_states(self):
        """Compatibility: Return V1-style item states dict."""
        with self.manager_v2.items_lock:
            v1_states = {}
            for link_id, item in self.manager_v2.items.items():
                from research.phases.streaming_summarization_manager_v2 import ItemState
                v1_states[link_id] = {
                    'scraped': item.state.value >= ItemState.SCRAPED.value,
                    'summarized': item.state == ItemState.COMPLETED,
                    'data': item.scraped_data,
                    'error': item.error
                }
            return v1_states
    
    @property
    def completed_lock(self):
        """Compatibility: Return V2 items_lock."""
        return self.manager_v2.items_lock
    
    @property
    def session(self):
        """Access session from V2 manager."""
        return self.manager_v2.session
    
    @property
    def client(self):
        """Access client from V2 manager."""
        return self.manager_v2.client
    
    @property
    def ui(self):
        """Access UI from V2 manager."""
        return self.manager_v2.ui

