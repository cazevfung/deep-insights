"""Test YouTube comments scraper."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.youtube_comments_scraper import YouTubeCommentsScraper
from tests.test_links_loader import TestLinksLoader


def test_youtube_comments_scraper():
    """Test YouTube comments scraper with provided URLs."""

    scraper = YouTubeCommentsScraper(headless=False)
    loader = TestLinksLoader()
    batch_id = loader.get_batch_id()
    yt_links = loader.get_links('youtube')
    if not yt_links:
        print("No youtube links found in test links file; skipping test.")
        return

    print("\n" + "="*60)
    print("Testing YouTube Comments Scraper")
    print("="*60)

    results = []

    for i, link in enumerate(yt_links, 1):
        url = link['url']
        link_id = link['id']
        print(f"\n[{i}/{len(yt_links)}] Testing: {url} (link_id={link_id})")

        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        results.append(result)

        print(f"Success: {result['success']}")
        print(f"Video ID: {result.get('video_id', 'unknown')}")
        print(f"Title: {result.get('title', '')}")
        print(f"Author: {result.get('author', '')}")
        print(f"Num Comments: {result.get('num_comments', 0)}")

        if result['success'] and result.get('comments'):
            preview = result['comments'][0][:200]
            print(f"First Comment Preview: {preview}...")
        else:
            print(f"Error: {result.get('error')}")

    scraper.close()
    print("\n" + "="*60)
    print("YouTube Comments Scraper Test Complete")
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
    total_words = 0
    
    for result in results:
        if result['success']:
            successful_extractions += 1
            video_id = result.get('video_id', 'unknown')
            link_id = result.get('link_id', 'unknown')
            comments = result.get('comments', [])
            
            # Add video metadata to each comment
            for comment in comments:
                comment_with_metadata = {
                    'content': comment,
                    'video_id': video_id,
                    'link_id': link_id
                }
                batch_comments.append(comment_with_metadata)
                total_words += len(comment.split())
            
            total_comments += len(comments)
    
    # Create batch result structure
    batch_result = {
        'batch_id': batch_id,
        'source': 'YouTube',
        'extraction_timestamp': datetime.now().isoformat(),
        'total_videos': len(results),
        'successful_extractions': successful_extractions,
        'total_comments': total_comments,
        'word_count': total_words,
        'comments': batch_comments
    }
    
    # Save batch file
    filename = batch_folder / f"{batch_id}_YT_batch_cmts.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(batch_result, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved batch file: {filename.name}")
    print(f"  Total videos: {len(results)}")
    print(f"  Successful extractions: {successful_extractions}")
    print(f"  Total comments: {total_comments}")
    print(f"  Total words: {total_words}")


if __name__ == '__main__':
    test_youtube_comments_scraper()


