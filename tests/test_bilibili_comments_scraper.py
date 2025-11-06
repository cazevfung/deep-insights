"""Test Bilibili comments scraper."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.bilibili_comments_scraper import BilibiliCommentsScraper
from tests.test_links_loader import TestLinksLoader


def test_bilibili_comments_scraper():
    """Test Bilibili comments scraper with provided URLs."""
    
    scraper = BilibiliCommentsScraper()
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    bili_links = loader.get_links('bilibili')
    if not bili_links:
        print("No bilibili links found in test links file; skipping test.")
        return
    
    print("\n" + "="*60)
    print("Testing Bilibili Comments Scraper")
    print("="*60)
    
    results = []
    
    for i, link in enumerate(bili_links, 1):
        url = link['url']
        link_id = link['id']
        print(f"\n[{i}/{len(bili_links)}] Testing: {url} (link_id={link_id})")
        
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        results.append(result)
        
        print(f"Success: {result['success']}")
        print(f"BV ID: {result['bv_id']}")
        print(f"Total Comments: {result['total_comments']}")
        
        if result['success']:
            # Show first few comments
            if result['comments']:
                print("\nFirst 3 comments:")
                for j, comment in enumerate(result['comments'][:3], 1):
                    print(f"\nComment {j}:")
                    print(f"  Content: {comment.get('content', '')[:100]}...")
                    print(f"  Likes: {comment.get('likes', 0)}")
        else:
            print(f"Error: {result['error']}")
    
    print("\n" + "="*60)
    print("Bilibili Comments Scraper Test Complete")
    print("="*60)
    
    # Save all comments from batch in one file
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    batch_folder = output_dir / f"run_{batch_id}"
    batch_folder.mkdir(exist_ok=True)
    
    # Aggregate all comments from all videos
    batch_comments = []
    total_comments = 0
    successful_extractions = 0
    
    for result in results:
        if result['success']:
            successful_extractions += 1
            bv_id = result.get('bv_id', 'unknown')
            link_id = result.get('link_id', 'unknown')
            comments = result.get('comments', [])
            
            # Add video metadata to each comment
            for comment in comments:
                comment_with_metadata = {
                    **comment,
                    'bv_id': bv_id,
                    'link_id': link_id
                }
                batch_comments.append(comment_with_metadata)
            
            total_comments += len(comments)
    
    # Create batch result structure
    batch_result = {
        'batch_id': batch_id,
        'source': 'Bilibili',
        'extraction_timestamp': datetime.now().isoformat(),
        'total_videos': len(results),
        'successful_extractions': successful_extractions,
        'total_comments': total_comments,
        'comments': batch_comments
    }
    
    # Save batch file
    filename = batch_folder / f"{batch_id}_BILI_batch_cmt.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(batch_result, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved batch file: {filename.name}")
    print(f"  Total videos: {len(results)}")
    print(f"  Successful extractions: {successful_extractions}")
    print(f"  Total comments: {total_comments}")


if __name__ == '__main__':
    test_bilibili_comments_scraper()

 


