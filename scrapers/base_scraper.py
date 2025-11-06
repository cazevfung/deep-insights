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
        
        # Progress callback for tracking downloads and loading
        self.progress_callback: Optional[Callable] = kwargs.get('progress_callback', None)
        
        # Cancellation checker callback - returns True if cancelled
        self.cancellation_checker: Optional[Callable[[], bool]] = kwargs.get('cancellation_checker', None)
        
        # Current extraction context (set during extract() call)
        self._current_batch_id: Optional[str] = None
        self._current_link_id: Optional[str] = None
        self._current_url: Optional[str] = None
        
        # Browser resources (lazy initialization)
        self._playwright = None
        self._browser = None
        self._context = None
        self._browser_process_pid = None  # Track browser process PID for force-killing
    
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
            try:
                # Start Playwright - this should work in any thread context
                self._playwright = sync_playwright().start()
                logger.info(f"[{self.scraper_type}] Playwright started successfully")
            except Exception as playwright_error:
                logger.error(f"[{self.scraper_type}] Failed to start Playwright: {playwright_error}")
                import traceback
                logger.error(f"[{self.scraper_type}] Playwright start traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Failed to start Playwright: {playwright_error}") from playwright_error
            
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
                except Exception as e:
                    logger.error(f"[{self.scraper_type}] Failed to connect to existing browser in strict mode: {e}")
                    raise
            else:
                # Launch new browser instance (default behavior)
                # headless=True hides the browser window by default
                chrome_args = ['--disable-blink-features=AutomationControlled']
                
                # Add args for web server environments (when running from FastAPI/async context)
                # These are needed when Playwright runs from asyncio.to_thread() or web server
                chrome_args.extend([
                    '--no-sandbox',  # Required when running from web server/thread context
                    '--disable-dev-shm-usage',  # Prevents shared memory issues in web server
                    '--disable-setuid-sandbox',  # Additional sandbox bypass for web server
                ])
                
                if self.headless:
                    # Additional args for optimal headless mode performance
                    chrome_args.append('--disable-gpu')
                
                try:
                    logger.info(f"[{self.scraper_type}] Launching Chromium browser (headless={self.headless})...")
                    logger.debug(f"[{self.scraper_type}] Chrome args: {chrome_args}")
                    self._browser = self._playwright.chromium.launch(
                        headless=self.headless,
                        args=chrome_args
                    )
                    logger.info(f"[{self.scraper_type}] Chromium browser launched successfully")
                    logger.debug(f"[{self.scraper_type}] New browser instance launched")
                except Exception as launch_error:
                    logger.error(f"[{self.scraper_type}] Failed to launch Chromium: {launch_error}")
                    import traceback
                    logger.error(f"[{self.scraper_type}] Launch traceback: {traceback.format_exc()}")
                    raise RuntimeError(f"Failed to launch Chromium browser: {launch_error}") from launch_error
            
            logger.debug(f"[{self.scraper_type}] Browser initialized")
        except Exception as e:
            logger.error(f"[{self.scraper_type}] Failed to initialize browser: {e}")
            import traceback
            logger.error(f"[{self.scraper_type}] Traceback: {traceback.format_exc()}")
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
    
    def _check_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.
        
        Returns:
            True if cancelled, False otherwise
        """
        if self.cancellation_checker:
            try:
                return self.cancellation_checker()
            except Exception as e:
                logger.warning(f"[{self.scraper_type}] Cancellation checker failed: {e}")
        return False
    
    def _error_result(self, url: str, error: str, batch_id: str = None, link_id: str = None) -> Dict:
        """
        Create a standardized error result dictionary.
        
        Args:
            url: URL that failed
            error: Error message
            batch_id: Optional batch ID
            link_id: Optional link ID
            
        Returns:
            Error result dictionary
        """
        return {
            'success': False,
            'url': url,
            'content': None,
            'title': '',
            'author': '',
            'publish_date': '',
            'source': self.scraper_type.title(),
            'language': '',
            'word_count': 0,
            'extraction_method': self.scraper_type,
            'extraction_timestamp': datetime.now().isoformat(),
            'batch_id': batch_id,
            'link_id': link_id,
            'error': error
        }
    
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
    
    def _force_kill_browser_processes(self):
        """
        Force kill all Chromium/Chrome browser processes spawned by Playwright.
        This is a more aggressive cleanup method used when cancellation is detected.
        """
        try:
            import platform
            import psutil
            
            # Find and kill all Chromium/Chrome processes
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    cmdline = proc_info.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    
                    # Check if it's a Playwright Chromium process
                    is_playwright_chrome = (
                        ('chromium' in proc_name or 'chrome' in proc_name) and
                        ('playwright' in cmdline_str.lower() or 
                         'ms-playwright' in cmdline_str.lower() or
                         '--remote-debugging-port' in cmdline_str)
                    )
                    
                    if is_playwright_chrome:
                        try:
                            logger.info(f"[{self.scraper_type}] Force killing browser process PID {proc_info['pid']}")
                            proc.kill()
                            killed_count += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                            logger.debug(f"[{self.scraper_type}] Could not kill process {proc_info['pid']}: {e}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if killed_count > 0:
                logger.info(f"[{self.scraper_type}] Force killed {killed_count} browser process(es)")
            
        except ImportError:
            # psutil not available, try using OS-specific commands
            logger.warning(f"[{self.scraper_type}] psutil not available, using OS-specific kill commands")
            try:
                import platform
                if platform.system() == 'Windows':
                    # Windows: Use taskkill to kill Chromium processes
                    subprocess.run(
                        ['taskkill', '/F', '/IM', 'chrome.exe', '/FI', 'WINDOWTITLE eq *playwright*'],
                        capture_output=True,
                        timeout=5
                    )
                    # Also try killing processes with ms-playwright in path
                    subprocess.run(
                        ['taskkill', '/F', '/FI', 'IMAGENAME eq chrome.exe', '/FI', 'COMMANDLINE eq *ms-playwright*'],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    # Linux/Mac: Use pkill
                    subprocess.run(['pkill', '-f', 'playwright.*chromium'], capture_output=True, timeout=5)
            except Exception as e:
                logger.warning(f"[{self.scraper_type}] Could not force kill browser processes: {e}")
        except Exception as e:
            logger.warning(f"[{self.scraper_type}] Error in force kill browser processes: {e}")
    
    def close(self, force_kill=False):
        """
        Cleanup browser resources.
        
        Args:
            force_kill: If True, force kill browser processes at OS level
        """
        try:
            # Force kill browser processes if requested (e.g., on cancellation)
            if force_kill:
                self._force_kill_browser_processes()
            
            # Check if we're using an existing browser
            connect_to_existing = self.config.get('browser.connect_to_existing_browser', False)
            
            if self._context:
                try:
                    self._context.close()
                except Exception as e:
                    logger.warning(f"[{self.scraper_type}] Error closing context: {e}")
            
            if self._browser:
                try:
                    if connect_to_existing:
                        # Don't close the browser when connected to existing instance
                        logger.info(f"[{self.scraper_type}] Disconnecting from browser (browser stays open)")
                        self._browser.close()
                    else:
                        # Close the browser we launched
                        self._browser.close()
                except Exception as e:
                    logger.warning(f"[{self.scraper_type}] Error closing browser: {e}")
            
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception as e:
                    logger.warning(f"[{self.scraper_type}] Error stopping playwright: {e}")
            
            # Force kill again after closing (in case some processes didn't terminate)
            if force_kill:
                import time
                time.sleep(0.5)  # Give processes a moment to terminate
                self._force_kill_browser_processes()
            
            self._browser = None
            self._context = None
            self._playwright = None
            self._browser_process_pid = None
            logger.info(f"[{self.scraper_type}] Browser session closed successfully")
        except Exception as e:
            logger.error(f"[{self.scraper_type}] Error closing browser: {e}")

