"""
Direct scraper execution with progress callbacks.

This module runs scrapers directly (not as subprocesses) so that progress callbacks
can be passed to scrapers and work correctly.
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import scrapers and loader
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.youtube_comments_scraper import YouTubeCommentsScraper
from scrapers.bilibili_scraper import BilibiliScraper
from scrapers.bilibili_comments_scraper import BilibiliCommentsScraper
from scrapers.article_scraper import ArticleScraper
from scrapers.reddit_scraper import RedditScraper
from tests.test_links_loader import TestLinksLoader


def _run_scraper_for_link(
    scraper_class,
    scraper_name: str,
    url: str,
    batch_id: str,
    link_id: str,
    progress_callback: Optional[Callable[[dict], None]] = None,
    cancellation_checker: Optional[Callable[[], bool]] = None,
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Run a single scraper for a single link.
    
    Args:
        scraper_class: Scraper class to instantiate
        scraper_name: Name of scraper (for logging)
        url: URL to scrape
        batch_id: Batch ID
        link_id: Link ID
        progress_callback: Optional progress callback
        cancellation_checker: Optional function that returns True if cancelled
        **scraper_kwargs: Additional kwargs for scraper initialization
        
    Returns:
        Extraction result dictionary
    """
    try:
        # Create scraper with progress callback and cancellation checker
        scraper = scraper_class(
            progress_callback=progress_callback,
            cancellation_checker=cancellation_checker,
            **scraper_kwargs
        )
        
        # Extract content
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        
        # Close scraper
        try:
            scraper.close()
        except:
            pass
        
        return result
    except Exception as e:
        logger.error(f"[{scraper_name}] Error extracting {url}: {e}")
        return {
            'success': False,
            'url': url,
            'link_id': link_id,
            'batch_id': batch_id,
            'error': str(e),
            'word_count': 0
        }


