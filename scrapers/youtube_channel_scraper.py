"""YouTube channel video link scraper."""
import re
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from scrapers.base_scraper import BaseScraper
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


class YouTubeChannelScraper(BaseScraper):
    """Extract video links from YouTube channel videos page."""
    
    def __init__(self, **kwargs):
        """Initialize YouTube channel scraper."""
        super().__init__(**kwargs)
        self.video_id_pattern = re.compile(
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        )
        
        # Get channel scraper config
        channel_config = self.config.get('channel_scraper', {})
        self.scroll_delay_min = channel_config.get('scroll_delay_min', 1.0)
        self.scroll_delay_max = channel_config.get('scroll_delay_max', 2.0)
        self.max_scrolls = channel_config.get('max_scrolls', 50)
        self.videos_per_channel_limit = channel_config.get('videos_per_channel_limit', 1000)
        self.request_timeout = channel_config.get('request_timeout', 60000)
        self.min_video_duration_seconds = channel_config.get('min_video_duration_seconds', 300)
        
        logger.debug(
            f"[YouTubeChannel] Config: scroll_delay={self.scroll_delay_min}-{self.scroll_delay_max}s, "
            f"max_scrolls={self.max_scrolls}, limit={self.videos_per_channel_limit}"
        )
    
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is a valid YouTube channel URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid YouTube channel URL
        """
        return 'youtube.com/channel/' in url or 'youtube.com/@' in url or 'youtube.com/c/' in url
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract video links from a YouTube channel URL.
        
        This method is required by BaseScraper but channel scraping
        uses scrape_channel_videos() instead.
        
        Args:
            url: YouTube channel URL
            batch_id: Optional batch ID
            link_id: Optional link ID
            
        Returns:
            Dictionary with extraction results
        """
        # Extract channel ID from URL
        channel_id = None
        if '/channel/' in url:
            channel_id = url.split('/channel/')[-1].split('/')[0].split('?')[0]
        elif '/@' in url:
            # Handle handle-based URLs - would need to resolve to channel ID
            logger.warning(f"[YouTubeChannel] Handle-based URLs not directly supported, use channel ID")
            return self._error_result(url, "Handle-based URLs not supported, use channel ID", batch_id, link_id)
        elif '/c/' in url:
            # Handle custom URLs - would need to resolve to channel ID
            logger.warning(f"[YouTubeChannel] Custom URLs not directly supported, use channel ID")
            return self._error_result(url, "Custom URLs not supported, use channel ID", batch_id, link_id)
        
        if not channel_id:
            return self._error_result(url, "Could not extract channel ID from URL", batch_id, link_id)
        
        # Scrape videos (no date filtering for extract method)
        video_urls = self.scrape_channel_videos(channel_id=channel_id)
        
        return {
            'success': True,
            'url': url,
            'channel_id': channel_id,
            'video_count': len(video_urls),
            'video_urls': video_urls,
            'content': '\n'.join(video_urls),  # For compatibility
            'word_count': len(video_urls),  # Count of videos
            'title': f"YouTube Channel: {channel_id}",
            'source': 'youtube_channel'
        }
    
    def scrape_channel_videos(
        self,
        channel_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[str]:
        """
        Scrape video links from a YouTube channel.
        
        Args:
            channel_id: YouTube channel ID
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            List of video URLs
        """
        url = f"https://www.youtube.com/channel/{channel_id}/videos"
        logger.info(f"[YouTubeChannel] Scraping channel: {channel_id}")
        
        try:
            # Create browser context and page
            context = self._create_context()
            page = context.new_page()
            
            # Navigate to channel videos page
            logger.debug(f"[YouTubeChannel] Navigating to {url}")
            page.goto(url, wait_until='networkidle', timeout=self.request_timeout)
            time.sleep(2)  # Wait for initial load
            
            # Scroll and load videos
            videos = self._scroll_and_load_videos(page, start_date, end_date)
            
            # Extract video links
            video_urls = []
            for video in videos:
                video_url = video.get('url')
                if video_url:
                    duration_seconds = video.get('duration_seconds')
                    if self.min_video_duration_seconds:
                        if duration_seconds is None:
                            logger.debug(f"[YouTubeChannel] Skipping {video_url} - missing duration")
                            continue
                        if duration_seconds <= self.min_video_duration_seconds:
                            logger.debug(
                                f"[YouTubeChannel] Skipping {video_url} - duration {duration_seconds}s "
                                f"<= min {self.min_video_duration_seconds}s"
                            )
                            continue
                    
                    # Filter by date if dates provided
                    if start_date or end_date:
                        publish_date = video.get('publish_date')
                        if publish_date:
                            if self._is_date_in_range(publish_date, start_date, end_date):
                                video_urls.append(video_url)
                        else:
                            # If no date, include it (conservative approach)
                            logger.warning(f"[YouTubeChannel] No publish date for video {video_url}, including anyway")
                            video_urls.append(video_url)
                    else:
                        # No date filtering, include all
                        video_urls.append(video_url)
            
            logger.info(f"[YouTubeChannel] Found {len(video_urls)} videos for channel {channel_id}")
            return video_urls
            
        except Exception as e:
            logger.error(f"[YouTubeChannel] Error scraping channel {channel_id}: {e}", exc_info=True)
            return []
        finally:
            try:
                if 'page' in locals():
                    page.close()
                if 'context' in locals():
                    context.close()
            except Exception:
                pass
            self.close()
    
    def _scroll_and_load_videos(
        self,
        page: Page,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Scroll down to load all videos and extract video metadata.
        
        Args:
            page: Playwright page object
            start_date: Optional start date for early stopping
            end_date: Optional end date for early stopping
            
        Returns:
            List of video dictionaries with url and publish_date
        """
        videos = []
        last_video_count = 0
        no_new_videos_count = 0
        scroll_count = 0
        
        while scroll_count < self.max_scrolls:
            # Extract current videos
            current_videos = self._extract_video_links(page)
            
            # Check if we got new videos
            if len(current_videos) == last_video_count:
                no_new_videos_count += 1
                if no_new_videos_count >= 3:
                    logger.debug(f"[YouTubeChannel] No new videos after {no_new_videos_count} scrolls, stopping")
                    break
            else:
                no_new_videos_count = 0
                last_video_count = len(current_videos)
            
            # Update videos list (deduplicate by URL)
            existing_urls = {v.get('url') for v in videos}
            for video in current_videos:
                if video.get('url') and video.get('url') not in existing_urls:
                    videos.append(video)
            
            # Check if we've hit the limit
            if len(videos) >= self.videos_per_channel_limit:
                logger.warning(f"[YouTubeChannel] Hit video limit ({self.videos_per_channel_limit}), stopping")
                break
            
            # Check if we've gone past the date range (if filtering by date)
            if start_date:
                # If we have dates, check if we've scrolled past the start date
                # This is a heuristic - if all recent videos are before start_date, we can stop
                recent_videos_with_dates = [v for v in videos[-10:] if v.get('publish_date')]
                if recent_videos_with_dates:
                    oldest_recent = min(
                        (v['publish_date'] for v in recent_videos_with_dates),
                        default=None
                    )
                    if oldest_recent and oldest_recent < start_date:
                        logger.debug(f"[YouTubeChannel] Scrolled past start_date, stopping")
                        break
            
            # Scroll down
            page.evaluate("window.scrollBy(0, 500)")
            scroll_count += 1
            
            # Random delay between scrolls
            delay = random.uniform(self.scroll_delay_min, self.scroll_delay_max)
            time.sleep(delay)
        
        logger.info(f"[YouTubeChannel] Scrolled {scroll_count} times, found {len(videos)} unique videos")
        return videos
    
    def _extract_video_links(self, page: Page) -> List[Dict]:
        """
        Extract video links from the current page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of video dictionaries with url and optional publish_date
        """
        videos = []
        
        try:
            # Try multiple selectors for video links
            selectors = [
                'a#video-title-link',
                'ytd-grid-video-renderer a#video-title',
                'a[href*="/watch?v="]'
            ]
            
            for selector in selectors:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        for element in elements:
                            try:
                                href = element.get_attribute('href')
                                if href and '/watch?v=' in href:
                                    # Convert to absolute URL
                                    if href.startswith('/'):
                                        video_url = f"https://www.youtube.com{href}"
                                    elif href.startswith('http'):
                                        video_url = href
                                    else:
                                        continue
                                    
                                    # Extract video ID
                                    video_id_match = self.video_id_pattern.search(video_url)
                                    if not video_id_match:
                                        continue
                                    
                                    # Extract publish date & video container for downstream metadata
                                    publish_date = None
                                    video_container = None
                                    try:
                                        parent_selectors = [
                                            'xpath=ancestor::ytd-rich-item-renderer',
                                            'xpath=ancestor::ytd-grid-video-renderer',
                                        ]
                                        
                                        for parent_selector in parent_selectors:
                                            try:
                                                parent_element = element.locator(parent_selector).first
                                                
                                                if parent_element.count() > 0:
                                                    video_container = parent_element
                                                    date_selectors = [
                                                        'ytd-video-meta-block span.inline-metadata-item',
                                                        'ytd-video-meta-block div div span.inline-metadata-item',
                                                        '#metadata-line span.inline-metadata-item',
                                                        'span.inline-metadata-item',
                                                    ]
                                                    
                                                    for selector in date_selectors:
                                                        try:
                                                            date_spans = parent_element.locator(selector).all()
                                                            
                                                            for span in date_spans:
                                                                try:
                                                                    date_text = span.inner_text(timeout=500).strip()
                                                                    if date_text and re.search(
                                                                        r'(ago|前|day|week|month|year|hour|minute|second|天|周|月|年|小时|分钟|秒)',
                                                                        date_text,
                                                                        re.IGNORECASE
                                                                    ):
                                                                        publish_date = self._parse_relative_date(date_text)
                                                                        if publish_date:
                                                                            logger.debug(f"[YouTubeChannel] ✓ Found date: '{date_text}' -> {publish_date.date()}")
                                                                            break
                                                                except Exception as e:
                                                                    logger.debug(f"[YouTubeChannel] Error reading span text: {e}")
                                                                    continue
                                                            
                                                            if publish_date:
                                                                break
                                                        except Exception as e:
                                                            logger.debug(f"[YouTubeChannel] Selector '{selector}' failed: {e}")
                                                            continue
                                                    
                                                    if publish_date:
                                                        break
                                            except Exception:
                                                continue
                                        
                                        if not publish_date:
                                            try:
                                                element_handle = element.element_handle()
                                                date_text = page.evaluate("""
                                                    (linkElement) => {
                                                        try {
                                                            // Try both parent types
                                                            let videoRenderer = linkElement.closest('ytd-rich-item-renderer');
                                                            if (!videoRenderer) {
                                                                videoRenderer = linkElement.closest('ytd-grid-video-renderer');
                                                            }
                                                            if (!videoRenderer) return null;
                                                            
                                                            // Find ytd-video-meta-block
                                                            const metaBlock = videoRenderer.querySelector('ytd-video-meta-block');
                                                            if (!metaBlock) return null;
                                                            
                                                            // Find all inline-metadata-item spans
                                                            const items = metaBlock.querySelectorAll('span.inline-metadata-item');
                                                            for (let item of items) {
                                                                const text = (item.innerText || item.textContent || '').trim();
                                                                // Check if it looks like a date
                                                                if (text && (text.includes('ago') || text.includes('前') || 
                                                                    /\\d+\\s*(day|week|month|year|hour|minute|second|天|周|月|年|小时|分钟|秒)/i.test(text))) {
                                                                    return text;
                                                                }
                                                            }
                                                            
                                                            return null;
                                                        } catch (e) {
                                                            return null;
                                                        }
                                                    }
                                                """, element_handle)
                                                
                                                if date_text:
                                                    publish_date = self._parse_relative_date(date_text)
                                                    if publish_date:
                                                        logger.debug(f"[YouTubeChannel] ✓ Found date via JS: '{date_text}' -> {publish_date.date()}")
                                            except Exception as e:
                                                logger.debug(f"[YouTubeChannel] JS evaluation failed: {e}")
                                    except Exception as e:
                                        logger.debug(f"[YouTubeChannel] Error extracting date: {e}")
                                        pass
                                    
                                    duration_seconds = self._extract_video_duration_seconds(video_container or element)
                                    
                                    videos.append({
                                        'url': video_url,
                                        'video_id': video_id_match.group(1),
                                        'publish_date': publish_date,
                                        'duration_seconds': duration_seconds
                                    })
                            except Exception as e:
                                logger.debug(f"[YouTubeChannel] Error extracting video link: {e}")
                                continue
                        
                        if videos:
                            break  # Found videos with this selector
                except Exception as e:
                    logger.debug(f"[YouTubeChannel] Selector {selector} failed: {e}")
                    continue
            
        except Exception as e:
            logger.warning(f"[YouTubeChannel] Error extracting video links: {e}")
        
        return videos
    
    def _extract_video_duration_seconds(self, container) -> Optional[int]:
        """
        Extract video duration (in seconds) from the video container.
        """
        if not container:
            return None
        
        selectors = [
            '.yt-badge-shape__text',
            'yt-thumbnail-overlay-time-status-renderer span',
            'ytd-thumbnail-overlay-time-status-renderer span',
            '#time-status span',
        ]
        
        for selector in selectors:
            try:
                elements = container.locator(selector).all()
                if not elements:
                    continue
                for element in elements:
                    try:
                        text = (element.inner_text(timeout=500) or '').strip()
                        seconds = self._parse_duration_to_seconds(text)
                        if seconds is not None:
                            return seconds
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Fallback to JS evaluation for newer layouts
        try:
            duration_text = container.evaluate("""
                (node) => {
                    try {
                        const renderer = node.closest('ytd-rich-item-renderer') || 
                                         node.closest('ytd-grid-video-renderer') || node;
                        if (!renderer) return null;
                        const badges = renderer.querySelectorAll('.yt-badge-shape__text, yt-thumbnail-overlay-time-status-renderer span');
                        for (const badge of badges) {
                            const text = (badge.innerText || badge.textContent || '').trim();
                            if (text && /^\\d{1,2}:\\d{2}(?::\\d{2})?$/.test(text.replace(/\\s+/g, ''))) {
                                return text;
                            }
                        }
                        return null;
                    } catch (e) {
                        return null;
                    }
                }
            """)
            return self._parse_duration_to_seconds(duration_text)
        except Exception:
            return None
    
    def _parse_duration_to_seconds(self, text: Optional[str]) -> Optional[int]:
        """Convert duration text like '7:11' or '1:02:03' to seconds."""
        if not text:
            return None
        normalized = text.replace('\u2009', '').replace(' ', '').strip()
        if not re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', normalized):
            return None
        
        parts = normalized.split(':')
        seconds = 0
        for part in parts:
            try:
                seconds = seconds * 60 + int(part)
            except ValueError:
                return None
        return seconds
    
    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """
        Parse relative date strings in both English and Chinese to absolute dates.
        
        Supports:
        - English: "2 days ago", "3 weeks ago", "5 minutes ago"
        - Chinese: "2天前", "3周前", "5分钟前", "1小时前", "1个月前", "1年前"
        
        Args:
            text: Date string (may be relative or absolute)
            
        Returns:
            Datetime object or None if parsing fails
        """
        if not text:
            return None
        
        text = text.strip()
        now = datetime.now()
        
        # English patterns
        english_patterns = [
            (r'(\d+)\s*(?:second|sec)s?\s*ago', lambda m: now - timedelta(seconds=int(m.group(1)))),
            (r'(\d+)\s*(?:minute|min)s?\s*ago', lambda m: now - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*(?:hour|hr)s?\s*ago', lambda m: now - timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*(?:day|d)s?\s*ago', lambda m: now - timedelta(days=int(m.group(1)))),
            (r'(\d+)\s*(?:week|wk)s?\s*ago', lambda m: now - timedelta(weeks=int(m.group(1)))),
            (r'(\d+)\s*(?:month|mo)s?\s*ago', lambda m: now - relativedelta(months=int(m.group(1)))),
            (r'(\d+)\s*(?:year|yr)s?\s*ago', lambda m: now - relativedelta(years=int(m.group(1)))),
        ]
        
        # Chinese patterns
        chinese_patterns = [
            (r'(\d+)\s*秒前', lambda m: now - timedelta(seconds=int(m.group(1)))),  # seconds ago
            (r'(\d+)\s*分钟前', lambda m: now - timedelta(minutes=int(m.group(1)))),  # minutes ago
            (r'(\d+)\s*小时前', lambda m: now - timedelta(hours=int(m.group(1)))),  # hours ago
            (r'(\d+)\s*天前', lambda m: now - timedelta(days=int(m.group(1)))),  # days ago
            (r'(\d+)\s*周前', lambda m: now - timedelta(weeks=int(m.group(1)))),  # weeks ago
            (r'(\d+)\s*个月前', lambda m: now - relativedelta(months=int(m.group(1)))),  # months ago
            (r'(\d+)\s*年前', lambda m: now - relativedelta(years=int(m.group(1)))),  # years ago
        ]
        
        # Try English patterns (case-insensitive)
        for pattern, func in english_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result = func(match)
                    logger.debug(f"[YouTubeChannel] Parsed English date '{text}' -> {result.date()}")
                    return result
                except Exception as e:
                    logger.debug(f"[YouTubeChannel] Error parsing English date '{text}': {e}")
                    continue
        
        # Try Chinese patterns
        for pattern, func in chinese_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    result = func(match)
                    logger.debug(f"[YouTubeChannel] Parsed Chinese date '{text}' -> {result.date()}")
                    return result
                except Exception as e:
                    logger.debug(f"[YouTubeChannel] Error parsing Chinese date '{text}': {e}")
                    continue
        
        # Try to parse as absolute date
        try:
            result = date_parser.parse(text, fuzzy=True)
            logger.debug(f"[YouTubeChannel] Parsed absolute date '{text}' -> {result.date()}")
            return result
        except Exception:
            pass
        
        logger.debug(f"[YouTubeChannel] Could not parse date: '{text}'")
        return None
    
    def _is_date_in_range(
        self,
        date: datetime,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> bool:
        """
        Check if date is within the specified range (inclusive).
        Compares only calendar days so any time on the same date counts.
        
        Args:
            date: Date to check
            start_date: Optional start date (inclusive)
            end_date: Optional end date (inclusive)
            
        Returns:
            True if date is in range
        """
        date_only = date.date()
        if start_date and date_only < start_date.date():
            return False
        if end_date and date_only > end_date.date():
            return False
        return True

