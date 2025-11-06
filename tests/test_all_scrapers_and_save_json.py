"""Discover and run all test_*.py scripts directly under the tests folder.

Enhancements:
- Run four production lines in parallel by default:
  1) Bilibili Transcript, 2) Bilibili Comments, 3) YouTube Transcript, 4) YouTube Comments
- Dynamic work-stealing: if a line finishes early, it can run remaining tasks from other lines
- Flexible grouping: no hardcoded execution order; groups are derived from filenames
- Progress tracking: durations, statuses, and aggregate summary
- Waits for transcript files to be saved before marking scraping as complete
"""
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque, defaultdict
from typing import Dict, List, Tuple, Optional

# Ensure project root is on path (in case individual tests rely on it)
sys.path.insert(0, str(Path(__file__).parent.parent))


def _group_scripts(scripts: List[Path]) -> Dict[str, deque]:
    """Group discovered scripts into four production lines and an optional 'other' queue.

    - bili_transcripts: test_bilibili_scraper.py
    - bili_comments:   test_bilibili_comments_scraper.py
    - yt_transcripts:  test_youtube_scraper.py
    - yt_comments:     test_youtube_comments_scraper.py
    - other:           any remaining test_*_scraper.py files
    """
    groups: Dict[str, deque] = {
        "bili_transcripts": deque(),
        "bili_comments": deque(),
        "yt_transcripts": deque(),
        "yt_comments": deque(),
        "other": deque(),
    }

    name_to_group = {
        "test_bilibili_scraper.py": "bili_transcripts",
        "test_bilibili_comments_scraper.py": "bili_comments",
        "test_youtube_scraper.py": "yt_transcripts",
        "test_youtube_comments_scraper.py": "yt_comments",
    }

    # Ensure deterministic order within each queue by sorting names
    for p in sorted(scripts, key=lambda x: x.name):
        group = name_to_group.get(p.name, "other")
        groups[group].append(p)

    return groups


def _wait_for_transcript_files(script_name: str, batch_id: str, tests_dir: Path, max_wait_seconds: int = 300) -> bool:
    """
    Wait for transcript files to be saved and stable before marking as complete.
    
    Args:
        script_name: Name of the script (e.g., 'test_bilibili_scraper.py')
        batch_id: Batch ID to check for expected files
        tests_dir: Tests directory path
        max_wait_seconds: Maximum time to wait (default 5 minutes)
        
    Returns:
        True if files are saved and stable, False if timeout
    """
    if script_name != "test_bilibili_scraper.py":
        # Only check for bilibili transcript scraper
        return True
    
    try:
        from tests.test_links_loader import TestLinksLoader
        loader = TestLinksLoader()
        bili_links = loader.get_links('bilibili')
        
        if not bili_links:
            # No bilibili links, nothing to wait for
            return True
        
        results_dir = tests_dir / "results" / f"run_{batch_id}"
        expected_files = []
        
        for link in bili_links:
            link_id = link.get('id', 'unknown')
            expected_file = results_dir / f"{batch_id}_BILI_{link_id}_tsct.json"
            expected_files.append(expected_file)
        
        if not expected_files:
            return True
        
        print(f"  ⏳ Waiting for {len(expected_files)} transcript file(s) to be saved...")
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        stable_period = 5  # File must be stable (unchanged) for 5 seconds
        last_print_time = 0
        print_interval = 10  # Print status every 10 seconds
        
        last_mod_times: Dict[Path, float] = {}
        stable_since: Dict[Path, float] = {}
        
        while time.time() - start_time < max_wait_seconds:
            all_stable = True
            all_exist = True
            
            for file_path in expected_files:
                if file_path.exists():
                    current_mtime = file_path.stat().st_mtime
                    
                    # Check if file modification time changed
                    if file_path in last_mod_times and last_mod_times[file_path] != current_mtime:
                        # File is still being written
                        last_mod_times[file_path] = current_mtime
                        stable_since[file_path] = time.time()
                        all_stable = False
                    elif file_path not in last_mod_times:
                        # File just appeared
                        last_mod_times[file_path] = current_mtime
                        stable_since[file_path] = time.time()
                        all_stable = False
                    else:
                        # File exists and hasn't changed
                        if file_path not in stable_since:
                            stable_since[file_path] = time.time()
                        
                        # Check if file has been stable long enough
                        if time.time() - stable_since[file_path] < stable_period:
                            all_stable = False
                else:
                    # File doesn't exist yet
                    all_exist = False
                    all_stable = False
                    if file_path in stable_since:
                        del stable_since[file_path]
            
            # Only return True if all files exist AND are stable
            if all_exist and all_stable:
                saved_count = len(expected_files)
                print(f"  ✓ All transcript files saved and stable ({saved_count}/{len(expected_files)} files)")
                return True
            elif not all_exist:
                # Some files are missing - wait longer
                current_time = time.time()
                if current_time - last_print_time >= print_interval:
                    missing = [f.name for f in expected_files if not f.exists()]
                    elapsed = int(current_time - start_time)
                    print(f"  ⏳ Waiting for {len(missing)} missing file(s) ({elapsed}s elapsed)...")
                    last_print_time = current_time
            
            time.sleep(check_interval)
        
        # Timeout - check how many files were saved
        saved_count = sum(1 for f in expected_files if f.exists())
        if saved_count > 0:
            print(f"  ⚠️  Timeout waiting for transcript files ({saved_count}/{len(expected_files)} saved, some may still be in progress)")
        else:
            print(f"  ⚠️  Timeout waiting for transcript files (none saved yet)")
        return False
        
    except Exception as e:
        print(f"  ⚠️  Error checking transcript files: {e}")
        # Don't fail the entire process if checking fails
        return True


