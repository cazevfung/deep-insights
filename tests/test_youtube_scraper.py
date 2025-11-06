"""Test YouTube scraper."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.youtube_scraper import YouTubeScraper
from tests.test_links_loader import TestLinksLoader

def test_youtube_scraper():
    """Test YouTube scraper with provided URLs."""
    
    scraper = YouTubeScraper(headless=False)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    yt_links = loader.get_links('youtube')
    if not yt_links:
        print("No youtube links found in test links file; skipping test.")
        return
    
    print("\n" + "="*60)
    print("Testing YouTube Scraper")
    print("="*60)
    
    results = []
    
    for i, link in enumerate(yt_links, 1):
        url = link['url']
        link_id = link['id']
        print(f"\n[{i}/{len(yt_links)}] Testing: {url} (link_id={link_id})")
        
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        results.append(result)
        
        print(f"Success: {result['success']}")
        print(f"Video ID: {result['video_id']}")
        print(f"Title: {result['title']}")
        print(f"Author: {result['author']}")
        print(f"Word Count: {result['word_count']}")
        
        if result['success']:
            print(f"Content Preview: {result['content'][:200]}...")
        else:
            print(f"Error: {result['error']}")
    
    scraper.close()
    print("\n" + "="*60)
    print("YouTube Scraper Test Complete")
    print("="*60)
    
    # Save each result as individual JSON file
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    batch_folder = output_dir / f"run_{batch_id}"
    batch_folder.mkdir(exist_ok=True)
    
    print(f"\nSaving individual files...")
    for result in results:
        if result['success']:
            link_id = result.get('link_id', 'unknown')
            filename = batch_folder / f"{batch_id}_YT_{link_id}_tsct.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  Saved: {filename.name}")
        else:
            print(f"  Skipped failed extraction for link_id: {result.get('link_id', 'unknown')}")

if __name__ == '__main__':
    test_youtube_scraper()
