"""
Direct scraper execution with progress callbacks.

This module runs scrapers directly (not as subprocesses) so that progress callbacks
can be passed to scrapers and work correctly.
"""
import sys
import json
import time
import uuid
import threading
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

# Debug mode flag
DEBUG_MODE = os.environ.get('WORKFLOW_DEBUG', 'false').lower() == 'true'

# Message validation schemas
REQUIRED_FIELDS_BY_TYPE = {
    'scraping:start': ['type', 'message'],
    'scraping:discover': ['type', 'message', 'total_links'],
    'scraping:start_type': ['type', 'scraper', 'link_type', 'count', 'message'],
    'scraping:start_link': ['type', 'scraper', 'url', 'link_id', 'index', 'total'],
    'scraping:complete_link': ['type', 'scraper', 'url', 'link_id', 'status'],
    'scraping:complete': ['type', 'message', 'passed', 'total', 'batch_id'],
    'scraping:verify_completion': ['type', 'batch_id', 'message']
}

# Track callback invocations per batch
_callback_tracking: Dict[str, Dict[str, Any]] = {}
_tracking_lock = threading.Lock()

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


def _validate_message(message: dict, message_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate message format against schema.
    
    Returns:
        (is_valid, error_message)
    """
    if message_type not in REQUIRED_FIELDS_BY_TYPE:
        return True, None  # Unknown type, skip validation
    
    required_fields = REQUIRED_FIELDS_BY_TYPE[message_type]
    missing_fields = [field for field in required_fields if field not in message]
    
    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"
    
    # Validate status values
    if message_type == 'scraping:complete_link':
        status = message.get('status')
        if status not in ['success', 'failed', 'unknown']:
            return False, f"Invalid status value: {status}"
    
    # Validate progress values
    if 'progress' in message:
        progress = message.get('progress', 0.0)
        if not (0.0 <= progress <= 100.0):
            return False, f"Invalid progress value: {progress} (must be 0.0-100.0)"
    
    return True, None


def _safe_callback_invoke(
    progress_callback: Optional[Callable[[dict], None]],
    message: dict,
    batch_id: str,
    scraper_name: str
) -> None:
    """
    Safely invoke progress callback with tracking and validation.
    
    Args:
        progress_callback: Callback function
        message: Message dictionary
        batch_id: Batch ID
        scraper_name: Scraper name for logging
    """
    if not progress_callback:
        return
    
    message_type = message.get('type', 'unknown')
    message_id = uuid.uuid4().hex[:8]
    message['_debug_message_id'] = message_id
    
    # Track callback invocation
    if DEBUG_MODE:
        thread_id = threading.current_thread().ident
        with _tracking_lock:
            if batch_id not in _callback_tracking:
                _callback_tracking[batch_id] = {
                    'callback_count': 0,
                    'messages': [],
                    'threads': set()
                }
            tracking = _callback_tracking[batch_id]
            tracking['callback_count'] += 1
            tracking['threads'].add(thread_id)
            tracking['messages'].append({
                'message_id': message_id,
                'type': message_type,
                'scraper': scraper_name,
                'thread_id': thread_id,
                'timestamp': time.time()
            })
    
    # Validate message format
    is_valid, error_msg = _validate_message(message, message_type)
    if not is_valid:
        logger.warning(
            f"[CALLBACK] Invalid message format (message_id={message_id}): {error_msg}. "
            f"Message: {message}"
        )
    
    # Log callback invocation
    if DEBUG_MODE:
        logger.debug(
            f"[CALLBACK] Invoking callback (message_id={message_id}, type={message_type}, "
            f"scraper={scraper_name}, batch_id={batch_id}, thread_id={threading.current_thread().ident})"
        )
    
    # Invoke callback with error handling
    try:
        callback_start = time.time()
        progress_callback(message)
        callback_elapsed = time.time() - callback_start
        
        if DEBUG_MODE and callback_elapsed > 0.1:
            logger.warning(
                f"[CALLBACK] Slow callback execution: {callback_elapsed:.3f}s "
                f"(message_id={message_id}, type={message_type})"
            )
    except Exception as e:
        logger.error(
            f"[CALLBACK] Error in callback execution (message_id={message_id}, type={message_type}): {e}",
            exc_info=True
        )


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
    operation_start = time.time()
    try:
        # Create scraper with progress callback and cancellation checker
        scraper = scraper_class(
            progress_callback=progress_callback,
            cancellation_checker=cancellation_checker,
            **scraper_kwargs
        )
        
        # Extract content
        extract_start = time.time()
        result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
        extract_elapsed = time.time() - extract_start
        
        if DEBUG_MODE:
            logger.debug(
                f"[TIMING] [{scraper_name}] Extraction took {extract_elapsed:.2f}s "
                f"for {url} (link_id={link_id})"
            )
        
        # Close scraper
        try:
            scraper.close()
            if DEBUG_MODE:
                logger.debug(f"[CLEANUP] [{scraper_name}] Scraper closed for {url}")
        except Exception as close_error:
            logger.warning(f"[CLEANUP] [{scraper_name}] Error closing scraper for {url}: {close_error}")
        
        operation_elapsed = time.time() - operation_start
        if DEBUG_MODE:
            logger.debug(
                f"[TIMING] [{scraper_name}] Total operation took {operation_elapsed:.2f}s "
                f"for {url} (link_id={link_id})"
            )
        
        return result
    except Exception as e:
        operation_elapsed = time.time() - operation_start
        logger.error(
            f"[ERROR] [{scraper_name}] Error extracting {url} (link_id={link_id}, "
            f"batch_id={batch_id}, elapsed={operation_elapsed:.2f}s): {e}",
            exc_info=True
        )
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
    
    type_start_time = time.time()
    
    if progress_callback:
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:start_type',
                'scraper': scraper_name,
                'link_type': link_type,
                'count': len(links),
                'message': f'开始处理 {len(links)} 个{link_type}链接',
                'batch_id': batch_id
            },
            batch_id,
            scraper_name
        )
    
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
                    _safe_callback_invoke(
                        progress_callback,
                        {
                            'type': 'scraping:complete_link',
                            'scraper': scraper_name,
                            'link_type': link_type,
                            'url': link['url'],
                            'link_id': link['id'],
                            'status': 'failed',
                            'message': f'Scraper initialization failed: {str(e)}',
                            'error': f'Failed to create scraper: {str(e)}',
                            'batch_id': batch_id
                        },
                        batch_id,
                        scraper_name
                    )
            raise
        
        # Process links sequentially (scrapers handle their own parallelization internally)
        for i, link in enumerate(links, 1):
            # Check for cancellation before processing each link
            if cancellation_checker and cancellation_checker():
                logger.info(
                    f"[CANCEL] [{scraper_name}] Cancellation detected, stopping processing "
                    f"(processed {i-1}/{len(links)} links)"
                )
                break
            
            url = link['url']
            link_id = link['id']
            
            logger.info(f"[{scraper_name}] Processing {i}/{len(links)}: {url} (link_id={link_id})")
            
            link_start_time = time.time()
            
            if progress_callback:
                _safe_callback_invoke(
                    progress_callback,
                    {
                        'type': 'scraping:start_link',
                        'scraper': scraper_name,
                        'link_type': link_type,
                        'url': url,
                        'link_id': link_id,
                        'index': i,
                        'total': len(links),
                        'message': f'处理链接 {i}/{len(links)}: {url}',
                        'batch_id': batch_id
                    },
                    batch_id,
                    scraper_name
                )
            
            # Extract content using the shared scraper instance
            try:
                logger.debug(f"[{scraper_name}] Starting extraction for {url}")
                result = scraper.extract(url, batch_id=batch_id, link_id=link_id)
                logger.debug(f"[{scraper_name}] Extraction result: success={result.get('success')}, error={result.get('error')}")
                results.append(result)
                
                # Check for cancellation after extraction
                if cancellation_checker and cancellation_checker():
                    logger.info(
                        f"[CANCEL] [{scraper_name}] Cancellation detected after extraction, "
                        f"stopping processing (processed {i}/{len(links)} links)"
                    )
                    break
                
                link_elapsed = time.time() - link_start_time
                if DEBUG_MODE:
                    logger.debug(
                        f"[TIMING] [{scraper_name}] Link {i}/{len(links)} took {link_elapsed:.2f}s "
                        f"(url={url}, link_id={link_id}, success={result.get('success')})"
                    )
                
                if progress_callback:
                    status = 'success' if result.get('success') else 'failed'
                    error_msg = result.get('error')
                    if error_msg:
                        message_text = f'链接 {i}/{len(links)} 完成: {status} - {error_msg}'
                    else:
                        message_text = f'链接 {i}/{len(links)} 完成: {status}'
                    
                    _safe_callback_invoke(
                        progress_callback,
                        {
                            'type': 'scraping:complete_link',
                            'scraper': scraper_name,
                            'link_type': link_type,
                            'url': url,
                            'link_id': link_id,
                            'status': status,
                            'message': message_text,
                            'error': error_msg,
                            'batch_id': batch_id
                        },
                        batch_id,
                        scraper_name
                    )
            except Exception as e:
                link_elapsed = time.time() - link_start_time
                error_str = str(e)
                logger.error(
                    f"[ERROR] [{scraper_name}] Error extracting {url} (link_id={link_id}, "
                    f"batch_id={batch_id}, elapsed={link_elapsed:.2f}s): {e}",
                    exc_info=True
                )
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
                    _safe_callback_invoke(
                        progress_callback,
                        {
                            'type': 'scraping:complete_link',
                            'scraper': scraper_name,
                            'link_type': link_type,
                            'url': url,
                            'link_id': link_id,
                            'status': 'failed',
                            'message': f'链接 {i}/{len(links)} 失败: {error_str}',
                            'error': error_str,
                            'batch_id': batch_id
                        },
                        batch_id,
                        scraper_name
                    )
    
    finally:
        # Close scraper instance after processing all links
        if scraper:
            try:
                scraper.close()
                logger.info(f"[CLEANUP] [{scraper_name}] Closed scraper instance")
                if DEBUG_MODE:
                    logger.debug(f"[CLEANUP] [{scraper_name}] Scraper cleanup successful")
            except Exception as e:
                logger.warning(
                    f"[CLEANUP] [{scraper_name}] Error closing scraper: {e}",
                    exc_info=True
                )
    
    type_elapsed = time.time() - type_start_time
    success_count = sum(1 for r in results if r.get('success'))
    logger.info(
        f"[{scraper_name}] Completed: {success_count}/{len(links)} succeeded "
        f"(elapsed={type_elapsed:.2f}s)"
    )
    
    if DEBUG_MODE:
        logger.debug(
            f"[TIMING] [{scraper_name}] Total type processing took {type_elapsed:.2f}s "
            f"for {len(links)} links"
        )
    
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
    workflow_start_time = time.time()
    
    if progress_callback:
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:start',
                'message': '开始抓取内容...',
                'batch_id': batch_id
            },
            batch_id or 'unknown',
            'workflow'
        )
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
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:discover',
                'message': f'发现 {total_links} 个链接',
                'total_links': total_links,
                'batch_id': batch_id
            },
            batch_id,
            'workflow'
        )
    
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
    # v3: Only transcript scrapers are used; comment scrapers have been removed.
    scraper_configs = [
        {
            'scraper_class': YouTubeScraper,
            'scraper_name': 'youtube',
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
    
    workflow_elapsed = time.time() - workflow_start_time
    
    if progress_callback:
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:complete',
                'message': f'抓取完成: {passed}/{total} 成功',
                'passed': passed,
                'total': total,
                'batch_id': batch_id
            },
            batch_id,
            'workflow'
        )
        
        # After sending scraping:complete, verify and send confirmation signal
        # The progress callback has access to check_completion function via closure
        # We'll check completion by calling it through the callback mechanism
        # Since we don't have direct access to ProgressService, we'll send a request
        # for the workflow service to verify and send confirmation
        
        # Wait a bit for final status updates to be processed
        logger.debug(f"[VERIFY] Waiting 0.5s for status updates to process before verification...")
        time.sleep(0.5)
        
        # Send request to verify completion (workflow service will handle verification)
        # We use a special message type that triggers verification
        logger.info(f"[VERIFY] Sending verify_completion request for batch {batch_id}")
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:verify_completion',
                'batch_id': batch_id,
                'message': 'Verifying all scraping processes are complete...'
            },
            batch_id,
            'workflow'
        )
    else:
        logger.info(f"Scrapers Summary: {passed}/{total} passed")
    
    if DEBUG_MODE:
        with _tracking_lock:
            if batch_id in _callback_tracking:
                tracking = _callback_tracking[batch_id]
                logger.info(
                    f"[DEBUG] Batch {batch_id} callback stats: "
                    f"total_callbacks={tracking['callback_count']}, "
                    f"unique_threads={len(tracking['threads'])}, "
                    f"workflow_elapsed={workflow_elapsed:.2f}s"
                )
    
    return {
        'batch_id': batch_id,
        'passed': passed,
        'total': total,
        'success': passed > 0  # At least one scraper succeeded
    }


def run_all_scrapers_direct_v2(
    progress_callback: Optional[Callable[[dict], None]] = None,
    batch_id: Optional[str] = None,
    cancellation_checker: Optional[Callable[[], bool]] = None,
    worker_pool_size: int = 8
) -> Dict[str, Any]:
    """
    Run all scrapers using the new centralized control center with dynamic worker pool.
    
    This version uses a centralized control center that maintains a constant pool
    of active workers (default 8) and dynamically assigns tasks from a unified queue.
    When a worker completes, it immediately picks up the next task, ensuring
    maximum efficiency and resource utilization.
    
    Args:
        progress_callback: Optional callable(message: dict) for progress updates.
                          Will be called with progress messages as scrapers run.
        batch_id: Optional batch ID. If not provided, will be loaded from TestLinksLoader.
        cancellation_checker: Optional function that returns True if cancelled.
        worker_pool_size: Number of parallel workers (default: 8)
        
    Returns:
        Dict with batch_id, success status, and results
    """
    from backend.lib.scraping_control_center import (
        ScrapingControlCenter,
        ScrapingTask,
        TaskStatus
    )
    
    workflow_start_time = time.time()
    
    if progress_callback:
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:start',
                'message': '开始抓取内容...',
                'batch_id': batch_id
            },
            batch_id or 'unknown',
            'workflow'
        )
    else:
        logger.info("Starting all scrapers with control center...")
    
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
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:discover',
                'message': f'发现 {total_links} 个链接',
                'total_links': total_links,
                'batch_id': batch_id
            },
            batch_id,
            'workflow'
        )
    
    if total_links == 0:
        logger.warning("No links found in test links file")
        return {
            'batch_id': batch_id,
            'success': False,
            'error': 'No links found',
            'passed': 0,
            'total': 0
        }
    
    # Create tasks for all links
    tasks: List[ScrapingTask] = []
    task_id_counter = 0
    
    # YouTube links - v3: create transcript tasks only (no comment scraping)
    for link in link_types['youtube']:
        task_id_counter += 1
        tasks.append(ScrapingTask(
            task_id=f"task_{task_id_counter:06d}",
            link_id=link['id'],
            url=link['url'],
            link_type='youtube',
            scraper_type='youtube',
            batch_id=batch_id
        ))
    
    # Bilibili links - v3: create transcript tasks only (no comment scraping)
    for link in link_types['bilibili']:
        task_id_counter += 1
        tasks.append(ScrapingTask(
            task_id=f"task_{task_id_counter:06d}",
            link_id=link['id'],
            url=link['url'],
            link_type='bilibili',
            scraper_type='bilibili',
            batch_id=batch_id
        ))
    
    # Article links
    for link in link_types['article']:
        task_id_counter += 1
        tasks.append(ScrapingTask(
            task_id=f"task_{task_id_counter:06d}",
            link_id=link['id'],
            url=link['url'],
            link_type='article',
            scraper_type='article',
            batch_id=batch_id
        ))
    
    # Reddit links
    for link in link_types['reddit']:
        task_id_counter += 1
        tasks.append(ScrapingTask(
            task_id=f"task_{task_id_counter:06d}",
            link_id=link['id'],
            url=link['url'],
            link_type='reddit',
            scraper_type='reddit',
            batch_id=batch_id
        ))
    
    logger.info(f"Created {len(tasks)} tasks for {total_links} links")
    
    # Create control center
    control_center = ScrapingControlCenter(
        worker_pool_size=worker_pool_size,
        progress_callback=progress_callback,
        cancellation_checker=cancellation_checker
    )
    
    # Add all tasks
    control_center.add_tasks(tasks)
    
    # Start control center
    control_center.start()
    
    # Wait for completion
    try:
        completed = control_center.wait_for_completion()
        
        if not completed:
            logger.warning("Control center did not complete all tasks")
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down...")
        control_center.shutdown(wait=True, timeout=30.0)
        raise
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        control_center.shutdown(wait=True, timeout=30.0)
        raise
    finally:
        # Shutdown control center
        control_center.shutdown(wait=True, timeout=30.0)
    
    # Collect results for statistics
    all_tasks = control_center.state_tracker.get_all_tasks()
    all_results = []
    
    for task in all_tasks:
        if task.result:
            all_results.append(task.result)
    
    # NOTE: Results are now saved incrementally in _handle_worker_completion
    # via _save_single_result, so we don't need to save them again here.
    # This prevents duplication and ensures files are available immediately.
    
    # Calculate success rate
    passed = sum(1 for r in all_results if r.get('success'))
    total = len(all_results)
    
    workflow_elapsed = time.time() - workflow_start_time
    
    # Get statistics
    stats = control_center.get_statistics()
    logger.info(
        f"Control center statistics: "
        f"completed={stats['tasks']['completed']}, "
        f"failed={stats['tasks']['failed']}, "
        f"race_conditions={stats['race_conditions_detected']}, "
        f"elapsed={stats['elapsed_seconds']:.2f}s"
    )
    
    if progress_callback:
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:complete',
                'message': f'抓取完成: {passed}/{total} 成功',
                'passed': passed,
                'total': total,
                'batch_id': batch_id
            },
            batch_id,
            'workflow'
        )
        
        # Wait a bit for final status updates to be processed
        logger.debug(f"[VERIFY] Waiting 0.5s for status updates to process before verification...")
        time.sleep(0.5)
        
        # Send request to verify completion
        logger.info(f"[VERIFY] Sending verify_completion request for batch {batch_id}")
        _safe_callback_invoke(
            progress_callback,
            {
                'type': 'scraping:verify_completion',
                'batch_id': batch_id,
                'message': 'Verifying all scraping processes are complete...'
            },
            batch_id,
            'workflow'
        )
    else:
        logger.info(f"Scrapers Summary: {passed}/{total} passed")
    
    if DEBUG_MODE:
        logger.info(
            f"[DEBUG] Control center stats: {stats}, "
            f"workflow_elapsed={workflow_elapsed:.2f}s"
        )
    
    return {
        'batch_id': batch_id,
        'passed': passed,
        'total': total,
        'success': passed > 0,  # At least one scraper succeeded
        'statistics': stats
    }