def _run_scraper_type(
    scraper_class,
    scraper_name: str,
    link_type: str,
    batch_id: str,
    links: List[Dict],
    progress_callback: Optional[Callable[[dict], None]] = None,
    cancellation_checker: Optional[Callable[[], bool]] = None,
    **scraper_kwargs
) -> List[Dict[str, Any]]:
    """
    Run a scraper type for all links of that type.
    
    Creates ONE scraper instance and reuses it for all links (matching test pattern).
    This fixes browser context lifecycle issues that occur when creating/destroying
    scrapers per link in thread pool contexts.
    
    Args:
        scraper_class: Scraper class to instantiate
        scraper_name: Name of scraper (for logging)
        link_type: Type of links (for logging)
        batch_id: Batch ID
        links: List of link dictionaries with 'url' and 'id' keys
        progress_callback: Optional progress callback
        **scraper_kwargs: Additional kwargs for scraper initialization
        
    Returns:
        List of extraction results
    """
    if not links:
        logger.info(f"[{scraper_name}] No {link_type} links found")
        return []
    
    logger.info(f"[{scraper_name}] Processing {len(links)} {link_type} link(s)")
    
    if progress_callback:
        progress_callback({
            'type': 'scraping:start_type',
            'scraper': scraper_name,
            'link_type': link_type,
            'count': len(links),
            'message': f'开始处理 {len(links)} 个{link_type}链接'
        })
    
        # Create ONE scraper instance and reuse it for all links (fixes browser context lifecycle issues)
        scraper = None
        results = []
        
        try:
            # Create scraper with progress callback and cancellation checker (reused for all links)
            try:
                logger.info(f"[{scraper_name}] Creating scraper instance...")
                logger.debug(f"[{scraper_name}] Creating scraper instance with kwargs: {scraper_kwargs}")
                scraper = scraper_class(
                    progress_callback=progress_callback,
                    cancellation_checker=cancellation_checker,
                    **scraper_kwargs
                )
                logger.info(f"[{scraper_name}] Created scraper instance (will be reused for {len(links)} links)")
            except Exception as e:
                logger.error(f"[{scraper_name}] Failed to create scraper instance: {e}")
                import traceback
                logger.error(f"[{scraper_name}] Traceback: {traceback.format_exc()}")
                # Report error via progress callback if available
                if progress_callback:
                    for i, link in enumerate(links, 1):
                        progress_callback({
                            'type': 'scraping:complete_link',
                            'scraper': scraper_name,
                            'link_type': link_type,
                            'url': link['url'],
                            'link_id': link['id'],
                            'status': 'failed',
                            'message': f'Scraper initialization failed: {str(e)}',
                            'error': f'Failed to create scraper: {str(e)}',
                            'batch_id': batch_id
                        })
                raise
        
        # Process links sequentially (scrapers handle their own parallelization internally)
        for i, link in enumerate(links, 1):
            # Check for cancellation before processing each link
            if cancellation_checker and cancellation_checker():
                logger.info(f"[{scraper_name}] Cancellation detected, stopping processing")
                break
            
            url = link['url']
            link_id = link['id']
            
            logger.info(f"[{scraper_name}] Processing {i}/{len(links)}: {url} (link_id={link_id})")
            
            if progress_callback:
                progress_callback({
                    'type': 'scraping:start_link',
                    'scraper': scraper_name,
                    'link_type': link_type,
                    'url': url,
                    'link_id': link_id,
                    'index': i,
                    'total': len(links),
                    'message': f'处理链接 {i}/{len(links)}: {url}'
                })
            
            # Extract content using the shared scraper instance
            try:
                logger.debug(f"[{scraper_name}] Starting extraction for {url}")
                result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
                logger.debug(f"[{scraper_name}] Extraction result: success={result.get('success')}, error={result.get('error')}")
                results.append(result)
                
                # Check for cancellation after extraction
                if cancellation_checker and cancellation_checker():
                    logger.info(f"[{scraper_name}] Cancellation detected after extraction, stopping processing")
                    break
                
                if progress_callback:
                    status = 'success' if result.get('success') else 'failed'
                    error_msg = result.get('error')
                    if error_msg:
                        message_text = f'链接 {i}/{len(links)} 完成: {status} - {error_msg}'
                    else:
                        message_text = f'链接 {i}/{len(links)} 完成: {status}'
                    
                    progress_callback({
                        'type': 'scraping:complete_link',
                        'scraper': scraper_name,
                        'link_type': link_type,
                        'url': url,
                        'link_id': link_id,
                        'status': status,
                        'message': message_text,
                        'error': error_msg,
                        'batch_id': batch_id
                    })
            except Exception as e:
                logger.error(f"[{scraper_name}] Error extracting {url}: {e}", exc_info=True)
                error_str = str(e)
                result = {
                    'success': False,
                    'url': url,
                    'link_id': link_id,
                    'batch_id': batch_id,
                    'error': error_str,
                    'word_count': 0
                }
                results.append(result)
                
                if progress_callback:
                    progress_callback({
                        'type': 'scraping:complete_link',
                        'scraper': scraper_name,
                        'link_type': link_type,
                        'url': url,
                        'link_id': link_id,
                        'status': 'failed',
                        'message': f'链接 {i}/{len(links)} 失败: {error_str}',
                        'error': error_str,
                        'batch_id': batch_id
                    })
    
    finally:
        # Close scraper instance after processing all links
        if scraper:
            try:
                scraper.close()
                logger.info(f"[{scraper_name}] Closed scraper instance")
            except Exception as e:
                logger.warning(f"[{scraper_name}] Error closing scraper: {e}")
    
    success_count = sum(1 for r in results if r.get('success'))
    logger.info(f"[{scraper_name}] Completed: {success_count}/{len(links)} succeeded")
    
    return results


