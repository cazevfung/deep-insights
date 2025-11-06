"""YouTube comments scraper using Playwright."""
import re
import time
from datetime import datetime
from typing import Dict, List
from loguru import logger
from playwright.sync_api import Page
from scrapers.base_scraper import BaseScraper


class YouTubeCommentsScraper(BaseScraper):
    """Extract top-level comments from YouTube videos."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.video_id_pattern = re.compile(
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        )

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

    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        start_time = time.time()
        video_id = None
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        try:
            video_id = self._extract_video_id(url)
            logger.info(f"[YouTubeComments] Extracting comments for video: {video_id}")

            context = self._create_context()
            page = context.new_page()

            self._report_progress('loading', 10, 'Loading YouTube video')
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
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

            page.close()
            context.close()

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


