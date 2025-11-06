"""Article content scraper with Playwright and trafilatura."""
import time
import uuid
from datetime import datetime
from typing import Dict
from loguru import logger
from playwright.sync_api import Page
import trafilatura
from scrapers.base_scraper import BaseScraper


class ArticleScraper(BaseScraper):
    """Extract text content from articles and web pages."""
    
    def __init__(self, **kwargs):
        """Initialize article scraper."""
        super().__init__(**kwargs)
        self.method_preference = self.scraper_config.get('method_preference', 'playwright')
        self.min_content_words = self.scraper_config.get('min_content_words', 50)
        self.remove_blocking = self.scraper_config.get('remove_blocking_elements', True)
    
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is valid (accepts any http/https URL except Reddit).
        
        Args:
            url: URL to validate
        
        Returns:
            True if valid URL
        """
        return url.startswith(('http://', 'https://')) and 'reddit.com' not in url
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract content from article.
        Tries Playwright first, falls back to trafilatura.
        
        Args:
            url: Article URL
        
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        result = None
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        # Try Playwright first if preference is playwright
        if self.method_preference == 'playwright':
            result = self._extract_with_playwright(url)
            
            # If Playwright fails and we got content but it's too short, try trafilatura
            if not result['success'] or (result.get('content') and len(result.get('content', '').split()) < self.min_content_words):
                logger.info("[Article] Falling back to trafilatura...")
                result = self._extract_with_trafilatura(url)
        
        # Try trafilatura if preference is trafilatura or as fallback
        if self.method_preference == 'trafilatura' or result is None:
            result = self._extract_with_trafilatura(url)
        
        # Ensure all required fields are present
        if 'extraction_timestamp' not in result:
            result['extraction_timestamp'] = datetime.now().isoformat()
        
        # Assign a random identifier to this article extraction if not present
        try:
            if 'article_id' not in result or not result.get('article_id'):
                result['article_id'] = uuid.uuid4().hex[:12]
        except Exception:
            # Best-effort; do not fail extraction due to ID assignment
            result['article_id'] = uuid.uuid4().hex[:12]

        elapsed_time = round(time.time() - start_time, 2)
        logger.info(f"[Article] Extraction completed in {elapsed_time}s - Success: {result['success']}")
        
        return result
    
    def _extract_with_playwright(self, url: str) -> Dict:
        """
        Extract content using Playwright.
        
        Args:
            url: Article URL
        
        Returns:
            Dictionary with extraction results
        """
        try:
            context = self._create_context()
            page = context.new_page()
            
            # Navigate
            self._report_progress("loading", 10, "Loading article")
            page.goto(url, wait_until='networkidle', timeout=self.timeout)
            
            # Check for cancellation
            if self._check_cancelled():
                logger.info(f"[Article] Cancellation detected, force closing browser for {url}")
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
            
            time.sleep(2.0)
            self._report_progress("loading", 30, "Article loaded")
            
            # Check for cancellation again
            if self._check_cancelled():
                logger.info(f"[Article] Cancellation detected, force closing browser for {url}")
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
            
            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            self._report_progress("loading", 40, "Loading additional content")
            
            # Click expand buttons
            self._click_expand_buttons(page)
            self._report_progress("extracting", 50, "Expanding content")
            
            # Scroll again
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            
            # Remove blocking elements if enabled
            if self.remove_blocking:
                self._remove_blocking_elements(page)
            
            # Extract metadata
            self._report_progress("extracting", 60, "Extracting metadata")
            metadata = self._extract_metadata(page, url)
            
            # Extract content using multiple selectors
            self._report_progress("extracting", 70, "Extracting article content")
            content_selectors = [
                'article',
                'main',
                '[role="article"]',
                '.article-content',
                '.content-wrapper',
                '.post-content',
                '.entry-content',
                '#content',
                '.article-body',
                '.news-content',
                '.article-text',
                'div[class*="content"]',
                'div[class*="article"]',
            ]
            
            content = None
            for selector in content_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        content = element.inner_text(timeout=2000)
                        if content and len(content.split()) > self.min_content_words:
                            logger.debug(f"[Article] Found content with selector: {selector}")
                            break
                except:
                    continue
            
            # Fallback to body if no specific content found
            if not content or len(content.split()) < self.min_content_words:
                try:
                    page.evaluate("""
                        document.querySelectorAll('nav, header, footer, aside, .ad, .advertisement, .comment').forEach(el => el.remove());
                    """)
                    body = page.locator('body')
                    content = body.inner_text(timeout=2000)
                except:
                    pass
            
            # Clean up
            page.close()
            context.close()
            
            if content:
                content = self._clean_content(content)
                word_count = len(content.split())
                self._report_progress("extracting", 100, f"Extracted {word_count} words")
                
                if word_count >= self.min_content_words:
                    return {
                        'success': True,
                        'url': url,
                        'content': content,
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', ''),
                        'publish_date': metadata.get('publish_date', ''),
                        'source': metadata.get('source', ''),
                        'language': 'auto',
                        'word_count': word_count,
                        'extraction_method': 'article_playwright',
                        'extraction_timestamp': datetime.now().isoformat(),
                        'batch_id': self._current_batch_id,
                        'link_id': self._current_link_id,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'url': url,
                        'content': content,
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', ''),
                        'publish_date': metadata.get('publish_date', ''),
                        'source': metadata.get('source', ''),
                        'language': 'auto',
                        'word_count': word_count,
                        'extraction_method': 'article_playwright',
                        'extraction_timestamp': datetime.now().isoformat(),
                        'batch_id': self._current_batch_id,
                        'link_id': self._current_link_id,
                        'error': f'Content too short ({word_count} words)'
                    }
            else:
                return {
                    'success': False,
                    'url': url,
                    'content': None,
                    'title': metadata.get('title', ''),
                    'author': metadata.get('author', ''),
                    'publish_date': metadata.get('publish_date', ''),
                    'source': metadata.get('source', ''),
                    'language': 'auto',
                    'word_count': 0,
                    'extraction_method': 'article_playwright',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': self._current_batch_id,
                    'link_id': self._current_link_id,
                    'error': 'No content found'
                }
        
        except Exception as e:
            logger.error(f"[Article] Playwright extraction failed: {e}")
            return {
                'success': False,
                'url': url,
                'content': None,
                'title': '',
                'author': '',
                'publish_date': '',
                'source': '',
                'language': 'auto',
                'word_count': 0,
                'extraction_method': 'article_playwright',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': self._current_batch_id,
                'link_id': self._current_link_id,
                'error': str(e)
            }
    
    def _extract_with_trafilatura(self, url: str) -> Dict:
        """
        Extract content using trafilatura.
        
        Args:
            url: Article URL
        
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.debug("[Article] Using trafilatura...")
            
            # Download and extract
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return {
                    'success': False,
                    'url': url,
                    'content': None,
                    'title': '',
                    'author': '',
                    'publish_date': '',
                    'source': self._extract_domain(url),
                    'language': 'auto',
                    'word_count': 0,
                    'extraction_method': 'article_trafilatura',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'error': 'Download failed'
                }
            
            # Extract content
            try:
                content = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    include_links=False,
                    output_format='txt'
                )
            except Exception as e:
                logger.debug(f"Trafilatura extract failed: {e}")
                content = None
            
            if content:
                content = self._clean_content(content)
                word_count = len(content.split())
                
                if word_count >= self.min_content_words:
                    # Extract metadata from downloaded HTML
                    try:
                        metadata = trafilatura.extract_metadata(downloaded)
                        if metadata and hasattr(metadata, 'get'):
                            metadata_dict = metadata
                        else:
                            metadata_dict = None
                    except:
                        metadata_dict = None
                    
                    return {
                        'success': True,
                        'url': url,
                        'content': content,
                        'title': metadata_dict.get('title', '') if metadata_dict and hasattr(metadata_dict, 'get') else '',
                        'author': metadata_dict.get('author', '') if metadata_dict and hasattr(metadata_dict, 'get') else '',
                        'publish_date': metadata_dict.get('date', '') if metadata_dict and hasattr(metadata_dict, 'get') else '',
                        'source': self._extract_domain(url),
                        'language': 'auto',
                        'word_count': word_count,
                        'extraction_method': 'article_trafilatura',
                        'extraction_timestamp': datetime.now().isoformat(),
                        'batch_id': self._current_batch_id,
                        'link_id': self._current_link_id,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'url': url,
                        'content': content,
                        'title': '',
                        'author': '',
                        'publish_date': '',
                        'source': self._extract_domain(url),
                        'language': 'auto',
                        'word_count': word_count,
                        'extraction_method': 'article_trafilatura',
                        'extraction_timestamp': datetime.now().isoformat(),
                        'batch_id': self._current_batch_id,
                        'link_id': self._current_link_id,
                        'error': f'Content too short ({word_count} words)'
                    }
            else:
                return {
                    'success': False,
                    'url': url,
                    'content': None,
                    'title': '',
                    'author': '',
                    'publish_date': '',
                    'source': self._extract_domain(url),
                    'language': 'auto',
                    'word_count': 0,
                    'extraction_method': 'article_trafilatura',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': self._current_batch_id,
                    'link_id': self._current_link_id,
                    'error': 'Extraction failed'
                }
        
        except Exception as e:
            logger.error(f"[Article] Trafilatura extraction failed: {e}")
            return {
                'success': False,
                'url': url,
                'content': None,
                'title': '',
                'author': '',
                'publish_date': '',
                'source': self._extract_domain(url),
                'language': 'auto',
                'word_count': 0,
                'extraction_method': 'article_trafilatura',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': self._current_batch_id,
                'link_id': self._current_link_id,
                'error': str(e)
            }
    
    def _click_expand_buttons(self, page: Page):
        """Click 'Read More' / 'Expand' buttons."""
        expand_selectors = [
            'button:has-text("Read More")',
            'button:has-text("Read more")',
            'button:has-text("Show More")',
            'button:has-text("展开全文")',
            'button:has-text("展开")',
            'button:has-text("查看更多")',
            'a:has-text("Read More")',
            '.read-more',
            '.show-more'
        ]
        
        for selector in expand_selectors:
            try:
                buttons = page.locator(selector).all()
                for button in buttons[:3]:  # Limit to 3 buttons
                    try:
                        if button.is_visible(timeout=1000):
                            button.click()
                            time.sleep(0.5)
                    except:
                        continue
            except:
                continue
    
    def _remove_blocking_elements(self, page: Page):
        """Remove paywalls, overlays, modals."""
        try:
            page.evaluate("""
                const selectors = [
                    '.paywall', '.paywall-overlay', '.subscription-required',
                    '[class*="paywall"]', '[class*="overlay"]', '[class*="modal"]',
                    '.cookie-notice', '.gdpr-banner', '.privacy-notice',
                    '.newsletter', '.email-signup', '.subscribe-modal'
                ];
                
                selectors.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.getBoundingClientRect().width > 100 && 
                                el.getBoundingClientRect().height > 100) {
                                el.remove();
                            }
                        });
                    } catch(e) {}
                });
            """)
        except:
            pass
    
    def _extract_metadata(self, page: Page, url: str) -> Dict:
        """Extract metadata from page."""
        metadata = {
            'title': '',
            'author': '',
            'publish_date': '',
            'source': self._extract_domain(url)
        }
        
        # Title
        title_selectors = [
            'h1',
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'title'
        ]
        
        for selector in title_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if selector == 'h1':
                        metadata['title'] = element.inner_text(timeout=2000).strip()
                    else:
                        metadata['title'] = element.get_attribute('content').strip()
                    if metadata['title']:
                        break
            except:
                continue
        
        # Author
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            '[rel="author"]',
            '.author',
            '[class*="author"]'
        ]
        
        for selector in author_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if 'meta' in selector:
                        metadata['author'] = element.get_attribute('content').strip()
                    else:
                        metadata['author'] = element.inner_text(timeout=2000).strip()
                    if metadata['author']:
                        break
            except:
                continue
        
        # Publish date
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publish-date"]',
            'time[datetime]',
            '[class*="date"]'
        ]
        
        for selector in date_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if 'meta' in selector:
                        metadata['publish_date'] = element.get_attribute('content').strip()
                    else:
                        metadata['publish_date'] = element.get_attribute('datetime') or element.inner_text(timeout=2000)
                    if metadata['publish_date']:
                        break
            except:
                continue
        
        return metadata
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace('www.', '')

