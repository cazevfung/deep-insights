"""Configuration management for the research tool."""
import yaml
from pathlib import Path
from typing import Any, Optional

def find_project_root(start_path: Path = None) -> Path:
    """Find the project root directory."""
    if start_path is None:
        start_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for project root markers
    current = start_path if start_path.is_dir() else start_path.parent
    
    while current.parent != current:
        # Check for common project root markers
        if (current / 'config.yaml').exists():
            return current
        if (current / 'README.md').exists() and (current / 'scrapers').exists():
            return current
        current = current.parent
    
    # If no marker found, return current path
    return start_path.parent

class Config:
    """Load and manage configuration from YAML file."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration."""
        # If path is relative, find it relative to project root
        if not Path(config_path).is_absolute():
            project_root = find_project_root()
            config_path = project_root / config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, key_path: str, default: Optional[Any] = None) -> Any:
        """
        Get config value using dot notation.
        
        Args:
            key_path: Dot-separated key path (e.g., 'scrapers.youtube.timeout')
            default: Default value if not found
        
        Returns:
            Config value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if value is None:
                return default
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        
        return value

    def get_int(self, key_path: str, default: int) -> int:
        """Get an int value with fallback."""
        try:
            val = self.get(key_path, default)
            return int(val) if val is not None else int(default)
        except Exception:
            return int(default)

    def get_bool(self, key_path: str, default: bool) -> bool:
        """Get a boolean value with common string conversions."""
        try:
            val = self.get(key_path, default)
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:
            return bool(default)
    
    def get_scraper_config(self, scraper_type: str) -> dict:
        """
        Get scraper-specific configuration.
        
        Args:
            scraper_type: Type of scraper ('youtube', 'bilibili', 'article')
        
        Returns:
            Configuration dict for the scraper
        """
        return self.config.get('scrapers', {}).get(scraper_type, {})
    
    def get_backend_config(self) -> dict:
        """
        Get backend server configuration.
        
        Returns:
            Configuration dict with host, port, reload, and reload_dirs
        """
        return {
            'host': self.get('servers.backend.host', '0.0.0.0'),
            'port': self.get_int('servers.backend.port', 3001),
            'reload': self.get_bool('servers.backend.reload', True),
            'reload_dirs': self.get('servers.backend.reload_dirs', ['backend/app']),
        }
    
    def get_frontend_config(self) -> dict:
        """
        Get frontend server configuration.
        
        Returns:
            Configuration dict with host, port, proxy_timeout, and proxy_target
        """
        backend_port = self.get_int('servers.backend.port', 3001)
        return {
            'host': self.get('servers.frontend.host', '0.0.0.0'),
            'port': self.get_int('servers.frontend.port', 3000),
            'proxy_timeout': self.get_int('servers.frontend.proxy_timeout', 10000),
            'proxy_target': self.get('servers.frontend.proxy_target', f'http://localhost:{backend_port}'),
        }
    
    def get_cors_config(self) -> dict:
        """
        Get CORS configuration.
        
        Returns:
            Configuration dict with allowed_origins, allow_credentials, allow_methods, and allow_headers
        """
        backend_port = self.get_int('servers.backend.port', 3001)
        frontend_port = self.get_int('servers.frontend.port', 3000)
        
        # Build default origins if not specified
        default_origins = [
            f'http://localhost:{frontend_port}',
            f'http://127.0.0.1:{frontend_port}',
            f'http://localhost:{backend_port}',
            f'http://127.0.0.1:{backend_port}',
        ]
        
        return {
            'allowed_origins': self.get('servers.cors.allowed_origins', default_origins),
            'allow_credentials': self.get_bool('servers.cors.allow_credentials', True),
            'allow_methods': self.get('servers.cors.allow_methods', ['*']),
            'allow_headers': self.get('servers.cors.allow_headers', ['*']),
        }

    def get_browser_proxy_config(self) -> dict:
        """
        Get browser proxy configuration.

        Returns:
            Dict containing proxy settings suitable for Playwright
        """
        enabled = self.get('browser.proxy.enabled', False)
        server = self.get('browser.proxy.server', '')
        username = self.get('browser.proxy.username', '')
        password = self.get('browser.proxy.password', '')
        bypass = self.get('browser.proxy.bypass', [])

        # Normalise inputs
        server = (server or '').strip()
        username = (username or '').strip()
        password = (password or '').strip()

        if isinstance(bypass, str):
            bypass_list = [bypass.strip()] if bypass.strip() else []
        elif isinstance(bypass, list):
            bypass_list = [str(item).strip() for item in bypass if str(item).strip()]
        else:
            bypass_list = []

        return {
            'enabled': bool(enabled) and bool(server),
            'server': server,
            'username': username,
            'password': password,
            'bypass': bypass_list,
        }
    
    def get_batches_dir(self) -> Path:
        """
        Get batches directory path where batch run directories are stored.
        
        Returns:
            Path object pointing to batches directory
        """
        project_root = find_project_root()
        batches_dir = self.get('storage.paths.batches_dir', 'data/research/batches')
        return project_root / batches_dir
    
    def get_reports_dir(self) -> Path:
        """
        Get reports directory path where research reports are stored.
        
        Returns:
            Path object pointing to reports directory
        """
        project_root = find_project_root()
        reports_dir = self.get('storage.paths.reports_dir', 'data/research/reports')
        return project_root / reports_dir