def _run_script(script: Path, tests_dir: Path) -> Tuple[str, int, float]:
    start_ts = datetime.now()
    # Set timeout to 15 minutes (900 seconds) to handle long transcriptions
    # Bilibili transcript scraper can take 5-10 minutes per video
    timeout_seconds = 900
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tests_dir),
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        print(f"⚠️  {script.name} timed out after {timeout_seconds}s")
        # Return a non-zero exit code to indicate timeout
        completed = subprocess.CompletedProcess([sys.executable, str(script)], returncode=124)
    
    # For transcript scrapers, wait for files to be saved before marking as complete
    if script.name == "test_bilibili_scraper.py":
        try:
            from tests.test_links_loader import TestLinksLoader
            loader = TestLinksLoader()
            batch_id = loader.get_batch_id()
            
            # Wait for transcript files to be saved (up to 5 minutes)
            files_ready = _wait_for_transcript_files(script.name, batch_id, tests_dir, max_wait_seconds=300)
            
            if not files_ready:
                # Files may still be in progress, but we've waited long enough
                # Don't mark as failure, but log warning
                print(f"  ⚠️  {script.name} completed but transcript files may still be in progress")
        except Exception as e:
            # If checking fails, don't fail the entire process
            print(f"  ⚠️  Could not verify transcript files: {e}")
    
    end_ts = datetime.now()
    duration_s = (end_ts - start_ts).total_seconds()
    return script.name, completed.returncode, duration_s


