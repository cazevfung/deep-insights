"""Test YouTube channel scraper."""
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("="*60)
print("Starting YouTube Channel Scraper Test")
print("="*60)
print(f"Project root: {project_root}")
print(f"Python path: {sys.path[0]}")

try:
    from scrapers.youtube_channel_scraper import YouTubeChannelScraper
    print("✓ Imported YouTubeChannelScraper")
except Exception as e:
    print(f"✗ Failed to import YouTubeChannelScraper: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from backend.app.services.channel_scraper_service import ChannelScraperService
    print("✓ Imported ChannelScraperService")
except Exception as e:
    print(f"✗ Failed to import ChannelScraperService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def test_channel_scraper():
    """Test YouTube channel scraper with a single channel for today's videos."""
    
    print("\n" + "="*60)
    print("Testing YouTube Channel Scraper")
    print("="*60)
    
    # Use ABC News channel (likely to have videos today)
    test_channel_id = "UCBi2mrWuNuyYy4gbM6fU18Q"  # ABC News
    test_channel_name = "ABC News"
    
    # Get today's date
    today = datetime.now().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    print(f"\nChannel: {test_channel_name}")
    print(f"Channel ID: {test_channel_id}")
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print("\nStarting scrape...\n")
    
    try:
        # Test the scraper directly
        scraper = YouTubeChannelScraper(headless=False)  # Show browser for debugging
        
        video_urls = scraper.scrape_channel_videos(
            channel_id=test_channel_id,
            start_date=start_date,
            end_date=end_date
        )
        
        print("\n" + "="*60)
        print("Scrape Results")
        print("="*60)
        print(f"\nTotal videos found: {len(video_urls)}")
        
        if video_urls:
            print("\nVideo URLs:")
            for i, url in enumerate(video_urls[:10], 1):  # Show first 10
                print(f"  {i}. {url}")
            if len(video_urls) > 10:
                print(f"  ... and {len(video_urls) - 10} more")
        else:
            print("\n⚠️  No videos found for today. This could mean:")
            print("   - The channel hasn't posted today")
            print("   - Date parsing needs adjustment")
            print("   - The scraper needs debugging")
        
        scraper.close()
        
        # Also test the service
        print("\n" + "="*60)
        print("Testing Channel Scraper Service")
        print("="*60)
        
        service = ChannelScraperService()
        result = service.scrape_channels(
            start_date=start_date,
            end_date=end_date,
            channel_ids=[test_channel_id]
        )
        
        print(f"\nService Results:")
        print(f"  Batch ID: {result['batch_id']}")
        print(f"  Total Videos: {result['total_videos']}")
        print(f"  Channels Scraped: {result['channels_scraped']}")
        print(f"  Batch File: {result['batch_file']}")
        print(f"  Metadata File: {result['metadata_file']}")
        
        # Read and display batch file
        batch_file = Path(result['batch_file'])
        if batch_file.exists():
            print(f"\nBatch file contents (first 5 lines):")
            with open(batch_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:5], 1):
                    print(f"  {i}. {line.strip()}")
                if len(lines) > 5:
                    print(f"  ... and {len(lines) - 5} more lines")
        
        print("\n" + "="*60)
        print("Test Complete")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_channel_scraper()
    sys.exit(0 if success else 1)

