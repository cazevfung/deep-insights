"""Test script to demonstrate progress tracking in scrapers."""

from scrapers.bilibili_scraper import BilibiliScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.article_scraper import ArticleScraper
from tests.test_links_loader import TestLinksLoader

def progress_callback(data):
    """
    Callback function to receive progress updates.
    
    Args:
        data: Dictionary containing:
            - stage: Current operation stage (e.g., 'downloading', 'uploading')
            - progress: Progress percentage (0.0 to 100.0)
            - message: Status message
            - bytes_downloaded: Bytes downloaded so far (if applicable)
            - total_bytes: Total bytes to download (if applicable)
            - scraper: Type of scraper
    """
    stage = data.get('stage', 'unknown')
    progress = data.get('progress', 0)
    message = data.get('message', '')
    bytes_downloaded = data.get('bytes_downloaded', 0)
    total_bytes = data.get('total_bytes', 0)
    scraper = data.get('scraper', 'unknown')
    
    # Format progress bar
    bar_length = 30
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    # Print progress
    if bytes_downloaded and total_bytes:
        mb_downloaded = bytes_downloaded / (1024 * 1024)
        mb_total = total_bytes / (1024 * 1024)
        print(f"[{scraper}] [{stage:12s}] [{bar}] {progress:5.1f}% | {message} ({mb_downloaded:.2f} MB / {mb_total:.2f} MB)")
    else:
        print(f"[{scraper}] [{stage:12s}] [{bar}] {progress:5.1f}% | {message}")


def test_reddit_scraper():
    """Test Reddit scraper with progress tracking."""
    print("\n=== Testing Reddit Scraper with Progress Tracking ===\n")
    
    scraper = RedditScraper(progress_callback=progress_callback)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('reddit')
    if not links:
        print("No reddit links found; skipping.")
        return
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    print(f"\nResult: {'✓ Success' if result['success'] else '✗ Failed'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    if result.get('word_count'):
        print(f"Word count: {result['word_count']}")
    
    scraper.close()


def test_youtube_scraper():
    """Test YouTube scraper with progress tracking."""
    print("\n=== Testing YouTube Scraper with Progress Tracking ===\n")
    
    scraper = YouTubeScraper(progress_callback=progress_callback)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('youtube')
    if not links:
        print("No youtube links found; skipping.")
        return
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    print(f"\nResult: {'✓ Success' if result['success'] else '✗ Failed'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    if result.get('word_count'):
        print(f"Word count: {result['word_count']}")
    
    scraper.close()


def test_article_scraper():
    """Test Article scraper with progress tracking."""
    print("\n=== Testing Article Scraper with Progress Tracking ===\n")
    
    scraper = ArticleScraper(progress_callback=progress_callback)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('article')
    if not links:
        print("No article links found; skipping.")
        return
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    print(f"\nResult: {'✓ Success' if result['success'] else '✗ Failed'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    if result.get('word_count'):
        print(f"Word count: {result['word_count']}")
    
    scraper.close()


def test_bilibili_scraper():
    """Test Bilibili scraper with progress tracking."""
    print("\n=== Testing Bilibili Scraper with Progress Tracking ===\n")
    
    scraper = BilibiliScraper(progress_callback=progress_callback)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    links = loader.get_links('bilibili')
    if not links:
        print("No bilibili links found; skipping.")
        return
    link = links[0]
    result = scraper.extract(link['url'], batch_id=batch_id, link_id=link['id'])
    
    print(f"\nResult: {'✓ Success' if result['success'] else '✗ Failed'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    if result.get('word_count'):
        print(f"Word count: {result['word_count']}")
    
    scraper.close()


if __name__ == "__main__":
    import sys
    
    print("Progress Tracking Test")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        scraper_type = sys.argv[1].lower()
        
        if scraper_type == 'reddit':
            test_reddit_scraper()
        elif scraper_type == 'youtube':
            test_youtube_scraper()
        elif scraper_type == 'article':
            test_article_scraper()
        elif scraper_type == 'bilibili':
            test_bilibili_scraper()
        else:
            print(f"Unknown scraper type: {scraper_type}")
            print("Usage: python test_progress_tracking.py [reddit|youtube|article|bilibili]")
    else:
        print("Usage: python test_progress_tracking.py [reddit|youtube|article|bilibili]")
        print("\nThis script demonstrates the progress tracking feature.")
        print("\nExample:")
        print("  python test_progress_tracking.py reddit")
        print("\nEach scraper will show progress updates as it:")
        print("  - Loads pages")
        print("  - Extracts content")
        print("  - Downloads files (with byte-level tracking)")
        print("  - Processes data")

