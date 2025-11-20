"""Data loading and normalization for research agent.

This module handles loading scraped data from batch results and
normalizing different source formats into a unified structure.
"""

import json
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from core.config import Config


class ResearchDataLoader:
    """Load and normalize scraped data from batch results."""
    
    def __init__(self, results_base_path: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            results_base_path: Base path for batch results (defaults to configured batches_dir)
        """
        if results_base_path is None:
            # Default to configured batches directory
            config = Config()
            self.results_base_path = config.get_batches_dir()
        else:
            self.results_base_path = Path(results_base_path)
        
        logger.info(f"Initialized ResearchDataLoader with base path: {self.results_base_path}")
    
    def load_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Load all scraped files for a batch.
        
        Args:
            batch_id: Batch identifier (e.g., "251029_150500")
            
        Returns:
            Dict mapping link_id to data structure:
            {
                "link_id_1": {
                    "transcript": {...},  # or "article"
                    "comments": [...],
                    "metadata": {...},
                    "source": "youtube" | "bilibili" | "reddit" | "article"
                },
                ...
            }
        """
        batch_dir = self.results_base_path / f"run_{batch_id}"
        
        if not batch_dir.exists():
            raise FileNotFoundError(f"Batch directory not found: {batch_dir}")
        
        logger.info(f"Loading batch: {batch_id} from {batch_dir}")
        
        # Group files by link_id
        link_data = {}

        # Prefer manifest.json if present for deterministic discovery
        manifest_path = batch_dir / "manifest.json"
        file_iterable = None
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as mf:
                    manifest = json.load(mf)
                items = manifest.get("items", [])
                file_iterable = [batch_dir / item.get("relative_path", "") for item in items]
                logger.info(f"Using manifest.json with {len(items)} entries")
            except Exception as e:
                logger.warning(f"Failed to read manifest.json, falling back to glob: {e}")
                file_iterable = list(batch_dir.glob("*.json"))
        else:
            file_iterable = list(batch_dir.glob("*.json"))
        
        # Iterate through selected JSON files in batch directory
        for file_path in file_iterable:
            file_name = file_path.stem
            # Parse filename: {batch_id}_{SOURCE}_{link_id}_{type}.json
            # Examples:
            # - 251029_150500_YT_yt_demo1_tsct.json (YouTube transcript)
            # - 251029_150500_YT_yt_demo1_cmts.json (YouTube comments)
            # - 251029_150500_BILI_bili_req1_cmt.json (Bilibili comments)
            # - 251029_150500_RD_rd_case1_tsct.json (Reddit transcript/article)
            
            parts = file_name.split('_')
            if len(parts) < 4:
                logger.warning(f"Unexpected filename format: {file_name}")
                continue
            
            # Extract source prefix and link_id
            # Format: {batch_id}_{SOURCE}_{link_id}_{type}
            source_prefix = parts[2]  # YT, BILI, RD, etc.
            link_id = parts[3]  # First part of link_id
            
            # Handle multi-part link_ids (e.g., yt_demo1)
            if len(parts) > 4:
                link_id = '_'.join(parts[3:-1])  # Everything between source and type
            
            file_type = parts[-1]  # tsct, cmts, cmt, etc.
            
            # Load JSON file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Initialize link_data entry if needed
                if link_id not in link_data:
                    link_data[link_id] = {
                        "transcript": None,
                        "comments": [],  # Initialize as empty list, not None
                        "metadata": {},
                        "source": None,
                        "data_availability": {  # Enhancement: track data availability
                            "has_transcript": False,
                            "has_comments": False,
                            "transcript_word_count": 0,
                            "comment_count": 0
                        }
                    }
                
                # Map source prefix to source type
                source_mapping = {
                    "YT": "youtube",
                    "BILI": "bilibili",
                    "RD": "reddit",
                    "ARTICLE": "article"
                }
                source = source_mapping.get(source_prefix, source_prefix.lower())
                link_data[link_id]["source"] = source
                
                # Process based on file type
                if file_type in ["tsct", "article"]:
                    # Transcript or article content
                    transcript_content = data.get("content", "")
                    link_data[link_id]["transcript"] = transcript_content
                    
                    # Update availability metadata
                    word_count = len(transcript_content.split()) if transcript_content else 0
                    link_data[link_id]["data_availability"]["has_transcript"] = bool(transcript_content)
                    link_data[link_id]["data_availability"]["transcript_word_count"] = word_count
                    
                    link_data[link_id]["metadata"].update({
                        "title": data.get("title", ""),
                        "author": data.get("author", ""),
                        "url": data.get("url", ""),
                        "word_count": data.get("word_count", word_count),
                        "publish_date": data.get("publish_date", ""),
                    })
                
                elif file_type in ["cmts", "cmt"]:
                    # Comments data
                    comments = data.get("comments") or []
                    if source == "youtube":
                        # YouTube: comments is a list of strings
                        if comments and isinstance(comments[0], dict) and "content" in comments[0]:
                            comments = [c.get("content", "") for c in comments]
                        link_data[link_id]["comments"] = comments
                    elif source == "bilibili":
                        # Bilibili: comments is a list of objects with content and likes
                        link_data[link_id]["comments"] = comments
                    elif source == "reddit":
                        # Reddit: comments are embedded in content
                        # For now, we'll extract from content if available
                        if "comments" in data:
                            link_data[link_id]["comments"] = comments
                    
                    # Update availability metadata
                    link_data[link_id]["data_availability"]["has_comments"] = bool(comments)
                    link_data[link_id]["data_availability"]["comment_count"] = len(comments)
                
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {str(e)}")
                continue
        
        logger.info(f"Loaded {len(link_data)} content items from batch {batch_id}")
        return link_data
    
    def load_scraped_data_for_link(self, link_id: str, batch_id: str, max_retries: int = 10, retry_delay: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Load scraped data for a single link_id from batch results.
        
        This is used in streaming mode to load data incrementally as items finish scraping.
        Includes retry logic to handle race conditions where files may not be saved yet.
        
        Args:
            link_id: Link identifier (e.g., "yt_demo1")
            batch_id: Batch identifier (e.g., "251029_150500")
            max_retries: Maximum number of retry attempts (default: 10)
            retry_delay: Initial delay between retries in seconds (default: 0.5, uses exponential backoff)
            
        Returns:
            Data structure for this link_id, or None if not found:
            {
                "transcript": {...},  # or "article"
                "comments": [...],
                "metadata": {...},
                "source": "youtube" | "bilibili" | "reddit" | "article"
            }
        """
        import time
        
        batch_dir = self.results_base_path / f"run_{batch_id}"
        
        # Retry logic: wait for batch directory and files to be created
        for attempt in range(max_retries):
            if not batch_dir.exists():
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.debug(f"Batch directory not found (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.2f}s: {batch_dir}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Batch directory not found after {max_retries} attempts: {batch_dir}")
                    return None
            
            # Directory exists, check if files are available and stable
            matching_files = list(batch_dir.glob(f"*_{link_id}_*.json"))
            
            if not matching_files:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.debug(f"No files found for link_id={link_id} (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"No files found for link_id={link_id} after {max_retries} attempts in {batch_dir}")
                    return None
            
            # Check if files are stable (not being written)
            files_stable = True
            for file_path in matching_files:
                if not file_path.exists():
                    files_stable = False
                    break
                # Check if file was recently modified (within last 0.5 seconds)
                try:
                    mtime = file_path.stat().st_mtime
                    if time.time() - mtime < 0.5:
                        files_stable = False
                        break
                except OSError:
                    files_stable = False
                    break
            
            if not files_stable and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.debug(f"Files for link_id={link_id} not yet stable (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                continue
            
            # Files exist and are stable, proceed with loading
            break
        
        # Final check: ensure we have files before proceeding
        matching_files = list(batch_dir.glob(f"*_{link_id}_*.json"))
        if not matching_files:
            logger.warning(f"No files found for link_id={link_id} in {batch_dir} after retries")
            return None
        
        logger.info(f"Loading data for link_id={link_id} from batch {batch_id} (found {len(matching_files)} file(s))")
        
        # Initialize result structure
        result = {
            "transcript": None,
            "comments": [],
            "metadata": {},
            "source": None,
            "data_availability": {
                "has_transcript": False,
                "has_comments": False,
                "transcript_word_count": 0,
                "comment_count": 0
            }
        }
        
        # Find all JSON files for this link_id
        # Pattern: {batch_id}_{SOURCE}_{link_id}_{type}.json
        files_found = False
        
        for file_path in batch_dir.glob(f"*_{link_id}_*.json"):
            files_found = True
            file_name = file_path.stem
            parts = file_name.split('_')
            
            if len(parts) < 4:
                logger.warning(f"Unexpected filename format: {file_name}")
                continue
            
            # Extract source prefix and file type
            source_prefix = parts[2]  # YT, BILI, RD, etc.
            file_type = parts[-1]  # tsct, cmts, cmt, etc.
            
            # Map source prefix to source type
            source_mapping = {
                "YT": "youtube",
                "BILI": "bilibili",
                "RD": "reddit",
                "ARTICLE": "article"
            }
            source = source_mapping.get(source_prefix, source_prefix.lower())
            result["source"] = source  # Will be overwritten if multiple files, but that's OK
            
            # Load JSON file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Process based on file type
                if file_type in ["tsct", "article"]:
                    # Transcript or article content
                    transcript_content = data.get("content", "")
                    result["transcript"] = transcript_content
                    
                    # Update availability metadata
                    word_count = len(transcript_content.split()) if transcript_content else 0
                    result["data_availability"]["has_transcript"] = bool(transcript_content)
                    result["data_availability"]["transcript_word_count"] = word_count
                    
                    result["metadata"].update({
                        "title": data.get("title", ""),
                        "author": data.get("author", ""),
                        "url": data.get("url", ""),
                        "word_count": data.get("word_count", word_count),
                        "publish_date": data.get("publish_date", ""),
                    })
                    
                    # Check if summary exists in file
                    if "summary" in data:
                        result["summary"] = data["summary"]
                
                elif file_type in ["cmts", "cmt"]:
                    # Comments data
                    comments = data.get("comments") or []
                    if source == "youtube":
                        # YouTube: comments is a list of strings
                        if comments and isinstance(comments[0], dict) and "content" in comments[0]:
                            comments = [c.get("content", "") for c in comments]
                        result["comments"] = comments
                    elif source == "bilibili":
                        # Bilibili: comments is a list of objects with content and likes
                        result["comments"] = comments
                    elif source == "reddit":
                        # Reddit: comments are embedded in content
                        if "comments" in data:
                            result["comments"] = comments
                    
                    # Update availability metadata
                    result["data_availability"]["has_comments"] = bool(comments)
                    result["data_availability"]["comment_count"] = len(comments)
            
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {str(e)}")
                continue
        
        if not files_found:
            logger.warning(f"No files found for link_id={link_id} in batch {batch_id}")
            return None
        
        logger.debug(f"Loaded data for link_id={link_id}: transcript={bool(result['transcript'])}, comments={len(result['comments'])}")
        return result
    
    def create_abstract(
        self, 
        data: Dict[str, Any],
        transcript_sample_words: int = 500,
        comment_sample_size: int = 30,
        use_intelligent_sampling: bool = True
    ) -> str:
        """
        Create data abstract for Phase 1 (goal generation).
        Enhancement #3: Intelligent sampling (multi-point for transcripts, engagement-based for comments)
        
        Args:
            data: Loaded data for a single link_id
            transcript_sample_words: Number of words to sample from transcript
            comment_sample_size: Number of comments to sample
            use_intelligent_sampling: Use intelligent sampling strategies
            
        Returns:
            Formatted abstract string
        """
        abstract_parts = []
        
        # Add transcript/article sample (enhancement #3: multi-point sampling)
        transcript = data.get("transcript", "")
        if transcript:
            words = transcript.split()
            total_words = len(words)
            
            if use_intelligent_sampling and total_words > transcript_sample_words * 1.5:
                # Multi-point sampling: beginning, middle, end
                words_per_sample = transcript_sample_words // 3
                
                samples = []
                # Beginning
                if words_per_sample > 0:
                    samples.append(("开头", " ".join(words[:words_per_sample])))
                
                # Middle
                if total_words > words_per_sample * 2:
                    mid_start = (total_words - words_per_sample) // 2
                    mid_end = mid_start + words_per_sample
                    samples.append(("中间", " ".join(words[mid_start:mid_end])))
                
                # End
                if total_words > words_per_sample:
                    samples.append(("结尾", " ".join(words[-words_per_sample:])))
                
                sample_parts = [f"{label}（{len(s.split())}词）:\n{s}" for label, s in samples]
                abstract_parts.append(
                    f"**转录本/文章摘要**（多点采样，共{transcript_sample_words}词）:\n\n" + 
                    "\n\n---\n\n".join(sample_parts)
                )
            else:
                # Traditional: first N words
                sample_words = words[:transcript_sample_words]
                sample = " ".join(sample_words)
                abstract_parts.append(f"**转录本/文章摘要**（前{len(sample_words)}词）:\n{sample}")
        
        # Add comments sample (enhancement #3: engagement-based sampling)
        comments = data.get("comments", [])
        if comments:
            if isinstance(comments[0], str):
                # YouTube format: list of strings - random sample
                sampled = random.sample(
                    comments, 
                    min(comment_sample_size, len(comments))
                )
                comments_text = "\n".join([f"- {c}" for c in sampled])
                abstract_parts.append(
                    f"\n**评论样本**（随机{len(sampled)}/{len(comments)}条）:\n{comments_text}"
                )
            else:
                # Bilibili format: list of objects - engagement-based sorting
                if use_intelligent_sampling:
                    # Sort by engagement (likes + replies/2 for weighting)
                    sorted_comments = sorted(
                        comments,
                        key=lambda x: x.get("likes", 0) + (x.get("replies", 0) / 2),
                        reverse=True
                    )
                    sampled = sorted_comments[:min(comment_sample_size, len(comments))]
                    comments_text = "\n".join([
                        f"- [点赞:{c.get('likes', 0)}, 回复:{c.get('replies', 0)}] {c.get('content', '')}"
                        for c in sampled
                    ])
                    abstract_parts.append(
                        f"\n**评论样本**（按热度排序，{len(sampled)}/{len(comments)}条）:\n{comments_text}"
                    )
                else:
                    # Random sampling
                    sampled = random.sample(
                        comments,
                        min(comment_sample_size, len(comments))
                    )
                    comments_text = "\n".join([
                        f"- [点赞:{c.get('likes', 0)}] {c.get('content', '')}"
                        for c in sampled
                    ])
                    abstract_parts.append(
                        f"\n**评论样本**（随机{len(sampled)}/{len(comments)}条）:\n{comments_text}"
                    )
        
        # Add metadata
        metadata = data.get("metadata", {})
        if metadata:
            meta_info = []
            if metadata.get("title"):
                meta_info.append(f"标题: {metadata['title']}")
            if metadata.get("author"):
                meta_info.append(f"作者: {metadata['author']}")
            if metadata.get("word_count"):
                meta_info.append(f"字数: {metadata['word_count']}")
            if metadata.get("url"):
                meta_info.append(f"链接: {metadata['url']}")
            
            if meta_info:
                abstract_parts.append(f"\n**元数据**:\n" + "\n".join(meta_info))
        
        return "\n\n".join(abstract_parts)
    
    def assess_data_quality(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess data quality and flag potential issues.
        Enhancement #4: Content quality indicators
        
        Args:
            batch_data: Loaded batch data
            
        Returns:
            Dict with quality assessment including flags and score
        """
        quality_flags = []
        issues = []
        
        if not batch_data:
            return {
                "quality_flags": [{"type": "empty", "message": "无可用数据", "severity": "error"}],
                "quality_score": 0.0,
                "summary": "无数据"
            }
        
        # Collect statistics
        word_counts = []
        comment_counts = []
        sources = []
        items_with_comments = 0
        
        for link_id, data in batch_data.items():
            metadata = data.get("metadata", {})
            word_count = metadata.get("word_count", 0)
            word_counts.append(word_count)
            
            comments = data.get("comments", [])
            if comments:
                items_with_comments += 1
                comment_counts.append(len(comments))
            
            source = data.get("source", "unknown")
            sources.append(source)
        
        total_words = sum(word_counts)
        num_items = len(batch_data)
        avg_words = total_words / num_items if num_items > 0 else 0
        
        # Check for imbalance (one source dominates)
        if len(word_counts) > 1:
            max_words = max(word_counts)
            if total_words > 0 and max_words / total_words > 0.8:
                dominant_source_idx = word_counts.index(max_words)
                dominant_link_id = list(batch_data.keys())[dominant_source_idx]
                quality_flags.append({
                    "type": "imbalance",
                    "message": f"数据不平衡：{max_words}/{total_words} 字（{max_words/total_words*100:.1f}%）来自单一来源 ({dominant_link_id})",
                    "severity": "warning"
                })
                issues.append("数据不平衡")
        
        # Check for sparse data
        if avg_words < 500:
            quality_flags.append({
                "type": "sparse",
                "message": f"数据稀疏：平均内容长度仅为 {avg_words:.0f} 字",
                "severity": "info"
            })
            issues.append("数据稀疏")
        elif avg_words < 100:
            quality_flags.append({
                "type": "sparse",
                "message": f"数据严重稀疏：平均内容长度仅为 {avg_words:.0f} 字",
                "severity": "warning"
            })
            issues.append("数据严重稀疏")
        
        # Check comment coverage
        comment_coverage = items_with_comments / num_items if num_items > 0 else 0
        if comment_coverage < 0.5 and num_items > 1:
            quality_flags.append({
                "type": "comment_coverage",
                "message": f"评论覆盖率低：仅 {items_with_comments}/{num_items} 个项目包含评论",
                "severity": "info"
            })
            issues.append("评论覆盖率低")
        elif comment_coverage == 0:
            quality_flags.append({
                "type": "comment_coverage",
                "message": "无评论数据：所有项目都缺少评论",
                "severity": "warning"
            })
            issues.append("无评论数据")
        
        # Check source diversity
        unique_sources = set(sources)
        if len(unique_sources) == 1 and num_items > 1:
            quality_flags.append({
                "type": "source_diversity",
                "message": f"来源单一：所有数据均来自 {unique_sources.pop()}",
                "severity": "info"
            })
            issues.append("来源单一")
        
        # Check for very long content (may need chunking)
        if max(word_counts) > 10000:
            quality_flags.append({
                "type": "long_content",
                "message": f"存在超长内容：最长项目 {max(word_counts)} 字，建议使用分块策略",
                "severity": "info"
            })
        
        # Calculate quality score (0.0 - 1.0)
        score = 1.0
        for flag in quality_flags:
            if flag["severity"] == "error":
                score -= 0.3
            elif flag["severity"] == "warning":
                score -= 0.15
            elif flag["severity"] == "info":
                score -= 0.05
        
        score = max(0.0, min(1.0, score))
        
        summary = "数据质量良好"
        if issues:
            summary = f"发现 {len(issues)} 个潜在问题: {', '.join(issues[:3])}"
        
        return {
            "quality_flags": quality_flags,
            "quality_score": score,
            "summary": summary,
            "statistics": {
                "total_items": num_items,
                "total_words": total_words,
                "avg_words_per_item": avg_words,
                "items_with_comments": items_with_comments,
                "comment_coverage": comment_coverage,
                "unique_sources": len(unique_sources),
                "sources": list(unique_sources)
            }
        }
    
    def chunk_data(
        self,
        data: Dict[str, Any],
        strategy: str,
        chunk_size: int = 2000
    ) -> List[Dict[str, Any]]:
        """
        Chunk data based on strategy.
        
        Args:
            data: Data for a single link_id
            strategy: Chunking strategy:
                - "sequential": Split transcript into sequential chunks
                - "all": Return entire data in one chunk
                - "random_sample": Random sample (for comments)
                - "top_by_likes": Top N by likes (for Bilibili)
            chunk_size: Size of chunks (in words for sequential)
            
        Returns:
            List of data chunks
        """
        chunks = []
        source = data.get("source", "unknown")
        
        if strategy == "all":
            chunks.append(data)
        
        elif strategy == "sequential":
            transcript = data.get("transcript", "")
            if not transcript:
                chunks.append(data)
                return chunks
            
            words = transcript.split()
            num_chunks = (len(words) + chunk_size - 1) // chunk_size
            
            for i in range(num_chunks):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(words))
                chunk_words = words[start_idx:end_idx]
                
                chunk_data_copy = data.copy()
                chunk_data_copy["transcript"] = " ".join(chunk_words)
                chunk_data_copy["chunk_info"] = {
                    "chunk_index": i + 1,
                    "total_chunks": num_chunks,
                    "start_word": start_idx,
                    "end_word": end_idx
                }
                chunks.append(chunk_data_copy)
        
        elif strategy == "random_sample":
            comments = data.get("comments", [])
            if comments:
                sampled = random.sample(
                    comments,
                    min(chunk_size, len(comments))
                )
                chunk_data_copy = data.copy()
                chunk_data_copy["comments"] = sampled
                chunks.append(chunk_data_copy)
            else:
                chunks.append(data)
        
        elif strategy == "top_by_likes":
            # For Bilibili comments, sort by likes
            comments = data.get("comments", [])
            if comments and isinstance(comments[0], dict):
                sorted_comments = sorted(
                    comments,
                    key=lambda x: x.get("likes", 0),
                    reverse=True
                )[:chunk_size]
                chunk_data_copy = data.copy()
                chunk_data_copy["comments"] = sorted_comments
                chunks.append(chunk_data_copy)
            else:
                chunks.append(data)
        
        else:
            logger.warning(f"Unknown chunking strategy: {strategy}, using 'all'")
            chunks.append(data)
        
        return chunks

