"""YouTube transcript scraper."""
import re
import time
from datetime import datetime
from typing import Dict
from loguru import logger
from playwright.sync_api import Page
from scrapers.base_scraper import BaseScraper


class YouTubeScraper(BaseScraper):
    """Extract transcripts from YouTube videos."""
    
    def __init__(self, **kwargs):
        """Initialize YouTube scraper."""
        super().__init__(**kwargs)
        self.video_id_pattern = re.compile(
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        )
    
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
                context = self._create_context()
                page = context.new_page()
            except Exception as e:
                logger.error(f"[YouTube] Failed to create browser context: {e}")
                import traceback
                logger.error(f"[YouTube] Traceback: {traceback.format_exc()}")
                raise
            
            # Extract metadata first
            self._report_progress("loading", 10, "Loading YouTube video")
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            # Check for cancellation
            if self._check_cancelled():
                logger.info(f"[YouTube] Cancellation detected, force closing browser for {url}")
                try:
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
                            logger.debug("Refreshing page and retrying transcript extraction")
                            page.reload(wait_until='domcontentloaded', timeout=self.timeout)
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
                page.close()
                context.close()
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
                            page.close()
                        except:
                            pass
                        try:
                            context.close()
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
            
            # Clean up
            page.close()
            context.close()
            
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
                'error': str(e)
            }

