"""Phase 0: Data Preparation."""

import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from queue import Queue, Empty
from research.phases.base_phase import BasePhase
from research.data_loader import ResearchDataLoader
from core.config import Config

try:
    from research.embeddings.vector_indexer import VectorIndexer
except Exception:  # pragma: no cover - optional dependency during bootstrap
    VectorIndexer = None  # type: ignore


class Phase0Prepare(BasePhase):
    """Phase 0: Load and prepare data for research."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_loader = ResearchDataLoader()
        self.config = Config()
        self._vector_indexer: Optional[VectorIndexer] = None
        
        # Check if summarization is enabled
        self.summarization_enabled = self.config.get(
            "research.summarization.enabled",
            True  # Default to enabled
        )
        self.summarization_model = self.config.get(
            "research.summarization.model",
            "qwen-flash"  # Default to qwen-flash
        )
        self.save_summaries_to_files = self.config.get(
            "research.summarization.save_to_files",
            True  # Default to saving
        )
        self.reuse_existing_summaries = self.config.get(
            "research.summarization.reuse_existing_summaries",
            True  # Default to reusing existing summaries
        )
    
    def _get_item_display_name(self, link_id: str, item_data: Optional[Dict[str, Any]]) -> str:
        """
        Prefer human-friendly titles from metadata when available.
        Falls back to the raw link_id if no title information exists.
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
    
    def execute(
        self, 
        batch_id: str, 
        streaming_mode: bool = False,
        streaming_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute Phase 0: Load batch data, create summaries, and create abstracts.
        Enhancement #3: Intelligent sampling enabled
        Enhancement #4: Quality assessment included
        Enhancement: Content summarization with markers using qwen-flash
        
        Args:
            batch_id: Batch identifier to load
            streaming_mode: If True, use streaming summarization (process items as they arrive)
            streaming_manager: StreamingSummarizationManager instance (required if streaming_mode=True)
            
        Returns:
            Dict with loaded data, summaries, and abstracts, including quality assessment
        """
        if streaming_mode:
            return self._execute_streaming_mode(batch_id, streaming_manager)
        else:
            return self._execute_batch_mode(batch_id)
    
    def _execute_batch_mode(self, batch_id: str) -> Dict[str, Any]:
        """
        Execute Phase 0 in batch mode (legacy behavior).
        
        Args:
            batch_id: Batch identifier to load
            
        Returns:
            Dict with loaded data, summaries, and abstracts, including quality assessment
        """
        self.logger.info(f"Phase 0: Loading batch {batch_id} (batch mode)")
        
        # Load batch data
        batch_data = self.data_loader.load_batch(batch_id)
        
        # Assess data quality (enhancement #4)
        quality_assessment = self.data_loader.assess_data_quality(batch_data)
        
        # Log quality warnings
        for flag in quality_assessment.get("quality_flags", []):
            if flag["severity"] == "warning":
                self.logger.warning(f"Data quality: {flag['message']}")
            elif flag["severity"] == "error":
                self.logger.error(f"Data quality: {flag['message']}")
        
        # NEW: Summarize content items using qwen-flash to create markers
        # BUT: Check if summaries already exist (from streaming mode) before re-summarizing
        if self.summarization_enabled:
            # Check if summaries already exist in the loaded data
            items_with_summaries = sum(1 for data in batch_data.values() if data.get("summary"))
            total_items = len(batch_data)
            
            # Also check JSON files if enabled
            if self.reuse_existing_summaries and self.save_summaries_to_files:
                for link_id, data in batch_data.items():
                    if not data.get("summary"):
                        existing_summary = self._load_existing_summary(batch_id, link_id)
                        if existing_summary:
                            data["summary"] = existing_summary
                            items_with_summaries += 1
            
            # Only summarize if we have items missing summaries
            if items_with_summaries < total_items:
                try:
                    self.logger.info(
                        f"Phase 0: Creating content summaries with markers (qwen-flash) "
                        f"for {total_items - items_with_summaries} items "
                        f"({items_with_summaries}/{total_items} already have summaries)"
                    )
                    batch_data = self._summarize_content_items(batch_data, batch_id)
                    
                    # Save summaries to JSON files if enabled
                    if self.save_summaries_to_files:
                        self._save_summaries_to_files(batch_id, batch_data)
                except Exception as e:
                    self.logger.error(f"Failed to create content summaries: {e}")
                    self.logger.warning("Continuing without summaries - markers will not be available")
            else:
                self.logger.info(
                    f"Phase 0: All {total_items} items already have summaries. "
                    f"Skipping re-summarization to avoid duplication."
                )
                # Still save summaries to JSON files if enabled (in case they weren't saved before)
                if self.save_summaries_to_files:
                    self._save_summaries_to_files(batch_id, batch_data)
        
        # Create abstracts for each content item (enhancement #3: intelligent sampling)
        abstracts = {}
        for link_id, data in batch_data.items():
            abstract = self.data_loader.create_abstract(data, use_intelligent_sampling=True)
            abstracts[link_id] = abstract
        
        # Store in session
        self.session.set_metadata("batch_id", batch_id)
        self.session.set_metadata("data_loaded", True)
        self.session.set_metadata("quality_assessment", quality_assessment)
        
        result = {
            "batch_id": batch_id,
            "content_items": list(batch_data.keys()),
            "data": batch_data,
            "abstracts": abstracts,
            "num_items": len(batch_data),
            "quality_assessment": quality_assessment,  # Enhancement #4
            "summaries_created": self.summarization_enabled  # Track if summaries were created
        }

        # Vector indexing (Phase 0 → vector store)
        if VectorIndexer is not None and self.config.get("research.embeddings.enable", True):
            if self._vector_indexer is None:
                try:
                    self._vector_indexer = VectorIndexer(config=self.config)
                except Exception as exc:
                    self.logger.warning("Vector indexer initialization failed: %s", exc)
                    self._vector_indexer = None

            if self._vector_indexer:
                try:
                    self.logger.info("Phase 0: Indexing embeddings for batch %s", batch_id)
                    self._vector_indexer.index_batch(batch_id, batch_data)
                    result["vector_indexed"] = True
                except Exception as exc:
                    self.logger.error("Phase 0 vector indexing failed: %s", exc, exc_info=True)
                    result["vector_indexed"] = False
        else:
            result["vector_indexed"] = False
        
        self.logger.info(
            f"Phase 0 complete: Loaded {len(batch_data)} content items "
            f"(Quality score: {quality_assessment['quality_score']:.2f})"
        )
        
        return result
    
    def _execute_streaming_mode(
        self, 
        batch_id: str, 
        streaming_manager: Any
    ) -> Dict[str, Any]:
        """
        Execute Phase 0 in streaming mode (process items as they finish scraping).
        
        Args:
            batch_id: Batch identifier
            streaming_manager: StreamingSummarizationManager instance
            
        Returns:
            Dict with loaded data, summaries, and abstracts, including quality assessment
        """
        self.logger.info(f"Phase 0: Starting streaming mode for batch {batch_id}")
        
        # NOTE: wait_for_completion() was already called in workflow_service.py before this method
        # We don't need to wait again here - just get the data that's ready
        # However, we should verify that all expected items are present
        
        # Get all summarized data
        batch_data = streaming_manager.get_all_summarized_data()
        
        # Verify we have all expected items
        stats = streaming_manager.get_statistics()
        expected_count = stats['expected_items']
        actual_count = len(batch_data)
        
        if actual_count < expected_count:
            self.logger.warning(
                f"Phase 0: Only {actual_count}/{expected_count} items processed. "
                f"Scraped: {stats['scraped']}, Summarized: {stats['summarized']}"
            )
            # Don't proceed if we're missing items - this indicates a problem
            raise Exception(
                f"Phase 0 incomplete: Only {actual_count}/{expected_count} items processed. "
                f"Scraped: {stats['scraped']}, Summarized: {stats['summarized']}"
            )
        
        self.logger.info(
            f"Phase 0: All {actual_count}/{expected_count} items processed successfully. "
            f"Summaries: {stats['summaries_created']} created, {stats['summaries_reused']} reused, {stats['summaries_failed']} failed"
        )
        
        # Shutdown workers (but don't do it here - let workflow_service handle it after artifact is saved)
        # streaming_manager.shutdown()  # Moved to workflow_service after artifact save
        
        self.logger.info(f"Phase 0: Received {len(batch_data)} summarized items")
        
        # Assess data quality
        quality_assessment = self.data_loader.assess_data_quality(batch_data)
        
        # Log quality warnings
        for flag in quality_assessment.get("quality_flags", []):
            if flag["severity"] == "warning":
                self.logger.warning(f"Data quality: {flag['message']}")
            elif flag["severity"] == "error":
                self.logger.error(f"Data quality: {flag['message']}")
        
        # Create abstracts for each content item (enhancement #3: intelligent sampling)
        abstracts = {}
        for link_id, data in batch_data.items():
            abstract = self.data_loader.create_abstract(data, use_intelligent_sampling=True)
            abstracts[link_id] = abstract
        
        # Store in session
        self.session.set_metadata("batch_id", batch_id)
        self.session.set_metadata("data_loaded", True)
        self.session.set_metadata("quality_assessment", quality_assessment)
        
        # Get statistics from streaming manager
        stats = streaming_manager.get_statistics()
        
        result = {
            "batch_id": batch_id,
            "content_items": list(batch_data.keys()),
            "data": batch_data,
            "abstracts": abstracts,
            "num_items": len(batch_data),
            "quality_assessment": quality_assessment,
            "summaries_created": stats['summaries_created'] > 0,
            "summaries_reused": stats['summaries_reused'],
            "summaries_failed": stats['summaries_failed'],
            "streaming_mode": True
        }
        
        # Save summaries to JSON files if enabled
        if self.save_summaries_to_files:
            self._save_summaries_to_files(batch_id, batch_data)
        
        # Vector indexing (Phase 0 → vector store)
        if VectorIndexer is not None and self.config.get("research.embeddings.enable", True):
            if self._vector_indexer is None:
                try:
                    self._vector_indexer = VectorIndexer(config=self.config)
                except Exception as exc:
                    self.logger.warning("Vector indexer initialization failed: %s", exc)
                    self._vector_indexer = None
            
            if self._vector_indexer:
                try:
                    self.logger.info("Phase 0: Indexing embeddings for batch %s", batch_id)
                    self._vector_indexer.index_batch(batch_id, batch_data)
                    result["vector_indexed"] = True
                except Exception as exc:
                    self.logger.error("Phase 0 vector indexing failed: %s", exc, exc_info=True)
                    result["vector_indexed"] = False
        else:
            result["vector_indexed"] = False
        
        self.logger.info(
            f"Phase 0 complete (streaming): Loaded {len(batch_data)} content items "
            f"(Quality score: {quality_assessment['quality_score']:.2f}, "
            f"Summaries: {stats['summaries_created']} created, {stats['summaries_reused']} reused)"
        )
        
        return result
    
    def _summarize_content_items(
        self, 
        batch_data: Dict[str, Any], 
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Summarize all content items using qwen-flash to extract marker lists.
        Uses parallel processing with 8 workers, similar to scraping pipeline.
        
        Args:
            batch_data: Loaded batch data
            batch_id: Batch identifier (for checking existing summaries)
            
        Returns:
            batch_data with summaries added to each content item
        """
        from research.summarization.content_summarizer import ContentSummarizer
        
        # Initialize summarizer with client and config
        summarizer = ContentSummarizer(client=self.client, config=self.config, ui=self.ui)
        
        summaries_created = 0
        summaries_reused = 0
        
        total_items = len(batch_data)
        self.logger.info(f"Starting parallel summarization for {total_items} content items (8 workers)")
        
        # Send initial progress update
        if hasattr(self, 'ui') and self.ui:
            if hasattr(self.ui, 'display_summarization_progress'):
                self.ui.display_summarization_progress(
                    current_item=0,
                    total_items=total_items,
                    link_id="",
                    stage="starting",
                    message=f"开始创建摘要 ({total_items} 个内容项, 8个并行工作线程)"
                )
            else:
                self.ui.display_message(
                    f"开始创建摘要 ({total_items} 个内容项, 8个并行工作线程)",
                    "info"
                )
        
        # Create queue for summarization tasks
        task_queue = Queue()
        completed_lock = threading.Lock()
        completed_count = [0]  # Use list to allow modification in nested function
        summaries_created_shared = [0]  # Thread-safe counter for created summaries
        in_progress = set()  # Track items currently being processed (thread-safe with lock)
        processed_link_ids = set()  # Track which link_ids have been processed to prevent duplicates
        
        # Prepare tasks: filter out items that already have summaries
        tasks_to_process = []
        for link_id, data in batch_data.items():
            # Check if summary already exists (if reuse_existing_summaries is enabled)
            if self.reuse_existing_summaries and data.get("summary"):
                self.logger.debug(f"Reusing existing summary for {link_id}")
                summaries_reused += 1
                with completed_lock:
                    completed_count[0] += 1
                if hasattr(self, 'ui') and self.ui:
                    if hasattr(self.ui, 'display_summarization_progress'):
                        self.ui.display_summarization_progress(
                            current_item=completed_count[0],
                            total_items=total_items,
                            link_id=link_id,
                            stage="reused",
                                message=f"摘要已存在 [{completed_count[0]}/{total_items}]: {self._get_item_display_name(link_id, data)}"
                        )
                continue
            
            # Check if summary exists in JSON file
            if self.reuse_existing_summaries and self.save_summaries_to_files:
                existing_summary = self._load_existing_summary(batch_id, link_id)
                if existing_summary:
                    data["summary"] = existing_summary
                    summaries_reused += 1
                    with completed_lock:
                        completed_count[0] += 1
                    self.logger.info(f"Loaded existing summary from file for {link_id}")
                    if hasattr(self, 'ui') and self.ui:
                        if hasattr(self.ui, 'display_summarization_progress'):
                            self.ui.display_summarization_progress(
                                current_item=completed_count[0],
                                total_items=total_items,
                                link_id=link_id,
                                stage="loaded",
                                message=f"从文件加载摘要 [{completed_count[0]}/{total_items}]: {self._get_item_display_name(link_id, data)}"
                            )
                    continue
            
            # Add to queue for processing
            tasks_to_process.append((link_id, data))
            task_queue.put((link_id, data))
        
        # If no tasks to process, return early
        if not tasks_to_process:
            self.logger.info(f"All {total_items} items already have summaries")
            if hasattr(self, 'ui') and self.ui:
                if hasattr(self.ui, 'display_summarization_progress'):
                    self.ui.display_summarization_progress(
                        current_item=total_items,
                        total_items=total_items,
                        link_id="",
                        stage="all_completed",
                        message=f"所有摘要创建完成 (0 新建, {summaries_reused} 重用)"
                    )
            return batch_data
        
        # Worker function that processes items from queue
        def worker(worker_id: int):
            """Worker thread that processes summarization tasks from queue."""
            self.logger.info(f"[WORKER-{worker_id}] Summarization worker started")
            worker_summaries_created = 0
            
            while True:
                try:
                    # Get next task from queue (with timeout to allow checking for completion)
                    try:
                        link_id, data = task_queue.get(timeout=0.1)
                    except Empty:
                        # Check if all tasks are done: queue empty AND nothing in progress AND all completed
                        with completed_lock:
                            queue_empty = task_queue.empty()
                            nothing_in_progress = len(in_progress) == 0
                            all_completed = completed_count[0] >= total_items
                            
                            if queue_empty and nothing_in_progress and all_completed:
                                self.logger.info(f"[WORKER-{worker_id}] All tasks completed, exiting")
                                break
                            elif queue_empty and nothing_in_progress:
                                # Queue is empty and nothing in progress, but not all completed
                                # This shouldn't happen, but wait a bit and check again
                                self.logger.debug(
                                    f"[WORKER-{worker_id}] Queue empty, nothing in progress, "
                                    f"but completed={completed_count[0]}/{total_items}, waiting..."
                                )
                        continue
                    
                    # Check if this item was already processed (prevent duplicates)
                    with completed_lock:
                        if link_id in processed_link_ids:
                            self.logger.warning(f"[WORKER-{worker_id}] Link {link_id} already processed, skipping")
                            task_queue.task_done()
                            continue
                        processed_link_ids.add(link_id)
                        in_progress.add(link_id)
                    
                    self.logger.info(f"[WORKER-{worker_id}] Processing: {link_id} (queue_size={task_queue.qsize()}, in_progress={len(in_progress)})")
                    
                    # Send progress update
                    with completed_lock:
                        current_idx = completed_count[0] + 1
                    if hasattr(self, 'ui') and self.ui:
                        if hasattr(self.ui, 'display_summarization_progress'):
                            item_display_name = self._get_item_display_name(link_id, data)
                            self.ui.display_summarization_progress(
                                current_item=current_idx,
                                total_items=total_items,
                                link_id=link_id,
                                stage="summarizing",
                                message=f"正在总结 [{current_idx}/{total_items}]: {item_display_name} (Worker {worker_id})"
                            )
                    
                    # Create summary
                    try:
                        api_start_time = time.time()
                        self.logger.info(f"[WORKER-{worker_id}] [TIMING] Starting summarization API call for {link_id}")
                        
                        summary = summarizer.summarize_content_item(
                            link_id=link_id,
                            transcript=data.get("transcript"),
                            comments=data.get("comments"),
                            metadata=data.get("metadata")
                        )
                        
                        api_elapsed = time.time() - api_start_time
                        self.logger.info(f"[WORKER-{worker_id}] [TIMING] Summarization completed in {api_elapsed:.3f}s for {link_id}")
                        
                        # Add summary to data (thread-safe - each worker modifies different dict entry)
                        data["summary"] = summary
                        worker_summaries_created += 1
                        with completed_lock:
                            summaries_created_shared[0] += 1
                            in_progress.discard(link_id)  # Remove from in_progress
                        
                        # Log summary stats
                        transcript_markers = summary.get("transcript_summary", {}).get("total_markers", 0)
                        comments_markers = summary.get("comments_summary", {}).get("total_markers", 0)
                        self.logger.info(
                            f"[WORKER-{worker_id}] Created summary for {link_id}: "
                            f"{transcript_markers} transcript markers, "
                            f"{comments_markers} comment markers"
                        )
                        
                        # Send summaries to frontend
                        if hasattr(self, 'ui') and self.ui:
                            # Send transcript summary if available
                            transcript_summary = summary.get("transcript_summary", {})
                            if transcript_summary and transcript_summary.get("total_markers", 0) > 0:
                                if hasattr(self.ui, 'display_summary'):
                                    self.ui.display_summary(
                                        link_id=link_id,
                                        summary_type="transcript",
                                        summary_data=transcript_summary
                                    )
                                else:
                                    flattened_transcript = {
                                        **transcript_summary,
                                        "link_id": link_id,
                                        "summary_type": "transcript"
                                    }
                                    self.ui.display_message(
                                        json.dumps(flattened_transcript, ensure_ascii=False),
                                        "info"
                                    )
                            
                            # Send comments summary if available
                            comments_summary = summary.get("comments_summary", {})
                            if comments_summary and comments_summary.get("total_markers", 0) > 0:
                                if hasattr(self.ui, 'display_summary'):
                                    self.ui.display_summary(
                                        link_id=link_id,
                                        summary_type="comments",
                                        summary_data=comments_summary
                                    )
                                else:
                                    flattened_comments = {
                                        **comments_summary,
                                        "link_id": link_id,
                                        "summary_type": "comments"
                                    }
                                    self.ui.display_message(
                                        json.dumps(flattened_comments, ensure_ascii=False),
                                        "info"
                                    )
                            
                            # Send completion update
                            with completed_lock:
                                completed_count[0] += 1
                                current_completed = completed_count[0]
                            
                            if hasattr(self.ui, 'display_summarization_progress'):
                                item_display_name = self._get_item_display_name(link_id, data)
                                self.ui.display_summarization_progress(
                                    current_item=current_completed,
                                    total_items=total_items,
                                    link_id=link_id,
                                    stage="completed",
                                    message=f"总结好了 [{current_completed}/{total_items}]: {item_display_name} ({transcript_markers + comments_markers} 标记, Worker {worker_id})"
                                )
                            else:
                                self.ui.display_message(
                                    f"摘要创建完成 [{current_completed}/{total_items}]: {link_id} ({transcript_markers + comments_markers} 标记)",
                                    "success"
                                )
                        
                    except Exception as e:
                        self.logger.error(f"[WORKER-{worker_id}] Failed to create summary for {link_id}: {e}", exc_info=True)
                        # Add empty summary structure to maintain consistency
                        data["summary"] = {
                            "transcript_summary": {},
                            "comments_summary": {},
                            "created_at": None,
                            "model_used": self.summarization_model,
                            "error": str(e)
                        }
                        
                        # Send error update
                        with completed_lock:
                            in_progress.discard(link_id)  # Remove from in_progress
                            completed_count[0] += 1
                            current_completed = completed_count[0]
                        
                        if hasattr(self, 'ui') and self.ui:
                            if hasattr(self.ui, 'display_summarization_progress'):
                                item_display_name = self._get_item_display_name(link_id, data)
                                self.ui.display_summarization_progress(
                                    current_item=current_completed,
                                    total_items=total_items,
                                    link_id=link_id,
                                    stage="error",
                                    message=f"摘要创建失败 [{current_completed}/{total_items}]: {item_display_name} (Worker {worker_id})"
                                )
                    
                    # Mark task as done (must be called even if exception occurred)
                    task_queue.task_done()
                    
                except Exception as e:
                    self.logger.error(f"[WORKER-{worker_id}] Unexpected error in worker: {e}", exc_info=True)
                    # Ensure we remove from in_progress and mark task as done even on unexpected error
                    try:
                        with completed_lock:
                            if 'link_id' in locals():
                                in_progress.discard(link_id)
                                processed_link_ids.discard(link_id)  # Allow retry if needed
                        task_queue.task_done()
                    except:
                        pass
                    break
            
            self.logger.info(f"[WORKER-{worker_id}] Worker finished, created {worker_summaries_created} summaries")
        
        # Start 8 worker threads
        num_workers = 8
        workers = []
        for i in range(num_workers):
            worker_thread = threading.Thread(
                target=worker,
                args=(i + 1,),
                name=f"SummarizationWorker-{i+1}",
                daemon=False
            )
            worker_thread.start()
            workers.append(worker_thread)
            self.logger.info(f"Started summarization worker {i+1}")
        
        # Wait for all workers to complete
        for worker_thread in workers:
            worker_thread.join()
        
        # Wait for all tasks to be marked as done
        task_queue.join()
        
        # Get final count of created summaries
        with completed_lock:
            summaries_created = summaries_created_shared[0]
        
        # Send final completion update
        if hasattr(self, 'ui') and self.ui:
            if hasattr(self.ui, 'display_summarization_progress'):
                self.ui.display_summarization_progress(
                    current_item=total_items,
                    total_items=total_items,
                    link_id="",
                    stage="all_completed",
                    message=f"所有摘要创建完成 ({summaries_created} 新建, {summaries_reused} 重用)"
                )
            else:
                self.ui.display_message(
                    f"所有摘要创建完成 ({summaries_created} 新建, {summaries_reused} 重用)",
                    "success"
                )
        
        self.logger.info(
            f"Parallel summarization complete: {summaries_created} created, "
            f"{summaries_reused} reused out of {total_items} total items"
        )
        
        return batch_data
    
    def _save_summaries_to_files(self, batch_id: str, batch_data: Dict[str, Any]):
        """
        Save summaries back to JSON files for persistence.
        
        Args:
            batch_id: Batch identifier
            batch_data: Batch data with summaries
        """
        batch_dir = self.data_loader.results_base_path / f"run_{batch_id}"
        
        if not batch_dir.exists():
            self.logger.warning(f"Batch directory not found for saving summaries: {batch_dir}")
            return
        
        saved_count = 0
        
        # Iterate through all JSON files in batch directory
        for file_path in batch_dir.glob("*.json"):
            if file_path.name == "manifest.json":
                continue
            
            # Extract link_id from filename
            file_name = file_path.stem
            parts = file_name.split('_')
            if len(parts) < 4:
                continue
            
            link_id = parts[3] if len(parts) == 4 else '_'.join(parts[3:-1])
            
            # Get summary for this link_id
            if link_id in batch_data and batch_data[link_id].get("summary"):
                summary = batch_data[link_id]["summary"]
                
                try:
                    # Load existing JSON file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    
                    # Add/update summary field
                    file_data["summary"] = summary
                    
                    # Save back to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(file_data, f, ensure_ascii=False, indent=2)
                    
                    saved_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save summary to {file_path}: {e}")
        
        if saved_count > 0:
            self.logger.info(f"Saved {saved_count} summaries to JSON files")
    
    def _load_existing_summary(self, batch_id: str, link_id: str) -> Optional[Dict[str, Any]]:
        """
        Load existing summary from JSON file if it exists.
        
        Args:
            batch_id: Batch identifier
            link_id: Link identifier
            
        Returns:
            Summary dict if found, None otherwise
        """
        batch_dir = self.data_loader.results_base_path / f"run_{batch_id}"
        
        if not batch_dir.exists():
            return None
        
        # Find JSON file(s) for this link_id
        for file_path in batch_dir.glob(f"*_{link_id}_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                if "summary" in file_data:
                    return file_data["summary"]
            except Exception:
                continue
        
        return None