def _save_results(results: List[Dict], batch_id: str, scraper_name: str, link_type: str):
    """
    Save results to JSON files (same format as test scripts).
    
    Args:
        results: List of extraction results
        batch_id: Batch ID
        scraper_name: Name of scraper (for filename)
        link_type: Type of links (for filename)
    """
    if not results:
        return
    
    output_dir = Path(__file__).parent.parent.parent / "tests" / "results"
    output_dir.mkdir(exist_ok=True, parents=True)
    batch_folder = output_dir / f"run_{batch_id}"
    batch_folder.mkdir(exist_ok=True)
    
    saved_count = 0
    
    # Comments scrapers save all comments in one batch file
    if scraper_name in ['youtubecomments', 'bilibilicomments']:
        # Aggregate all comments from all results
        batch_comments = []
        total_comments = 0
        successful_extractions = 0
        
        for result in results:
            if result.get('success'):
                successful_extractions += 1
                if scraper_name == 'youtubecomments':
                    video_id = result.get('video_id', 'unknown')
                    link_id = result.get('link_id', 'unknown')
                    comments = result.get('comments', [])
                    
                    # Add video metadata to each comment
                    for comment in comments:
                        comment_with_metadata = {
                            'content': comment if isinstance(comment, str) else comment.get('content', ''),
                            'video_id': video_id,
                            'link_id': link_id,
                        }
                        batch_comments.append(comment_with_metadata)
                        total_comments += 1
                elif scraper_name == 'bilibilicomments':
                    bv_id = result.get('bv_id', 'unknown')
                    link_id = result.get('link_id', 'unknown')
                    comments = result.get('comments', [])
                    
                    # Add video metadata to each comment
                    for comment in comments:
                        comment_with_metadata = {
                            **comment,
                            'bv_id': bv_id,
                            'link_id': link_id,
                        }
                        batch_comments.append(comment_with_metadata)
                        total_comments += len(comments) if isinstance(comments, list) else 1
        
        # Save batch file
        if scraper_name == 'youtubecomments':
            filename = batch_folder / f"{batch_id}_YT_batch_cmts.json"
        else:  # bilibilicomments
            filename = batch_folder / f"{batch_id}_BILI_batch_cmt.json"
        
        batch_result = {
            'batch_id': batch_id,
            'scraper_type': scraper_name,
            'total_comments': total_comments,
            'successful_extractions': successful_extractions,
            'total_videos': len(results),
            'comments': batch_comments,
            'generated_at': datetime.now().isoformat()
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2)
            saved_count = 1
            logger.info(f"[{scraper_name}] Saved batch file: {filename.name} ({total_comments} comments)")
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")
    
    else:
        # Transcript/article scrapers save one file per link
        # Filename format: {batch_id}_{TYPE}_{link_id}_{suffix}.json
        type_prefix_map = {
            'youtube': 'YT',
            'bilibili': 'BILI',
            'article': 'AR',
            'reddit': 'RD',
        }
        type_prefix = type_prefix_map.get(link_type, link_type.upper()[:4])
        
        suffix_map = {
            'youtube': 'tsct',
            'bilibili': 'tsct',
            'article': 'tsct',
            'reddit': 'tsct',
        }
        suffix = suffix_map.get(link_type, 'tsct')
        
        for result in results:
            # For bilibili, also check for content (same as test script)
            if result.get('success') and (link_type != 'bilibili' or result.get('content')):
                link_id = result.get('link_id', 'unknown')
                filename = batch_folder / f"{batch_id}_{type_prefix}_{link_id}_{suffix}.json"
                
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save {filename}: {e}")
        
        logger.info(f"[{scraper_name}] Saved {saved_count}/{len(results)} results")


