"""Base scraper class for all content extractors."""
import time
import subprocess
import socket
import sys
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional, Callable
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from core.config import Config, find_project_root

class BaseScraper(ABC):
    """Abstract base class for all content scrapers."""
    
    def __init__(self, config: Optional[Config] = None, **kwargs):
        """
        Initialize base scraper.
        
        Args:
            config: Configuration object
            **kwargs: Additional scraper-specific parameters
        """
        self.config = config or Config()
        self.scraper_type = self.__class__.__name__.lower().replace('scraper', '')
        self.scraper_config = self.config.get_scraper_config(self.scraper_type)
        
        # Browser settings
        self.headless = kwargs.get('headless', self.scraper_config.get('headless', True))
        self.timeout = kwargs.get('timeout', self.scraper_config.get('timeout', 30000))
        self.num_workers = kwargs.get('num_workers', self.scraper_config.get('num_workers', 3))
        self.proxy_config = self.config.get_browser_proxy_config()
        
        # Progress callback for tracking downloads and loading
        self.progress_callback: Optional[Callable] = kwargs.get('progress_callback', None)
        self.cancellation_checker: Optional[Callable[[], bool]] = kwargs.get('cancellation_checker')
        
        # Current extraction context (set during extract() call)
        self._current_batch_id: Optional[str] = None
        self._current_link_id: Optional[str] = None
        self._current_url: Optional[str] = None
        self._cancelled: bool = False
        
        # Browser resources (lazy initialization)
        self._playwright = None
        self._browser = None
        self._context = None
    
    def _check_chrome_running(self, port: int = 9222) -> bool:
        """
        Check if Chrome is already running with remote debugging.
        
        Args:
            port: Debugging port to check
            
        Returns:
            True if Chrome is running with debugging
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _check_chrome_process_running(self) -> bool:
        """
        Check if any Chrome process is running.
        
        Returns:
            True if Chrome process is found
        """
        try:
            # Check if chrome.exe is running
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq chrome.exe'],
                capture_output=True,
                text=True,
                shell=True
            )
            return 'chrome.exe' in result.stdout
        except Exception:
            return False
    
    def _start_chrome_with_debugging(self, port: int = 9222) -> bool:
        """
        Start Chrome with remote debugging enabled.
        
        Args:
            port: Port to enable debugging on
            
        Returns:
            True if Chrome started successfully
        """
        try:
            logger.info(f"[{self.scraper_type}] Starting Chrome with remote debugging on port {port}...")
            
            # Try to find Chrome in common locations
            chrome_paths = [
                Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                Path('C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'),
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if path.exists():
                    chrome_path = path
                    break
            
            if not chrome_path:
                logger.error(f"[{self.scraper_type}] Chrome executable not found in any location")
                return False
            
            logger.info(f"[{self.scraper_type}] Found Chrome at: {chrome_path}")
            
            # Use the user's existing Chrome profile to maintain logged-in sessions
            # Get the Chrome User Data directory from the user's profile
            user_data_dir = Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data'
            
            logger.info(f"[{self.scraper_type}] Using existing Chrome profile: {user_data_dir}")
            logger.info(f"[{self.scraper_type}] This will use your logged-in sessions and cookies")
            
            # Start Chrome with debugging enabled using the existing profile
            logger.info(f"[{self.scraper_type}] Launching Chrome with your logged-in session...")
            process = subprocess.Popen(
                [
                    str(chrome_path),
                    f'--remote-debugging-port={port}',
                    f'--user-data-dir={user_data_dir}',
                    '--disable-blink-features=AutomationControlled'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info(f"[{self.scraper_type}] Chrome process started with PID: {process.pid}")
            
            # Wait for Chrome to start and bind to the debugging port
            logger.info(f"[{self.scraper_type}] Waiting for Chrome to start (checking port {port})...")
            for i in range(15):  # Wait up to 15 seconds
                time.sleep(1)
                if self._check_chrome_running(port):
                    logger.info(f"[{self.scraper_type}] Chrome started successfully with debugging on port {port}")
                    return True
                if i % 5 == 0:  # Log every 5 seconds
                    logger.info(f"[{self.scraper_type}] Still waiting for Chrome... ({i+1}/15)")
            
            logger.warning(f"[{self.scraper_type}] Chrome may not have started properly")
            return False
            
        except Exception as e:
            logger.error(f"[{self.scraper_type}] Failed to start Chrome: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _init_playwright(self):
        """Initialize Playwright browser (lazy loading)."""
        if self._browser:
            return
        
        try:
            # Check if we should connect to existing browser
            connect_to_existing = self.config.get('browser.connect_to_existing_browser', False)
            
            logger.info(f"[{self.scraper_type}] Initializing Playwright...")
            self._playwright = sync_playwright().start()
            
            if connect_to_existing:
                # Connect to existing Chrome browser (uses your normal Chrome profile)
                cdp_url = self.config.get('browser.browser_cdp_url', 'http://localhost:9222')
                
                # Extract port from URL
                port_match = re.search(r':(\d+)', cdp_url)
                port = int(port_match.group(1)) if port_match else 9222
                
                logger.info(f"[{self.scraper_type}] Checking if Chrome is running on port {port}...")
                
                # Check if Chrome is already running with debugging
                if not self._check_chrome_running(port):
                    # Check if Chrome is running but without debugging
                    if self._check_chrome_process_running():
                        logger.error(f"[{self.scraper_type}] Chrome is running but does NOT have debugging enabled!")
                        logger.error(f"[{self.scraper_type}] Strict mode: Not falling back to a new browser instance.")
                        logger.error(f"[{self.scraper_type}] Close all Chrome windows, then rerun the scraper, or manually start Chrome with --remote-debugging-port={port}.")
                        raise RuntimeError("Chrome running without debugging; strict mode prohibits fallback.")
                    
                    # No Chrome running at all - start it with the user's profile
                    logger.info(f"[{self.scraper_type}] No Chrome running. Starting with YOUR profile...")
                    if not self._start_chrome_with_debugging(port):
                        logger.error(f"[{self.scraper_type}] Failed to start Chrome automatically in strict mode")
                        raise RuntimeError("Failed to start Chrome with debugging; strict mode prohibits fallback.")
                
                logger.info(f"[{self.scraper_type}] Connecting to existing browser at {cdp_url}")
                
                try:
                    self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
                    logger.info(f"[{self.scraper_type}] Successfully connected to existing browser")
                    if self.proxy_config.get('enabled'):
                        logger.info(f"[{self.scraper_type}] Proxy configuration ignored because an existing browser is being used")
                except Exception as e:
                    logger.error(f"[{self.scraper_type}] Failed to connect to existing browser in strict mode: {e}")
                    raise
            else:
                # Launch new browser instance (default behavior)
                # headless=True hides the browser window by default
                chrome_args = ['--disable-blink-features=AutomationControlled']
                if self.headless:
                    # Additional args for optimal headless mode performance
                    chrome_args.append('--disable-gpu')
                proxy_settings = None
                if self.proxy_config.get('enabled'):
                    proxy_settings = {
                        'server': self.proxy_config['server']
                    }
                    if self.proxy_config.get('username'):
                        proxy_settings['username'] = self.proxy_config['username']
                    if self.proxy_config.get('password'):
                        proxy_settings['password'] = self.proxy_config['password']
                    if self.proxy_config.get('bypass'):
                        proxy_settings['bypass'] = ",".join(self.proxy_config['bypass'])
                    logger.info(f"[{self.scraper_type}] Launching browser with proxy {self.proxy_config['server']}")
                elif self.proxy_config.get('server'):
                    logger.warning(f"[{self.scraper_type}] Proxy server configured but disabled; set browser.proxy.enabled to true to use it")
                self._browser = self._playwright.chromium.launch(
                    headless=self.headless,
                    args=chrome_args,
                    proxy=proxy_settings
                )
                logger.debug(f"[{self.scraper_type}] New browser instance launched")
            
            logger.debug(f"[{self.scraper_type}] Browser initialized")
        except Exception as e:
            logger.error(f"[{self.scraper_type}] Failed to initialize browser: {e}")
            raise
    
    def _create_context(self) -> BrowserContext:
        """
        Create a new browser context.
        
        Returns:
            Browser context
        """
        if not self._browser:
            self._init_playwright()
        
        # Check if we're using an existing browser
        connect_to_existing = self.config.get('browser.connect_to_existing_browser', False)
        
        if connect_to_existing:
            # When connected to existing browser, use the existing context
            # or create a new one with minimal changes to respect the user's session
            contexts = self._browser.contexts
            if contexts:
                logger.info(f"[{self.scraper_type}] Using existing browser context")
                return contexts[0]
            else:
                # No existing context, create one with minimal overrides
                return self._browser.new_context()
        else:
            # Normal mode: create context with custom settings
            return self._browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
    
    def _clean_content(self, content: str) -> str:
        """
        Basic content cleaning.
        
        Args:
            content: Raw content
        
        Returns:
            Cleaned content
        """
        if not content:
            return ''
        
        # Remove extra whitespace
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        cleaned = '\n'.join(lines)
        
        # Remove multiple spaces
        while '  ' in cleaned:
            cleaned = cleaned.replace('  ', ' ')
        
        return cleaned.strip()
    
    def _set_extraction_context(self, batch_id: Optional[str], link_id: Optional[str], url: str):
        """
        Set current extraction context for progress reporting.
        
        Args:
            batch_id: Batch ID for this extraction
            link_id: Link ID for this extraction
            url: URL being extracted
        """
        self._current_batch_id = batch_id
        self._current_link_id = link_id
        self._current_url = url
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extract video ID from URL.
        
        Args:
            url: Video URL
            
        Returns:
            Video ID
        """
        # Implement in subclasses if needed
        return url
    
    def _report_progress(self, stage: str, progress: float, message: str = "", 
                         bytes_downloaded: int = 0, total_bytes: int = 0):
        """
        Report progress to callback if available.
        
        Args:
            stage: Current stage (e.g., 'downloading', 'uploading', 'transcribing')
            progress: Progress percentage (0.0 to 100.0)
            message: Optional status message
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total bytes to download
        """
        if self.progress_callback:
            try:
                self.progress_callback({
                    'stage': stage,
                    'progress': progress,
                    'message': message,
                    'bytes_downloaded': bytes_downloaded,
                    'total_bytes': total_bytes,
                    'scraper': self.scraper_type,
                    # Include current extraction context if available
                    'batch_id': self._current_batch_id,
                    'link_id': self._current_link_id,
                    'url': self._current_url,
                })
            except Exception as e:
                logger.warning(f"[{self.scraper_type}] Progress callback failed: {e}")
    
    def _check_cancelled(self) -> bool:
        """
        Check whether the current scraping operation has been cancelled.
        
        Returns:
            True if a cancellation request has been detected.
        """
        if self._cancelled:
            return True
        
        if not self.cancellation_checker:
            return False
        
        try:
            cancelled = bool(self.cancellation_checker())
        except Exception as e:
            logger.warning(f"[{self.scraper_type}] Cancellation checker failed: {e}")
            return False
        
        if cancelled:
            logger.info(f"[{self.scraper_type}] Cancellation flag detected")
            self._cancelled = True
        return cancelled
    
    def _error_result(
        self,
        url: str,
        error: str,
        batch_id: Optional[str] = None,
        link_id: Optional[str] = None,
        **extra_fields
    ) -> Dict:
        """
        Build a standardized error result payload.
        
        Args:
            url: URL that failed to scrape
            error: Error message
            batch_id: Optional batch identifier
            link_id: Optional link identifier
            **extra_fields: Additional fields to merge into result
        
        Returns:
            Dictionary representing an error result
        """
        source_name = getattr(self, 'source_name', None)
        if not source_name:
            # Remove trailing "scraper" and title-case for readability
            base_name = self.__class__.__name__.replace('Scraper', '')
            source_name = base_name or self.__class__.__name__
        
        result = {
            'success': False,
            'url': url,
            'content': None,
            'title': '',
            'author': '',
            'publish_date': '',
            'source': source_name,
            'language': '',
            'word_count': 0,
            'extraction_method': self.scraper_type,
            'extraction_timestamp': datetime.now().isoformat(),
            'batch_id': batch_id,
            'link_id': link_id,
            'error': error
        }
        if extra_fields:
            result.update(extra_fields)
        return result
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Check if URL is valid for this scraper.
        
        Args:
            url: URL to validate
        
        Returns:
            True if valid, False otherwise
        """
        raise NotImplementedError
    
    @abstractmethod
    def extract(self, url: str) -> Dict:
        """
        Extract content from URL.
        
        Args:
            url: URL to extract from
        
        Returns:
            Dictionary with extraction results:
            {
                'success': bool,
                'url': str,
                'content': str or None,
                'title': str,
                'author': str,
                'publish_date': str,
                'source': str,
                'language': str,
                'word_count': int,
                'extraction_method': str,
                'extraction_timestamp': str,
                'error': str or None
            }
        """
        raise NotImplementedError
    
    def close(self, force_kill: bool = False):
        """Cleanup browser resources."""
        try:
            # Check if we're using an existing browser
            connect_to_existing = self.config.get('browser.connect_to_existing_browser', False)
            
            if self._context:
                try:
                    self._context.close()
                except Exception as ctx_err:
                    logger.warning(f"[{self.scraper_type}] Failed to close context: {ctx_err}")
                finally:
                    self._context = None
            
            if self._browser:
                try:
                    if connect_to_existing and not force_kill:
                        # Don't close the shared browser instance, just disconnect
                        logger.info(f"[{self.scraper_type}] Disconnecting from existing browser")
                        self._browser.close()
                    else:
                        # Close the browser we launched or force close when requested
                        logger.info(f"[{self.scraper_type}] Closing browser (force_kill={force_kill})")
                        self._browser.close()
                except Exception as browser_err:
                    logger.warning(f"[{self.scraper_type}] Failed to close browser: {browser_err}")
                finally:
                    self._browser = None
            
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception as pw_err:
                    logger.warning(f"[{self.scraper_type}] Failed to stop Playwright: {pw_err}")
                finally:
                    self._playwright = None
            
            self._cancelled = False
            logger.info(f"[{self.scraper_type}] Browser session closed successfully")
        except Exception as e:
            logger.error(f"[{self.scraper_type}] Error closing browser: {e}")

