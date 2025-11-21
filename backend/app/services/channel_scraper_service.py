"""
Channel scraper service for scraping video links from YouTube channels.
"""
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from scrapers.youtube_channel_scraper import YouTubeChannelScraper


class ChannelScraperService:
    """Service for scraping video links from YouTube channels."""
    
    def __init__(self):
        """Initialize channel scraper service."""
        self.config = Config()
        
        # Read paths from config (with defaults as fallback)
        batches_dir = self.config.get('channel_scraper.paths.batches_dir', 'data/channel_scrapes/batches')
        metadata_dir = self.config.get('channel_scraper.paths.metadata_dir', 'data/channel_scrapes/metadata')
        channels_file = self.config.get('channel_scraper.channels_file', 'data/news/channels')
        
        # Convert to Path objects relative to project root
        self.batches_dir = project_root / batches_dir
        self.metadata_dir = project_root / metadata_dir
        self.channels_file = project_root / channels_file
        
        # Ensure directories exist
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Get delay configuration
        channel_config = self.config.get('channel_scraper', {})
        self.channel_delay_min = channel_config.get('channel_delay_min', 0.0)
        self.channel_delay_max = channel_config.get('channel_delay_max', 2.0)
        
        logger.info(
            f"[ChannelScraper] Initialized: batches_dir={self.batches_dir}, "
            f"metadata_dir={self.metadata_dir}, channels_file={self.channels_file}"
        )
    
    def load_channels(self) -> List[Dict]:
        """
        Load channels from the channels file.
        
        Returns:
            List of channel dictionaries (only active channels)
        """
        try:
            if not self.channels_file.exists():
                logger.error(f"[ChannelScraper] Channels file not found: {self.channels_file}")
                return []
            
            # Check file size first
            file_size = self.channels_file.stat().st_size
            if file_size == 0:
                logger.error(f"[ChannelScraper] Channels file is empty: {self.channels_file}")
                return []
            
            with open(self.channels_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logger.error(f"[ChannelScraper] Channels file has no content: {self.channels_file}")
                    return []
                
                channels = json.loads(content)
            
            # Filter active channels
            active_channels = [ch for ch in channels if ch.get('active', True)]
            logger.info(f"[ChannelScraper] Loaded {len(active_channels)} active channels from {len(channels)} total")
            
            return active_channels
            
        except json.JSONDecodeError as e:
            logger.error(f"[ChannelScraper] Invalid JSON in channels file: {e}")
            logger.error(f"[ChannelScraper] File path: {self.channels_file}")
            logger.error(f"[ChannelScraper] File size: {file_size if 'file_size' in locals() else 'unknown'} bytes")
            # Try to show first 200 chars for debugging
            try:
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    preview = f.read(200)
                    logger.error(f"[ChannelScraper] File preview: {preview}")
            except:
                pass
            return []
        except Exception as e:
            logger.error(f"[ChannelScraper] Error loading channels: {e}", exc_info=True)
            return []
    
    def scrape_channels(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel_ids: Optional[List[str]] = None,
        batch_id: Optional[str] = None
    ) -> Dict:
        """
        Scrape video links from channels.
        
        Args:
            start_date: Optional start date for filtering videos
            end_date: Optional end date for filtering videos
            channel_ids: Optional list of channel IDs to filter (if None, scrape all active channels)
            
        Returns:
            Dictionary with batch_id, total_videos, and channel results
        """
        # Load channels
        channels = self.load_channels()
        
        # If loading failed but channel_ids provided, create minimal channel objects
        if not channels and channel_ids:
            logger.warning("[ChannelScraper] Could not load channels file, creating from provided IDs")
            channels = []
            for cid in channel_ids:
                # Try to find channel info from test data or create minimal entry
                channel = {
                    "id": cid,
                    "channelId": cid,
                    "active": True,
                    "name": f"Channel {cid}",
                    "link": f"https://www.youtube.com/channel/{cid}"
                }
                channels.append(channel)
            logger.info(f"[ChannelScraper] Created {len(channels)} channel entries from provided IDs")
        
        if not channels:
            raise ValueError("No active channels found")
        
        # Filter by channel_ids if provided
        if channel_ids:
            channels = [ch for ch in channels if ch.get('channelId') in channel_ids or ch.get('id') in channel_ids]
            logger.info(f"[ChannelScraper] Filtered to {len(channels)} channels by IDs")
        
        # Generate batch ID if not provided
        if not batch_id:
            batch_id = self.generate_batch_id()
        
        logger.info(
            f"[ChannelScraper] Starting scrape: batch_id={batch_id}, "
            f"channels={len(channels)}, date_range={start_date} to {end_date}"
        )
        
        # Scrape each channel
        all_video_urls = []
        channel_results = []
        
        for i, channel in enumerate(channels, 1):
            channel_id = channel.get('channelId') or channel.get('id')
            channel_name = channel.get('name', 'Unknown')
            
            logger.info(f"[ChannelScraper] [{i}/{len(channels)}] Scraping channel: {channel_name} ({channel_id})")
            
            try:
                # Create scraper with headless=False to show browser window
                scraper = YouTubeChannelScraper(headless=False)
                logger.info(f"[ChannelScraper] Created YouTubeChannelScraper (headless=False) for {channel_name}")
                
                # Scrape videos - this will open Playwright browser window
                logger.info(f"[ChannelScraper] Starting video scraping for channel {channel_id}...")
                video_urls = scraper.scrape_channel_videos(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date
                )
                logger.info(f"[ChannelScraper] Scraped {len(video_urls)} videos from {channel_name}")
                
                all_video_urls.extend(video_urls)
                
                channel_results.append({
                    'name': channel_name,
                    'channelId': channel_id,
                    'handle': channel.get('handle'),
                    'videos_found': len(video_urls),
                    'status': 'success',
                    'error': None
                })
                
                logger.info(
                    f"[ChannelScraper] Channel {channel_name}: found {len(video_urls)} videos "
                    f"(total so far: {len(all_video_urls)})"
                )
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ChannelScraper] Error scraping channel {channel_name}: {error_msg}", exc_info=True)
                
                channel_results.append({
                    'name': channel_name,
                    'channelId': channel_id,
                    'handle': channel.get('handle'),
                    'videos_found': 0,
                    'status': 'failed',
                    'error': error_msg
                })
            
            finally:
                # Random delay between channels
                if i < len(channels):  # Don't delay after last channel
                    delay = random.uniform(self.channel_delay_min, self.channel_delay_max)
                    time.sleep(delay)
        
        # Save batch file
        batch_file_path, metadata_file_path = self.save_batch_file(
            batch_id=batch_id,
            links=all_video_urls,
            metadata={
                'batch_id': batch_id,
                'timestamp': datetime.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                },
                'channels_scraped': len(channels),
                'total_videos': len(all_video_urls),
                'channels': channel_results,
                'errors': [
                    {
                        'channel': ch['name'],
                        'error': ch['error']
                    }
                    for ch in channel_results if ch['status'] == 'failed'
                ]
            }
        )
        
        logger.info(
            f"[ChannelScraper] Scrape complete: batch_id={batch_id}, "
            f"total_videos={len(all_video_urls)}, saved to {batch_file_path}"
        )
        
        return {
            'batch_id': batch_id,
            'total_videos': len(all_video_urls),
            'channels_scraped': len(channels),
            'batch_file': str(batch_file_path),
            'metadata_file': str(metadata_file_path)
        }
    
    def generate_batch_id(self) -> str:
        """
        Generate a new batch ID.
        
        Returns:
            Batch ID in format: batch_{number:03d}_{timestamp}
        """
        next_number = self._get_next_batch_number()
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        return f"batch_{next_number:03d}_{timestamp}"
    
    def _get_next_batch_number(self) -> int:
        """
        Get the next batch number by scanning existing batch files.
        
        Returns:
            Next batch number
        """
        if not self.batches_dir.exists():
            return 1
        
        max_number = 0
        for file in self.batches_dir.glob('batch_*.txt'):
            # Extract number from filename like "batch_001_2025-01-20_14-30-00.txt"
            try:
                parts = file.stem.split('_')
                if len(parts) >= 2 and parts[0] == 'batch':
                    number = int(parts[1])
                    max_number = max(max_number, number)
            except (ValueError, IndexError):
                continue
        
        return max_number + 1
    
    def save_batch_file(
        self,
        batch_id: str,
        links: List[str],
        metadata: Dict
    ) -> tuple[Path, Path]:
        """
        Save batch file and metadata.
        
        Args:
            batch_id: Batch ID
            links: List of video URLs
            metadata: Metadata dictionary
            
        Returns:
            Tuple of (batch_file_path, metadata_file_path)
        """
        # Save links file
        batch_file = self.batches_dir / f"{batch_id}.txt"
        with open(batch_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Batch: {batch_id}\n")
            f.write(f"# Scraped: {metadata.get('timestamp', datetime.now().isoformat())}\n")
            
            date_range = metadata.get('date_range', {})
            if date_range.get('start') or date_range.get('end'):
                f.write(f"# Date Range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}\n")
            
            f.write(f"# Total Videos: {len(links)}\n")
            f.write("\n")
            
            # Write links
            for link in links:
                f.write(f"{link}\n")
        
        # Save metadata file
        metadata_file = self.metadata_dir / f"{batch_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[ChannelScraper] Saved batch file: {batch_file}, metadata: {metadata_file}")
        
        return batch_file, metadata_file
    
    def get_batch_metadata(self, batch_id: str) -> Optional[Dict]:
        """
        Get metadata for a batch.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_file = self.metadata_dir / f"{batch_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ChannelScraper] Error loading metadata for {batch_id}: {e}")
            return None
    
    def list_batches(self) -> List[Dict]:
        """
        List all batches.
        
        Returns:
            List of batch metadata dictionaries
        """
        batches = []
        
        if not self.metadata_dir.exists():
            return batches
        
        for metadata_file in self.metadata_dir.glob('batch_*.json'):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    batches.append({
                        'batch_id': metadata.get('batch_id'),
                        'timestamp': metadata.get('timestamp'),
                        'date_range': metadata.get('date_range'),
                        'total_videos': metadata.get('total_videos', 0),
                        'channels_scraped': metadata.get('channels_scraped', 0)
                    })
            except Exception as e:
                logger.warning(f"[ChannelScraper] Error loading batch metadata {metadata_file}: {e}")
        
        # Sort by timestamp (newest first)
        batches.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return batches

