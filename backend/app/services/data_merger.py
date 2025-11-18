"""Data merger for streaming workflow - merges transcript and comments before summarization."""

from typing import Dict, Any, Optional, Set
import threading
from loguru import logger


class DataMerger:
    """
    Merges transcript and comments data before sending to summarization.
    
    For YouTube/Bilibili items, we receive two separate callbacks:
    - One for transcript
    - One for comments
    
    This class:
    1. Stores partial data as it arrives
    2. Merges when both parts are ready
    3. Calls callback with complete merged data
    4. Handles edge cases (only transcript, only comments, etc.)
    """
    
    def __init__(self, completion_callback, source_types: Optional[Dict[str, str]] = None):
        """
        Initialize data merger.
        
        Args:
            completion_callback: Function to call with (link_id, merged_data) when item is complete
            source_types: Optional dict mapping link_id -> source type ('youtube', 'bilibili', 'reddit', 'article')
        """
        self.completion_callback = completion_callback
        self.source_types = source_types or {}
        
        # Track partial data: {link_id: {'transcript': ..., 'comments': ..., 'metadata': ..., 'source': ...}}
        self.partial_data: Dict[str, Dict[str, Any]] = {}
        
        # Track which items are complete
        self.completed_items: Set[str] = set()
        
        # Lock for thread-safe access
        self.lock = threading.Lock()
        
        logger.info(f"[DataMerger] Initialized with {len(self.source_types)} source types")
    
    def on_transcript_complete(self, link_id: str, data: Dict[str, Any]):
        """
        Called when transcript scraping completes.
        
        Args:
            link_id: Link identifier (base, without _comments suffix)
            data: Scraped data with transcript
        """
        with self.lock:
            # Check if already completed
            if link_id in self.completed_items:
                logger.debug(f"[DataMerger] {link_id} already completed, ignoring transcript")
                return
            
            # Initialize if needed
            if link_id not in self.partial_data:
                self.partial_data[link_id] = {}
            
            # Store transcript data
            self.partial_data[link_id]['transcript'] = data.get('transcript', '')
            self.partial_data[link_id]['source'] = data.get('source', '')
            self.partial_data[link_id]['metadata'] = data.get('metadata', {})
            
            # Update metadata if present
            if data.get('metadata'):
                if 'metadata' not in self.partial_data[link_id]:
                    self.partial_data[link_id]['metadata'] = {}
                self.partial_data[link_id]['metadata'].update(data['metadata'])
            
            logger.info(f"[DataMerger] Received transcript for {link_id}")
            
            # Check if ready to complete
            self._try_complete_item(link_id)
    
    def on_comments_complete(self, link_id: str, data: Dict[str, Any]):
        """
        Called when comments scraping completes.
        
        Args:
            link_id: Link identifier (base, without _comments suffix)
            data: Scraped data with comments
        """
        with self.lock:
            # Check if already completed
            if link_id in self.completed_items:
                logger.debug(f"[DataMerger] {link_id} already completed, ignoring comments")
                return
            
            # Initialize if needed
            if link_id not in self.partial_data:
                self.partial_data[link_id] = {}
            
            # Store comments data
            self.partial_data[link_id]['comments'] = data.get('comments', [])
            if not self.partial_data[link_id].get('source'):
                self.partial_data[link_id]['source'] = data.get('source', '')
            
            # Update metadata if present
            if data.get('metadata'):
                if 'metadata' not in self.partial_data[link_id]:
                    self.partial_data[link_id]['metadata'] = {}
                self.partial_data[link_id]['metadata'].update(data['metadata'])
            
            logger.info(f"[DataMerger] Received comments for {link_id}")
            
            # Check if ready to complete
            self._try_complete_item(link_id)
    
    def on_single_item_complete(self, link_id: str, data: Dict[str, Any]):
        """
        Called when a single-part item completes (Reddit, Article).
        
        These items don't need merging - send directly to completion callback.
        
        Args:
            link_id: Link identifier
            data: Complete scraped data
        """
        with self.lock:
            # Check if already completed
            if link_id in self.completed_items:
                logger.debug(f"[DataMerger] {link_id} already completed, ignoring")
                return
            
            # Mark as complete
            self.completed_items.add(link_id)
        
        # Call completion callback (outside lock to avoid deadlock)
        logger.info(f"[DataMerger] Single item complete: {link_id}")
        try:
            self.completion_callback(link_id, data)
        except Exception as e:
            logger.error(f"[DataMerger] Error in completion callback for {link_id}: {e}", exc_info=True)
    
    def _try_complete_item(self, link_id: str):
        """
        Check if item is ready to complete and call completion callback if so.
        
        Must be called within lock!
        
        Args:
            link_id: Link identifier to check
        """
        # Get partial data
        data = self.partial_data.get(link_id, {})
        
        # Check what we have
        has_transcript = bool(data.get('transcript'))
        has_comments = bool(data.get('comments'))
        
        # Determine source type with robust fallback:
        # 1) Explicit mapping from workflow (preferred)
        # 2) Source field in partial data (from scraped JSON)
        # 3) 'unknown' as last resort
        mapped_source = self.source_types.get(link_id)
        data_source = (data.get('source') or '').lower()
        source_type = (mapped_source or data_source or 'unknown').lower()
        is_ready = False
        
        if source_type in ['youtube', 'bilibili']:
            # Need BOTH transcript AND comments for YouTube/Bilibili
            is_ready = has_transcript and has_comments
            
            if not is_ready:
                logger.info(
                    f"[DataMerger] ⏳ Waiting for {link_id} (source={source_type}): "
                    f"has_transcript={has_transcript}, has_comments={has_comments}"
                )
                return
        else:
            # For Reddit/Article or unknown, complete as soon as we have either part
            is_ready = has_transcript or has_comments
            
            if not is_ready:
                logger.debug(f"[DataMerger] Item not ready yet: {link_id}")
                return
        
        # Ready! Prepare merged data
        merged_data = {
            'source': data.get('source', ''),
            'metadata': data.get('metadata', {}),
            'transcript': data.get('transcript', ''),
            'comments': data.get('comments', [])
        }
        
        # Mark as complete
        self.completed_items.add(link_id)
        
        # Clean up partial data
        del self.partial_data[link_id]
        
        transcript_len = len(merged_data.get('transcript', ''))
        comments_count = len(merged_data.get('comments', []))
        
        logger.info(
            f"[DataMerger] ✓ Item complete and merged: {link_id} (source={source_type}) "
            f"({transcript_len} chars transcript, {comments_count} comments)"
        )
        
        # Call completion callback (inside lock is fine - it should be quick)
        try:
            self.completion_callback(link_id, merged_data)
        except Exception as e:
            logger.error(f"[DataMerger] Error in completion callback for {link_id}: {e}", exc_info=True)
    
    def get_pending_items(self) -> Dict[str, Dict[str, Any]]:
        """
        Get items that are still pending (not yet complete).
        
        Returns:
            Dict mapping link_id to partial data
        """
        with self.lock:
            return self.partial_data.copy()
    
    def get_completed_count(self) -> int:
        """Get count of completed items."""
        with self.lock:
            return len(self.completed_items)
    
    def reset(self):
        """Reset merger state."""
        with self.lock:
            self.partial_data.clear()
            self.completed_items.clear()
            logger.info("[DataMerger] Reset")

