"""
Workflow functions - thin wrappers around test_full_workflow_integration.

These functions use the proven, working code from tests/ folder.
They are simple re-exports that can be used directly by backend services.
"""
import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Re-export working test functions directly
# Backend services will use asyncio.to_thread() to call these sync functions
# and provide progress callbacks that queue messages for async processing
from tests.test_full_workflow_integration import (
    run_all_scrapers,
    run_research_agent,
)


def verify_scraper_results(batch_id: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
    """
    Verify that scraper results exist in the production results folder.
    
    This is a production version that looks in data/research/batches/ instead of tests/results/.
    
    Args:
        batch_id: The batch ID to check for
        progress_callback: Optional callable(message: dict) for progress updates.
        
    Returns:
        True if results exist, False otherwise
    """
    from core.config import Config
    
    # Use production path from config
    config = Config()
    results_dir = config.get_batches_dir() / f"run_{batch_id}"
    
    if not results_dir.exists():
        message = f"❌ Results directory not found: {results_dir}"
        logger.error(f"[VerifyResults] {message}")
        if progress_callback:
            progress_callback({"type": "error", "message": message})
        return False
    
    # Check for JSON files (either _complete.json or _scraped.json files)
    json_files = list(results_dir.glob("*.json"))
    
    if not json_files:
        message = f"❌ No JSON files found in {results_dir}"
        logger.error(f"[VerifyResults] {message}")
        if progress_callback:
            progress_callback({"type": "error", "message": message})
        return False
    
    # Count complete files (preferred indicator of success)
    complete_files = list(results_dir.glob("*_complete.json"))
    scraped_files = list(results_dir.glob("*_scraped.json"))
    
    logger.info(
        f"[VerifyResults] Found {len(json_files)} total files in {results_dir}: "
        f"{len(complete_files)} complete, {len(scraped_files)} scraped"
    )
    
    if progress_callback:
        progress_callback({
            "type": "verification:progress",
            "message": f"找到 {len(complete_files)} 个完整结果文件",
            "file_count": len(complete_files),
            "total_files": len(json_files)
        })
    
    # Create per-batch manifest for research agent discovery
    try:
        manifest = []
        for json_file in sorted(json_files):
            # Only include complete files in manifest
            if not json_file.name.endswith('_complete.json'):
                continue
                
            rel_path = json_file.name
            entry = {
                "relative_path": rel_path,
                "batch_id": batch_id,
                "size_bytes": json_file.stat().st_size
            }
            # Infer source, link_id, kind from filename when possible
            stem = json_file.stem
            parts = stem.split('_')
            if len(parts) >= 4:
                # Format: {batch_id}_{SOURCE}_{link_id}_complete
                entry['source_prefix'] = parts[1]
                entry['link_id'] = parts[2]
                entry['kind'] = parts[3] if len(parts) > 3 else 'complete'
            manifest.append(entry)
        
        manifest_path = results_dir / "manifest.json"
        import json
        with open(manifest_path, 'w', encoding='utf-8') as mf:
            json.dump({
                "batch_id": batch_id,
                "total_files": len(manifest),
                "items": manifest
            }, mf, indent=2, ensure_ascii=False)
        
        logger.info(f"[VerifyResults] Created manifest with {len(manifest)} items at {manifest_path}")
        
    except Exception as e:
        logger.warning(f"[VerifyResults] Failed to create manifest: {e}")
    
    return len(complete_files) > 0


__all__ = [
    'run_all_scrapers',
    'verify_scraper_results',
    'run_research_agent',
]

