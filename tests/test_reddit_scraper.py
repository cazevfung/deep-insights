"""Test Reddit scraper."""
import sys
import json
import io
import time
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.reddit_scraper import RedditScraper
from tests.test_links_loader import TestLinksLoader

def test_reddit_scraper():
    """Test Reddit scraper with provided URLs."""
    
    # headless=False to show browser window for debugging
    # Make sure config.yaml has connect_to_existing_browser: true
    print("\n" + "=" * 80)
    print("Testing Reddit Scraper")
    print("=" * 80)
    print("\nChrome will start automatically if not already running.")
    print("The scraper will handle Chrome startup for you!")
    print("=" * 80 + "\n")
    
    scraper = RedditScraper(headless=False)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    rd_links = loader.get_links('reddit')
    if not rd_links:
        print("No reddit links found in test links file; skipping test.")
        return
    
    print("\n" + "="*60)
    print("Testing Reddit Scraper")
    print("="*60)
    
    results = []
    
    for i, link in enumerate(rd_links, 1):
        url = link['url']
        link_id = link['id']
        print(f"\n[{i}/{len(rd_links)}] Testing: {url} (link_id={link_id})")
        
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        results.append(result)
        
        print(f"Success: {result['success']}")
        print(f"Title: {result['title']}")
        print(f"Author: {result['author']}")
        print(f"Word Count: {result['word_count']}")
        
        if result['success']:
            try:
                preview = result['content'][:300] if result['content'] else ''
                print(f"Content Preview: {preview}...")
            except Exception as e:
                print(f"Content Preview: [Preview unavailable]")
        else:
            print(f"Error: {result['error']}")
    
    # Wait before closing so user can see what happened
    print("\nWaiting 5 seconds before closing browser so you can inspect the page...")
    time.sleep(5)
    
    scraper.close()
    print("\n" + "="*60)
    print("Reddit Scraper Test Complete")
    print("="*60)
    
    # Save each result as individual JSON file
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    batch_folder = output_dir / f"run_{batch_id}"
    batch_folder.mkdir(exist_ok=True)
    
    print(f"\nSaving individual files...")
    for i, result in enumerate(results):
        if result['success']:
            link_id = result.get('link_id', f'post_{i}')
            filename = batch_folder / f"{batch_id}_RD_{link_id}_tsct.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  Saved: {filename.name}")
        else:
            print(f"  Skipped failed extraction for post {i+1}")

if __name__ == '__main__':
    test_reddit_scraper()
