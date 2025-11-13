"""Phase 0: Data Preparation."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
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
    
    def execute(self, batch_id: str) -> Dict[str, Any]:
        """
        Execute Phase 0: Load batch data, create summaries, and create abstracts.
        Enhancement #3: Intelligent sampling enabled
        Enhancement #4: Quality assessment included
        Enhancement: Content summarization with markers using qwen-flash
        
        Args:
            batch_id: Batch identifier to load
            
        Returns:
            Dict with loaded data, summaries, and abstracts, including quality assessment
        """
        self.logger.info(f"Phase 0: Loading batch {batch_id}")
        
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
        if self.summarization_enabled:
            try:
                self.logger.info("Phase 0: Creating content summaries with markers (qwen-flash)")
                batch_data = self._summarize_content_items(batch_data, batch_id)
                
                # Save summaries to JSON files if enabled
                if self.save_summaries_to_files:
                    self._save_summaries_to_files(batch_id, batch_data)
            except Exception as e:
                self.logger.error(f"Failed to create content summaries: {e}")
                self.logger.warning("Continuing without summaries - markers will not be available")
        
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
    
    def _summarize_content_items(
        self, 
        batch_data: Dict[str, Any], 
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Summarize all content items using qwen-flash to extract marker lists.
        
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
        self.logger.info(f"Starting summarization for {total_items} content items")
        
        # Send initial progress update
        if hasattr(self, 'ui') and self.ui:
            if hasattr(self.ui, 'display_summarization_progress'):
                self.ui.display_summarization_progress(
                    current_item=0,
                    total_items=total_items,
                    link_id="",
                    stage="starting",
                    message=f"开始创建摘要 ({total_items} 个内容项)"
                )
            else:
                self.ui.display_message(
                    f"开始创建摘要 ({total_items} 个内容项)",
                    "info"
                )
        
        for idx, (link_id, data) in enumerate(batch_data.items(), 1):
            self.logger.info(f"[{idx}/{total_items}] Processing content item: {link_id}")
            
            # Send progress update before processing item
            if hasattr(self, 'ui') and self.ui:
                if hasattr(self.ui, 'display_summarization_progress'):
                    self.ui.display_summarization_progress(
                        current_item=idx,
                        total_items=total_items,
                        link_id=link_id,
                        stage="summarizing",
                        message=f"正在总结 [{idx}/{total_items}]: {link_id}"
                    )
                else:
                    self.ui.display_message(
                        f"正在创建摘要 [{idx}/{total_items}]: {link_id}",
                        "info"
                    )
            
            # Check if summary already exists (if reuse_existing_summaries is enabled)
            if self.reuse_existing_summaries and data.get("summary"):
                self.logger.debug(f"Reusing existing summary for {link_id}")
                summaries_reused += 1
                if hasattr(self, 'ui') and self.ui:
                    if hasattr(self.ui, 'display_summarization_progress'):
                        self.ui.display_summarization_progress(
                            current_item=idx,
                            total_items=total_items,
                            link_id=link_id,
                            stage="reused",
                            message=f"摘要已存在 [{idx}/{total_items}]: {link_id}"
                        )
                    else:
                        self.ui.display_message(
                            f"摘要已存在 [{idx}/{total_items}]: {link_id}",
                            "success"
                        )
                continue
            
            # Check if summary exists in JSON file
            if self.reuse_existing_summaries and self.save_summaries_to_files:
                existing_summary = self._load_existing_summary(batch_id, link_id)
                if existing_summary:
                    data["summary"] = existing_summary
                    summaries_reused += 1
                    self.logger.info(f"Loaded existing summary from file for {link_id}")
                    if hasattr(self, 'ui') and self.ui:
                        if hasattr(self.ui, 'display_summarization_progress'):
                            self.ui.display_summarization_progress(
                                current_item=idx,
                                total_items=total_items,
                                link_id=link_id,
                                stage="loaded",
                                message=f"从文件加载摘要 [{idx}/{total_items}]: {link_id}"
                            )
                        else:
                            self.ui.display_message(
                                f"从文件加载摘要 [{idx}/{total_items}]: {link_id}",
                                "success"
                            )
                    continue
            
            # Create new summary
            self.logger.info(f"[{idx}/{total_items}] Creating summary with markers for '{link_id}' using {self.summarization_model}")
            
            try:
                # Time the API call
                import time
                api_start_time = time.time()
                self.logger.info(f"[TIMING] Starting summarization API call for {link_id} at {api_start_time:.3f}")
                
                summary = summarizer.summarize_content_item(
                    link_id=link_id,
                    transcript=data.get("transcript"),
                    comments=data.get("comments"),
                    metadata=data.get("metadata")
                )
                
                api_elapsed = time.time() - api_start_time
                self.logger.info(f"[TIMING] Summarization API call completed in {api_elapsed:.3f}s for {link_id}")
                
                # Add summary to data
                data["summary"] = summary
                summaries_created += 1
                
                # Log summary stats
                transcript_markers = summary.get("transcript_summary", {}).get("total_markers", 0)
                comments_markers = summary.get("comments_summary", {}).get("total_markers", 0)
                self.logger.info(
                    f"Created summary for {link_id}: "
                    f"{transcript_markers} transcript markers, "
                    f"{comments_markers} comment markers"
                )
                
                # Send summaries to frontend
                if hasattr(self, 'ui') and self.ui:
                    # Send transcript summary if available
                    transcript_summary = summary.get("transcript_summary", {})
                    if transcript_summary and transcript_summary.get("total_markers", 0) > 0:
                        # Check if UI has display_summary method
                        if hasattr(self.ui, 'display_summary'):
                            self.ui.display_summary(
                                link_id=link_id,
                                summary_type="transcript",
                                summary_data=transcript_summary
                            )
                        else:
                            # Fallback: send as JSON message
                            self.logger.warning("UI does not have display_summary method, using display_message fallback")
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
                        # Check if UI has display_summary method
                        if hasattr(self.ui, 'display_summary'):
                            self.ui.display_summary(
                                link_id=link_id,
                                summary_type="comments",
                                summary_data=comments_summary
                            )
                        else:
                            # Fallback: send as JSON message
                            flattened_comments = {
                                **comments_summary,
                                "link_id": link_id,
                                "summary_type": "comments"
                            }
                            self.ui.display_message(
                                json.dumps(flattened_comments, ensure_ascii=False),
                                "info"
                            )
                    
                    # Send completion update after item
                    if hasattr(self.ui, 'display_summarization_progress'):
                        self.ui.display_summarization_progress(
                            current_item=idx,
                            total_items=total_items,
                            link_id=link_id,
                            stage="completed",
                            message=f"总结好了 [{idx}/{total_items}]: {link_id} ({transcript_markers + comments_markers} 标记)"
                        )
                    else:
                        self.ui.display_message(
                            f"摘要创建完成 [{idx}/{total_items}]: {link_id} ({transcript_markers + comments_markers} 标记)",
                            "success"
                        )
                
            except Exception as e:
                self.logger.error(f"Failed to create summary for {link_id}: {e}", exc_info=True)
                # Add empty summary structure to maintain consistency
                data["summary"] = {
                    "transcript_summary": {},
                    "comments_summary": {},
                    "created_at": None,
                    "model_used": self.summarization_model,
                    "error": str(e)
                }
                # Send error update
                if hasattr(self, 'ui') and self.ui:
                    if hasattr(self.ui, 'display_summarization_progress'):
                        self.ui.display_summarization_progress(
                            current_item=idx,
                            total_items=total_items,
                            link_id=link_id,
                            stage="error",
                            message=f"摘要创建失败 [{idx}/{total_items}]: {link_id}"
                        )
        
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
            f"Summarization complete: {summaries_created} created, "
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

