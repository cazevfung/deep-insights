"""Test Article scraper."""
import sys
import json
import io
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.article_scraper import ArticleScraper
from tests.test_links_loader import TestLinksLoader

def test_article_scraper():
    """Test Article scraper with provided URLs."""
    
    scraper = ArticleScraper(headless=True)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    art_links = loader.get_links('article')
    if not art_links:
        print("No article links found in test links file; skipping test.")
        return
    
    print("\n" + "="*60)
    print("Testing Article Scraper")
    print("="*60)
    
    results = []
    
    for i, link in enumerate(art_links, 1):
        url = link['url']
        link_id = link['id']
        print(f"\n[{i}/{len(art_links)}] Testing: {url} (link_id={link_id})")
        
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        results.append(result)
        
        print(f"Success: {result['success']}")
        print(f"Article ID: {result.get('article_id', '')}")
        print(f"Method: {result['extraction_method']}")
        print(f"Title: {result['title']}")
        print(f"Word Count: {result['word_count']}")
        
        if result['success']:
            try:
                preview = result['content'][:200] if result['content'] else ''
                print(f"Content Preview: {preview}...")
            except Exception as e:
                print(f"Content Preview: [Preview unavailable - {type(e).__name__}]")
        else:
            print(f"Error: {result['error']}")
    
    scraper.close()
    print("\n" + "="*60)
    print("Article Scraper Test Complete")
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
            filename = batch_folder / f"{batch_id}_AR_{link_id}_tsct.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  Saved: {filename.name}")
        else:
            print(f"  Skipped failed extraction for link_id: {result.get('link_id', 'unknown')}")

if __name__ == '__main__':
    test_article_scraper()
