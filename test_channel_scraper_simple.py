"""Simple test for YouTube channel scraper."""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*60)
print("Testing YouTube Channel Scraper")
print("="*60)

try:
    from scrapers.youtube_channel_scraper import YouTubeChannelScraper
    print("✓ Imported scraper")
    
    # Test with ABC News channel
    channel_id = "UCBi2mrWuNuyYy4gbM6fU18Q"
    today = datetime.now().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    print(f"\nChannel: ABC News ({channel_id})")
    print(f"Date: {today}")
    print("\nStarting scrape (this may take a minute)...\n")
    
    scraper = YouTubeChannelScraper(headless=False)
    video_urls = scraper.scrape_channel_videos(
        channel_id=channel_id,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"\n{'='*60}")
    print(f"Results: Found {len(video_urls)} videos")
    print(f"{'='*60}")
    
    if video_urls:
        print("\nVideo URLs:")
        for i, url in enumerate(video_urls[:5], 1):
            print(f"  {i}. {url}")
        if len(video_urls) > 5:
            print(f"  ... and {len(video_urls) - 5} more")
    else:
        print("\n⚠️  No videos found for today")
    
    scraper.close()
    print("\n✓ Test complete")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

