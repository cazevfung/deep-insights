"""YouTube transcript scraper."""
import re
import time
from datetime import datetime
from typing import Dict, Tuple
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from scrapers.base_scraper import BaseScraper


class YouTubeScraper(BaseScraper):
    """Extract transcripts from YouTube videos."""
    
    def __init__(self, **kwargs):
        """Initialize YouTube scraper."""
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
            f"[YouTube] Timeout configuration: base={base_timeout}ms, config={config_timeout}ms, "
            f"final={self.timeout}ms"
        )
        # Retry configuration
        self.max_retries = 3
        self.retry_delay_base = 2.0  # Base delay in seconds
        logger.debug(f"[YouTube] Retry configuration: max_retries={self.max_retries}, delay_base={self.retry_delay_base}s")
    
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is a valid YouTube URL.
        
        Args:
            url: URL to validate
        
        Returns:
            True if valid YouTube URL
        """
        return 'youtube.com' in url or 'youtu.be' in url
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube URL
        
        Returns:
            Video ID
        """
        match = self.video_id_pattern.search(url)
        if match:
            return match.group(1)
        
        # Fallback: try to extract from query string
        if 'watch?v=' in url:
            parts = url.split('watch?v=')
            if len(parts) > 1:
                video_id = parts[1].split('&')[0]
                return video_id
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def _extract_metadata(self, page: Page) -> Dict:
        """
        Extract metadata from YouTube page.
        
        Args:
            page: Playwright page object
        
        Returns:
            Dictionary with metadata
        """
        metadata = {
            'title': 'Unknown',
            'author': 'Unknown',
            'publish_date': '',
            'source': 'YouTube'
        }
        
        try:
            # Extract title
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
                except:
                    continue
            
            # Extract channel name (author)
            try:
                channel = page.locator('ytd-channel-name a').first
                if channel.count() > 0:
                    metadata['author'] = channel.inner_text(timeout=2000).strip()
            except:
                pass
            
            # Extract publish date
            try:
                date_element = page.locator('ytd-video-primary-info-renderer span').first
                if date_element.count() > 0:
                    date_text = date_element.inner_text(timeout=2000).strip()
                    if date_text:
                        metadata['publish_date'] = date_text
            except:
                pass
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        
        return metadata
    
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
        logger.info(f"[YouTube] Starting navigation to {url} with timeout={self.timeout}ms, max_retries={max_retries}")
        logger.debug(f"[YouTube] Page state: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
        
        def _recreate_context_and_page():
            """Recreate browser context and page when connection is lost."""
            nonlocal current_page, current_context
            logger.warning(f"[YouTube] Recreating browser context and page due to connection error")
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
                logger.debug(f"[YouTube] New browser context created successfully")
                current_page = current_context.new_page()
                logger.debug(f"[YouTube] New page created successfully")
                return True
            except Exception as e:
                logger.error(f"[YouTube] Failed to recreate context/page: {e}")
                import traceback
                logger.error(f"[YouTube] Traceback: {traceback.format_exc()}")
                return False
        
        for attempt in range(max_retries):
            attempt_start_time = time.time()
            try:
                if attempt > 0:
                    delay = self.retry_delay_base * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[YouTube] Retrying page navigation (attempt {attempt + 1}/{max_retries}) after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                logger.info(f"[YouTube] Navigating to {url} (attempt {attempt + 1}/{max_retries}, timeout={self.timeout}ms)")
                
                # Check page state before navigation
                if current_page.is_closed():
                    logger.warning(f"[YouTube] Page is closed before navigation attempt {attempt + 1}, recreating...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                
                # Check if context is still valid by trying to access it
                try:
                    _ = current_context.pages  # This will raise if context is invalid
                except Exception as context_check_error:
                    logger.warning(f"[YouTube] Context appears invalid: {context_check_error}, recreating...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                
                # Perform navigation
                current_page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                
                elapsed = round((time.time() - attempt_start_time) * 1000, 0)
                logger.info(f"[YouTube] ✓ Successfully navigated to {url} in {elapsed}ms (attempt {attempt + 1})")
                logger.debug(f"[YouTube] Final page URL: {current_page.url}")
                return (True, current_page)
                
            except PlaywrightTimeout as e:
                elapsed = round((time.time() - attempt_start_time) * 1000, 0)
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(
                    f"[YouTube] Page.goto TIMEOUT on attempt {attempt + 1}/{max_retries} "
                    f"(after {elapsed}ms, timeout={self.timeout}ms): {error_type}: {error_msg}"
                )
                logger.debug(f"[YouTube] Page state after timeout: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
                
                if attempt == max_retries - 1:
                    logger.error(
                        f"[YouTube] ✗ All {max_retries} navigation attempts FAILED with timeout. "
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
                        f"[YouTube] Network error on attempt {attempt + 1}/{max_retries} "
                        f"(after {elapsed}ms): {error_type}: {error_msg}"
                    )
                    if full_traceback:
                        logger.debug(f"[YouTube] Full traceback:\n{full_traceback}")
                    logger.debug(f"[YouTube] Page state after network error: closed={current_page.is_closed()}, url={current_page.url if not current_page.is_closed() else 'N/A'}")
                    
                    # Recreate context and page for network errors (connection may be lost)
                    logger.warning(f"[YouTube] Network error detected, recreating browser context and page...")
                    if not _recreate_context_and_page():
                        if attempt == max_retries - 1:
                            return (False, current_page)
                        continue
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            f"[YouTube] ✗ All {max_retries} navigation attempts FAILED with network error. "
                            f"URL: {url}, Error: {error_msg}"
                        )
                        return (False, current_page)
                    # Wait longer for network errors
                    network_delay = self.retry_delay_base * (2 ** attempt)
                    logger.info(f"[YouTube] Waiting {network_delay:.1f}s before network retry...")
                    time.sleep(network_delay)
                else:
                    # Other errors - log full details but don't retry
                    logger.error(
                        f"[YouTube] Navigation failed with unexpected error on attempt {attempt + 1}: "
                        f"{error_type}: {error_msg}"
                    )
                    if full_traceback:
                        logger.error(f"[YouTube] Full traceback:\n{full_traceback}")
                    raise
        
        logger.error(f"[YouTube] ✗ Navigation failed after {max_retries} attempts without returning")
        return (False, current_page)
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract transcript from YouTube video.
        
        Args:
            url: YouTube video URL
        
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        video_id = None
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        try:
            # Extract video ID
            video_id = self._extract_video_id(url)
            logger.info(f"[YouTube] Extracting transcript for video: {video_id}")
            
            # Create browser context and page
            try:
                logger.debug(f"[YouTube] Creating browser context (timeout={self.timeout}ms, headless={self.headless})")
                context = self._create_context()
                logger.debug(f"[YouTube] Browser context created successfully")
                page = context.new_page()
                logger.debug(f"[YouTube] New page created successfully")
            except Exception as e:
                logger.error(f"[YouTube] Failed to create browser context/page: {e}")
                import traceback
                logger.error(f"[YouTube] Traceback: {traceback.format_exc()}")
                raise
            
            # Extract metadata first
            self._report_progress("loading", 10, "Loading YouTube video")
            
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
                logger.error(f"[YouTube] {error_msg}")
                return self._error_result(url, error_msg, batch_id, link_id, video_id=video_id)
            
            # Update context reference in case it was recreated
            # Use page.context to get the current context (may be new if recreated)
            context = page.context
            
            # Check for cancellation
            if self._check_cancelled():
                logger.info(f"[YouTube] Cancellation detected, force closing browser for {url}")
                try:
                    if not page.is_closed():
                        page.close()
                except:
                    pass
                try:
                    context.close()
                except:
                    pass
                self.close(force_kill=True)  # Force kill browser processes
                return self._error_result(url, "Cancelled by user", batch_id, link_id)
            
            time.sleep(2.0)  # Wait for dynamic content
            self._report_progress("loading", 30, "Video loaded")
            
            # Check for cancellation again
            if self._check_cancelled():
                logger.info(f"[YouTube] Cancellation detected, force closing browser for {url}")
                try:
                    if not page.is_closed():
                        page.close()
                except:
                    pass
                try:
                    context.close()
                except:
                    pass
                self.close(force_kill=True)  # Force kill browser processes
                return self._error_result(url, "Cancelled by user", batch_id, link_id)
            
            self._report_progress("extracting", 40, "Extracting metadata")
            metadata = self._extract_metadata(page)
            
            # Try to expand description if collapsed
            try:
                expand_button = page.locator('tp-yt-paper-button#expand').first
                if expand_button.is_visible(timeout=2000):
                    expand_button.click()
                    logger.debug("Expanded description")
            except:
                pass
            
            # Click "Show transcript" button
            self._report_progress("extracting", 50, "Opening transcript")
            transcript_button_selectors = [
                'button[aria-label="Show transcript"]',
                'ytd-video-description-transcript-section-renderer button',
                'button:has-text("Show transcript")',
                'button[aria-label*="transcript" i]'
            ]
            
            clicked = False
            for selector in transcript_button_selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=2000):
                        button.click()
                        clicked = True
                        logger.debug("Clicked transcript button")
                        # Wait a moment for UI to update
                        time.sleep(3)
                        # If transcript panel is stuck loading, try toggling to Timeline/Chapters then back
                        transcript_loaded = False
                        try:
                            page.wait_for_selector('ytd-transcript-segment-renderer', timeout=5000)
                            transcript_loaded = True
                        except Exception:
                            logger.debug("Transcript segments not visible after 5s, toggling Timeline/Chapters -> Transcript")
                            # Try toggling to either Timeline or Chapters, then back to Transcript
                            # These elements can be in different languages (English/Chinese/etc)
                            # Timeline: "时间轴" or "Timeline"
                            # Chapters: "章节" or "Chapters"
                            # Transcript: "转写文稿" or "Transcript"
                            tab_selectors = [
                                ('Chapters', [
                                    'button.ytChipShapeButtonReset[role="tab"][aria-label="Chapters"]',
                                    'button.ytChipShapeButtonReset[role="tab"][aria-label="章节"]',
                                    'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("Chapters"))',
                                    'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("章节"))'
                                ]),
                                ('Timeline', [
                                    'button.ytChipShapeButtonReset[role="tab"][aria-label="Timeline"]',
                                    'button.ytChipShapeButtonReset[role="tab"][aria-label="时间轴"]',
                                    'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("Timeline"))',
                                    'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("时间轴"))'
                                ])
                            ]
                            transcript_tab_selectors = [
                                'button.ytChipShapeButtonReset[role="tab"][aria-label="Transcript"]',
                                'button.ytChipShapeButtonReset[role="tab"][aria-label="转写文稿"]',
                                'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("Transcript"))',
                                'button.ytChipShapeButtonReset[role="tab"]:has(div:has-text("转写文稿"))'
                            ]
                            
                            toggled = False
                            logger.debug(f"Trying to find and click Chapters or Timeline tab...")
                            for tab_name, tab_selector_list in tab_selectors:
                                logger.debug(f"Searching for {tab_name} tab with {len(tab_selector_list)} selector variations")
                                for tab_sel in tab_selector_list:
                                    try:
                                        tab_element = page.locator(tab_sel).first
                                        count = tab_element.count()
                                        logger.debug(f"Found {count} elements for selector: {tab_sel}")
                                        if count > 0 and tab_element.is_visible(timeout=1000):
                                            logger.debug(f"Clicking on {tab_name} tab")
                                            tab_element.click()
                                            toggled = True
                                            break
                                    except Exception as e:
                                        logger.debug(f"Could not click {tab_name} with selector {tab_sel}: {e}")
                                        continue
                                if toggled:
                                    break
                            
                            if not toggled:
                                logger.debug("Could not find or click any Timeline/Chapters tab")
                            
                            # Wait 0.5s if we clicked on a tab
                            if toggled:
                                time.sleep(0.5)
                            
                            # Click back to Transcript tab
                            clicked_transcript = False
                            for tr_sel in transcript_tab_selectors:
                                try:
                                    tr_element = page.locator(tr_sel).first
                                    count = tr_element.count()
                                    logger.debug(f"Found {count} Transcript tab elements for selector: {tr_sel}")
                                    if count > 0 and tr_element.is_visible(timeout=1000):
                                        logger.debug("Clicking on Transcript tab")
                                        tr_element.click()
                                        clicked_transcript = True
                                        break
                                except Exception as e:
                                    logger.debug(f"Could not click Transcript tab with selector {tr_sel}: {e}")
                                    continue
                            
                            if not clicked_transcript:
                                logger.debug("Could not find or click Transcript tab")

                            # Give time for transcript to render after returning to Transcript (wait 5s)
                            time.sleep(5.0)
                            try:
                                page.wait_for_selector('ytd-transcript-segment-renderer', timeout=5000)
                                transcript_loaded = True
                            except Exception:
                                logger.debug("Transcript still not visible after toggling and waiting 5s")
                        
                        # If transcript still not loaded, refresh page and try again
                        if not transcript_loaded:
                            logger.info(f"[YouTube] Refreshing page and retrying transcript extraction (timeout={self.timeout}ms)")
                            # Use retry logic for reload as well
                            reload_start = time.time()
                            try:
                                page.reload(wait_until='domcontentloaded', timeout=self.timeout)
                                reload_elapsed = round((time.time() - reload_start) * 1000, 0)
                                logger.debug(f"[YouTube] Page reload completed in {reload_elapsed}ms")
                            except PlaywrightTimeout as e:
                                reload_elapsed = round((time.time() - reload_start) * 1000, 0)
                                logger.warning(
                                    f"[YouTube] Page reload TIMEOUT after {reload_elapsed}ms "
                                    f"(timeout={self.timeout}ms): {e}, continuing anyway"
                                )
                            except Exception as e:
                                reload_elapsed = round((time.time() - reload_start) * 1000, 0)
                                logger.warning(
                                    f"[YouTube] Page reload failed after {reload_elapsed}ms: {e}, continuing anyway"
                                )
                            time.sleep(2.0)
                            # Re-extract metadata after refresh
                            metadata = self._extract_metadata(page)
                            # Try to expand description again
                            try:
                                expand_button = page.locator('tp-yt-paper-button#expand').first
                                if expand_button.is_visible(timeout=2000):
                                    expand_button.click()
                                    logger.debug("Expanded description on retry")
                            except:
                                pass
                            # Click transcript button again
                            for selector in transcript_button_selectors:
                                try:
                                    button = page.locator(selector).first
                                    if button.is_visible(timeout=2000):
                                        button.click()
                                        logger.debug("Clicked transcript button on retry")
                                        time.sleep(8)  # Wait longer after retry
                                        break
                                except:
                                    continue
                        break
                except:
                    continue
            
            if not clicked:
                try:
                    if not page.is_closed():
                        page.close()
                except:
                    pass
                try:
                    page.context.close()
                except:
                    pass
                return {
                    'success': False,
                    'video_id': video_id,
                    'url': url,
                    'content': None,
                    'title': metadata['title'],
                    'author': metadata['author'],
                    'publish_date': metadata['publish_date'],
                    'source': 'YouTube',
                    'language': '',
                    'word_count': 0,
                    'extraction_method': 'youtube',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': 'Transcript button not found'
                }
            
            # Extract transcript segments
            self._report_progress("extracting", 70, "Extracting transcript segments")
            transcript_texts = []
            try:
                # Wait for transcript to fully load
                page.wait_for_selector('ytd-transcript-segment-renderer', timeout=10000)
                time.sleep(0.5)  # Small additional wait to ensure segments are fully rendered
                segments = page.locator('ytd-transcript-segment-renderer').all()
                logger.debug(f"Found {len(segments)} transcript segments")
                self._report_progress("extracting", 85, f"Processing {len(segments)} segments")
                
                for segment in segments:
                    # Check for cancellation during segment processing
                    if self._check_cancelled():
                        logger.info(f"[YouTube] Cancellation detected during segment processing for {url}")
                        try:
                            if not page.is_closed():
                                page.close()
                        except:
                            pass
                        try:
                            page.context.close()
                        except:
                            pass
                        self.close(force_kill=True)  # Force kill browser processes
                        return self._error_result(url, "Cancelled by user", batch_id, link_id)
                    
                    try:
                        text_element = segment.locator('yt-formatted-string.segment-text').first
                        text = text_element.inner_text().strip()
                        # Filter out audio markers
                        if text and text not in ['[Music]', '[Applause]', '[Laughter]', '[laughs]']:
                            transcript_texts.append(text)
                    except:
                        continue
            
            except Exception as e:
                logger.debug(f"Error extracting segments: {e}")
            
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
            
            if not transcript_texts:
                return {
                    'success': False,
                    'video_id': video_id,
                    'url': url,
                    'content': None,
                    'title': metadata['title'],
                    'author': metadata['author'],
                    'publish_date': metadata['publish_date'],
                    'source': 'YouTube',
                    'language': '',
                    'word_count': 0,
                    'extraction_method': 'youtube',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': 'No transcript found'
                }
            
            # Join transcript (no timestamps)
            content = ' '.join(transcript_texts)
            content = self._clean_content(content)
            word_count = len(content.split())
            
            self._report_progress("extracting", 100, f"Extracted {word_count} words")
            elapsed_time = round(time.time() - start_time, 2)
            logger.info(f"[YouTube] Extracted {word_count} words in {elapsed_time}s")
            
            return {
                'success': True,
                'video_id': video_id,
                'url': url,
                'content': content,
                'title': metadata['title'],
                'author': metadata['author'],
                'publish_date': metadata['publish_date'],
                'source': 'YouTube',
                'language': 'auto',  # Will be detected from content
                'word_count': word_count,
                'extraction_method': 'youtube',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"[YouTube] Extraction failed: {e}")
            error_message = str(e)
            if "ERR_CONNECTION_TIMED_OUT" in error_message:
                hint = (
                    "Unable to reach YouTube. Check your network connectivity or configure a proxy "
                    "under browser.proxy in config.yaml."
                )
                logger.error(f"[YouTube] Network hint: {hint}")
                error_message = f"{error_message} ({hint})"
            # Try to extract video_id for error result if not already extracted
            if video_id is None:
                try:
                    video_id = self._extract_video_id(url)
                except:
                    video_id = 'unknown'
            
            return {
                'success': False,
                'video_id': video_id,
                'url': url,
                'content': None,
                'title': '',
                'author': '',
                'publish_date': '',
                'source': 'YouTube',
                'language': '',
                'word_count': 0,
                'extraction_method': 'youtube',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': error_message
            }

