"""
Scraping service with progress tracking.
"""
import asyncio
from typing import Dict, List, Optional, Callable
from pathlib import Path
import sys
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scrapers.youtube_scraper import YouTubeScraper
from scrapers.bilibili_scraper import BilibiliScraper
from scrapers.article_scraper import ArticleScraper
from scrapers.reddit_scraper import RedditScraper
from app.services.progress_service import ProgressService
from tests.test_links_loader import TestLinksLoader


class ScrapingService:
    """Service for running scrapers with progress tracking."""
    
    def __init__(self, progress_service: ProgressService):
        """
        Initialize scraping service.
        
        Args:
            progress_service: Progress service for tracking and broadcasting
        """
        self.progress_service = progress_service
    
    def create_progress_callback(
        self,
        batch_id: str,
        link_id: str,
        url: str,
        source: str
    ) -> Callable:
        """
        Create a progress callback that bridges scraper progress to ProgressService.
        
        Args:
            batch_id: Batch ID
            link_id: Link ID
            url: Link URL
            source: Source type (youtube, bilibili, etc.)
        
        Returns:
            Callback function for scrapers
        """
        async def progress_callback(data: dict):
            """
            Callback function called by scrapers.
            
            Args:
                data: Dictionary with:
                    - stage: Current stage name
                    - progress: Progress percentage (0.0-100.0)
                    - message: Status message
                    - bytes_downloaded: Optional bytes downloaded
                    - total_bytes: Optional total bytes
            """
            try:
                stage = data.get('stage', 'unknown')
                progress = data.get('progress', 0.0)
                message = data.get('message', '')
                bytes_downloaded = data.get('bytes_downloaded', 0)
                total_bytes = data.get('total_bytes', 0)
                
                # Calculate overall progress based on source and stage
                overall_progress = self.progress_service._calculate_overall_progress(
                    source, stage, progress
                )
                
                # Update via ProgressService
                await self.progress_service.update_link_progress(
                    batch_id=batch_id,
                    link_id=link_id,
                    url=url,
                    stage=stage,
                    stage_progress=progress,
                    overall_progress=overall_progress,
                    message=message,
                    metadata={
                        'bytes_downloaded': bytes_downloaded,
                        'total_bytes': total_bytes,
                        'source': source
                    }
                )
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        # Use a queue to pass progress updates from sync context to async context
        # This will be checked by the scraping service
        import queue
        progress_queue = queue.Queue()
        
        def sync_wrapper(data: dict):
            """Wrapper to queue progress updates from sync context."""
            try:
                progress_queue.put_nowait(data)
            except queue.Full:
                logger.warning(f"Progress queue full, dropping update: {data.get('stage', 'unknown')}")
            except Exception as e:
                logger.error(f"Error queuing progress update: {e}")
        
        # Store queue and async callback for async polling
        sync_wrapper._queue = progress_queue
        sync_wrapper._async_callback = progress_callback
        
        return sync_wrapper
    
    async def scrape_link(
        self,
        batch_id: str,
        link: dict
    ) -> Dict:
        """
        Scrape a single link with progress tracking.
        
        Args:
            batch_id: Batch ID
            link: Link dictionary with url, link_id, source
        
        Returns:
            Result dictionary
        """
        link_id = link.get('link_id') or link.get('id', 'unknown')
        url = link['url']
        source = link.get('source', 'unknown')
        
        logger.info(f"Starting scraping: {source} - {url}")
        
        # Create progress callback
        progress_cb = self.create_progress_callback(batch_id, link_id, url, source)
        
        # Get appropriate scraper
        scraper = None
        try:
            if source == 'youtube':
                scraper = YouTubeScraper(progress_callback=progress_cb)
            elif source == 'bilibili':
                scraper = BilibiliScraper(progress_callback=progress_cb)
            elif source == 'article':
                scraper = ArticleScraper(progress_callback=progress_cb)
            elif source == 'reddit':
                scraper = RedditScraper(progress_callback=progress_cb)
            else:
                # Try to detect from URL
                if 'youtube.com' in url or 'youtu.be' in url:
                    scraper = YouTubeScraper(progress_callback=progress_cb)
                    source = 'youtube'
                elif 'bilibili.com' in url:
                    scraper = BilibiliScraper(progress_callback=progress_cb)
                    source = 'bilibili'
                elif 'reddit.com' in url:
                    scraper = RedditScraper(progress_callback=progress_cb)
                    source = 'reddit'
                else:
                    scraper = ArticleScraper(progress_callback=progress_cb)
                    source = 'article'
            
            # Update status to in-progress (kebab-case for frontend compatibility)
            await self.progress_service.update_link_status(
                batch_id, link_id, url, 'in-progress',
                metadata={'source': source}
            )
            
            # Start progress polling task
            progress_task = None
            scraping_done = False
            if hasattr(progress_cb, '_queue') and hasattr(progress_cb, '_async_callback'):
                # Import queue module to access Empty exception (must be before shadowing)
                import queue as queue_module
                
                async_callback = progress_cb._async_callback
                
                async def poll_progress():
                    progress_queue = progress_cb._queue
                    while not scraping_done:
                        # Check for cancellation during polling
                        if self.progress_service.is_cancelled(batch_id):
                            logger.info(f"Cancellation detected during progress polling for {url}")
                            break
                        try:
                            # Try to get item from queue without blocking
                            try:
                                data = progress_queue.get_nowait()
                                await async_callback(data)
                            except queue_module.Empty:
                                # No item available, wait a bit
                                await asyncio.sleep(0.1)
                        except Exception as e:
                            logger.error(f"Error polling progress: {e}")
                            await asyncio.sleep(0.1)
                    # Process any remaining items
                    while True:
                        try:
                            data = progress_queue.get_nowait()
                            await async_callback(data)
                        except queue_module.Empty:
                            break
                
                progress_task = asyncio.create_task(poll_progress())
            
            # Scrape (this will call progress_callback throughout)
            # Run in thread pool to avoid blocking
            # Check cancellation before starting
            if self.progress_service.is_cancelled(batch_id):
                await self.progress_service.update_link_status(
                    batch_id, link_id, url, 'failed',
                    error="Cancelled by user",
                    metadata={'source': source}
                )
                return {
                    'success': False,
                    'error': 'Cancelled by user',
                    'url': url
                }
            
            try:
                result = await asyncio.to_thread(
                    scraper.extract,
                    url,
                    batch_id=batch_id,
                    link_id=link_id
                )
                
                # Check cancellation after scraping
                if self.progress_service.is_cancelled(batch_id):
                    logger.info(f"Scraping cancelled for {url}, stopping processing")
                    await self.progress_service.update_link_status(
                        batch_id, link_id, url, 'failed',
                        error="Cancelled by user",
                        metadata={'source': source}
                    )
                    return {
                        'success': False,
                        'error': 'Cancelled by user',
                        'url': url
                    }
            finally:
                # Mark scraping as done and wait for any remaining progress updates
                scraping_done = True
                if progress_task:
                    # Wait a bit for final progress updates
                    await asyncio.sleep(0.5)
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass
            
            if result.get('success'):
                await self.progress_service.update_link_status(
                    batch_id, link_id, url, 'completed',
                    metadata={
                        'source': source,
                        'word_count': result.get('word_count', 0),
                        'title': result.get('title', '')
                    }
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await self.progress_service.update_link_status(
                    batch_id, link_id, url, 'failed',
                    error=error_msg,
                    metadata={'source': source}
                )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error scraping {url}: {error_msg}")
            await self.progress_service.update_link_status(
                batch_id, link_id, url, 'failed',
                error=error_msg,
                metadata={'source': source}
            )
            return {
                'success': False,
                'error': error_msg,
                'url': url
            }
        finally:
            if scraper:
                try:
                    scraper.close()
                except:
                    pass
    
    async def scrape_batch(
        self,
        batch_id: str,
        max_concurrent: int = 3
    ) -> List[Dict]:
        """
        Scrape all links in a batch with progress tracking.
        
        Args:
            batch_id: Batch ID
            max_concurrent: Maximum concurrent scrapers
        
        Returns:
            List of results
        """
        # Load links from test_links.json
        loader = TestLinksLoader()
        links = []
        
        try:
            # Get all link types
            for source in ['youtube', 'bilibili', 'article', 'reddit']:
                source_links = loader.get_links(source)
                for link in source_links:
                    link['source'] = source
                    links.append(link)
        except Exception as e:
            logger.error(f"Error loading links: {e}")
            return []
        
        logger.info(f"Starting batch scraping: {len(links)} links")
        
        # Initialize all links as pending
        for link in links:
            link_id = link.get('link_id') or link.get('id', 'unknown')
            url = link['url']
            source = link.get('source', 'unknown')
            await self.progress_service.update_link_status(
                batch_id, link_id, url, 'pending',
                metadata={'source': source}
            )
        
        # Scrape links with concurrency limit
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(link):
            # Check cancellation before starting each link
            if self.progress_service.is_cancelled(batch_id):
                link_id = link.get('link_id') or link.get('id', 'unknown')
                url = link['url']
                await self.progress_service.update_link_status(
                    batch_id, link_id, url, 'failed',
                    error="Cancelled by user"
                )
                return {
                    'success': False,
                    'error': 'Cancelled by user',
                    'url': url
                }
            async with semaphore:
                return await self.scrape_link(batch_id, link)
        
        tasks = [scrape_with_semaphore(link) for link in links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # If cancelled, mark remaining links as cancelled
        if self.progress_service.is_cancelled(batch_id):
            logger.info(f"Batch {batch_id} was cancelled, stopping processing")
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                link = links[i]
                link_id = link.get('link_id') or link.get('id', 'unknown')
                url = link['url']
                await self.progress_service.update_link_status(
                    batch_id, link_id, url, 'failed',
                    error=str(result)
                )
                final_results.append({
                    'success': False,
                    'error': str(result),
                    'url': url
                })
            else:
                final_results.append(result)
        
        return final_results
