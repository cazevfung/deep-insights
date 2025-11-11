"""
Reports API routes.
"""
import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
from fastapi import APIRouter, HTTPException
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

router = APIRouter()


def _safe_load_json_file(file_path: Path, max_retries: int = 3, retry_delay: float = 0.1):
    """
    Safely load JSON file with retry logic for file locking issues.
    
    Args:
        file_path: Path to JSON file
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Parsed JSON data as dictionary
    
    Raises:
        json.JSONDecodeError: If file contains invalid JSON
        IOError: If file cannot be read after retries
    """
    import time
    last_error = None
    for attempt in range(max_retries):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Don't retry JSON decode errors - file is corrupted
            raise
        except (IOError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                logger.warning(f"Retry {attempt + 1}/{max_retries} reading {file_path}: {e}")
            else:
                raise IOError(f"Failed to read file after {max_retries} attempts: {str(e)}") from last_error
    
    raise IOError(f"Failed to read file: {str(last_error)}")


def _find_report_file(batch_id: str) -> Tuple[Optional[Path], Optional[str]]:
    """
    Find report file by batch_id.
    
    Checks:
    1. tests/results/reports/report_{batch_id}_{session_id}.md
    2. data/research/reports/report_{session_id}.md (if session can be found)
    
    Args:
        batch_id: Batch ID to search for
    
    Returns:
        Tuple of (report_file_path, session_id) or (None, None) if not found
    """
    # Try to find report in tests/results/reports/ (pattern: report_{batch_id}_{session_id}.md)
    test_reports_dir = project_root / "tests" / "results" / "reports"
    if test_reports_dir.exists():
        pattern = f"report_{batch_id}_*.md"
        for report_file in test_reports_dir.glob(pattern):
            # Extract session_id from filename
            match = re.match(rf"report_{re.escape(batch_id)}_(.+?)\.md", report_file.name)
            if match:
                session_id = match.group(1)
                return report_file, session_id
    
    # Try to find report in data/research/reports/ by checking session files
    # First, find all sessions that match batch_id
    sessions_dir = project_root / "data" / "research" / "sessions"
    matching_sessions = []
    
    if sessions_dir.exists():
        for session_file in sessions_dir.glob("session_*.json"):
            try:
                session_data = _safe_load_json_file(session_file)
                metadata = session_data.get("metadata", {})
                
                # Check if this session matches the requested batch_id
                if metadata.get("batch_id") == batch_id:
                    session_id_match = re.match(r"session_(.+?)\.json", session_file.name)
                    if session_id_match:
                        session_id = session_id_match.group(1)
                        # Check if report file exists
                        reports_dir = project_root / "data" / "research" / "reports"
                        report_file = reports_dir / f"report_{session_id}.md"
                        if report_file.exists():
                            # Prioritize sessions with:
                            # 1. status="completed" (highest priority)
                            # 2. final_report metadata exists
                            # 3. Most recent update time
                            priority = 0
                            if metadata.get("status") == "completed":
                                priority += 1000
                            if metadata.get("final_report"):
                                priority += 100
                            updated_at = metadata.get("updated_at", metadata.get("created_at", ""))
                            
                            matching_sessions.append({
                                "report_file": report_file,
                                "session_id": session_id,
                                "priority": priority,
                                "updated_at": updated_at
                            })
            except Exception as e:
                logger.debug(f"Error reading session file {session_file}: {e}")
                continue
        
        # Sort by priority (descending), then by updated_at (descending)
        if matching_sessions:
            matching_sessions.sort(key=lambda x: (x["priority"], x["updated_at"]), reverse=True)
            best_match = matching_sessions[0]
            logger.info(f"Found {len(matching_sessions)} sessions for batch_id {batch_id}, selecting session {best_match['session_id']} (priority={best_match['priority']})")
            return best_match["report_file"], best_match["session_id"]
    
    return None, None


def _extract_metadata_from_report(report_content: str, batch_id: str, session_id: Optional[str]) -> dict:
    """
    Extract metadata from report markdown content.
    
    Args:
        report_content: Markdown content of report
        batch_id: Batch ID
        session_id: Session ID if available
    
    Returns:
        Dictionary with metadata
    """
    metadata = {
        "batchId": batch_id,
        "sessionId": session_id,
        "generatedAt": None,
        "topic": None,
    }
    
    # Extract from markdown header
    lines = report_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("**研究目标**:") or line.startswith("**研究目标**:"):
            topic = line.split(":", 1)[1].strip() if ":" in line else None
            if topic:
                metadata["topic"] = topic
        elif line.startswith("**生成时间**:") or line.startswith("**生成时间**:"):
            time_str = line.split(":", 1)[1].strip() if ":" in line else None
            if time_str:
                metadata["generatedAt"] = time_str
        elif line.startswith("**批次ID**:") or line.startswith("**批次ID**:"):
            # Already have batch_id, but verify
            pass
    
    return metadata


def _get_session_metadata(session_id: str) -> dict:
    """
    Get additional metadata from session file.
    
    Args:
        session_id: Session ID
    
    Returns:
        Dictionary with session metadata
    """
    session_file = project_root / "data" / "research" / "sessions" / f"session_{session_id}.json"
    if not session_file.exists():
        return {}
    
    try:
        session_data = _safe_load_json_file(session_file)
        metadata = session_data.get("metadata", {})
        return {
            "originalTopic": metadata.get("comprehensive_topic"),
            "componentQuestions": metadata.get("component_questions", []),
            "status": session_data.get("status", "unknown"),
        }
    except Exception as e:
        logger.warning(f"Failed to read session metadata: {e}")
        return {}


@router.get("/{batch_id}")
async def get_report(batch_id: str):
    """
    Get final report by batch_id.
    
    Returns enhanced JSON structure with content, metadata, and editHistory.
    """
    try:
        # Find report file
        report_file, session_id = _find_report_file(batch_id)
        
        if not report_file or not report_file.exists():
            raise HTTPException(status_code=404, detail=f"Report not found for batch_id: {batch_id}")
        
        # Read report content
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read report file {report_file}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to read report file: {str(e)}")
        
        # Extract metadata from report
        report_metadata = _extract_metadata_from_report(report_content, batch_id, session_id)
        
        # Get additional metadata from session if available
        session_metadata = {}
        if session_id:
            session_metadata = _get_session_metadata(session_id)
        
        # Combine metadata
        metadata = {
            **report_metadata,
            **session_metadata,
        }
        
        # Get file modification time as fallback for generatedAt
        if not metadata.get("generatedAt"):
            try:
                mtime = report_file.stat().st_mtime
                metadata["generatedAt"] = datetime.fromtimestamp(mtime).isoformat()
            except Exception:
                metadata["generatedAt"] = datetime.now().isoformat()
        
        # Return enhanced JSON structure
        return {
            "content": report_content,
            "metadata": metadata,
            "editHistory": [],  # Empty for now, will be populated when editing is implemented
            "currentVersion": 1,
            "status": "ready",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

