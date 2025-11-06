"""
History API routes.

This module provides endpoints for managing research history,
including listing all sessions and resuming/deleting sessions by batch_id.
"""
import json
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

router = APIRouter()

# Session directory path
SESSIONS_DIR = project_root / "data" / "research" / "sessions"


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


def _map_session_status(metadata: Dict[str, Any]) -> str:
    """
    Map internal session status to frontend expected status.
    
    Args:
        metadata: Session metadata dictionary
    
    Returns:
        Status string: 'completed', 'in-progress', 'failed', or 'cancelled'
    """
    status = metadata.get("status", "").lower()
    finished = metadata.get("finished", False)
    
    # Check if explicitly completed
    if status == "completed" and finished:
        return "completed"
    
    # Check if explicitly failed or cancelled
    if status == "failed":
        return "failed"
    if status == "cancelled":
        return "cancelled"
    
    # Default to in-progress for any other status or if not finished
    return "in-progress"


def _extract_session_info(session_data: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    """
    Extract session information in frontend format.
    
    Args:
        session_data: Full session data dictionary
        session_id: Session ID (for fallback)
    
    Returns:
        Session info dictionary in frontend format, or None if invalid
    """
    try:
        metadata = session_data.get("metadata", {})
        
        # Extract batch_id - required field
        batch_id = metadata.get("batch_id")
        if not batch_id:
            logger.warning(f"Session {session_id} has no batch_id, skipping")
            return None
        
        # Extract created_at
        created_at = metadata.get("created_at", metadata.get("updated_at"))
        if not created_at:
            logger.warning(f"Session {session_id} has no created_at, skipping")
            return None
        
        # Map status
        status = _map_session_status(metadata)
        
        # Extract topic from synthesized_goal
        topic = None
        synthesized_goal = metadata.get("synthesized_goal", {})
        if isinstance(synthesized_goal, dict):
            topic = synthesized_goal.get("comprehensive_topic")
        
        # Extract URL count from quality_assessment
        url_count = None
        quality_assessment = metadata.get("quality_assessment", {})
        if isinstance(quality_assessment, dict):
            statistics = quality_assessment.get("statistics", {})
            if isinstance(statistics, dict):
                url_count = statistics.get("total_items")
        
        # Determine current_phase from session progress
        current_phase = None
        if status == "completed":
            current_phase = "complete"
        elif status == "in-progress":
            # Try to determine phase from metadata
            if metadata.get("research_plan"):
                current_phase = "research"
            elif metadata.get("data_loaded"):
                current_phase = "research"
            else:
                current_phase = "scraping"
        
        return {
            "batch_id": batch_id,
            "created_at": created_at,
            "status": status,
            "topic": topic,
            "url_count": url_count,
            "current_phase": current_phase,
            # Include session_id for reference
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Error extracting session info for {session_id}: {e}")
        return None


def _discover_all_sessions() -> List[Dict[str, Any]]:
    """
    Discover and load all session files.
    
    Returns:
        List of session info dictionaries in frontend format
    """
    sessions = []
    
    if not SESSIONS_DIR.exists():
        logger.warning(f"Sessions directory does not exist: {SESSIONS_DIR}")
        return sessions
    
    # Find all session files
    session_files = list(SESSIONS_DIR.glob("session_*.json"))
    logger.info(f"Found {len(session_files)} session files")
    
    for session_file in session_files:
        try:
            # Extract session_id from filename
            session_id = session_file.stem.replace("session_", "")
            
            # Load session data
            try:
                session_data = _safe_load_json_file(session_file)
            except json.JSONDecodeError as e:
                logger.error(f"Session file {session_file} contains invalid JSON: {e}")
                continue
            except IOError as e:
                logger.error(f"Failed to read session file {session_file}: {e}")
                continue
            
            # Extract session info
            session_info = _extract_session_info(session_data, session_id)
            if session_info:
                sessions.append(session_info)
        
        except Exception as e:
            logger.error(f"Error processing session file {session_file}: {e}")
            continue
    
    # Sort by created_at descending (newest first)
    sessions.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    
    return sessions


@router.get("")
async def get_history(
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
):
    """
    Get research history list.
    
    Returns all research sessions, including WIP/incomplete ones.
    Supports filtering by status and date range.
    """
    try:
        # Discover all sessions
        all_sessions = _discover_all_sessions()
        
        # Apply filters
        filtered_sessions = all_sessions
        
        # Filter by status
        if status:
            filtered_sessions = [
                s for s in filtered_sessions
                if s.get("status") == status
            ]
        
        # Filter by date range
        if date_from:
            try:
                # Normalize date string (handle Z suffix)
                date_from_str = date_from.replace('Z', '+00:00') if 'Z' in date_from else date_from
                date_from_dt = datetime.fromisoformat(date_from_str)
                
                filtered_sessions = [
                    s for s in filtered_sessions
                    if s.get("created_at") and datetime.fromisoformat(
                        s.get("created_at", "").replace('Z', '+00:00') if 'Z' in s.get("created_at", "") else s.get("created_at", "")
                    ) >= date_from_dt
                ]
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid date_from format: {date_from}, ignoring filter: {e}")
        
        if date_to:
            try:
                # Normalize date string (handle Z suffix)
                date_to_str = date_to.replace('Z', '+00:00') if 'Z' in date_to else date_to
                date_to_dt = datetime.fromisoformat(date_to_str)
                
                filtered_sessions = [
                    s for s in filtered_sessions
                    if s.get("created_at") and datetime.fromisoformat(
                        s.get("created_at", "").replace('Z', '+00:00') if 'Z' in s.get("created_at", "") else s.get("created_at", "")
                    ) <= date_to_dt
                ]
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid date_to format: {date_to}, ignoring filter: {e}")
        
        # Apply pagination
        total = len(filtered_sessions)
        if offset is not None:
            filtered_sessions = filtered_sessions[offset:]
        if limit is not None:
            filtered_sessions = filtered_sessions[:limit]
        
        return {
            "sessions": filtered_sessions,
            "total": total,
            "offset": offset or 0,
            "limit": limit,
        }
    
    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{batch_id}")
async def get_history_session(batch_id: str):
    """
    Get session details by batch_id.
    
    Finds the most recent session for the given batch_id.
    """
    try:
        # Discover all sessions
        all_sessions = _discover_all_sessions()
        
        # Find sessions matching batch_id
        matching_sessions = [
            s for s in all_sessions
            if s.get("batch_id") == batch_id
        ]
        
        if not matching_sessions:
            raise HTTPException(status_code=404, detail=f"Session with batch_id {batch_id} not found")
        
        # Get the most recent session (first in sorted list)
        session_info = matching_sessions[0]
        session_id = session_info.get("session_id")
        
        # Load full session data
        session_file = SESSIONS_DIR / f"session_{session_id}.json"
        if not session_file.exists():
            raise HTTPException(status_code=404, detail=f"Session file for batch_id {batch_id} not found")
        
        try:
            session_data = _safe_load_json_file(session_file)
        except json.JSONDecodeError as e:
            logger.error(f"Session file {session_file} contains invalid JSON: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Session file is corrupted: {str(e)}"
            )
        except IOError as e:
            logger.error(f"Failed to read session file {session_file}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read session file: {str(e)}"
            )
        
        # Add frontend-formatted info to response
        response = session_data.copy()
        response["frontend_info"] = session_info
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{batch_id}/resume")
async def resume_session(batch_id: str):
    """
    Resume a session by batch_id.
    
    This endpoint is a placeholder for resuming workflow.
    The actual resume logic should integrate with the workflow service.
    """
    try:
        # Verify session exists and get session info
        session_data = await get_history_session(batch_id)
        session_info = session_data.get("frontend_info", {})
        
        # TODO: Integrate with workflow service to actually resume
        # For now, just return success
        
        logger.info(f"Resume request for batch_id: {batch_id}")
        
        return {
            "batch_id": batch_id,
            "status": "resumed",
            "message": "Session resumed successfully",
            "session_info": session_info,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{batch_id}")
async def delete_session(batch_id: str):
    """
    Delete a session by batch_id.
    
    Finds and deletes the session file(s) for the given batch_id.
    """
    try:
        # Discover all sessions
        all_sessions = _discover_all_sessions()
        
        # Find sessions matching batch_id
        matching_sessions = [
            s for s in all_sessions
            if s.get("batch_id") == batch_id
        ]
        
        if not matching_sessions:
            raise HTTPException(status_code=404, detail=f"Session with batch_id {batch_id} not found")
        
        # Delete all session files for this batch_id
        deleted_count = 0
        for session_info in matching_sessions:
            session_id = session_info.get("session_id")
            session_file = SESSIONS_DIR / f"session_{session_id}.json"
            
            if session_file.exists():
                try:
                    session_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted session file: {session_file}")
                except Exception as e:
                    logger.error(f"Failed to delete session file {session_file}: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to delete session file: {str(e)}"
                    )
        
        return {
            "batch_id": batch_id,
            "status": "deleted",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} session(s) for batch_id {batch_id}",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