def test_all_scrapers_and_save(progress_callback=None):
    """
    Auto-discover and run scraper tests with four parallel production lines and work-stealing.
    
    Args:
        progress_callback: Optional callable(message: dict) for progress updates.
                          Will be called with progress messages as scrapers complete.
    """
    if progress_callback:
        progress_callback({
            "type": "scraping:discover",
            "message": "正在发现并运行所有抓取脚本..."
        })
    else:
        print("\n" + "=" * 80)
        print("Discovering and Running Scraper Test Scripts in tests/ (parallel production lines)")
        print("=" * 80)

    tests_dir = Path(__file__).parent
    runner_name = Path(__file__).name

    # Only scripts directly under tests folder matching test_*_scraper.py
    scripts = [p for p in tests_dir.glob("test_*_scraper.py")]

    if not scripts:
        message = "No test_*_scraper.py scripts found directly under tests/."
        if progress_callback:
            progress_callback({"type": "warning", "message": message})
        else:
            print(message)
        return []

    groups = _group_scripts(scripts)

    # Build initial work: four production lines; 'other' can be stolen by any idle worker
    production_lines = [
        ("bili_transcripts", groups["bili_transcripts"]),
        ("bili_comments", groups["bili_comments"]),
        ("yt_transcripts", groups["yt_transcripts"]),
        ("yt_comments", groups["yt_comments"]),
    ]
    other_queue = groups["other"]

    # Progress tracking
    run_results: List[Dict[str, object]] = []
    total_scripts = sum(len(q) for _, q in production_lines) + len(other_queue)

    # Thread pool to orchestrate subprocess calls concurrently
    # Using threads is fine here because each task is an external subprocess call
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Active futures per line
        line_futures: Dict[str, List] = defaultdict(list)

        def submit_next_from(queue_name: str, queue: deque):
            if queue:
                script = queue.popleft()
                if progress_callback:
                    progress_callback({
                        "type": "scraping:start_script",
                        "message": f"开始运行: {script.name}",
                        "script": script.name,
                        "line": queue_name
                    })
                else:
                    print("\n" + "-" * 80)
                    print(f"[line={queue_name}] Running {script.name}")
                    print("-" * 80)
                fut = executor.submit(_run_script, script, tests_dir)
                line_futures[queue_name].append(fut)
                return True
            return False

        # Initial submissions: one per line if available
        for name, q in production_lines:
            submit_next_from(name, q)

        # Work-stealing loop
        completed_count = 0
        while completed_count < total_scripts:
            # Collect any completed future across all lines
            all_futs = [f for futs in line_futures.values() for f in futs]
            if not all_futs:
                # No active futures -> steal new work from any queue or 'other'
                progressed = False
                for name, q in production_lines:
                    progressed |= submit_next_from(name, q)
                if not progressed and other_queue:
                    submit_next_from("other", other_queue)
                continue

            for fut in as_completed(all_futs):
                # Find which line this future belonged to and remove it
                owning_line = None
                for name, futs in line_futures.items():
                    if fut in futs:
                        futs.remove(fut)
                        owning_line = name
                        break

                script_name, returncode, duration_s = fut.result()
                status_text = "OK" if returncode == 0 else f"FAIL ({returncode})"
                success = returncode == 0
                
                if progress_callback:
                    progress_callback({
                        "type": "scraping:script_complete",
                        "message": f"{script_name}: {status_text} ({duration_s:.1f}s)",
                        "script": script_name,
                        "success": success,
                        "returncode": returncode,
                        "duration": duration_s,
                        "line": owning_line or "unknown",
                        "progress": f"{completed_count + 1}/{total_scripts}"
                    })
                else:
                    print(f"Finished {script_name} -> {status_text} in {duration_s:.1f}s")
                
                run_results.append({
                    "script": script_name,
                    "returncode": returncode,
                    "duration_seconds": duration_s,
                    "line": owning_line or "unknown",
                })
                completed_count += 1

                # Try to submit next from the same line first
                if owning_line and owning_line != "other":
                    for name, q in production_lines:
                        if name == owning_line:
                            if submit_next_from(name, q):
                                break
                            # Steal from other queues if this one is empty
                            stolen = False
                            for alt_name, alt_q in production_lines:
                                if alt_name == owning_line:
                                    continue
                                if submit_next_from(alt_name, alt_q):
                                    stolen = True
                                    break
                            if not stolen and other_queue:
                                submit_next_from("other", other_queue)
                            break

                # Break after handling one completion to refresh all_futs snapshot
                break

    # Summary
    num_ok = sum(1 for r in run_results if r["returncode"] == 0)
    
    if progress_callback:
        progress_callback({
            "type": "scraping:summary",
            "message": f"抓取完成: {num_ok}/{total_scripts} 成功",
            "passed": num_ok,
            "total": total_scripts,
            "results": run_results
        })
    else:
        print("\n" + "=" * 80)
        print("Test Scripts Summary")
        print("=" * 80)
        print(f"Passed: {num_ok}/{total_scripts}")
        for r in run_results:
            status = "OK" if r["returncode"] == 0 else f"FAIL ({r['returncode']})"
            line = r.get("line", "?")
            print(f"- [{line}] {r['script']}: {status} in {r['duration_seconds']:.1f}s")

    return run_results


if __name__ == '__main__':
    test_all_scrapers_and_save()