def run_all_scrapers_direct(
    progress_callback: Optional[Callable[[dict], None]] = None,
    batch_id: Optional[str] = None,
    cancellation_checker: Optional[Callable[[], bool]] = None
) -> Dict[str, Any]:
    """
    Run all scrapers directly (not as subprocesses) with progress callbacks.
    
    Args:
        progress_callback: Optional callable(message: dict) for progress updates.
                          Will be called with progress messages as scrapers run.
        batch_id: Optional batch ID. If not provided, will be loaded from TestLinksLoader.
        
    Returns:
        Dict with batch_id, success status, and results
    """
    if progress_callback:
        progress_callback({
            'type': 'scraping:start',
            'message': '开始抓取内容...'
        })
    else:
        logger.info("Starting all scrapers...")
    
    # Load test links
    try:
        loader = TestLinksLoader()
        loaded_batch_id = loader.get_batch_id()
        batch_id = batch_id or loaded_batch_id
    except Exception as e:
        logger.error(f"Failed to load test links: {e}")
        return {
            'batch_id': batch_id or 'unknown',
            'success': False,
            'error': f'Failed to load test links: {e}'
        }
    
    # Get links by type
    link_types = {
        'youtube': loader.get_links('youtube'),
        'bilibili': loader.get_links('bilibili'),
        'reddit': loader.get_links('reddit'),
        'article': loader.get_links('article'),
    }
    
    total_links = sum(len(links) for links in link_types.values())
    
    if progress_callback:
        progress_callback({
            'type': 'scraping:discover',
            'message': f'发现 {total_links} 个链接',
            'total_links': total_links
        })
    
    if total_links == 0:
        logger.warning("No links found in test links file")
        return {
            'batch_id': batch_id,
            'success': False,
            'error': 'No links found',
            'passed': 0,
            'total': 0
        }
    
    # Define scraper configurations
    scraper_configs = [
        {
            'scraper_class': YouTubeScraper,
            'scraper_name': 'youtube',
            'link_type': 'youtube',
            'links': link_types['youtube'],
            'kwargs': {'headless': False}
        },
        {
            'scraper_class': YouTubeCommentsScraper,
            'scraper_name': 'youtubecomments',
            'link_type': 'youtube',
            'links': link_types['youtube'],
            'kwargs': {'headless': False}
        },
        {
            'scraper_class': BilibiliScraper,
            'scraper_name': 'bilibili',
            'link_type': 'bilibili',
            'links': link_types['bilibili'],
            'kwargs': {}
        },
        {
            'scraper_class': BilibiliCommentsScraper,
            'scraper_name': 'bilibilicomments',
            'link_type': 'bilibili',
            'links': link_types['bilibili'],
            'kwargs': {}
        },
        {
            'scraper_class': ArticleScraper,
            'scraper_name': 'article',
            'link_type': 'article',
            'links': link_types['article'],
            'kwargs': {'headless': True}
        },
        {
            'scraper_class': RedditScraper,
            'scraper_name': 'reddit',
            'link_type': 'reddit',
            'links': link_types['reddit'],
            'kwargs': {'headless': False}
        },
    ]
    
    # Filter out scrapers with no links
    active_configs = [cfg for cfg in scraper_configs if cfg['links']]
    
    all_results = []
    
    # Run scrapers in parallel (one thread per scraper type)
    # Each scraper type processes its links sequentially
    with ThreadPoolExecutor(max_workers=len(active_configs)) as executor:
        futures = []
        
        for config in active_configs:
            future = executor.submit(
                _run_scraper_type,
                config['scraper_class'],
                config['scraper_name'],
                config['link_type'],
                batch_id,
                config['links'],
                progress_callback,
                cancellation_checker,
                **config['kwargs']
            )
            futures.append((future, config))
        
        # Collect results as they complete
        for future, config in futures:
            try:
                results = future.result()
                all_results.extend(results)
                
                # Save results (same format as test scripts)
                _save_results(results, batch_id, config['scraper_name'], config['link_type'])
                
            except Exception as e:
                logger.error(f"[{config['scraper_name']}] Error: {e}")
                if progress_callback:
                    progress_callback({
                        'type': 'error',
                        'scraper': config['scraper_name'],
                        'message': f'抓取器错误: {e}'
                    })
    
    # Calculate success rate
    passed = sum(1 for r in all_results if r.get('success'))
    total = len(all_results)
    
    if progress_callback:
        progress_callback({
            'type': 'scraping:complete',
            'message': f'抓取完成: {passed}/{total} 成功',
            'passed': passed,
            'total': total,
            'batch_id': batch_id
        })
        
        # After sending scraping:complete, verify and send confirmation signal
        # The progress callback has access to check_completion function via closure
        # We'll check completion by calling it through the callback mechanism
        # Since we don't have direct access to ProgressService, we'll send a request
        # for the workflow service to verify and send confirmation
        import time
        import asyncio
        
        # Wait a bit for final status updates to be processed
        time.sleep(0.5)
        
        # Send request to verify completion (workflow service will handle verification)
        # We use a special message type that triggers verification
        progress_callback({
            'type': 'scraping:verify_completion',
            'batch_id': batch_id,
            'message': 'Verifying all scraping processes are complete...'
        })
    else:
        logger.info(f"Scrapers Summary: {passed}/{total} passed")
    
    return {
        'batch_id': batch_id,
        'passed': passed,
        'total': total,
        'success': passed > 0  # At least one scraper succeeded
    }

