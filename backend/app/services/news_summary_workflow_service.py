"""
News Summary Workflow Service.

Orchestrates the complete news article generation pipeline from channel scraping
to final article generation.
"""
import json
import os
import re
import time
import threading
from queue import Queue
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.config import Config, find_project_root
    from app.services.channel_scraper_service import ChannelScraperService
    from app.services.news_outline_service import NewsOutlineService
    from app.services.news_article_service import NewsArticleService
    from scrapers.youtube_scraper import YouTubeScraper
    from research.summarization.content_summarizer import ContentSummarizer
    from research.client import QwenStreamingClient
except ImportError as e:
    logger.warning(f"Unable to import required modules: {e}")
    Config = None  # type: ignore
    find_project_root = None  # type: ignore
    ChannelScraperService = None  # type: ignore
    NewsOutlineService = None  # type: ignore
    NewsArticleService = None  # type: ignore
    YouTubeScraper = None  # type: ignore
    ContentSummarizer = None  # type: ignore
    QwenStreamingClient = None  # type: ignore


class NewsSummaryWorkflowService:
    """Orchestrates the complete news summary workflow from channels to articles."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the news summary workflow service."""
        if Config is None:
            raise RuntimeError("Config module unavailable")
        
        self.config = config or Config()
        self._load_config()
        self._initialize_services()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        news_config = self.config.get('news', {})
        self.workflow_config = news_config.get('workflow', {})
        self.paths_config = news_config.get('paths', {})
        
        # Initialize paths
        project_root = find_project_root() if find_project_root else Path.cwd()
        sessions_dir_str = self.paths_config.get('sessions_dir', 'data/news/sessions')
        
        if Path(sessions_dir_str).is_absolute():
            self.sessions_dir = Path(sessions_dir_str)
        else:
            self.sessions_dir = project_root / sessions_dir_str
        
        # Create directories if needed
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Get workflow settings
        self.steps_config = self.workflow_config.get('steps', {})
        self.content_step_config = self.steps_config.get('content_scraping', {})
        self.continue_on_error = self.workflow_config.get('continue_on_error', True)
        self.save_partial_results = self.workflow_config.get('save_partial_results', True)
        self.session_metadata_file = self.workflow_config.get('session_metadata_file', 'session_metadata.json')
    
    def _initialize_services(self):
        """Initialize dependent services."""
        if ChannelScraperService is None or NewsOutlineService is None or NewsArticleService is None:
            raise RuntimeError("Required services unavailable")
        
        self.channel_scraper = ChannelScraperService()
        self.outline_service = NewsOutlineService(self.config)
        self.article_service = NewsArticleService(self.config)
    
    def create_session(self, date_range: Dict[str, str]) -> str:
        """
        Create a new workflow session and return session ID.
        
        Args:
            date_range: Dictionary with 'start_date' and 'end_date' (YYYY-MM-DD format)
        
        Returns:
            Session ID string
        """
        # Generate session ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Find next sequence number
        sequence = self._get_next_session_sequence()
        session_id = f"news_session_{timestamp}_{sequence:03d}"
        
        # Create session directory
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (session_dir / 'batches').mkdir(exist_ok=True)
        (session_dir / 'outlines').mkdir(exist_ok=True)
        (session_dir / 'articles').mkdir(exist_ok=True)
        
        # Create initial metadata
        metadata = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "date_range": date_range,
            "status": "created",
            "current_step": None,
            "steps": {},
            "artifacts": {},
            "errors": [],
            "metadata": {
                "prompt_version": "v1.0"
            }
        }
        
        # Save metadata
        metadata_file = session_dir / self.session_metadata_file
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Created workflow session: {session_id}")
        logger.info(f"Session date range: {date_range.get('start_date')} to {date_range.get('end_date')}")
        
        return session_id
    
    def _get_next_session_sequence(self) -> int:
        """Get next sequence number for session ID."""
        # Find existing sessions with same timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pattern = f"news_session_{timestamp}_*"
        
        existing_sessions = []
        for session_dir in self.sessions_dir.glob(pattern):
            if session_dir.is_dir():
                parts = session_dir.name.split('_')
                if len(parts) >= 5:
                    try:
                        seq = int(parts[-1])
                        existing_sessions.append(seq)
                    except ValueError:
                        pass
        
        if existing_sessions:
            return max(existing_sessions) + 1
        return 1
    
    def run_workflow(
        self,
        session_id: str,
        date_range: Dict[str, str],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run the complete workflow for a session.
        
        Args:
            session_id: Session ID
            date_range: Dictionary with 'start_date' and 'end_date'
            options: Optional workflow options (channel_ids, etc.)
        
        Returns:
            Dictionary with workflow results
        """
        session_dir = self.sessions_dir / session_id
        if not session_dir.exists():
            raise ValueError(f"Session not found: {session_id}")
        
        logger.info(f"Starting workflow for session: {session_id}")
        
        # Update status to running
        self._update_session_status(session_id, "running", None)
        
        results = {
            "session_id": session_id,
            "status": "running",
            "steps": {},
            "errors": []
        }
        
        # Step 1: Channel Scraping
        if self.steps_config.get('channel_scraping', {}).get('enabled', True):
            try:
                logger.info(f"Step 1: Channel scraping started for session {session_id}")
                step1_result = self._step_channel_scraping(session_id, date_range, options)
                results["steps"]["channel_scraping"] = step1_result
                self._update_session_step(session_id, "channel_scraping", "completed", step1_result)
                logger.info(f"Step 1: Channel scraping completed - {step1_result.get('total_videos', 0)} videos found")
            except Exception as e:
                error_msg = f"Channel scraping failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append({"step": "channel_scraping", "error": error_msg})
                self._update_session_step(session_id, "channel_scraping", "failed", {"error": error_msg})
                
                if not self.continue_on_error:
                    results["status"] = "failed"
                    self._update_session_status(session_id, "failed", "channel_scraping")
                    return results
        
        # Step 2: Content Scraping + Phase 0
        if self.steps_config.get('content_scraping', {}).get('enabled', True):
            try:
                # Get channel batch file from step 1
                channel_batch_file = self._get_channel_batch_file(session_id)
                if not channel_batch_file:
                    raise ValueError("Channel batch file not found")
                
                logger.info(f"Step 2: Content scraping started - loading links from {channel_batch_file}")
                step2_result = self._step_content_scraping_and_phase0(session_id, channel_batch_file, options)
                results["steps"]["content_scraping"] = step2_result
                self._update_session_step(session_id, "content_scraping", "completed", step2_result)
                logger.info(f"Step 2: Content scraping completed - batch_id: {step2_result.get('batch_id')}")
            except Exception as e:
                error_msg = f"Content scraping failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append({"step": "content_scraping", "error": error_msg})
                self._update_session_step(session_id, "content_scraping", "failed", {"error": error_msg})
                
                if not self.continue_on_error:
                    results["status"] = "failed"
                    self._update_session_status(session_id, "failed", "content_scraping")
                    return results
        
        # Step 3: Outline Generation
        if self.steps_config.get('outline_generation', {}).get('enabled', True):
            try:
                # Get batch_id from step 2
                batch_id = results["steps"].get("content_scraping", {}).get("batch_id")
                if not batch_id:
                    raise ValueError("Batch ID not found from content scraping step")
                
                logger.info(f"Step 3: Outline generation started for batch {batch_id}")
                step3_result = self._step_outline_generation(session_id, batch_id)
                results["steps"]["outline_generation"] = step3_result
                self._update_session_step(session_id, "outline_generation", "completed", step3_result)
                logger.info(f"Step 3: Outline generation completed - outline_id: {step3_result.get('outline_id')}")
            except Exception as e:
                error_msg = f"Outline generation failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append({"step": "outline_generation", "error": error_msg})
                self._update_session_step(session_id, "outline_generation", "failed", {"error": error_msg})
                
                if not self.continue_on_error:
                    results["status"] = "failed"
                    self._update_session_status(session_id, "failed", "outline_generation")
                    return results
        
        # Step 4: Article Generation
        if self.steps_config.get('article_generation', {}).get('enabled', True):
            try:
                # Get outline_id from step 3
                outline_id = results["steps"].get("outline_generation", {}).get("outline_id")
                if not outline_id:
                    raise ValueError("Outline ID not found from outline generation step")
                
                logger.info(f"Step 4: Article generation started for outline {outline_id}")
                step4_result = self._step_article_generation(session_id, outline_id)
                results["steps"]["article_generation"] = step4_result
                self._update_session_step(session_id, "article_generation", "completed", step4_result)
                logger.info(f"Step 4: Article generation completed - article_id: {step4_result.get('article_id')}")
            except Exception as e:
                error_msg = f"Article generation failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append({"step": "article_generation", "error": error_msg})
                self._update_session_step(session_id, "article_generation", "failed", {"error": error_msg})
                
                if not self.continue_on_error:
                    results["status"] = "failed"
                    self._update_session_status(session_id, "failed", "article_generation")
                    return results
        
        # Workflow completed
        results["status"] = "completed"
        self._update_session_status(session_id, "completed", "article_generation")
        logger.info(f"Workflow completed for session {session_id}")
        
        return results
    
    def _step_channel_scraping(
        self,
        session_id: str,
        date_range: Dict[str, str],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Step 1: Scrape channels for video links within date range."""
        session_dir = self.sessions_dir / session_id
        
        # Parse dates
        start_date = datetime.strptime(date_range['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(date_range['end_date'], '%Y-%m-%d')
        
        # Get channel IDs from options if provided
        channel_ids = options.get('channel_ids') if options else None
        
        # Run channel scraping
        result = self.channel_scraper.scrape_channels(
            start_date=start_date,
            end_date=end_date,
            channel_ids=channel_ids
        )
        
        # Save channel batch file to session directory
        batch_id = result.get('batch_id')
        if batch_id:
            # Read batch file from channel scraper output
            batches_dir = self.channel_scraper.batches_dir
            batch_file = batches_dir / f"{batch_id}.txt"
            
            if batch_file.exists():
                # Copy to session directory
                session_batch_file = session_dir / f"channel_batch_{batch_id}.txt"
                with open(batch_file, 'r', encoding='utf-8') as src:
                    with open(session_batch_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                
                # Update artifacts
                self._update_session_artifact(session_id, "channel_batch_file", f"channel_batch_{batch_id}.txt")
        
        return {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "total_videos": result.get('total_videos', 0),
            "channels_scraped": result.get('channels_scraped', 0)
        }
    
    def _step_content_scraping_and_phase0(
        self,
        session_id: str,
        channel_batch_file: Path,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Step 2: Scrape links and run Phase 0 summarization within the news session."""
        if YouTubeScraper is None or ContentSummarizer is None:
            raise RuntimeError("Scraper/summarizer dependencies unavailable")
        
        session_dir = self.sessions_dir / session_id
        if not session_dir.exists():
            raise ValueError(f"Session directory not found: {session_dir}")
        
        links = self._load_links_from_batch_file(channel_batch_file)
        if not links:
            raise ValueError("Channel batch file contains no video links to scrape")
        
        # Apply optional limits/deduplication
        unique_links: List[str] = []
        seen_links = set()
        for link in links:
            if link not in seen_links:
                unique_links.append(link)
                seen_links.add(link)
        
        content_options = options or {}
        max_links = content_options.get('max_links') or self.content_step_config.get('max_links')
        if max_links:
            unique_links = unique_links[:int(max_links)]
        
        if not unique_links:
            raise ValueError("No unique links available after applying filters")
        
        batch_id = self._derive_phase0_batch_id(channel_batch_file)
        batch_dir_format = self.content_step_config.get('batch_dir_format', 'batches/run_{batch_id}')
        relative_batch_dir = Path(batch_dir_format.format(batch_id=batch_id))
        batch_dir = session_dir / relative_batch_dir
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        scraper_headless = bool(self.content_step_config.get('headless', False))
        scraper_workers = self.content_step_config.get('scraper_workers')
        summarizer_workers = self.content_step_config.get('summarizer_workers')
        scraper_workers = int(scraper_workers or self.config.get('scraping.control_center.worker_pool_size', 4))
        summarizer_workers = int(summarizer_workers or self.config.get('research.summarization.worker_count', 4))
        scraper_workers = max(1, min(scraper_workers, len(unique_links)))
        summarizer_workers = max(1, min(summarizer_workers, len(unique_links)))
        
        logger.info(
            f"[ContentScraping] Starting Phase 0 for session {session_id}: "
            f"{len(unique_links)} link(s), batch_id={batch_id}, output={batch_dir}, "
            f"scraper_workers={scraper_workers}, summarizer_workers={summarizer_workers}"
        )
        
        # Validate summarizer configuration early to fail fast if API key is missing/misconfigured
        try:
            _summarizer_probe = self._create_content_summarizer()
        finally:
            _summarizer_probe = None
        
        # Queues and synchronization primitives
        url_queue: Queue = Queue()
        result_queue: Queue = Queue()
        failure_lock = threading.Lock()
        success_lock = threading.Lock()
        failure_details: List[Dict[str, Any]] = []
        related_link_ids: List[str] = []
        saved_files: List[str] = []
        success_counter = {"value": 0}
        
        tasks = []
        for idx, url in enumerate(unique_links, 1):
            link_id = self._generate_link_id(url, idx)
            task = (idx, url, link_id)
            tasks.append(task)
            url_queue.put(task)
        
        def record_failure(entry: Dict[str, Any]):
            with failure_lock:
                failure_details.append(entry)
        
        def scraper_worker():
            scraper = YouTubeScraper(headless=scraper_headless)
            while True:
                task = url_queue.get()
                if task is None:
                    url_queue.task_done()
                    break
                
                idx, url, link_id = task
                logger.info(f"[ContentScraping] [Scraper] ({idx}/{len(tasks)}) Processing {url} as {link_id}")
                try:
                    scrape_result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
                    
                    if not scrape_result or not scrape_result.get('success'):
                        error_msg = scrape_result.get('error') if isinstance(scrape_result, dict) else "Unknown scraping error"
                        record_failure({"url": url, "link_id": link_id, "error": error_msg, "stage": "scraping"})
                        continue
                    
                    transcript = scrape_result.get('content') or scrape_result.get('transcript') or ""
                    if not transcript.strip():
                        record_failure({"url": url, "link_id": link_id, "error": "No transcript content", "stage": "scraping"})
                        continue
                    
                    metadata = {
                        "title": scrape_result.get('title') or scrape_result.get('metadata', {}).get('title') or "",
                        "author": scrape_result.get('author') or scrape_result.get('metadata', {}).get('author') or "",
                        "url": scrape_result.get('url', url),
                        "word_count": scrape_result.get('word_count') or len(transcript.split()),
                        "publish_date": scrape_result.get('publish_date') or ""
                    }
                    
                    result_queue.put({
                        "idx": idx,
                        "url": url,
                        "link_id": link_id,
                        "transcript": transcript,
                        "metadata": metadata,
                        "source": scrape_result.get('source', 'youtube')
                    })
                except Exception as e:
                    logger.error(f"[ContentScraping] [Scraper] Error for {url}: {e}", exc_info=True)
                    record_failure({"url": url, "link_id": link_id, "error": str(e), "stage": "scraping"})
                finally:
                    url_queue.task_done()
            
            try:
                scraper.close()
            except Exception:
                pass
        
        def summarizer_worker(worker_idx: int):
            summarizer = self._create_content_summarizer()
            while True:
                task = result_queue.get()
                if task is None:
                    result_queue.task_done()
                    break
                
                link_id = task["link_id"]
                url = task["url"]
                transcript = task["transcript"]
                metadata = task["metadata"]
                source = task["source"]
                
                try:
                    summary = summarizer.summarize_content_item(
                        link_id=link_id,
                        transcript=transcript,
                        comments=None,
                        metadata=metadata
                    )
                    
                    complete_record = {
                        "batch_id": batch_id,
                        "link_id": link_id,
                        "source": source,
                        "metadata": metadata,
                        "transcript": transcript,
                        "comments": None,
                        "summary": summary,
                        "completed_at": time.time()
                    }
                    
                    saved_path = self._save_phase0_record(complete_record, batch_dir, batch_id, link_id)
                    relative_saved = str(saved_path.relative_to(session_dir)).replace("\\", "/")
                    
                    with success_lock:
                        success_counter["value"] += 1
                        related_link_ids.append(link_id)
                        saved_files.append(relative_saved)
                except Exception as e:
                    logger.error(f"[ContentScraping] [Summarizer-{worker_idx}] Error for {link_id}: {e}", exc_info=True)
                    record_failure({"url": url, "link_id": link_id, "error": f"Phase0 summarization failed: {e}", "stage": "summarization"})
                finally:
                    result_queue.task_done()
        
        # Start summarizer workers first so they pick up scraping results immediately
        summarizer_threads = []
        for i in range(summarizer_workers):
            thread = threading.Thread(
                target=summarizer_worker,
                args=(i + 1,),
                name=f"news-phase0-summarizer-{i+1}",
                daemon=True
            )
            thread.start()
            summarizer_threads.append(thread)
        
        scraper_threads = []
        for i in range(scraper_workers):
            thread = threading.Thread(
                target=scraper_worker,
                name=f"news-phase0-scraper-{i+1}",
                daemon=True
            )
            thread.start()
            scraper_threads.append(thread)
        
        # Wait for scraping stage to finish and shut down scraper workers
        url_queue.join()
        for _ in scraper_threads:
            url_queue.put(None)
        for thread in scraper_threads:
            thread.join()
        
        # Wait for summarization to complete and shut down summarizer workers
        result_queue.join()
        for _ in summarizer_threads:
            result_queue.put(None)
        for thread in summarizer_threads:
            thread.join()
        
        success_count = success_counter["value"]
        if success_count == 0:
            raise RuntimeError("Content scraping succeeded for 0 links; cannot continue to outline generation")
        
        # Record artifacts for downstream steps
        try:
            relative_dir_str = str(relative_batch_dir).replace("\\", "/")
            self._update_session_artifact(session_id, "phase0_batch_dir", relative_dir_str)
            self._update_session_artifact(session_id, "phase0_batch_id", batch_id)
        except Exception as e:
            logger.warning(f"Failed to update session artifacts for Phase 0: {e}")
        
        logger.info(
            f"[ContentScraping] Completed Phase 0 for session {session_id}: "
            f"{success_count}/{len(unique_links)} successes (batch_id={batch_id})"
        )
        
        return {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "total_links": len(unique_links),
            "success_count": success_count,
            "failed_count": len(failure_details),
            "failed_links": failure_details,
            "related_link_ids": related_link_ids,
            "batch_dir": str(relative_batch_dir).replace("\\", "/"),
            "saved_files": saved_files
        }
    
    def _load_links_from_batch_file(self, batch_file: Path) -> List[str]:
        """Read video URLs from the channel batch file."""
        if not batch_file.exists():
            logger.error(f"Channel batch file not found: {batch_file}")
            return []
        
        links: List[str] = []
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('http://') or line.startswith('https://'):
                    links.append(line)
        
        return links
    
    def _derive_phase0_batch_id(self, channel_batch_file: Path) -> str:
        """Derive Phase 0 batch ID from the channel batch filename or timestamp."""
        stem = channel_batch_file.stem
        match = re.match(r'channel_batch_(.+)', stem)
        if match:
            return match.group(1)
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _generate_link_id(self, url: str, index: int) -> str:
        """Generate a stable link_id for downstream processing."""
        video_id = self._extract_youtube_video_id(url)
        if video_id:
            return f"yt_{video_id}"
        return f"yt_req{index:03d}"
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract an 11-character YouTube video ID from a URL."""
        pattern = re.compile(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})')
        match = pattern.search(url)
        if match:
            return match.group(1)
        return None
    
    def _create_content_summarizer(self) -> ContentSummarizer:
        """Create a ContentSummarizer instance with configured Qwen client."""
        if ContentSummarizer is None or QwenStreamingClient is None:
            raise RuntimeError("Summarization dependencies unavailable")
        
        api_key = (
            self.content_step_config.get('api_key')
            or self.config.get('news.article_generation.api_key')
            or self.config.get('qwen.api_key')
            or os.getenv('QWEN_API_KEY')
            or os.getenv('DASHSCOPE_API_KEY')
        )
        
        if not api_key:
            raise ValueError(
                "Qwen API key not configured. Set qwen.api_key in config.yaml or "
                "define QWEN_API_KEY/DASHSCOPE_API_KEY environment variables."
            )
        
        client = QwenStreamingClient(api_key=api_key)
        return ContentSummarizer(client=client, config=self.config)
    
    def _save_phase0_record(
        self,
        record: Dict[str, Any],
        batch_dir: Path,
        batch_id: str,
        link_id: str
    ) -> Path:
        """Persist a Phase 0 complete record to the session batch directory."""
        source = (record.get('source') or '').lower()
        prefix_map = {
            'youtube': 'YT',
            'bilibili': 'BILI',
            'article': 'AR',
            'reddit': 'RD'
        }
        prefix = prefix_map.get(source, (source[:4] or 'SRC').upper())
        filename = batch_dir / f"{batch_id}_{prefix}_{link_id}_complete.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"[ContentScraping] Saved Phase 0 file: {filename}")
        return filename
    
    def _step_outline_generation(self, session_id: str, batch_id: str) -> Dict[str, Any]:
        """Step 3: Generate news outline from Phase 0 summaries."""
        session_dir = self.sessions_dir / session_id
        
        # Adapt outline service to use session batch directory
        # Temporarily override batch_source_dir in outline service
        original_batch_source_dir = self.outline_service.batch_source_dir
        session_batches_dir = session_dir / 'batches'
        self.outline_service.batch_source_dir = session_batches_dir
        
        try:
            # Generate outline (this will look in session/batches/run_{batch_id}/)
            outline = self.outline_service.generate_outline_from_batch(batch_id=batch_id)
            
            # Save outline to session directory instead of default outlines_dir
            original_outlines_dir = self.outline_service.outlines_dir
            session_outlines_dir = session_dir / 'outlines'
            self.outline_service.outlines_dir = session_outlines_dir
            
            try:
                outline_path = self.outline_service.save_outline(outline)
                outline_id = outline.get('outline_id')
                
                # Update artifacts
                self._update_session_artifact(session_id, "outline_file", f"outlines/{outline_id}.json")
                
                return {
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "outline_id": outline_id,
                    "batch_id": batch_id
                }
            finally:
                # Restore original outlines_dir
                self.outline_service.outlines_dir = original_outlines_dir
        finally:
            # Restore original batch_source_dir
            self.outline_service.batch_source_dir = original_batch_source_dir
    
    def _step_article_generation(self, session_id: str, outline_id: str) -> Dict[str, Any]:
        """Step 4: Generate news article from outline."""
        session_dir = self.sessions_dir / session_id
        
        # Adapt article service to use session directories
        # Temporarily override paths in article service
        original_outlines_dir = self.article_service.outlines_dir
        original_batch_source_dir = self.article_service.batch_source_dir
        original_articles_dir = self.article_service.articles_dir
        
        session_outlines_dir = session_dir / 'outlines'
        session_batches_dir = session_dir / 'batches'
        session_articles_dir = session_dir / 'articles'
        
        self.article_service.outlines_dir = session_outlines_dir
        self.article_service.batch_source_dir = session_batches_dir
        self.article_service.articles_dir = session_articles_dir
        
        try:
            # Generate article
            markdown_content, metadata = self.article_service.generate_article_from_outline(outline_id)
            
            # Save article
            md_file, json_file = self.article_service.save_article(metadata, markdown_content)
            article_id = metadata.get('article_id')
            
            # Update artifacts
            self._update_session_artifact(session_id, "article_file", f"articles/{article_id}.md")
            self._update_session_artifact(session_id, "article_metadata_file", f"articles/{article_id}.json")
            
            return {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "article_id": article_id,
                "outline_id": outline_id
            }
        finally:
            # Restore original paths
            self.article_service.outlines_dir = original_outlines_dir
            self.article_service.batch_source_dir = original_batch_source_dir
            self.article_service.articles_dir = original_articles_dir
    
    def _get_channel_batch_file(self, session_id: str) -> Optional[Path]:
        """Get channel batch file for a session."""
        session_dir = self.sessions_dir / session_id
        
        # Look for channel_batch_*.txt files
        batch_files = list(session_dir.glob("channel_batch_*.txt"))
        if batch_files:
            return batch_files[0]  # Return first match
        
        return None
    
    def _update_session_status(self, session_id: str, status: str, current_step: Optional[str]):
        """Update session status in metadata."""
        session_dir = self.sessions_dir / session_id
        metadata_file = session_dir / self.session_metadata_file
        
        if not metadata_file.exists():
            return
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        metadata['status'] = status
        metadata['current_step'] = current_step
        if status == "completed":
            metadata['completed_at'] = datetime.now().isoformat()
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _update_session_step(self, session_id: str, step_name: str, status: str, result: Dict[str, Any]):
        """Update a workflow step in session metadata."""
        session_dir = self.sessions_dir / session_id
        metadata_file = session_dir / self.session_metadata_file
        
        if not metadata_file.exists():
            return
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        if 'steps' not in metadata:
            metadata['steps'] = {}
        
        metadata['steps'][step_name] = {
            "status": status,
            **result
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _update_session_artifact(self, session_id: str, artifact_key: str, artifact_path: str):
        """Update an artifact path in session metadata."""
        session_dir = self.sessions_dir / session_id
        metadata_file = session_dir / self.session_metadata_file
        
        if not metadata_file.exists():
            return
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        if 'artifacts' not in metadata:
            metadata['artifacts'] = {}
        
        metadata['artifacts'][artifact_key] = artifact_path
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a workflow session."""
        session_dir = self.sessions_dir / session_id
        
        if not session_dir.exists():
            raise ValueError(f"Session not found: {session_id}")
        
        metadata_file = session_dir / self.session_metadata_file
        if not metadata_file.exists():
            raise ValueError(f"Session metadata not found: {session_id}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return {
            "session_id": session_id,
            "status": metadata.get('status', 'unknown'),
            "current_step": metadata.get('current_step'),
            "metadata": metadata
        }
    
    def load_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Load session metadata JSON file."""
        session_dir = self.sessions_dir / session_id
        metadata_file = session_dir / self.session_metadata_file
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Session metadata not found: {session_id}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_sessions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all workflow sessions, optionally filtered by date range or status."""
        sessions = []
        
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            if not session_dir.name.startswith('news_session_'):
                continue
            
            try:
                metadata = self.load_session_metadata(session_dir.name)
                
                # Apply filters
                if status and metadata.get('status') != status:
                    continue
                
                if start_date or end_date:
                    session_start = metadata.get('date_range', {}).get('start_date')
                    session_end = metadata.get('date_range', {}).get('end_date')
                    
                    if start_date and session_end and session_end < start_date:
                        continue
                    if end_date and session_start and session_start > end_date:
                        continue
                
                sessions.append({
                    "session_id": session_dir.name,
                    "created_at": metadata.get('created_at'),
                    "status": metadata.get('status'),
                    "date_range": metadata.get('date_range'),
                    "current_step": metadata.get('current_step')
                })
            except Exception as e:
                logger.warning(f"Failed to load session metadata for {session_dir.name}: {e}")
                continue
        
        # Sort by created_at descending
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return sessions

