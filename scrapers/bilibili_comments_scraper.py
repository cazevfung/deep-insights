"""Bilibili comments scraper using Bilibili API."""
import time
import re
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger
import requests
from scrapers.base_scraper import BaseScraper


class BilibiliCommentsScraper(BaseScraper):
    """
    Extract comments from Bilibili videos using Bilibili API.
    
    Cookie-based approach allows for easy updates without code changes.
    Cookies are loaded from data/cookies/bilibili_cookies.json.
    """
    
    def __init__(self, **kwargs):
        """Initialize Bilibili comments scraper."""
        super().__init__(**kwargs)
        
        # Load configuration
        self.cookie_source = self.scraper_config.get('cookie_source', 'file')
        self.cookie_file = self.scraper_config.get('cookie_file', 'data/cookies/bilibili_cookies.json')
        self.max_pages = self.scraper_config.get('max_pages', 30)
        self.sort_mode = self.scraper_config.get('sort_mode', 3)  # 3=hot, 2=new
        self.max_comments_per_page = self.scraper_config.get('max_comments_per_page', 20)
        
        # Load cookies
        self.cookies = self._load_cookies()
        logger.info(f"[BilibiliComments] Loaded {len(self.cookies)} cookies")
        if self.cookies:
            # Log first few cookie names for debugging
            cookie_names = [c.get('name', 'unknown') for c in self.cookies[:5]]
            logger.debug(f"[BilibiliComments] Cookie names: {cookie_names}")
        
        # Build headers
        self.headers = self._build_headers()
        
        # Cache for BV to AV conversion
        self.bv_av_cache = {}
        # Track current BV for referer/header purposes
        self.current_bv = None
        
        logger.info("[BilibiliComments] Initialized")
        logger.info(f"[BilibiliComments] Max pages: {self.max_pages}, Sort mode: {self.sort_mode}")
    
    def _load_cookies(self) -> List[Dict]:
        """Load cookies from file or config."""
        if self.cookie_source == 'file':
            return self._load_cookies_from_file()
        else:
            return self._load_cookies_from_config()
    
    def _load_cookies_from_file(self) -> List[Dict]:
        """Load cookies from JSON file."""
        try:
            cookie_path = Path(self.cookie_file)
            
            # If relative path, make it relative to project root
            if not cookie_path.is_absolute():
                project_root = find_project_root()
                cookie_path = project_root / cookie_path
            
            if not cookie_path.exists():
                logger.warning(f"[BilibiliComments] Cookie file not found: {cookie_path}")
                logger.warning("[BilibiliComments] Using empty cookies (IP location may not be available)")
                return []
            
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            logger.info(f"[BilibiliComments] Loaded {len(cookies)} cookies from {cookie_path}")
            return cookies
            
        except Exception as e:
            logger.error(f"[BilibiliComments] Failed to load cookies from file: {e}")
            return []
    
    def _load_cookies_from_config(self) -> List[Dict]:
        """Load cookies from config.yaml."""
        try:
            cookies = self.scraper_config.get('cookies', [])
            logger.info(f"[BilibiliComments] Loaded {len(cookies)} cookies from config")
            return cookies
        except Exception as e:
            logger.error(f"[BilibiliComments] Failed to load cookies from config: {e}")
            return []
    
    def _parse_cookies_to_string(self, cookies: List[Dict]) -> str:
        """Convert cookie JSON array to cookie header string."""
        if not cookies:
            return ""
        
        cookie_pairs = []
        for cookie in cookies:
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            if name and value:
                cookie_pairs.append(f"{name}={value}")
        
        cookie_string = '; '.join(cookie_pairs)
        logger.debug(f"[BilibiliComments] Parsed cookies: {len(cookie_pairs)} cookie pairs")
        return cookie_string
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with cookies."""
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'origin': 'https://www.bilibili.com',
            'sec-ch-ua': '"Chromium";v="106", "Microsoft Edge";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.47'
        }
        
        # Add cookies if available
        cookie_string = self._parse_cookies_to_string(self.cookies)
        if cookie_string:
            headers['cookie'] = cookie_string
            logger.info("[BilibiliComments] Cookies loaded successfully")
        else:
            logger.warning("[BilibiliComments] No cookies loaded - IP location may not be available")
        
        return headers
    
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is a valid Bilibili video URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid Bilibili video URL
        """
        # Accept:
        # - Full URLs: https://www.bilibili.com/video/BVxxxxxxx
        # - Full URLs: https://www.bilibili.com/video/avxxxxxxx
        # - Just BV ID: BVxxxxxxx
        bilibili_pattern = r'(bilibili\.com.*video|^BV[a-zA-Z0-9]+|^av\d+)'
        return bool(re.search(bilibili_pattern, url, re.IGNORECASE))
    
    def extract(self, url: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Extract comments from Bilibili video.
        
        Args:
            url: Bilibili video URL or BV ID
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        
        # Set extraction context for progress reporting
        self._set_extraction_context(batch_id, link_id, url)
        
        try:
            # Extract video IDs
            bv_id, av_id = self._extract_video_id(url)
            if not bv_id:
                raise ValueError(f"Could not extract BV ID from URL: {url}")
            
            logger.info(f"[BilibiliComments] Extracting comments from BV: {bv_id}")
            # Save BV for referer usage in subsequent requests
            self.current_bv = bv_id
            if av_id:
                logger.info(f"[BilibiliComments] Using AV ID: {av_id}")
            else:
                logger.info(f"[BilibiliComments] Will use BV ID directly (AV conversion failed or skipped)")
            
            self._report_progress("extracting", 10, f"Extracting comments from {bv_id}")
            
            # Fetch comments
            all_comments = []
            page_count = 0
            total_comments_available = None
            pagination_info = {}
            
            for page_num in range(1, self.max_pages + 1):
                self._report_progress("extracting", 
                                    10 + int((page_num / self.max_pages) * 80),
                                    f"Fetching page {page_num}/{self.max_pages}")
                
                # Use AV ID if available, otherwise use BV ID
                page_comments, had_replies, page_info = self._fetch_comments_page(av_id if av_id else bv_id, page_num)
                
                # Update pagination info (use info from first successful page)
                if page_info and total_comments_available is None:
                    total_comments_available = page_info.get('total', 0)
                    pagination_info = page_info
                    logger.info(f"[BilibiliComments] Total comments available: {total_comments_available}, total pages: {page_info.get('total_pages', 0)}")
                
                # Add comments from this page
                all_comments.extend(page_comments)
                page_count = page_num
                logger.info(f"[BilibiliComments] Fetched {len(page_comments)} kept comments from page {page_num} (total so far: {len(all_comments)})")
                
                # Check if we should stop:
                # 1. No replies on this page AND no more pages available
                # 2. Or we've collected enough comments (approaching total)
                # 3. Or we've hit max_pages
                if not had_replies:
                    logger.info(f"[BilibiliComments] No more replies available on page {page_num}, stopping")
                    break
                
                # If we know the total and have collected a significant portion, check if there are more pages
                if page_info:
                    has_more = page_info.get('has_more', False)
                    if not has_more:
                        logger.info(f"[BilibiliComments] Reached last available page ({page_num}), stopping")
                        break
                
                # Rate limiting: wait between requests (increased delay to avoid rate limits)
                if page_num < self.max_pages:
                    delay = 1.0 + random.uniform(0, 1.0)  # 1-2 seconds random delay
                    logger.debug(f"[BilibiliComments] Waiting {delay:.2f}s before next page...")
                    time.sleep(delay)
            
            # If no comments found
            if not all_comments:
                logger.warning("[BilibiliComments] No comments found")
                return self._error_result(url, "No comments found", bv_id, batch_id, link_id)
            
            # Format output - simplified structure with BV id as identifier
            elapsed_time = round(time.time() - start_time, 2)
            logger.info(f"[BilibiliComments] Extracted {len(all_comments)} comments in {elapsed_time}s (from {page_count} pages)")
            if total_comments_available:
                logger.info(f"[BilibiliComments] Total comments available in API: {total_comments_available}, extracted: {len(all_comments)}")
            
            self._report_progress("extracting", 100, f"Extracted {len(all_comments)} comments")
            
            # Return simplified structure with BV id as identifier
            return {
                'success': True,
                'bv_id': bv_id,
                'comments': all_comments,
                'total_comments': len(all_comments),
                'total_available': total_comments_available,
                'pages_fetched': page_count,
                'extraction_timestamp': datetime.now().isoformat(),
                'batch_id': batch_id,
                'link_id': link_id,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"[BilibiliComments] Extraction failed: {e}")
            # Try to extract BV id for error result
            try:
                bv_id, _ = self._extract_video_id(url)
            except:
                bv_id = None
            return self._error_result(url, str(e), bv_id, batch_id, link_id)
    
    def _extract_video_id(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Extract BV and AV IDs from URL.
        
        Supports various formats:
        - https://www.bilibili.com/video/BV18UxNzLE8K/?spm_id_from=...
        - https://bilibili.com/video/BV18UxNzLE8K
        - bilibili.com/video/av123456789
        - BV18UxNzLE8K
        - av123456789
        
        Args:
            url: Video URL or BV ID
            
        Returns:
            Tuple of (bv_id, av_id)
        """
        logger.debug(f"[BilibiliComments] Extracting video ID from: {url}")
        
        # Try to extract BV ID (case-insensitive)
        bv_match = re.search(r'BV([a-zA-Z0-9]+)', url, re.IGNORECASE)
        bv_id = None
        
        if bv_match:
            bv_id = "BV" + bv_match.group(1)
            logger.debug(f"[BilibiliComments] Extracted BV ID: {bv_id}")
        
        # Try to extract AV ID
        av_match = re.search(r'(?:/video/)?av(\d+)', url, re.IGNORECASE)
        av_id = None
        
        if av_match:
            av_id = int(av_match.group(1))
            logger.debug(f"[BilibiliComments] Extracted AV ID: {av_id}")
        elif bv_id:
            # Convert BV to AV
            logger.debug(f"[BilibiliComments] Converting BV to AV: {bv_id}")
            av_id = self._bv_to_av(bv_id)
        
        return (bv_id, av_id)
    
    def _bv_to_av(self, bv_id: str) -> Optional[int]:
        """
        Convert BV ID to AV ID.
        
        Bilibili uses AV IDs internally for the API.
        This is a simplified conversion (full conversion would require table lookup).
        
        Args:
            bv_id: BV ID (e.g., "BV1DP411g7jx")
            
        Returns:
            AV ID as integer
        """
        # Check cache
        if bv_id in self.bv_av_cache:
            return self.bv_av_cache[bv_id]
        
        try:
            # For now, we'll try to extract from the BV ID directly
            # This is a simplified approach - full conversion is complex
            logger.debug(f"[BilibiliComments] Converting BV {bv_id} to AV")
            
            # Try fetching video info to get AV ID
            # This is a workaround since full BV conversion is complex
            # We'll make an API call to get video info
            response = requests.get(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    aid = data.get('data', {}).get('aid')
                    if aid:
                        # Cache and return the AV ID from Bilibili API (modern videos use large AV IDs)
                        self.bv_av_cache[bv_id] = aid
                        logger.info(f"[BilibiliComments] Converted {bv_id} to AV{aid}")
                        return aid
            
            logger.warning(f"[BilibiliComments] Could not convert BV to AV directly, trying fallback")
            
            # Fallback: Extract numeric part from BV
            # This is not perfect but works for many cases
            numeric_part = re.search(r'BV(\d+)', bv_id)
            if numeric_part:
                av_id = int(numeric_part.group(1))
                logger.warning(f"[BilibiliComments] Using fallback conversion for {bv_id}: AV{av_id}")
                return av_id
            
            return None
            
        except Exception as e:
            logger.error(f"[BilibiliComments] BV to AV conversion failed: {e}")
            return None
    
    def _fetch_comments_page(self, video_id, page_num: int, retry_count: int = 0) -> Tuple[List[Dict], bool, Dict]:
        """
        Fetch one page of comments from Bilibili API with automatic retry.
        
        Args:
            video_id: Video AV ID (int) or BV ID (str)
            page_num: Page number (1-based)
            retry_count: Number of retry attempts
            
        Returns:
            Tuple of (comments_kept, had_replies, pagination_info)
            pagination_info: Dict with 'total', 'page_num', 'page_size', 'has_more'
        """
        max_retries = 3
        base_delay = 2.0  # Base delay in seconds
        
        try:
            url = f"https://api.bilibili.com/x/v2/reply"
            params = {
                'oid': video_id,
                'type': '1',  # Type 1 = video comments
                'pn': page_num,
                'ps': self.max_comments_per_page,
                'sort': self.sort_mode
            }
            
            # Update referer for this request
            headers = self.headers.copy()
            # Prefer BV-based referer if known, otherwise fall back
            if isinstance(video_id, str):
                referer_video_id = video_id
            else:
                referer_video_id = self.current_bv if getattr(self, 'current_bv', None) else f'av{video_id}'
            headers['referer'] = f'https://www.bilibili.com/video/{referer_video_id}'
            
            logger.debug(f"[BilibiliComments] Fetching page {page_num} for {video_id} (attempt {retry_count + 1}/{max_retries + 1})")
            logger.debug(f"[BilibiliComments] Request params: {params}")
            logger.debug(f"[BilibiliComments] Has cookies: {bool(headers.get('cookie'))}")
            
            # Add random delay before request to avoid rate limiting
            if retry_count > 0 or page_num > 1:
                delay = base_delay * (2 ** retry_count) + random.uniform(0.5, 1.5)
                logger.info(f"[BilibiliComments] Waiting {delay:.1f}s before request (retry count: {retry_count})")
                time.sleep(delay)
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"[BilibiliComments] API returned status {response.status_code}")
                try:
                    error_data = response.json() if response.text else {}
                    logger.error(f"[BilibiliComments] API error response: {error_data}")
                    logger.error(f"[BilibiliComments] Response text: {response.text[:200]}")
                except:
                    logger.error(f"[BilibiliComments] Response text: {response.text[:200]}")
                
                # Retry logic for 412 (banned) or 429 (rate limit) errors
                if retry_count < max_retries and (response.status_code in [412, 429]):
                    logger.warning(f"[BilibiliComments] Retrying (attempt {retry_count + 1}/{max_retries}) in {base_delay * (2 ** retry_count):.1f}s...")
                    time.sleep(base_delay * (2 ** retry_count))
                    return self._fetch_comments_page(video_id, page_num, retry_count + 1)
                
                return ([], False, {})
            
            data = response.json()
            
            if data.get('code') != 0:
                error_code = data.get('code')
                error_msg = data.get('message')
                logger.error(f"[BilibiliComments] API returned error code {error_code}: {error_msg}")
                
                # Retry logic for banned/rate limit errors
                if retry_count < max_retries and error_code in [-412, -412]:
                    logger.warning(f"[BilibiliComments] API banned/rate limited. Retrying (attempt {retry_count + 1}/{max_retries})...")
                    time.sleep(base_delay * (2 ** retry_count))
                    return self._fetch_comments_page(video_id, page_num, retry_count + 1)
                
                logger.error(f"[BilibiliComments] Full error data: {data}")
                return ([], False, {})
            
            # Extract pagination info from API response
            # Handle case where 'data' key exists but value is None
            data_obj = data.get('data') or {}
            page_info = data_obj.get('page') or {}
            total_comments = page_info.get('count', 0)  # Total comment count
            total_pages = page_info.get('pages', 0)  # Total pages
            current_page = page_info.get('num', page_num)  # Current page number
            page_size = page_info.get('size', self.max_comments_per_page)  # Page size
            
            # Handle case where 'replies' key exists but value is None
            replies = data_obj.get('replies') or []
            
            # Determine if there are more pages
            has_more = current_page < total_pages if total_pages > 0 else (len(replies) > 0)
            
            # Build pagination info
            pagination_info = {
                'total': total_comments,
                'page_num': current_page,
                'total_pages': total_pages,
                'page_size': page_size,
                'has_more': has_more,
                'current_replies': len(replies)
            }
            
            logger.debug(f"[BilibiliComments] Page {page_num} pagination info: total={total_comments}, pages={total_pages}, has_more={has_more}")
            
            # Parse comments
            comments = []
            for reply in replies:
                comment = self._parse_comment_data(reply, page_num, video_id)
                if comment:
                    comments.append(comment)
            
            # Return True for had_replies if we got replies OR if there are more pages (even if current page filtered to zero)
            had_replies = len(replies) > 0 or has_more
            
            logger.info(f"[BilibiliComments] Page {page_num}: raw replies={len(replies)}, kept={len(comments)}, total={total_comments}, has_more={has_more}")
            return (comments, had_replies, pagination_info)
            
        except Exception as e:
            logger.error(f"[BilibiliComments] Failed to fetch page {page_num}: {e}")
            
            # Retry on network errors
            if retry_count < max_retries:
                logger.warning(f"[BilibiliComments] Retrying after error (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(base_delay * (2 ** retry_count))
                return self._fetch_comments_page(video_id, page_num, retry_count + 1)
            
            return ([], False, {})
    
    def _parse_comment_data(self, reply: Dict, page_num: int, video_id) -> Optional[Dict]:
        """
        Parse single comment from API response.
        
        Args:
            reply: Raw comment data from API
            page_num: Page number
            video_id: Video AV ID (int) or BV ID (str)
            
        Returns:
            Parsed comment dictionary with only content and likes, or None
        """
        try:
            content = reply.get('content', {})
            comment_text = content.get('message', '')
            
            # Filter out comments shorter than 10 characters
            if len(comment_text) < 10:
                return None
            
            likes = reply.get('like', 0)
            
            # Standardized structure: content, likes, replies
            # Note: Bilibili API has reply counts, but we're extracting top-level comments only
            # Setting replies to 0 for consistency (sub-replies would need nested extraction)
            return {
                'content': comment_text,
                'likes': likes,
                'replies': 0
            }
            
        except Exception as e:
            logger.warning(f"[BilibiliComments] Failed to parse comment: {e}")
            return None
    
    def _trans_date(self, timestamp: int) -> str:
        """
        Convert 10-digit timestamp to readable date string.
        
        Args:
            timestamp: 10-digit Unix timestamp
            
        Returns:
            Date string in format "YYYY-MM-DD HH:MM:SS"
        """
        try:
            time_array = time.localtime(timestamp)
            return time.strftime("%Y-%m-%d %H:%M:%S", time_array)
        except Exception as e:
            logger.warning(f"[BilibiliComments] Failed to convert timestamp {timestamp}: {e}")
            return str(timestamp)
    
    def _format_comments_as_text(self, comments: List[Dict]) -> str:
        """
        Format comments list as readable text.
        
        Args:
            comments: List of comment dictionaries
            
        Returns:
            Formatted text string
        """
        lines = []
        
        for i, comment in enumerate(comments, 1):
            content = comment.get('content', '')
            likes = comment.get('likes', 0)
            
            # Format: [1] | ♥ Likes
            # [Comment content here]
            header = f"[{i}]"
            if likes > 0:
                header += f" | ♥ {likes}"
            
            lines.append(header)
            lines.append(content)
            lines.append("")  # Empty line between comments
        
        return '\n'.join(lines)
    
    def _error_result(self, url: str, error: str, bv_id: Optional[str] = None, batch_id: str = None, link_id: str = None) -> Dict:
        """Create error result dictionary."""
        return {
            'success': False,
            'bv_id': bv_id or 'unknown',
            'comments': [],
            'total_comments': 0,
            'extraction_timestamp': datetime.now().isoformat(),
            'batch_id': batch_id,
            'link_id': link_id,
            'error': error
        }


# Import find_project_root for path resolution
from core.config import find_project_root

