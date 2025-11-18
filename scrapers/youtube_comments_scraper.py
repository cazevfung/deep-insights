"""YouTube comments scraper using Playwright."""
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from scrapers.base_scraper import BaseScraper


class YouTubeCommentsScraper(BaseScraper):
    """Extract top-level comments from YouTube videos."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.video_id_pattern = re.compile(
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        )
        # Increase timeout for YouTube (can be slow to load)
        # Ensure at least 60 seconds for YouTube pages
        config_timeout = self.scraper_config.get('timeout', 60000)
        base_timeout = self.timeout
        self.timeout = max(self.timeout, config_timeout, 60000)
        logger.debug(
            f"[YouTubeComments] Timeout configuration: base={base_timeout}ms, config={config_timeout}ms, "
            f"final={self.timeout}ms"
        )
        # Retry configuration
        self.max_retries = 3
        self.retry_delay_base = 2.0  # Base delay in seconds
        logger.debug(f"[YouTubeComments] Retry configuration: max_retries={self.max_retries}, delay_base={self.retry_delay_base}s")

    def validate_url(self, url: str) -> bool:
        return 'youtube.com' in url or 'youtu.be' in url

    def _extract_video_id(self, url: str) -> str:
        match = self.video_id_pattern.search(url)
        if match:
            return match.group(1)
        if 'watch?v=' in url:
            parts = url.split('watch?v=')
            if len(parts) > 1:
                return parts[1].split('&')[0]
        raise ValueError(f"Could not extract video ID from URL: {url}")

    def _extract_metadata(self, page: Page) -> Dict:
        metadata = {
            'title': 'Unknown',
            'author': 'Unknown',
            'publish_date': '',
            'source': 'YouTube'
        }
        try:
            title_selectors = [
                'h1.ytd-watch-metadata yt-formatted-string',
                'h1.ytd-video-primary-info-renderer',
                'title'
            ]
            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        metadata['title'] = element.inner_text(timeout=2000).strip()
                        break
                except Exception:
                    continue

            try:
                channel = page.locator('ytd-channel-name a').first
                if channel.count() > 0:
                    metadata['author'] = channel.inner_text(timeout=2000).strip()
            except Exception:
                pass

            try:
                date_element = page.locator('ytd-video-primary-info-renderer span').first
                if date_element.count() > 0:
                    date_text = date_element.inner_text(timeout=2000).strip()
                    if date_text:
                        metadata['publish_date'] = date_text
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        return metadata

    def _scroll_comments_three_cycles(self, page: Page) -> None:
        # Ensure comments container is visible
        try:
            comments_root = page.locator('#comments').first
            if comments_root.count() > 0:
                comments_root.scroll_into_view_if_needed()
        except Exception:
            pass

        # Initial trigger: scroll down then up to get comments loading
        try:
            # Scroll down to trigger initial comment loading
            page.evaluate('() => window.scrollBy(0, window.innerHeight * 2)')
            time.sleep(1.0)
            # Scroll back up to ensure comments section is in view
            page.evaluate('() => window.scrollBy(0, -window.innerHeight)')
            time.sleep(0.5)
            logger.debug("Initial scroll trigger completed")
        except Exception as e:
            logger.debug(f"Initial scroll trigger error: {e}")

        # Perform three cycles of loading more comments
        selector = 'ytd-comment-thread-renderer #content-text'
        last_count = 0
        for i in range(3):
            try:
                # Scroll down the page progressively
                page.evaluate('() => window.scrollBy(0, window.innerHeight)')
                time.sleep(0.5)
                page.evaluate('() => window.scrollBy(0, window.innerHeight)')
                time.sleep(0.5)

                # Wait up to ~4s for more comments
                start = time.time()
                while time.time() - start < 4:
                    count = page.locator(selector).count()
                    if count > last_count:
                        last_count = count
                        break
                    time.sleep(0.25)
            except Exception as e:
                logger.debug(f"Scroll cycle {i+1} error: {e}")

    def _clean_and_filter_comments(self, texts: List[str]) -> List[str]:
        filtered: List[str] = []
        seen = set()
        for t in texts:
            if not t:
                continue
            # Normalize whitespace
            cleaned = ' '.join(t.split()).strip()
            if not cleaned:
                continue
            # Word threshold: > 12 words
            if len(cleaned.split()) > 12:
                if cleaned not in seen:
                    seen.add(cleaned)
                    filtered.append(cleaned)
        return filtered
    
    def _goto_with_retry(self, page: Page, context, url: str, max_retries: int = None) -> Tuple[bool, Page]:
        """
        Navigate to URL with retry logic for timeout and connection errors.
        
        When connection errors occur, this method will recreate the browser context and page
        to recover from browser crashes or disconnections.
        
        Args:
            page: Playwright page object
            context: Playwright browser context object
            url: URL to navigate to
            max_retries: Maximum number of retries (defaults to self.max_retries)
            
        Returns:
            Tuple of (success: bool, page: Page) where page may be a new page if context was recreated
        """
        max_retries = max_retries or self.max_retries
        current_page = page
        current_context = context
        
        # Log initial state
        logger.info(f"[YouTubeComments] Starting navigation to {url} with timeout={self.timeout}ms, max_retries={max_retries}")
        logger.debug(f"[YouTubeComments] Page state: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
        
        def _recreate_context_and_page():
            """Recreate browser context and page when connection is lost."""
            nonlocal current_page, current_context
            logger.warning(f"[YouTubeComments] Recreating browser context and page due to connection error")
            try:
                # Close old page and context if they still exist
                try:
                    if not current_page.is_closed():
                        current_page.close()
                except:
                    pass
                try:
                    current_context.close()
                except:
                    pass
            except:
                pass
            
            # Create new context and page
            try:
                current_context = self._create_context()
                logger.debug(f"[YouTubeComments] New browser context created successfully")
                current_page = current_context.new_page()
                logger.debug(f"[YouTubeComments] New page created successfully")
                return True
            except Exception as e:
                logger.error(f"[YouTubeComments] Failed to recreate context/page: {e}")
                import traceback
                logger.error(f"[YouTubeComments] Traceback: {traceback.format_exc()}")
                return False
        
        for attempt in range(max_retries):
            attempt_start_time = time.time()
            try:
                if attempt > 0:
                    delay = self.retry_delay_base * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[YouTubeComments] Retrying page navigation (attempt {attempt + 1}/{max_retries}) after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                logger.info(f"[YouTubeComments] Navigating to {url} (attempt {attempt + 1}/{max_retries}, timeout={self.timeout}ms)")
                
                # Check page state before navigation
                if current_page.is_closed():
                    logger.warning(f"[YouTubeComments] Page is closed before navigation attempt {attempt + 1}, recreating...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                
                # Check if context is still valid by trying to access it
                try:
                    _ = current_context.pages  # This will raise if context is invalid
                except Exception as context_check_error:
                    logger.warning(f"[YouTubeComments] Context appears invalid: {context_check_error}, recreating...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                
                # Perform navigation
                current_page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                
                elapsed = round((time.time() - attempt_start_time) * 1000, 0)
                logger.info(f"[YouTubeComments] ✓ Successfully navigated to {url} in {elapsed}ms (attempt {attempt + 1})")
                logger.debug(f"[YouTubeComments] Final page URL: {current_page.url}")
                return (True, current_page)
                
            except PlaywrightTimeout as e:
                elapsed = round((time.time() - attempt_start_time) * 1000, 0)
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(
                    f"[YouTubeComments] Page.goto TIMEOUT on attempt {attempt + 1}/{max_retries} "
                    f"(after {elapsed}ms, timeout={self.timeout}ms): {error_type}: {error_msg}"
                )
                logger.debug(f"[YouTubeComments] Page state after timeout: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
                
                if attempt == max_retries - 1:
                    logger.error(
                        f"[YouTubeComments] ✗ All {max_retries} navigation attempts FAILED with timeout. "
                        f"URL: {url}, Timeout setting: {self.timeout}ms, Total time: {round((time.time() - attempt_start_time) * 1000, 0)}ms"
                    )
                    return (False, current_page)
                # Continue to retry - page.goto can be called multiple times
                
            except Exception as e:
                elapsed = round((time.time() - attempt_start_time) * 1000, 0)
                error_msg = str(e)
                error_type = type(e).__name__
                full_traceback = None
                try:
                    import traceback
                    full_traceback = traceback.format_exc()
                except:
                    pass
                
                # Check for network errors
                if "ERR_SOCKET_NOT_CONNECTED" in error_msg or "net::ERR" in error_msg:
                    logger.error(
                        f"[YouTubeComments] Network error on attempt {attempt + 1}/{max_retries} "
                        f"(after {elapsed}ms): {error_type}: {error_msg}"
                    )
                    if full_traceback:
                        logger.debug(f"[YouTubeComments] Full traceback:\n{full_traceback}")
                    logger.debug(f"[YouTubeComments] Page state after network error: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
                    
                    # Recreate context and page for network errors (connection may be lost)
                    logger.warning(f"[YouTubeComments] Network error detected, recreating browser context and page...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            f"[YouTubeComments] ✗ All {max_retries} navigation attempts FAILED with network error. "
                            f"URL: {url}, Error: {error_msg}"
                        )
                        return (False, current_page)
                    # Wait longer for network errors
                    network_delay = self.retry_delay_base * (2 ** attempt)
                    logger.info(f"[YouTubeComments] Waiting {network_delay:.1f}s before network retry...")
                    time.sleep(network_delay)
                else:
                    # Other errors - log full details but don't retry
                    logger.error(
                        f"[YouTubeComments] Navigation failed with unexpected error on attempt {attempt + 1}: "
                        f"{error_type}: {error_msg}"
                    )
                    if full_traceback:
                        logger.error(f"[YouTubeComments] Full traceback:\n{full_traceback}")
                    raise
        
        logger.error(f"[YouTubeComments] ✗ Navigation failed after {max_retries} attempts without returning")
        return (False, current_page)

    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        start_time = time.time()
        video_id = None
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        try:
            video_id = self._extract_video_id(url)
            logger.info(f"[YouTubeComments] Extracting comments for video: {video_id}")

            # Create browser context and page
            try:
                logger.debug(f"[YouTubeComments] Creating browser context (timeout={self.timeout}ms, headless={self.headless})")
                context = self._create_context()
                logger.debug(f"[YouTubeComments] Browser context created successfully")
                page = context.new_page()
                logger.debug(f"[YouTubeComments] New page created successfully")
            except Exception as e:
                logger.error(f"[YouTubeComments] Failed to create browser context/page: {e}")
                import traceback
                logger.error(f"[YouTubeComments] Traceback: {traceback.format_exc()}")
                raise

            self._report_progress('loading', 10, 'Loading YouTube video')
            
            # Navigate with retry logic (may return a new page if context was recreated)
            navigation_success, page = self._goto_with_retry(page, context, url)
            if not navigation_success:
                # Navigation failed after all retries
                try:
                    if not page.is_closed():
                        page.close()
                except:
                    pass
                try:
                    context.close()
                except:
                    pass
                error_msg = f"Failed to load YouTube page after {self.max_retries} attempts. The page may be slow or unreachable."
                logger.error(f"[YouTubeComments] {error_msg}")
                return self._error_result(url, error_msg, batch_id, link_id, video_id=video_id)
            
            time.sleep(2.0)
            self._report_progress('loading', 30, 'Video loaded')

            self._report_progress('extracting', 40, 'Extracting metadata')
            metadata = self._extract_metadata(page)

            # Scroll to comments and load more (3 cycles)
            self._report_progress('extracting', 55, 'Loading comments section')
            try:
                page.wait_for_selector('#comments', timeout=10000)
            except Exception:
                logger.debug('Comments container not found within 10s; continuing to try scrolling')
            self._scroll_comments_three_cycles(page)

            # Extract top-level comment texts
            self._report_progress('extracting', 75, 'Extracting comments')
            comments_selector = 'ytd-comment-thread-renderer #content-text'
            comments_texts: List[str] = []
            try:
                elements = page.locator(comments_selector)
                count = elements.count()
                logger.debug(f"Found {count} comment text elements before filtering")
                for idx in range(count):
                    try:
                        text = elements.nth(idx).inner_text().strip()
                        if text:
                            comments_texts.append(text)
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Error collecting comment texts: {e}")

            filtered_comments = self._clean_and_filter_comments(comments_texts)

            # Clean up (use page.context in case context was recreated)
            try:
                if not page.is_closed():
                    page.close()
            except:
                pass
            try:
                # Get context from page in case it was recreated
                page_context = page.context
                page_context.close()
            except:
                pass

            # Standardize to list[str] to match tests and loader expectations
            standardized_comments = filtered_comments
            total_words = sum(len(c.split()) for c in standardized_comments)
            self._report_progress('extracting', 100, f"Collected {len(standardized_comments)} comments")
            elapsed_time = round(time.time() - start_time, 2)
            logger.info(f"[YouTubeComments] Extracted {len(standardized_comments)} comments ({total_words} words) in {elapsed_time}s")

            if not standardized_comments:
                return {
                    'success': False,
                    'video_id': video_id,
                    'url': url,
                    'comments': [],
                    'num_comments': 0,
                    'title': metadata['title'],
                    'author': metadata['author'],
                    'publish_date': metadata['publish_date'],
                    'source': 'YouTube',
                    'word_count': 0,
                    'extraction_method': 'youtube_comments',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': 'No comments found above threshold'
                }

            return {
                'success': True,
                'video_id': video_id,
                'url': url,
                'comments': standardized_comments,
                'num_comments': len(standardized_comments),
                'title': metadata['title'],
                'author': metadata['author'],
                'publish_date': metadata['publish_date'],
                'source': 'YouTube',
                'word_count': total_words,
                'extraction_method': 'youtube_comments',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': None
            }
        except Exception as e:
            logger.error(f"[YouTubeComments] Extraction failed: {e}")
            if video_id is None:
                try:
                    video_id = self._extract_video_id(url)
                except Exception:
                    video_id = 'unknown'
            return {
                'success': False,
                'video_id': video_id,
                'url': url,
                'comments': [],
                'num_comments': 0,
                'title': '',
                'author': '',
                'publish_date': '',
                'source': 'YouTube',
                'word_count': 0,
                'extraction_method': 'youtube_comments',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': str(e)
            }


