"""Quick test: Run a single scraper with progress callback."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.youtube_scraper import YouTubeScraper
from tests.test_links_loader import TestLinksLoader

def test_single_scraper():
    """Test a single scraper with progress callback."""
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('youtube')
    
    if not links:
        print("No YouTube links found, skipping test")
        return
    
    # Track progress
    progress_messages = []
    
    def progress_callback(message):
        progress_messages.append(message)
        stage = message.get('stage', 'unknown')
        progress = message.get('progress', 0)
        msg_text = message.get('message', '')
        print(f"[{stage}] {progress:.1f}%: {msg_text}")
    
    # Create scraper with callback
    print(f"Testing scraper with progress callback...")
    print(f"Batch ID: {batch_id}")
    print(f"Testing link: {links[0]['url']}")
    print()
    
    scraper = YouTubeScraper(progress_callback=progress_callback, headless=True)
    
    # Extract first link
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    scraper.close()
    
    # Verify progress was reported
    print(f"\n{'='*60}")
    print(f"Results: {len(progress_messages)} progress messages received")
    print('='*60)
    
    if len(progress_messages) > 0:
        print("✅ Scraper received and used progress callback!")
        print(f"✅ Success: {result.get('success')}")
    else:
        print("❌ No progress messages received!")
    
    return result

if __name__ == '__main__':
    test_single_scraper()


