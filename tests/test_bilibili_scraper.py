"""Test Bilibili scraper with in-house downloader method."""
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.bilibili_scraper import BilibiliScraper
from tests.test_links_loader import TestLinksLoader

def main():
    print("="*80)
    print("Testing Bilibili Scraper (In-house Downloader Method)")
    print("="*80)
    
    logger.info("[BilibiliTest] Starting test_bilibili_scraper.py")
    
    try:
        # Load test links from external file
        logger.info("[BilibiliTest] Loading test links...")
        loader = TestLinksLoader()
        batch_id = loader.get_batch_id()
        logger.info(f"[BilibiliTest] Batch ID: {batch_id}")
        
        bili_links = loader.get_links('bilibili')
        logger.info(f"[BilibiliTest] Found {len(bili_links) if bili_links else 0} bilibili links")
        
        if not bili_links:
            print("No bilibili links found in test links file; skipping test.")
            logger.warning("[BilibiliTest] No bilibili links found - test skipped")
            return
        
        print(f"Testing {len(bili_links)} URL(s)")
        print("\nTest URLs:")
        for i, link in enumerate(bili_links, 1):
            print(f"  {i}. {link['url']}")
            logger.info(f"[BilibiliTest] Link {i}: {link['url']} (id={link.get('id', 'unknown')})")
        
        print("\nEach test will:")
        print("1. Resolve BV/b23 and fetch playurl via API (WBI)")
        print("2. Download 480p video (DASH/durl)")
        print("3. Merge A+V to MP4")
        print("4. Convert MP4 to MP3")
        print("5. Upload to Alibaba Cloud")
        print("6. Transcribe with Paraformer")
        print("7. Return transcript")
        print("\n" + "="*80 + "\n")
        
        scraper = None
        try:
            logger.info("[BilibiliTest] Initializing BilibiliScraper...")
            scraper = BilibiliScraper()
            logger.info("[BilibiliTest] BilibiliScraper initialized successfully")
        except Exception as e:
            logger.error(f"[BilibiliTest] Failed to initialize scraper: {e}")
            logger.error(f"[BilibiliTest] Traceback: {traceback.format_exc()}")
            print(f"ERROR: Failed to initialize scraper: {e}")
            return
        
        all_results = []
        
        # Test each URL
        for idx, link in enumerate(bili_links, 1):
            test_url = link['url']
            link_id = link.get('id', f'link_{idx}')
            
            print(f"\n{'='*80}")
            print(f"TESTING URL {idx}/{len(bili_links)}")
            print(f"{'='*80}")
            print(f"URL: {test_url}")
            print(f"Link ID: {link_id}")
            print("-"*80)
            
            logger.info(f"[BilibiliTest] Testing URL {idx}/{len(bili_links)}: {test_url} (link_id={link_id})")
            
            try:
                result = scraper.extract(test_url, batch_id=batch_id, link_id=link_id)
                logger.info(f"[BilibiliTest] Extraction result for {link_id}: success={result.get('success')}, error={result.get('error')}")
                all_results.append(result)
                
                # Print immediate result
                print(f"\nResult: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
                if result['success']:
                    word_count = result.get('word_count', 0)
                    print(f"Word Count: {word_count}")
                    logger.info(f"[BilibiliTest] Successfully extracted {word_count} words for {link_id}")
                    
                    content = result.get('content', '')
                    if content:
                        preview = content[:200] if len(content) > 200 else content
                        print(f"\nContent Preview ({len(content)} chars):")
                        print("-"*80)
                        print(preview)
                        if len(content) > 200:
                            print(f"... ({len(content) - 200} more characters)")
                        print("-"*80)
                else:
                    error_msg = result.get('error', 'Unknown')
                    print(f"Error: {error_msg}")
                    logger.error(f"[BilibiliTest] Extraction failed for {link_id}: {error_msg}")
            except Exception as e:
                logger.error(f"[BilibiliTest] Exception during extraction for {link_id}: {e}")
                logger.error(f"[BilibiliTest] Traceback: {traceback.format_exc()}")
                error_result = {
                    'success': False,
                    'url': test_url,
                    'link_id': link_id,
                    'batch_id': batch_id,
                    'error': str(e),
                    'word_count': 0
                }
                all_results.append(error_result)
                print(f"\nResult: ✗ FAILED")
                print(f"Exception: {e}")
            
            print(f"{'='*80}\n")
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        success_count = sum(1 for r in all_results if r.get('success'))
        print(f"Successfully extracted: {success_count}/{len(bili_links)}")
        print(f"Failed: {len(bili_links) - success_count}/{len(bili_links)}")
        print("="*80)
        logger.info(f"[BilibiliTest] Summary: {success_count}/{len(bili_links)} successful")
        
        # Print detailed results
        print("\nDetailed Results:")
        print("-"*80)
        for i, result in enumerate(all_results, 1):
            status = "✓ SUCCESS" if result.get('success') else "✗ FAILED"
            word_count = result.get('word_count', 0)
            print(f"{i}. {status} - {word_count} words")
            if not result.get('success'):
                print(f"   Error: {result.get('error', 'Unknown')}")
        print("-"*80)
        
        # Save each result as individual JSON file (align with YT tsct behavior)
        try:
            output_dir = Path(__file__).parent / "results"
            logger.info(f"[BilibiliTest] Output directory: {output_dir}")
            output_dir.mkdir(exist_ok=True)
            logger.info(f"[BilibiliTest] Output directory created/exists: {output_dir.exists()}")
            
            batch_folder = output_dir / f"run_{batch_id}"
            logger.info(f"[BilibiliTest] Batch folder: {batch_folder}")
            batch_folder.mkdir(exist_ok=True)
            logger.info(f"[BilibiliTest] Batch folder created/exists: {batch_folder.exists()}")
            
            print("\nSaving individual files...")
            logger.info(f"[BilibiliTest] Starting to save {len(all_results)} result files...")
            saved = 0
            failed = 0
            
            for result in all_results:
                try:
                    # Validate both success flag and content before saving
                    if result.get('success') and result.get('content'):
                        link_id = result.get('link_id', 'unknown')
                        out_path = batch_folder / f"{batch_id}_BILI_{link_id}_tsct.json"
                        logger.info(f"[BilibiliTest] Saving successful result to: {out_path}")
                        
                        with open(out_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"[BilibiliTest] Successfully saved: {out_path.name}")
                        print(f"  Saved: {out_path.name}")
                        saved += 1
                    elif result.get('success') and not result.get('content'):
                        # Success=True but no content - this indicates transcription failed
                        link_id = result.get('link_id', 'unknown')
                        error_msg = result.get('error', 'Unknown error')
                        logger.warning(f"[BilibiliTest] Skipping result with success=True but no content for link_id: {link_id}, error: {error_msg}")
                        print(f"  Skipped result with no content for link_id: {link_id} (error: {error_msg})")
                        failed += 1
                    else:
                        link_id = result.get('link_id', 'unknown')
                        error_msg = result.get('error', 'Unknown error')
                        logger.warning(f"[BilibiliTest] Skipping failed extraction for link_id: {link_id}, error: {error_msg}")
                        print(f"  Skipped failed extraction for link_id: {link_id} (error: {error_msg})")
                        failed += 1
                except Exception as e:
                    link_id = result.get('link_id', 'unknown')
                    logger.error(f"[BilibiliTest] Failed to save result for {link_id}: {e}")
                    logger.error(f"[BilibiliTest] Traceback: {traceback.format_exc()}")
                    print(f"  ERROR saving result for link_id {link_id}: {e}")
                    failed += 1
            
            logger.info(f"[BilibiliTest] File saving complete: {saved} saved, {failed} skipped/failed")
            print(f"\nSaved {saved} files to: {batch_folder}")
            print(f"Failed/Skipped: {failed} files")
            print("Total processing time for all URLs completed.")
        except Exception as e:
            logger.error(f"[BilibiliTest] Critical error during file saving: {e}")
            logger.error(f"[BilibiliTest] Traceback: {traceback.format_exc()}")
            print(f"\nCRITICAL ERROR: Failed to save files: {e}")
            traceback.print_exc()
    except Exception as e:
        logger.error(f"[BilibiliTest] Critical error in main(): {e}")
        logger.error(f"[BilibiliTest] Traceback: {traceback.format_exc()}")
        print(f"\nCRITICAL ERROR: {e}")
        traceback.print_exc()
    finally:
        if scraper:
            try:
                logger.info("[BilibiliTest] Closing scraper...")
                scraper.close()
                logger.info("[BilibiliTest] Scraper closed successfully")
            except Exception as e:
                logger.error(f"[BilibiliTest] Error closing scraper: {e}")

if __name__ == '__main__':
    main()


