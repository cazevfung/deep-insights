"""Phase 3: Execute Research Plan."""

import json
from typing import Dict, Any, List, Optional
from research.phases.base_phase import BasePhase
from research.data_loader import ResearchDataLoader
from research.prompts import compose_messages, load_schema
from research.retrieval_handler import RetrievalHandler
from core.config import Config
from research.utils.marker_formatter import format_marker_overview


class Phase3Execute(BasePhase):
    """Phase 3: Execute research plan step by step."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_loader = ResearchDataLoader()
        # Track chunks for sequential processing (enhancement #1)
        self._chunk_tracker: Dict[int, List[Dict[str, Any]]] = {}
        # Load retrieval config
        cfg = Config()
        self._window_words = cfg.get_int("research.retrieval.window_words", 3000)
        self._window_overlap = cfg.get_int("research.retrieval.window_overlap_words", 400)
        self._max_windows = cfg.get_int("research.retrieval.max_windows_per_step", 8)
        # Optional per-step time budget (only enforced if explicitly configured)
        try:
            self._max_step_seconds = cfg.get("research.retrieval.max_seconds_per_step", None)
        except Exception:
            self._max_step_seconds = None
        # Sanity guard: avoid pathological overlap >= window size
        if isinstance(self._window_words, int) and isinstance(self._window_overlap, int):
            if self._window_overlap >= max(1, self._window_words):
                self.logger.warning(
                    f"Configured overlap ({self._window_overlap}) >= window size ({self._window_words}); adjusting to window_size//2"
                )
                self._window_overlap = max(1, self._window_words // 2)

        # New knobs for context retrieval flow
        self._max_followups = cfg.get_int("research.retrieval.max_followups_per_step", 2)
        self._min_chars_per_item = cfg.get_int("research.retrieval.min_chars_per_request_item", 400)
        self._max_chars_per_item = cfg.get_int("research.retrieval.max_chars_per_request_item", 4000)
        self._min_total_followup_chars = cfg.get_int("research.retrieval.min_total_followup_chars", 1500)
        self._max_total_followup_chars = cfg.get_int("research.retrieval.max_total_followup_chars", 20000)
        self._enable_cache = bool(cfg.get("research.retrieval.enable_cache", True))
        # Never truncate items flag (new: marker-based approach)
        self._never_truncate_items = cfg.get_bool("research.retrieval.never_truncate_items", True)
        # Max transcript chars (0 = no limit, let API handle token limits)
        self._max_transcript_chars = cfg.get_int("research.retrieval.max_transcript_chars", 0)
        # Debug: log config loading (INFO level for troubleshooting)
        try:
            self.logger.info(
                f"[CONFIG] Phase3Execute loaded: window_words={self._window_words}, "
                f"window_overlap={self._window_overlap}, max_windows={self._max_windows}, "
                f"max_transcript_chars={self._max_transcript_chars} (0=no limit)"
            )
        except Exception:
            pass
        # Simple in-memory cache (per executor instance)
        self._retrieval_cache: Dict[str, str] = {}
    
    def execute(
        self,
        research_plan: List[Dict[str, Any]],
        batch_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute Phase 3: Execute research plan.
        
        Args:
            research_plan: List of plan steps
            batch_data: Loaded batch data
            
        Returns:
            Dict with execution results
        """
        self.logger.info(f"Phase 3: Executing {len(research_plan)} steps")
        
        all_findings = []
        
        # Execute each step
        for step in research_plan:
            step_id = step.get("step_id")
            goal = step.get("goal")
            required_data = step.get("required_data")
            chunk_strategy = step.get("chunk_strategy", "all")
            
            # Log step configuration and batch stats for debugging
            try:
                transcripts_count = sum(1 for d in batch_data.values() if d.get("transcript"))
                total_words = sum(len((d.get("transcript") or "").split()) for d in batch_data.values())
                total_items = len(batch_data)
                chunk_size = step.get("chunk_size", self._window_words)
                self.logger.info(
                    "[Step %s] Config: required_data=%s, strategy=%s, chunk_size=%s | "
                    "batch: items=%s, transcripts=%s, total_words=%s",
                    step_id, required_data, chunk_strategy, chunk_size, total_items, transcripts_count, total_words
                )
            except Exception:
                pass

            if self.progress_tracker:
                self.progress_tracker.start_step(step_id, goal)
            
            try:
                chunk_size = step.get("chunk_size", self._window_words)
                if chunk_strategy == "sequential":
                    # Run paged processing to avoid truncation and improve coverage
                    findings = self._execute_step_paged(step_id, goal, batch_data, required_data, chunk_size)
                    # Complete step after paged processing
                    if self.progress_tracker:
                        self.progress_tracker.complete_step(step_id, findings)
                    all_findings.append({"step_id": step_id, "findings": findings})
                else:
                    # Prepare data chunk with source tracking (enhancement #2)
                    data_chunk, source_info = self._prepare_data_chunk(
                        batch_data,
                        required_data,
                        chunk_strategy,
                        chunk_size
                    )
                    
                    # Get scratchpad for context
                    scratchpad_summary = self.session.get_scratchpad_summary()
                    
                    # Get previous chunks context if sequential (enhancement #1)
                    previous_chunks_context = self._get_previous_chunks_context(step_id)
                    
                    # Execute step
                    required_content_items = step.get("required_content_items", None)
                    findings = self._execute_step(
                        step_id,
                        goal,
                        data_chunk,
                        scratchpad_summary,
                        required_data,
                        chunk_strategy,
                        previous_chunks_context,
                        batch_data=batch_data,  # Pass batch_data for marker overview
                        required_content_items=required_content_items  # Pass required items
                    )
                    
                    # Extract sources from findings or data chunk (enhancement #2)
                    sources = source_info.get("link_ids", [])
                    if not sources and "sources" in findings.get("findings", {}):
                        sources = findings["findings"].get("sources", [])
                    
                    # Update scratchpad with sources (enhancement #2)
                    insights = findings.get("insights", "")
                    confidence = findings.get("confidence", 0.0)
                    findings_data = findings.get("findings", {})
                    findings_data["sources"] = sources  # Add sources to findings
                    self.session.update_scratchpad(step_id, findings_data, insights, confidence, sources)
                    
                    # Track chunk for sequential processing (enhancement #1)
                    if chunk_strategy == "sequential" and data_chunk:
                        self._track_chunk(step_id, data_chunk, findings)
                    
                    all_findings.append({
                        "step_id": step_id,
                        "findings": findings
                    })
                    
                    if self.progress_tracker:
                        self.progress_tracker.complete_step(step_id, findings)
                
            except Exception as e:
                self.logger.error(f"Step {step_id} failed: {str(e)}")
                if self.progress_tracker:
                    self.progress_tracker.fail_step(step_id, str(e))
                raise
        
        result = {
            "completed_steps": len(all_findings),
            "findings": all_findings
        }
        
        self.logger.info(f"Phase 3 complete: Executed {len(all_findings)} steps")
        
        return result

    def _execute_step_paged(
        self,
        step_id: int,
        goal: str,
        batch_data: Dict[str, Any],
        required_data: str,
        chunk_size: int,
        *,
        overlap_words: int = None,
        max_windows: int = None,
    ) -> Dict[str, Any]:
        """Process large transcripts by paging through windows to avoid truncation."""
        if overlap_words is None:
            overlap_words = self._window_overlap
        if max_windows is None:
            max_windows = self._max_windows
        # Build combined transcript once
        transcript_content, source_info = self._get_transcript_content(
            batch_data, "sequential", chunk_size
        )
        words = transcript_content.split()
        n = len(words)
        if n == 0:
            # Fallback to normal single-call path with whatever is available
            scratchpad_summary = self.session.get_scratchpad_summary()
            return self._execute_step(
                step_id,
                goal,
                transcript_content,
                scratchpad_summary,
                required_data,
                "all",
                None,
                batch_data=batch_data,  # Pass batch_data for marker overview
                required_content_items=None
            )

        # Log paging plan
        try:
            effective_overlap = min(max(0, (overlap_words or 0)), max(0, chunk_size - 1))
            stride = max(1, chunk_size - effective_overlap)
            planned_windows = (n + stride - 1) // stride if stride > 0 else 1
            self.logger.info(
                f"[Step {step_id}] Paging: words={n}, chunk_size={chunk_size}, overlap={effective_overlap}, "
                f"max_windows={max_windows}, planned_windows≈{planned_windows}"
            )
        except Exception:
            pass

        # Initialize loop state
        window_start = 0
        windows_processed = 0
        aggregated_findings: Dict[str, Any] = {"summary": "", "points_of_interest": {}, "sources": source_info.get("link_ids", [])}
        insights_parts: List[str] = []
        overall_confidence: float = 0.0
        from time import time
        step_t0 = time()

        # Do not call progress_tracker per window; handle at the caller level
        while window_start < n and windows_processed < (max_windows or 8):
            window_end = min(n, window_start + chunk_size)
            window_text = " ".join(words[window_start:window_end])

            # Progress logging per window
            try:
                self.logger.info(
                    f"[Step {step_id}] Processing window {windows_processed+1} "
                    f"({window_start}-{window_end}/{n})"
                )
            except Exception:
                pass

            # Execute per-window analysis
            scratchpad_summary = self.session.get_scratchpad_summary()
            prev_ctx = self._get_previous_chunks_context(step_id)
            # Debug: log what we're passing to _execute_step
            try:
                self.logger.info(
                    f"[WINDOW_CALL] Step {step_id} Window {windows_processed+1}: calling _execute_step with "
                    f"required_data='{required_data}', chunk_strategy='sequential', "
                    f"window_text_len={len(window_text)}, max_transcript_chars={self._max_transcript_chars}"
                )
            except Exception:
                pass
            window_result = self._execute_step(
                step_id,
                goal,
                window_text,
                scratchpad_summary,
                required_data,
                "sequential",
                prev_ctx,
                batch_data=batch_data,  # Pass batch_data for marker overview
                required_content_items=None
            )

            # Merge results into aggregated structures
            findings = window_result.get("findings", {})
            if not isinstance(findings, dict):
                findings = {"raw": findings}

            # Merge summary
            summary_piece = findings.get("summary") or window_result.get("insights", "")
            if summary_piece:
                insights_parts.append(str(summary_piece)[:1000])

            # Merge points_of_interest shallowly by concatenation of lists
            poi = findings.get("points_of_interest", {}) or {}
            agg_poi = aggregated_findings.setdefault("points_of_interest", {})
            if isinstance(poi, dict):
                for k, v in poi.items():
                    if isinstance(v, list):
                        agg_poi.setdefault(k, [])
                        agg_poi[k].extend(v[:10])  # cap per-window additions

            # Update sources
            if "sources" in findings and isinstance(findings["sources"], list):
                aggregated_findings["sources"] = list(
                    { *aggregated_findings.get("sources", []), *findings["sources"] }
                )

            # Persist scratchpad for this window without hitting disk each time
            self.session.update_scratchpad(
                step_id,
                findings,
                window_result.get("insights", ""),
                float(window_result.get("confidence", 0.5)),
                findings.get("sources", []),
                autosave=False,
            )

            # Track for sequential context
            self._track_chunk(step_id, window_text, window_result)

            # Advance window with overlap (with guards to ensure real progress)
            windows_processed += 1
            if window_end >= n:
                break
            # Ensure overlap is strictly less than chunk size to avoid 1-word sliding
            effective_overlap = min(max(0, overlap_words or 0), max(0, chunk_size - 1))
            next_window_start = window_end - effective_overlap
            # Ensure we advance by a meaningful stride if overlap is too large
            if next_window_start <= window_start:
                minimal_stride = max(1, chunk_size // 2)
                next_window_start = window_start + minimal_stride
            window_start = min(next_window_start, n)

            # Enforce per-step time budget only if explicitly configured
            elapsed = time() - step_t0
            if isinstance(self._max_step_seconds, (int, float)) and self._max_step_seconds > 0 and elapsed > self._max_step_seconds:
                try:
                    self.logger.warning(
                        f"[Step {step_id}] Time budget exceeded after {elapsed:.1f}s; "
                        f"stopping paging early at window {windows_processed}."
                    )
                except Exception:
                    pass
                break

        # Persist accumulated window progress once for the step
        try:
            self.session.save()
        except Exception:
            pass

        # Build aggregated return object
        aggregated_insights = "\n\n".join(insights_parts)
        return {
            "step_id": step_id,
            "findings": aggregated_findings,
            "insights": aggregated_insights[:2000],
            "confidence": overall_confidence or 0.6,
        }
    
    def _prepare_data_chunk(
        self,
        batch_data: Dict[str, Any],
        required_data: str,
        chunk_strategy: str,
        chunk_size: int
    ) -> tuple[str, Dict[str, Any]]:
        """
        Prepare data chunk for analysis using transcript-anchored approach.
        Transcripts are primary anchors, comments are augmentation.
        
        Returns:
            Tuple of (data_chunk_string, source_info_dict)
        """
        source_info = {"link_ids": [], "source_types": []}
        
        if required_data == "previous_findings":
            return self.session.get_scratchpad_summary(), source_info
        
        # Migrate legacy data requirements to transcript-anchored approach
        required_data = self._migrate_legacy_required_data(required_data, batch_data)
        
        # Handle transcript-based data (primary anchor)
        if required_data in ["transcript", "transcript_with_comments"]:
            # Get transcript content (PRIMARY)
            transcript_content, transcript_source_info = self._get_transcript_content(
                batch_data, chunk_strategy, chunk_size
            )
            
            # Get comments content (AUGMENTATION) - only if explicitly requested
            comments_content = None
            comments_source_info = {"link_ids": [], "source_types": []}
            
            if required_data == "transcript_with_comments":
                comments_content, comments_source_info = self._get_comments_content(
                    batch_data, chunk_strategy, chunk_size
                )
            
            # Merge source info
            source_info["link_ids"] = list(set(
                transcript_source_info["link_ids"] + comments_source_info["link_ids"]
            ))
            source_info["source_types"] = list(set(
                transcript_source_info["source_types"] + comments_source_info["source_types"]
            ))
            
            # Structure combined chunk with clear hierarchy
            combined_chunk = self._structure_combined_chunk(
                transcript_content,
                comments_content,
                source_info
            )

            # Debug: report sizes and sources
            try:
                t_len = len(transcript_content or "")
                c_len = len(comments_content or "") if comments_content else 0
                self.logger.info(
                    "Prepared data chunk: transcript_len=%s, comments_len=%s, sources=%s",
                    t_len, c_len, len(source_info.get("link_ids", []))
                )
            except Exception:
                pass
            
            return combined_chunk, source_info
        
        # Legacy: comments-only (edge case - no transcripts available)
        elif required_data == "comments":
            self.logger.warning(
                "Processing comments-only step (no transcripts available). "
                "This is an edge case - consider using transcript_with_comments instead."
            )
            comments_content, comments_source_info = self._get_comments_content(
                batch_data, chunk_strategy, chunk_size
            )
            source_info = comments_source_info
            
            # Format as edge case with warning
            edge_case_chunk = (
                "⚠️ 警告: 无转录本数据，仅基于评论进行分析\n\n"
                "--------------------------------------------------------------------------------\n"
                "可用数据（评论）\n"
                "--------------------------------------------------------------------------------\n\n"
                + comments_content
            )
            return edge_case_chunk, source_info
        
        return "", source_info
    
    def _migrate_legacy_required_data(
        self, 
        required_data: str, 
        batch_data: Dict[str, Any]
    ) -> str:
        """
        Migrate legacy data requirements to transcript-anchored approach.
        
        Args:
            required_data: Original required_data value
            batch_data: Batch data to check for transcript availability
            
        Returns:
            Migrated required_data value
        """
        if required_data == "comments":
            # Check if transcripts available
            has_transcripts = any(
                data.get("transcript") for data in batch_data.values()
            )
            if has_transcripts:
                self.logger.info(
                    "Migrating comment-only step to transcript_with_comments "
                    "(transcripts available)"
                )
                return "transcript_with_comments"
            else:
                self.logger.warning(
                    "No transcripts available, using comments only (edge case)"
                )
                return "comments"  # Fallback for edge cases
        
        return required_data
    
    def _get_transcript_content(
        self,
        batch_data: Dict[str, Any],
        chunk_strategy: str,
        chunk_size: int
    ) -> tuple[str, Dict[str, Any]]:
        """
        Get transcript content as primary anchor.
        
        Returns:
            Tuple of (transcript_content_string, source_info_dict)
        """
        source_info = {"link_ids": [], "source_types": []}
        all_transcripts = []
        
        for link_id, data in batch_data.items():
            transcript = data.get("transcript", "")
            if transcript:
                all_transcripts.append(transcript)
                source_info["link_ids"].append(link_id)
                source_info["source_types"].append(data.get("source", "unknown"))
        
        if not all_transcripts:
            return "(无可用转录本数据)", source_info
        
        combined = " ".join(all_transcripts)
        
        # Apply chunking strategy
        if chunk_strategy == "sequential":
            words = combined.split()
            total_words = len(words)
            
            # Check if we need to chunk (only if larger than chunk_size)
            if total_words <= chunk_size:
                return combined, source_info
            
            # For sequential, return all and let plan handle chunking
            # In future, could return first chunk here
            return combined, source_info
        else:
            return combined, source_info
    
    def _get_comments_content(
        self,
        batch_data: Dict[str, Any],
        chunk_strategy: str,
        chunk_size: int
    ) -> tuple[str, Dict[str, Any]]:
        """
        Get comments content as augmentation.
        Uses engagement-based sampling for large comment sets.
        
        Returns:
            Tuple of (comments_content_string, source_info_dict)
        """
        source_info = {"link_ids": [], "source_types": []}
        all_comments = []  # Normalized to list of dicts with consistent structure
        
        for link_id, data in batch_data.items():
            comments = data.get("comments", [])
            if isinstance(comments, list) and comments:
                # Normalize all comments to standardized dict format
                # Scrapers now export consistent format, but handle legacy data for backward compatibility
                normalized_comments = []
                for c in comments:
                    if isinstance(c, str):
                        # Legacy YouTube format: string -> convert to dict
                        normalized_comments.append({
                            "content": c,
                            "likes": 0,
                            "replies": 0,
                            "source_link_id": link_id
                        })
                    elif isinstance(c, dict):
                        # Standard format (or legacy Bilibili): extract and ensure all fields present
                        content = c.get("content", "")
                        if content:
                            normalized_comments.append({
                                "content": content,
                                "likes": c.get("likes", 0),
                                "replies": c.get("replies", 0),  # Added in standardized format
                                "source_link_id": link_id
                            })
                
                all_comments.extend(normalized_comments)
        
        if not all_comments:
            return None, source_info
        
        # Now all_comments is guaranteed to be a list of dicts with consistent structure
        # Sample comments based on strategy
        if chunk_strategy == "random_sample" and len(all_comments) > chunk_size:
            import random
            sampled = random.sample(all_comments, chunk_size)
            comments_text = "\n".join([
                f"- [点赞:{c.get('likes', 0)}, 回复:{c.get('replies', 0)}] {c.get('content', '')}"
                for c in sampled
            ])
            sampled_sources = [c.get("source_link_id") for c in sampled]
            source_info["link_ids"] = list(set(sampled_sources))
        else:
            # Use all comments or engagement-based top selection
            # Sort by engagement (likes + replies/2) and take top N
            sorted_comments = sorted(
                all_comments,
                key=lambda x: x.get("likes", 0) + (x.get("replies", 0) / 2),
                reverse=True
            )
            # Limit to chunk_size if specified
            if chunk_size > 0 and chunk_size < len(sorted_comments):
                sorted_comments = sorted_comments[:chunk_size]
            
            comments_text = "\n".join([
                f"- [点赞:{c.get('likes', 0)}, 回复:{c.get('replies', 0)}] {c.get('content', '')}"
                for c in sorted_comments
            ])
            source_info["link_ids"] = list(set([
                c.get("source_link_id") for c in sorted_comments
            ]))
        
        source_info["source_types"] = [
            batch_data.get(link_id, {}).get("source", "unknown")
            for link_id in source_info["link_ids"]
        ]
        
        return comments_text, source_info
    
    def _structure_combined_chunk(
        self,
        transcript_content: str,
        comments_content: Optional[str],
        source_info: Dict[str, Any]
    ) -> str:
        """
        Structure data chunk with transcript as primary anchor,
        comments as augmentation.
        
        Args:
            transcript_content: Primary transcript content
            comments_content: Optional comments content for augmentation
            source_info: Source tracking information
            
        Returns:
            Formatted string with clear sections
        """
        parts = []
        
        # PRIMARY SECTION: Transcript content
        parts.append("=" * 80)
        parts.append("主要内容（转录本/文章）")
        parts.append("=" * 80)
        parts.append(transcript_content)
        
        # AUGMENTATION SECTION: Comments (if available)
        if comments_content:
            parts.append("\n\n")
            parts.append("-" * 80)
            parts.append("补充数据（评论）")
            parts.append("-" * 80)
            parts.append("以下评论数据可用于验证、补充情感反应或识别争议点：")
            parts.append("")
            parts.append(comments_content)
        else:
            # Note when comments are not available
            parts.append("\n\n")
            parts.append("(注: 无可用评论数据)")
        
        return "\n".join(parts)
    
    def _prepare_marker_overview_for_step(
        self,
        step_id: int,
        goal: str,
        batch_data: Dict[str, Any],
        required_content_items: Optional[List[str]] = None
    ) -> str:
        """
        Prepare marker overview for a step.
        
        Args:
            step_id: Step identifier
            goal: Step goal
            batch_data: Batch data with summaries
            required_content_items: Optional list of link_ids relevant to this step
            
        Returns:
            Formatted marker overview string
        """
        try:
            # Format marker overview for relevant content items
            marker_overview = format_marker_overview(
                batch_data,
                link_ids=required_content_items,
                max_items=None  # Show all relevant items
            )
            
            # Add step context
            overview_with_context = f"""**步骤 {step_id}: {goal}**

**相关内容的标记概览**

{marker_overview}

**已检索的完整内容**
(初始为空 - 将根据请求填充)

**检索能力说明**
你可以通过以下方式请求更多内容：
1. 请求完整内容项: 指定 link_id 和内容类型 (transcript/comments/both)
2. 基于标记检索: 指定相关标记，系统会检索包含该标记的完整上下文
3. 按话题检索: 指定话题领域，系统会检索相关内容

请分析可用的标记，然后：
- 如果需要更多上下文来完成分析，请明确请求
- 如果标记已足够，直接进行分析"""
            
            return overview_with_context
        except Exception as e:
            self.logger.warning(f"Failed to prepare marker overview for step {step_id}: {e}")
            return f"**步骤 {step_id}: {goal}**\n\n(无法加载标记概览)"
    
    def _safe_truncate_data_chunk(
        self,
        data_chunk: str,
        required_data: str,
        chunk_strategy: str
    ) -> str:
        """
        Truncate data chunk safely based on content type and strategy.
        
        Args:
            data_chunk: Full data chunk
            required_data: Type of data (transcript, comments, etc.)
            chunk_strategy: Chunking strategy used
            
        Returns:
            Safely truncated (or full) data chunk
        """
        data_len = len(data_chunk)
        
        # Debug logging (INFO level for troubleshooting)
        try:
            self.logger.info(
                f"[TRUNCATE_CHECK] required_data='{required_data}', "
                f"chunk_strategy='{chunk_strategy}', data_len={data_len}, "
                f"max_transcript_chars={self._max_transcript_chars}"
            )
        except Exception:
            pass
        
        # For transcript-based data
        if required_data in ["transcript", "transcript_with_comments"]:
            # Skip truncation for sequential strategy - window size already controls input
            if chunk_strategy == "sequential":
                try:
                    self.logger.info(
                        f"[TRUNCATE_SKIP] Sequential strategy detected, returning full chunk ({data_len} chars)"
                    )
                except Exception:
                    pass
                return data_chunk
            
            # Skip truncation if config is 0 (no limit) - let API handle token limits
            if self._max_transcript_chars == 0:
                try:
                    self.logger.info(
                        f"[TRUNCATE_SKIP] max_transcript_chars=0 (no limit), returning full chunk ({data_len} chars)"
                    )
                except Exception:
                    pass
                return data_chunk
            
            # Apply configured limit if set
            if self._max_transcript_chars > 0 and len(data_chunk) > self._max_transcript_chars:
                self.logger.warning(
                    f"Transcript chunk truncated from {len(data_chunk)} to {self._max_transcript_chars} chars "
                    f"(configured limit exceeded)"
                )
                return data_chunk[:self._max_transcript_chars] + "\n\n[注意: 内容被截断，可能遗漏部分细节]"
            return data_chunk
        
        # For comments-only, use moderate limit
        elif required_data == "comments":
            MAX_COMMENTS_CHARS = 15000
            if len(data_chunk) > MAX_COMMENTS_CHARS:
                self.logger.warning(
                    f"Comments chunk truncated from {len(data_chunk)} to {MAX_COMMENTS_CHARS} chars"
                )
                return data_chunk[:MAX_COMMENTS_CHARS] + "\n\n[注意: 评论内容被截断]"
            return data_chunk
        
        # Default: keep current limit for edge cases
        DEFAULT_LIMIT = 8000
        if len(data_chunk) > DEFAULT_LIMIT:
            return data_chunk[:DEFAULT_LIMIT] + "\n\n[注意: 内容被截断]"
        return data_chunk

    def _execute_step(
        self,
        step_id: int,
        goal: str,
        data_chunk: str,
        scratchpad_summary: str,
        required_data: str,
        chunk_strategy: str = "all",
        previous_chunks_context: Optional[str] = None,
        batch_data: Optional[Dict[str, Any]] = None,
        required_content_items: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a single step with marker-first approach and optional retrieval flow."""
        safe_summary = scratchpad_summary if scratchpad_summary != "暂无发现。" else "暂无之前的发现。"
        
        # Add previous chunks context for sequential chunking (enhancement #1)
        chunks_context_str = ""
        if previous_chunks_context and chunk_strategy == "sequential":
            chunks_context_str = f"\n\n**之前处理的数据块摘要**:\n{previous_chunks_context}\n"
        
        # Prepare marker overview if batch_data is available
        marker_overview = ""
        retrieved_content = ""  # Initially empty, will be populated by requests
        
        if batch_data:
            try:
                marker_overview = self._prepare_marker_overview_for_step(
                    step_id, goal, batch_data, required_content_items
                )
                self.logger.info(f"[Step {step_id}] Using marker overview (marker-first approach)")
            except Exception as e:
                self.logger.warning(f"Failed to prepare marker overview for step {step_id}: {e}")
                # Fallback to data_chunk if marker overview fails
                safe_data_chunk = self._safe_truncate_data_chunk(data_chunk, required_data, chunk_strategy)
                marker_overview = ""
        else:
            # Fallback: use truncated data_chunk if no batch_data
            safe_data_chunk = self._safe_truncate_data_chunk(data_chunk, required_data, chunk_strategy)
            self.logger.info(f"[Step {step_id}] Using data_chunk (no batch_data for markers)")
        
        context = {
            "step_id": step_id,
            "goal": goal,
            "marker_overview": marker_overview,  # New: marker overview first
            "data_chunk": safe_data_chunk if not marker_overview else "",  # Keep for backward compatibility
            "retrieved_content": retrieved_content,  # Will be populated by requests
            "scratchpad_summary": safe_summary,
            "previous_chunks_context": chunks_context_str,  # Enhancement #1
        }
        messages = compose_messages("phase3_execute", context=context)
        
        # Stream and parse initial JSON response
        try:
            self.logger.info(
                "[Step %s] Sending to model: data_chunk_len=%s, prev_ctx_len=%s",
                step_id, len(safe_data_chunk or ""), len(chunks_context_str or "")
            )
        except Exception:
            pass

        response1 = self._stream_with_callback(messages)
        parsed1 = self._parse_phase3_response_forgiving(response1, step_id)

        # If the model requests more context, run a follow-up turn with retrieved content
        requests: List[Dict[str, Any]] = []
        if isinstance(parsed1, dict):
            if parsed1.get("requests") and isinstance(parsed1["requests"], list):
                requests = parsed1["requests"]
            elif parsed1.get("missing_context") and isinstance(parsed1["missing_context"], list):
                # Convert missing_context to keyword-style requests as a fallback
                requests = self._convert_missing_context_to_requests(parsed1["missing_context"])  # type: ignore

        # Enhanced back-and-forth retrieval flow
        if requests:
            return self._run_followups_with_retrieval(
                step_id, messages, response1, parsed1, requests,
                batch_data=batch_data  # Pass batch_data for retrieval
            )

        return parsed1

    # ----------------------------- Enhanced Retrieval Loop -----------------------------
    def _run_followups_with_retrieval(
        self,
        step_id: int,
        base_messages: List[Dict[str, Any]],
        prior_response_text: str,
        prior_parsed: Dict[str, Any],
        initial_requests: List[Dict[str, Any]],
        batch_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run up to N follow-up turns with normalized, deduped, cached retrieval and size controls."""
        retriever = RetrievalHandler()
        
        # Get batch_data from session if not provided
        if batch_data is None:
            try:
                batch_data = self.session.batch_data  # type: ignore[attr-defined]
            except AttributeError:
                batch_data = None

        def _normalize_request(req: Dict[str, Any]) -> Dict[str, Any]:
            # Support new request types
            normalized = {
                "id": str(req.get("id") or ""),
                "request_type": req.get("request_type", req.get("method", "keyword")),
                "content_type": req.get("content_type") or req.get("type") or "transcript",
                "source_link_id": req.get("source_link_id") or req.get("source") or "",
                "method": req.get("method") or "keyword",
                "parameters": req.get("parameters") or {},
            }
            # Add new request type specific fields
            if req.get("request_type") == "full_content_item":
                normalized["content_types"] = req.get("content_types", ["transcript", "comments"])
            elif req.get("request_type") == "by_marker":
                normalized["marker_text"] = req.get("marker_text", "")
                normalized["context_window"] = req.get("context_window", 2000)
            elif req.get("request_type") == "by_topic":
                normalized["topic"] = req.get("topic", "")
                normalized["source_link_ids"] = req.get("source_link_ids", [])
                normalized["content_types"] = req.get("content_types", ["transcript", "comments"])
            elif req.get("request_type") == "selective_markers":
                normalized["marker_types"] = req.get("marker_types", [])
            return normalized

        def _req_key(req: Dict[str, Any]) -> str:
            import json
            norm = _normalize_request(req)
            return json.dumps(norm, sort_keys=True, ensure_ascii=False)

        def _clip(text: str) -> str:
            if not isinstance(text, str):
                text = str(text or "")
            # Check never_truncate_items flag - never truncate if enabled
            if self._never_truncate_items:
                # Never truncate - return full content
                return text
            # Legacy truncation (only if flag is False)
            if self._max_chars_per_item and len(text) > self._max_chars_per_item:
                return text[: self._max_chars_per_item] + "\n[...截断...]"
            return text

        def _retrieve_block(req: Dict[str, Any]) -> str:
            key = _req_key(req)
            if self._enable_cache and key in self._retrieval_cache:
                return self._retrieval_cache[key]
            try:
                block = self._handle_retrieval_request(_normalize_request(req), retriever, batch_data) or ""
            except Exception as e:
                block = f"[Retrieval error] {e}"
            block = _clip(block)
            if self._enable_cache:
                self._retrieval_cache[key] = block
            return block

        # Normalize and dedupe initial requests
        seen: set = set()
        pending: List[Dict[str, Any]] = []
        for r in initial_requests:
            k = _req_key(r)
            if k not in seen:
                seen.add(k)
                pending.append(_normalize_request(r))

        turn = 0
        prev_req_keys: set = set(seen)
        current_messages = list(base_messages)
        last_response_text = prior_response_text
        last_parsed = prior_parsed

        while pending and (turn < max(0, int(self._max_followups))):
            turn += 1
            # Fetch all blocks
            blocks: List[str] = []
            total_chars = 0
            for req in pending:
                b = _retrieve_block(req)
                if b:
                    # Enforce min size: if too small, keep it but we will supplement
                    blocks.append(b)
                    total_chars += len(b)

            # If total is too small, optionally broaden by relaxing constraints (simple: include raw transcript excerpts)
            if total_chars < self._min_total_followup_chars:
                try:
                    self.logger.info(
                        f"[Step {step_id}] Follow-up {turn}: total appended chars {total_chars} < min {self._min_total_followup_chars}, broadening context"
                    )
                except Exception:
                    pass

            # Cap total size
            if self._max_total_followup_chars and total_chars > self._max_total_followup_chars:
                trimmed = []
                running = 0
                for b in blocks:
                    if running + len(b) > self._max_total_followup_chars:
                        break
                    trimmed.append(b)
                    running += len(b)
                blocks = trimmed

            appended_context = "\n\n".join(blocks) if blocks else "(No additional context retrieved)"
            try:
                self.logger.info(
                    f"[Step {step_id}] Follow-up {turn}: appended_context_len={len(appended_context)} from {len(blocks)} blocks"
                )
            except Exception:
                pass

            followup_messages = [
                *current_messages,
                {"role": "assistant", "content": last_response_text},
                {
                    "role": "user",
                    "content": (
                        "以下是你请求的额外上下文（已去重并限制长度），请整合后完成分析。\n"
                        "- 若仍缺少关键信息，请一次性列出完整需求，避免重复请求。\n"
                        "- **重要**：无论源内容使用何种语言，所有输出必须使用中文。专业术语需提供跨语言引用（格式：中文术语（原文））。\n\n"
                        f"{appended_context}\n\n请给出最终的结构化输出（必须使用中文），并附上 completion_reason 与 still_missing 概要。"
                    ),
                },
            ]

            last_response_text = self._stream_with_callback(followup_messages)
            last_parsed = self._parse_phase3_response_forgiving(last_response_text, step_id)

            # Prepare next-turn requests, dedupe and detect churn
            new_requests: List[Dict[str, Any]] = []
            if isinstance(last_parsed, dict) and last_parsed.get("requests"):
                for r in last_parsed["requests"]:
                    k = _req_key(r)
                    if k not in prev_req_keys:
                        prev_req_keys.add(k)
                        new_requests.append(_normalize_request(r))

            # If no new requests or only duplicates, stop early
            if not new_requests:
                try:
                    self.logger.info(f"[Step {step_id}] Follow-up {turn}: no new requests; ending loop")
                except Exception:
                    pass
                break

            # Next turn
            pending = new_requests
            current_messages = followup_messages

        return last_parsed

    def _parse_phase3_response_forgiving(self, response_text: str, step_id: int) -> Dict[str, Any]:
        """Parse model response into the expected JSON shape with a forgiving fallback."""
        try:
            parsed = self.client.parse_json_from_stream(iter([response_text]))
            # Auto-fill missing required fields to be forgiving
            if isinstance(parsed, dict):
                if "step_id" not in parsed:
                    parsed["step_id"] = step_id
                if "findings" not in parsed or not isinstance(parsed.get("findings"), dict):
                    parsed["findings"] = parsed.get("findings", {}) if isinstance(parsed.get("findings"), dict) else {}
                if "insights" not in parsed or not isinstance(parsed.get("insights"), str):
                    parsed["insights"] = str(parsed.get("insights", ""))
                if "confidence" not in parsed or not isinstance(parsed.get("confidence"), (int, float)):
                    parsed["confidence"] = 0.6
            self._validate_phase3_schema(parsed)
            return parsed
        except Exception as e:
            self.logger.warning(f"JSON parsing error: {e}")
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                # Schema validation remains forgiving (extra fields allowed)
                if isinstance(parsed, dict):
                    if "step_id" not in parsed:
                        parsed["step_id"] = step_id
                    if "findings" not in parsed or not isinstance(parsed.get("findings"), dict):
                        parsed["findings"] = parsed.get("findings", {}) if isinstance(parsed.get("findings"), dict) else {}
                    if "insights" not in parsed or not isinstance(parsed.get("insights"), str):
                        parsed["insights"] = str(parsed.get("insights", ""))
                    if "confidence" not in parsed or not isinstance(parsed.get("confidence"), (int, float)):
                        parsed["confidence"] = 0.6
                self._validate_phase3_schema(parsed)
                return parsed
            return {
                "step_id": step_id,
                "findings": {"raw_analysis": response_text},
                "insights": response_text[:500],
                "confidence": 0.5,
            }

    def _convert_missing_context_to_requests(self, missing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Best-effort conversion of missing_context hints into retrieval requests."""
        requests: List[Dict[str, Any]] = []
        for idx, item in enumerate(missing):
            source_link_id = item.get("source") or item.get("source_link_id") or "unknown"
            search_hint = item.get("search_hint") or item.get("query") or ""
            if not search_hint:
                continue
            requests.append(
                {
                    "id": f"auto_req_{idx+1}",
                    "content_type": "transcript",
                    "source_link_id": source_link_id,
                    "method": "keyword",
                    "parameters": {"keywords": [search_hint], "context_window": 500},
                    "reason": item.get("reason", "Fill missing context"),
                }
            )
        return requests

    def _handle_retrieval_request(
        self,
        req: Dict[str, Any],
        retriever: RetrievalHandler,
        batch_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Route a single retrieval request to the appropriate handler and format a block."""
        # Get batch_data from session if not provided
        if batch_data is None:
            try:
                batch_data = self.session.batch_data  # type: ignore[attr-defined]
            except AttributeError:
                batch_data = None
        
        if batch_data is None:
            return "[Retrieval] Error: No batch_data available"
        
        request_type = req.get("request_type", req.get("method", "keyword"))  # Support new request_type field
        content_type = req.get("content_type") or req.get("type")
        link_id = req.get("source_link_id") or req.get("source")
        params = req.get("parameters", {})
        
        block_header = (
            f"[Retrieval Result] type={request_type}, content_type={content_type}, link_id={link_id}"
        )
        
        # New request types: full_content_item, by_marker, by_topic, by_marker_types
        if request_type == "full_content_item":
            content_types = req.get("content_types", ["transcript", "comments"])
            if not isinstance(content_types, list):
                content_types = [content_types]
            if not link_id:
                return "[Retrieval] Error: Missing source_link_id for full_content_item"
            content = retriever.retrieve_full_content_item(link_id, content_types, batch_data)
            return f"{block_header}\n{content}"
        
        elif request_type == "by_marker":
            marker_text = req.get("marker_text", "")
            if not marker_text:
                return "[Retrieval] Error: Missing marker_text for by_marker request"
            if not link_id:
                return "[Retrieval] Error: Missing source_link_id for by_marker request"
            content_type_marker = req.get("content_type", "transcript")
            context_window = params.get("context_window", 2000)
            content = retriever.retrieve_by_marker(marker_text, link_id, content_type_marker, context_window, batch_data)
            return f"{block_header}\n{content}"
        
        elif request_type == "by_topic":
            topic = req.get("topic", "")
            if not topic:
                return "[Retrieval] Error: Missing topic for by_topic request"
            source_link_ids = req.get("source_link_ids", [])
            if not source_link_ids:
                return "[Retrieval] Error: Missing source_link_ids for by_topic request"
            content_types = req.get("content_types", ["transcript", "comments"])
            if not isinstance(content_types, list):
                content_types = [content_types]
            content = retriever.retrieve_by_topic(topic, source_link_ids, content_types, batch_data)
            return f"{block_header}\n{content}"
        
        elif request_type == "selective_markers":
            marker_types = req.get("marker_types", [])
            if not marker_types:
                return "[Retrieval] Error: Missing marker_types for selective_markers request"
            if not link_id:
                return "[Retrieval] Error: Missing source_link_id for selective_markers request"
            content_type_selective = req.get("content_type", "transcript")
            content = retriever.retrieve_by_marker_types(marker_types, link_id, content_type_selective, batch_data)
            return f"{block_header}\n{content}"
        
        # Legacy request types: word_range, keyword, semantic
        if not link_id:
            return "[Retrieval] Error: Missing source_link_id"
        
        if content_type == "transcript":
            method = req.get("method", "keyword")
            if method == "word_range":
                start_word = int(params.get("start_word", 0))
                end_word = int(params.get("end_word", 0))
                content = retriever.retrieve_by_word_range(link_id, start_word, end_word, batch_data)
            elif method == "semantic":
                # Semantic search not implemented – degrade to keyword if possible
                query = params.get("query") or ""
                keywords = [query] if query else []
                content = retriever.retrieve_by_keywords(link_id, keywords, batch_data, params.get("context_window", 500)) if keywords else "(Semantic search unavailable)"
            else:
                keywords = params.get("keywords") or []
                content = retriever.retrieve_by_keywords(link_id, keywords, batch_data, params.get("context_window", 500))
            return f"{block_header}\n{content}"
        
        if content_type == "comments":
            keywords = params.get("filter_keywords") or params.get("keywords") or []
            limit = int(params.get("limit", 10))
            sort_by = params.get("sort_by", "relevance")
            content = retriever.retrieve_matching_comments(link_id, keywords, batch_data, limit=limit, sort_by=sort_by)
            return f"{block_header}\n{content}"
        
        # Fallback
        return f"{block_header}\n(Unsupported request_type: {request_type})"

    def _track_chunk(self, step_id: int, data_chunk: str, findings: Dict[str, Any]) -> None:
        """
        Track processed chunk for sequential processing.
        Enhancement #1: Context preservation for sequential chunking.
        Solution 4: Enhanced tracking with quotes and examples.
        """
        if step_id not in self._chunk_tracker:
            self._chunk_tracker[step_id] = []
        
        # Extract key quotes and examples from findings
        findings_data = findings.get("findings", {})
        points_of_interest = findings_data.get("points_of_interest", {})
        
        key_quotes = []
        if points_of_interest:
            # Extract quotable statements
            key_claims = points_of_interest.get("key_claims", [])
            notable_evidence = points_of_interest.get("notable_evidence", [])
            
            # Collect quotes from key claims
            for claim in key_claims[:2]:  # Top 2 claims
                if isinstance(claim, dict):
                    claim_text = claim.get("claim", "")
                    if claim_text and len(claim_text) > 20:  # Meaningful quotes
                        key_quotes.append(claim_text[:150])  # First 150 chars
            
            # Collect quotes from evidence
            for evidence in notable_evidence[:2]:  # Top 2 evidence
                if isinstance(evidence, dict):
                    quote = evidence.get("quote", "")
                    if quote:
                        key_quotes.append(quote[:150])
        
        # Store chunk summary with enhanced context
        chunk_summary = {
            "chunk_index": len(self._chunk_tracker[step_id]) + 1,
            "data_preview": " ".join(data_chunk.split()[:200]) + "..." if len(data_chunk.split()) > 200 else data_chunk,
            "insights": findings.get("insights", "")[:300],  # First 300 chars of insights
            "key_quotes": key_quotes[:3]  # Top 3 quotes/examples from this chunk
        }
        
        self._chunk_tracker[step_id].append(chunk_summary)
    
    def _get_previous_chunks_context(self, step_id: int) -> Optional[str]:
        """
        Get context summary from previously processed chunks.
        Enhancement #1: Context preservation for sequential chunking.
        Solution 4: Enhanced context with quotes and examples.
        """
        if step_id not in self._chunk_tracker or not self._chunk_tracker[step_id]:
            return None
        
        chunks = self._chunk_tracker[step_id]
        context_parts = []
        
        for chunk in chunks[-3:]:  # Last 3 chunks to avoid overload
            chunk_info = (
                f"数据块 {chunk['chunk_index']}:\n"
                f"  内容预览: {chunk['data_preview']}\n"
                f"  关键洞察: {chunk['insights']}"
            )
            
            # Add key quotes if available
            key_quotes = chunk.get("key_quotes", [])
            if key_quotes:
                chunk_info += f"\n  重要引述/例子: {', '.join([q[:80] + '...' if len(q) > 80 else q for q in key_quotes[:2]])}"
            
            context_parts.append(chunk_info)
        
        if len(chunks) > 3:
            context_parts.append(f"\n(已处理 {len(chunks) - 3} 个之前的数据块)")
        
        return "\n\n".join(context_parts)
    
    def _validate_phase3_schema(self, data: Dict[str, Any]) -> None:
        """
        Validate Phase 3 step output using output_schema.json if available.
        Enhanced to support points_of_interest structure.
        """
        schema = load_schema("phase3_execute", name="output_schema.json")
        if not schema:
            return
        
        # Basic required fields
        required_keys = schema.get("required", ["step_id", "findings", "insights", "confidence"])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Schema validation failed: missing required key '{key}' in step output")
        
        # Type checks
        if not isinstance(data.get("step_id"), int):
            raise ValueError("Schema validation failed: 'step_id' must be integer")
        if not isinstance(data.get("findings"), dict):
            raise ValueError("Schema validation failed: 'findings' must be object")
        if not isinstance(data.get("insights"), str):
            raise ValueError("Schema validation failed: 'insights' must be string")
        if not isinstance(data.get("confidence"), (int, float)):
            raise ValueError("Schema validation failed: 'confidence' must be number")
        
        # Validate findings structure (enhanced validation)
        findings = data.get("findings", {})
        
        # Check for summary (recommended but not strictly required for backward compatibility)
        if "summary" not in findings:
            self.logger.debug("Findings missing 'summary' field (recommended)")
        
        # Validate points_of_interest if present
        if "points_of_interest" in findings:
            poi = findings["points_of_interest"]
            if not isinstance(poi, dict):
                raise ValueError("Schema validation failed: 'points_of_interest' must be object")
            
            # Validate each interest type (all optional arrays)
            expected_types = [
                "key_claims", "notable_evidence", "controversial_topics",
                "surprising_insights", "specific_examples", "open_questions"
            ]
            
            for poi_type in expected_types:
                if poi_type in poi:
                    if not isinstance(poi[poi_type], list):
                        raise ValueError(
                            f"Schema validation failed: 'points_of_interest.{poi_type}' must be array"
                        )
                    
                    # Validate structure for complex types
                    if poi_type == "key_claims" and poi[poi_type]:
                        for idx, claim in enumerate(poi[poi_type]):
                            if not isinstance(claim, dict) or "claim" not in claim:
                                self.logger.warning(
                                    f"Key claim {idx} missing 'claim' field"
                                )
                    
                    elif poi_type == "notable_evidence" and poi[poi_type]:
                        for idx, evidence in enumerate(poi[poi_type]):
                            if not isinstance(evidence, dict):
                                self.logger.warning(
                                    f"Notable evidence {idx} must be object"
                                )
                            elif "evidence_type" not in evidence or "description" not in evidence:
                                self.logger.warning(
                                    f"Notable evidence {idx} missing required fields"
                                )
                    
                    elif poi_type == "controversial_topics" and poi[poi_type]:
                        for idx, topic in enumerate(poi[poi_type]):
                            if not isinstance(topic, dict) or "topic" not in topic:
                                self.logger.warning(
                                    f"Controversial topic {idx} missing 'topic' field"
                                )
                    
                    elif poi_type == "specific_examples" and poi[poi_type]:
                        for idx, example in enumerate(poi[poi_type]):
                            if not isinstance(example, dict) or "example" not in example:
                                self.logger.warning(
                                    f"Specific example {idx} missing 'example' field"
                                )
        
        # Validate analysis_details if present (flexible structure)
        if "analysis_details" in findings:
            if not isinstance(findings["analysis_details"], dict):
                self.logger.warning("analysis_details should be object")

