"""Reddit content scraper optimized for Reddit posts."""
import time
from datetime import datetime
from typing import Dict
from loguru import logger
from playwright.sync_api import Page
from scrapers.base_scraper import BaseScraper


class RedditScraper(BaseScraper):
    """Extract content from Reddit posts and comments."""
    
    def __init__(self, **kwargs):
        """Initialize Reddit scraper."""
        super().__init__(**kwargs)
    
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is a valid Reddit URL.
        
        Args:
            url: URL to validate
        
        Returns:
            True if valid Reddit URL
        """
        return 'reddit.com' in url
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract content from Reddit post.
        
        Args:
            url: Reddit post URL
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        try:
            # Always use a simple browser launch for Reddit
            logger.info("[Reddit] Starting Chromium browser...")
            if not self._browser:
                self._init_playwright()
            
            # Create context - always launch new browser for Reddit
            logger.info("[Reddit] Creating new browser context")
            context = self._browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Navigate to Reddit homepage first for login
            logger.info("[Reddit] Opening Reddit homepage for login...")
            self._report_progress("loading", 10, "Opening Reddit for login")
            # Use 'domcontentloaded' instead of 'networkidle' - Reddit takes too long to reach networkidle
            page.goto('https://www.reddit.com', wait_until='domcontentloaded', timeout=self.timeout)
            time.sleep(3.0)  # Give a moment for initial load
            
            # Wait for user to log in - check page title
            logger.info("=" * 80)
            logger.info("WAITING FOR YOU TO LOG IN")
            logger.info("=" * 80)
            logger.info("Please log in to Reddit in the browser window.")
            logger.info("The scraper will continue when you're logged in...")
            logger.info("=" * 80)
            
            print("\n" + "=" * 80)
            print("WAITING FOR YOU TO LOG IN")
            print("=" * 80)
            print("\nBrowser window is open. Please log in to Reddit.")
            print("The scraper will auto-detect when you're logged in and continue...")
            print("\n" + "=" * 80 + "\n")
            
            # Wait for user to login - check on every page navigation/navigation to reddit
            max_wait = 300  # 5 minutes
            check_interval = 1  # Check every second
            start_wait = time.time()
            last_url = ""
            
            while time.time() - start_wait < max_wait:
                try:
                    current_url = page.url.lower()
                    
                    # If URL changed, check login status immediately
                    if current_url != last_url:
                        last_url = current_url
                        logger.debug(f"[Reddit] Page URL changed to: {current_url}")
                        
                        # Check if we're logged in (not on login/signup page)
                        if 'reddit.com' in current_url and 'login' not in current_url and 'signup' not in current_url:
                            # Check for logged-in indicators
                            try:
                                login_indicators = [
                                    '[data-testid="username"]',
                                    '[data-testid="post"]',
                                    'div[class*="UserMenu"]',
                                    'button[aria-label*="account"]',
                                    'div[class*="header"]'  # Header usually appears when logged in
                                ]
                                
                                found_indicator = False
                                for selector in login_indicators:
                                    try:
                                        count = page.locator(selector).count()
                                        if count > 0:
                                            found_indicator = True
                                            logger.info(f"[Reddit] Found logged-in indicator: {selector}")
                                            break
                                    except:
                                        continue
                                
                                if found_indicator:
                                    logger.info("[Reddit] Login detected! Continuing with scraping...")
                                    break
                            except Exception as e:
                                logger.debug(f"[Reddit] Error checking login indicators: {e}")
                    
                    elapsed = int(time.time() - start_wait)
                    if elapsed % 5 == 0 and elapsed > 0:
                        logger.info(f"[Reddit] Waiting for login... ({elapsed}s elapsed, current URL: {current_url})")
                    
                    time.sleep(check_interval)
                except Exception as e:
                    logger.warning(f"[Reddit] Error checking login status: {e}")
                    time.sleep(check_interval)
            else:
                logger.warning("[Reddit] Login timeout after 5 minutes - continuing anyway...")
            
            time.sleep(2)  # Give a moment for page to settle
            
            # Now navigate to the actual post
            logger.info(f"[Reddit] Navigating to post: {url}")
            self._report_progress("loading", 20, "Loading Reddit post")
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            # Wait longer for dynamic content to load
            logger.info("[Reddit] Waiting for page content to load...")
            time.sleep(8.0)  # Longer wait for Reddit's JS to fully load
            self._report_progress("loading", 30, "Content loaded")
            
            # Check if we're blocked by anti-bot protection
            is_blocked = self._check_anti_bot_block(page)
            if is_blocked:
                logger.warning("[Reddit] Detected anti-bot protection")
                # Attempt automatic override by visiting Reddit home, then returning
                try:
                    logger.info("[Reddit] Trying anti-bot override via reddit.com → post reload...")
                    page.goto('https://www.reddit.com', wait_until='domcontentloaded', timeout=self.timeout)
                    time.sleep(5.0)
                    logger.info("[Reddit] Returning to target post after home page load...")
                    page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                    time.sleep(6.0)
                    # Re-check block status
                    if self._check_anti_bot_block(page):
                        logger.warning("[Reddit] Override failed; prompting for manual CAPTCHA/override")
                        self._handle_anti_bot_block(page)
                    else:
                        logger.info("[Reddit] Anti-bot override appears successful; continuing")
                except Exception as e:
                    logger.warning(f"[Reddit] Error during anti-bot override attempt: {e}")
                    self._handle_anti_bot_block(page)
            
            # Extract metadata first (while page is stable)
            self._report_progress("extracting", 40, "Extracting metadata")
            metadata = self._extract_metadata(page, url)
            
            # Extract post content using broader approach
            self._report_progress("extracting", 50, "Extracting post content")
            post_content = self._extract_content_broad(page)
            
            logger.info(f"[Reddit] Extracted post content length: {len(post_content) if post_content else 0} characters")
            
            # Extract top comments
            self._report_progress("extracting", 70, "Extracting comments")
            top_comments = self._extract_top_comments(page, max_comments=10)
            
            # Combine post and top comments
            if top_comments:
                full_content = f"{post_content}\n\n--- Top Comments ---\n{top_comments}"
            else:
                full_content = post_content
            
            full_content = self._clean_content(full_content)
            word_count = len(full_content.split()) if full_content else 0
            
            # Keep browser open for inspection (always)
            logger.info("[Reddit] Keeping browser window open for inspection")
            # Don't close the page or context - user can inspect results
            
            if word_count >= 10:  # Minimum content check
                elapsed_time = round(time.time() - start_time, 2)
                self._report_progress("extracting", 100, f"Extraction complete: {word_count} words")
                logger.info(f"[Reddit] Extracted {word_count} words in {elapsed_time}s")
                
                return {
                    'success': True,
                    'url': url,
                    'content': full_content,
                    'title': metadata.get('title', ''),
                    'author': metadata.get('author', ''),
                    'publish_date': metadata.get('publish_date', ''),
                    'source': 'Reddit',
                    'language': 'auto',
                    'word_count': word_count,
                    'extraction_method': 'reddit',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'url': url,
                    'content': post_content,
                    'title': metadata.get('title', ''),
                    'author': metadata.get('author', ''),
                    'publish_date': metadata.get('publish_date', ''),
                    'source': 'Reddit',
                    'language': 'auto',
                    'word_count': word_count,
                    'extraction_method': 'reddit',
                    'extraction_timestamp': datetime.now().isoformat(),
                    'batch_id': batch_id,
                    'link_id': link_id,
                    'error': 'Insufficient content extracted'
                }
            
        except Exception as e:
            logger.error(f"[Reddit] Extraction failed: {e}")
            return {
                'success': False,
                'url': url,
                'content': None,
                'title': '',
                'author': '',
                'publish_date': '',
                'source': 'Reddit',
                'language': 'auto',
                'word_count': 0,
                'extraction_method': 'reddit',
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': str(e)
            }
    
    def _check_anti_bot_block(self, page: Page) -> bool:
        """Check if Reddit is showing anti-bot protection."""
        try:
            page_title = page.title().lower()
            page_url = page.url.lower()
            
            # Primary detection: "prove your humanity" in page title
            if 'prove your humanity' in page_title:
                logger.warning("[Reddit] CAPTCHA page detected: 'prove your humanity' in title")
                return True
            
            # Other common indicators of bot blocking
            indicators = [
                'sorry, we have been unable to process your request',
                'we\'ve detected unusual activity',
                'verify you are human',
                'are you a bot',
                'cloudflare',
                'just a moment',
                'checking your browser'
            ]
            
            for indicator in indicators:
                if indicator in page_title or indicator in page_url:
                    logger.warning(f"[Reddit] Anti-bot indicator found: {indicator}")
                    return True
            
            # Check for CAPTCHA elements
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                'img[alt*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                if page.locator(selector).count() > 0:
                    logger.warning("[Reddit] CAPTCHA detected on page")
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"[Reddit] Error checking anti-bot block: {e}")
            return False
    
    def _handle_anti_bot_block(self, page: Page) -> None:
        """Handle anti-bot protection by waiting for user to complete CAPTCHA."""
        logger.warning("=" * 80)
        logger.warning("REDDIT CAPTCHA DETECTED")
        logger.warning("=" * 80)
        logger.warning("\nPlease complete the CAPTCHA in the browser window.")
        logger.warning("The page will automatically redirect once you're done.\n")
        
        print("\n" + "=" * 80)
        print("REDDIT CAPTCHA DETECTED")
        print("=" * 80)
        print("\nThe browser window is open and visible.")
        print("Please complete the CAPTCHA to prove your humanity.")
        print("The page will automatically redirect to the Reddit post.\n")
        
        # Wait for the page to navigate away from CAPTCHA page
        captcha_title = page.title()
        logger.info(f"[Reddit] Current page title: {captcha_title}")
        logger.info("[Reddit] Waiting for CAPTCHA completion and page redirect...")
        
        # Wait up to 2 minutes for the user to complete CAPTCHA
        max_wait_time = 120  # 2 minutes
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                current_title = page.title()
                current_url = page.url
                
                # Check if we've navigated away from the CAPTCHA page
                if 'prove your humanity' not in current_title.lower():
                    logger.info("[Reddit] Page has navigated away from CAPTCHA page")
                    logger.info(f"[Reddit] New page title: {current_title}")
                    logger.info(f"[Reddit] New URL: {current_url}")
                    break
                
                # Show progress
                elapsed = int(time.time() - start_time)
                remaining = max_wait_time - elapsed
                if elapsed % 10 == 0:  # Every 10 seconds
                    logger.info(f"[Reddit] Still on CAPTCHA page... ({remaining}s remaining)")
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"[Reddit] Error checking page state: {e}")
                time.sleep(check_interval)
        else:
            logger.warning("[Reddit] Timeout waiting for CAPTCHA completion, continuing anyway...")
        
        logger.info("[Reddit] Continuing with extraction...")
        time.sleep(2.0)  # Give the page a moment to fully load
        self._report_progress("extracting", 35, "CAPTCHA completed, continuing extraction...")
    
    def _extract_metadata(self, page: Page, url: str) -> Dict:
        """Extract metadata from Reddit post."""
        metadata = {
            'title': '',
            'author': '',
            'publish_date': '',
            'source': 'Reddit'
        }
        
        try:
            # Extract title
            title_selectors = [
                'h1',
                '[data-testid="post-title"]',
                'h1.reddit-entry-title',
                '.reddit-entry-title'
            ]
            
            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        metadata['title'] = element.inner_text(timeout=2000).strip()
                        if metadata['title']:
                            break
                except:
                    continue
            
            # Extract author
            author_selectors = [
                '[data-testid="author-name"]',
                'span.user-name',
                '.author',
                'a[data-testid="username"]'
            ]
            
            for selector in author_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        metadata['author'] = element.inner_text(timeout=2000).strip()
                        if metadata['author']:
                            break
                except:
                    continue
            
            # Extract publish date
            date_selectors = [
                '[data-testid="post-date"]',
                'time',
                '.entry-date'
            ]
            
            for selector in date_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        date_text = element.inner_text(timeout=2000).strip() or element.get_attribute('datetime')
                        if date_text:
                            metadata['publish_date'] = date_text
                            break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting Reddit metadata: {e}")
        
        return metadata
    
    def _extract_content_broad(self, page: Page) -> str:
        """Extract content using a broader, more robust approach."""
        content_parts = []
        
        try:
            # Strategy 1: Get ALL visible text from the main post area
            logger.info("[Reddit] Attempting broad content extraction...")
            
            # Wait for page to stabilize
            page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(3.0)
            
            # Extract all text content from the page body
            content = page.evaluate("""
                () => {
                    // Get all text nodes that contain substantial content
                    const textElements = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    let currentParent = null;
                    let currentText = '';
                    
                    while (node = walker.nextNode()) {
                        const parent = node.parentElement;
                        if (parent && !parent.closest('nav') && !parent.closest('header') && 
                            !parent.closest('aside') && !parent.closest('footer')) {
                            const text = node.textContent.trim();
                            if (text && text.length > 10) {
                                const parentClass = parent.className || '';
                                // Check if it's likely content (not just UI elements)
                                if (!text.includes('Posted by') && 
                                    !text.includes('Points') &&
                                    !text.includes('Comments') &&
                                    !text.includes('Share') &&
                                    !text.includes('Save') &&
                                    !text.includes('Hide') &&
                                    text.length > 20) {
                                    textElements.push(text);
                                }
                            }
                        }
                    }
                    
                    // Filter and deduplicate
                    const uniqueTexts = [...new Set(textElements)];
                    return uniqueTexts.join('\\n\\n');
                }
            """)
            
            if content and len(content) > 50:
                logger.info(f"[Reddit] Extracted {len(content)} characters using text node extraction")
                content_parts.append(content)
            
            # Strategy 2: If still no content, try getting text from specific regions
            if not content_parts:
                logger.info("[Reddit] Trying region-based extraction...")
                try:
                    # Try to get text from main content area
                    main_content = page.locator('main, [role="main"], article').first
                    if main_content.count() > 0:
                        text = main_content.inner_text(timeout=3000)
                        if text and len(text) > 50:
                            content_parts.append(text)
                except:
                    pass
                
                # Try to get text from any text-heavy div
                if not content_parts:
                    try:
                        all_divs = page.locator('div').all()
                        for div in all_divs[:50]:  # Check first 50 divs
                            if div.count() > 0:
                                text = div.inner_text(timeout=1000)
                                if text and 50 < len(text) < 2000:  # Reasonable content size
                                    content_parts.append(text)
                                    break
                    except:
                        pass
            
            # Strategy 3: Last resort - get visible text from body and clean it
            if not content_parts:
                logger.info("[Reddit] Falling back to body text extraction...")
                try:
                    body_text = page.evaluate("""
                        () => {
                            return document.body.innerText;
                        }
                    """)
                    # Filter out short or UI-related lines
                    lines = body_text.split('\n')
                    filtered_lines = [line.strip() for line in lines if 
                                     len(line.strip()) > 30]
                    
                    # Remove duplicate lines
                    unique_lines = []
                    seen = set()
                    for line in filtered_lines:
                        # Skip very short lines and UI elements
                        if (line and len(line) > 30 and 
                            'Posted by' not in line and
                            'Comments' not in line[:20] and
                            'Share' not in line and
                            'Save' not in line and
                            'Points' not in line and
                            line not in seen):
                            unique_lines.append(line)
                            seen.add(line)
                    
                    if unique_lines:
                        # Take the first substantial block of text
                        content_parts.append('\n'.join(unique_lines[:20]))
                except Exception as e:
                    logger.warning(f"Body text extraction failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Error in broad content extraction: {e}")
        
        combined = '\n\n'.join(content_parts) if content_parts else ''
        logger.info(f"[Reddit] Extracted {len(combined)} characters total")
        return combined if len(combined) > 50 else ''
    
    def _extract_post_content(self, page: Page) -> str:
        """Extract main post content."""
        content_parts = []
        
        try:
            # First, expand all "Read more" buttons in the post
            self._expand_read_more_buttons(page)
            time.sleep(1.0)
            
            # Try to find the post text - Reddit uses various selectors
            post_selectors = [
                'div[data-testid="post-content"] p',
                'div[class*="usertext"] p',
                'div[class*="md"] p',
                '.post-content p',
                'article p',
                'div.md > p',
                '[data-testid="post-content"]',  # Try the container itself
                'div[class*="Post"] p'  # More generic Reddit post selector
            ]
            
            for selector in post_selectors:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        texts = []
                        # Get more paragraphs now
                        for element in elements[:10]:  # More paragraphs
                            try:
                                text = element.inner_text(timeout=1000)
                                if text and len(text) > 20:
                                    texts.append(text.strip())
                            except:
                                pass
                        
                        if texts:
                            content_parts.extend(texts)
                            break
                except:
                    continue
            
            # If no content found with specific selectors, try broader approach
            if not content_parts:
                try:
                    # Get the first article or main content area
                    main_content = page.locator('article').first
                    if main_content.count() > 0:
                        text = main_content.inner_text(timeout=2000)
                        if text and len(text) > 100:
                            content_parts.append(text)
                    
                    # Try the div.md approach
                    md_div = page.locator('div.md').first
                    if md_div.count() > 0:
                        text = md_div.inner_text(timeout=2000)
                        if text and len(text) > 100:
                            content_parts.append(text)
                    
                    # Try using data-testid="post-content" container
                    post_content_div = page.locator('[data-testid="post-content"]').first
                    if post_content_div.count() > 0:
                        text = post_content_div.inner_text(timeout=2000)
                        if text and len(text) > 100:
                            content_parts.append(text)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error extracting post content: {e}")
        
        combined = '\n\n'.join(content_parts) if content_parts else ''
        return combined if len(combined) > 50 else ''
    
    def _expand_read_more_buttons(self, page: Page) -> None:
        """Expand all 'Read more' buttons on the page."""
        try:
            # Wait for page to be fully loaded
            time.sleep(2.0)
            
            # Find all "Read more" buttons using multiple selectors
            read_more_selectors = [
                'button[data-read-more-experiment-name]',
                'button:has-text("Read more")',
                '#read-more-button',
                '[id*="read-more-button"]'
            ]
            
            for selector in read_more_selectors:
                try:
                    buttons = page.locator(selector).all()
                    if buttons:
                        logger.info(f"[Reddit] Found {len(buttons)} 'Read more' buttons")
                        for button in buttons:
                            try:
                                # Check if button is visible
                                if button.is_visible():
                                    button.click(timeout=1000)
                                    time.sleep(0.5)  # Small delay between clicks
                            except:
                                pass
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error expanding 'Read more' buttons: {e}")
    
    def _expand_more_replies_buttons(self, page: Page) -> None:
        """Expand all 'More replies' buttons on the page."""
        try:
            # Find all "More replies" buttons using multiple approaches
            try:
                # Approach 1: Using Playwright text matching
                buttons = page.locator('button:has-text("more reply")').all()
                if buttons:
                    logger.info(f"[Reddit] Found {len(buttons)} 'More replies' buttons")
                    for button in buttons:
                        try:
                            if button.is_visible():
                                button.scroll_into_view_if_needed()
                                button.click(timeout=1000)
                                time.sleep(0.5)  # Small delay between clicks
                        except:
                            pass
            except:
                pass
            
            # Approach 2: Using JavaScript to find and click buttons
            try:
                clicked_count = page.evaluate("""
                    () => {
                        let count = 0;
                        const buttons = Array.from(document.querySelectorAll('button'));
                        buttons.forEach(btn => {
                            const text = btn.textContent?.toLowerCase() || '';
                            if (text.includes('more reply') || text.includes('reply')) {
                                try {
                                    if (btn.offsetParent !== null) {  // Check if visible
                                        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        btn.click();
                                        count++;
                                    }
                                } catch (e) {}
                            }
                        });
                        return count;
                    }
                """)
                if clicked_count > 0:
                    logger.info(f"[Reddit] Clicked {clicked_count} 'More replies' buttons via JS")
            except:
                pass
            
            # Approach 3: Try specific class selectors
            try:
                buttons = page.locator('button.text-tone-2').all()
                for button in buttons:
                    try:
                        text = button.inner_text()
                        if 'more reply' in text.lower():
                            if button.is_visible():
                                button.scroll_into_view_if_needed()
                                button.click(timeout=1000)
                                time.sleep(0.5)
                    except:
                        pass
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Error expanding 'More replies' buttons: {e}")
    
    def _expand_all_content(self, page: Page) -> None:
        """Expand all expandable content on the page."""
        logger.info("[Reddit] Expanding all content...")
        
        # Expand "Read more" buttons
        self._expand_read_more_buttons(page)
        
        # Wait a moment for content to expand
        time.sleep(1.0)
        
        # Expand "More replies" buttons
        self._expand_more_replies_buttons(page)
        
        # Wait for content to load
        time.sleep(1.0)
    
    def _extract_top_comments(self, page: Page, max_comments: int = 3) -> str:
        """Extract top comments from the post."""
        comments = []
        
        try:
            # Expand all content first
            self._expand_all_content(page)
            
            # Scroll down to load comments (only once, as requested)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2.0)
            
            # Try to expand content that appeared after scrolling
            try:
                self._expand_read_more_buttons(page)
                time.sleep(0.5)
                self._expand_more_replies_buttons(page)
                time.sleep(0.5)
            except:
                pass
            
            # Find comments with broader selectors
            comment_selectors = [
                '[data-testid="comment"]',
                'shreddit-comment',  # Reddit's shadow DOM element
                'div[class*="Comment"]',
                '[class*="comment"]',
                '.comment'
            ]
            
            for selector in comment_selectors:
                try:
                    comment_elements = page.locator(selector).all()
                    if comment_elements:
                        logger.info(f"[Reddit] Found {len(comment_elements)} comments with selector: {selector}")
                        
                        # Extract more comments now (was limited to 3)
                        for i, comment in enumerate(comment_elements[:max_comments * 3]):  # Get more comments
                            try:
                                text = comment.inner_text(timeout=2000)
                                if text and len(text) > 30:  # Minimum comment length
                                    comments.append(text.strip())
                            except:
                                pass
                        
                        if comments:
                            break
                except:
                    continue
                    
            # Also try to extract using direct DOM methods
            if not comments:
                try:
                    # Try extracting using evaluate
                    extracted_comments = page.evaluate("""
                        () => {
                            const comments = [];
                            const commentElements = document.querySelectorAll('[data-testid="comment"]');
                            commentElements.forEach(el => {
                                const text = el.innerText || el.textContent || '';
                                if (text && text.length > 30) {
                                    comments.push(text.trim());
                                }
                            });
                            return comments;
                        }
                    """)
                    comments.extend(extracted_comments)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error extracting comments: {e}")
        
        return '\n\n---\n\n'.join(comments) if comments else ''

