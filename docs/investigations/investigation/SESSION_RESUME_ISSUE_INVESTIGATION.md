# Session Resume Issue Investigation

## Problem Statement

When pressing "Continue" on a historic task that is not completed, a new session ID is created for the same batch ID. This is incorrect behavior. The system should:
1. Identify which phase/step the batch+session is at
2. Resume work based on that progress
3. Provide a script to make it possible to resume at any given point of progress

## Root Cause Analysis

### Current Flow

1. **Initial Session Creation (During Scraping)**
   - Location: `backend/app/services/workflow_service.py:2133`
   - Code: `session = ResearchSession.create_or_load(batch_id)`
   - Behavior: Uses `batch_id` as `session_id` when creating the session
   - Session file: `data/research/sessions/session_{batch_id}.json`

2. **Resume Flow (When Clicking Continue)**
   - Frontend: `client/src/pages/HistoryPage.tsx:182` - `handleResume()`
   - Calls: `apiService.resumeSession(batchId)`
   - Backend: `backend/app/routes/history.py:561` - `resume_session()`
   - Delegates to: `workflow_routes.run_workflow_task(batch_id)`
   - Workflow Service: `backend/app/services/workflow_service.py:1965-2006`

3. **Session Lookup Logic (The Problem)**
   - Location: `backend/app/services/workflow_service.py:1965-2006`
   - Current behavior:
     ```python
     # Check if this is a resume of an existing session
     session_id = None
     skip_scraping = False
     # Try to find existing session for this batch_id
     sessions_dir = project_root / "data" / "research" / "sessions"
     if sessions_dir.exists():
         session_files = list(sessions_dir.glob("session_*.json"))
         for session_file in session_files:
             session_data = json.load(f)
             metadata = session_data.get("metadata", {})
             session_batch_id = metadata.get("batch_id")
             if session_batch_id == batch_id:
                 session_id = metadata.get("session_id")
                 phase_artifacts = session_data.get("phase_artifacts", {})
                 has_phase0 = "phase0" in phase_artifacts
                 if has_phase0:
                     skip_scraping = True
                 break
     ```
   - **Issue**: Only sets `session_id` if it finds a matching batch_id AND only if phase0 exists
   - **Problem**: If session lookup fails or phase0 doesn't exist, `session_id` remains `None`

4. **Research Agent Session Creation (The Bug)**
   - Location: `research/agent.py:566-580`
   - Code:
     ```python
     def run_research(self, batch_id: str, user_topic: Optional[str] = None, session_id: Optional[str] = None):
         if session_id:
             try:
                 session = ResearchSession.load(session_id)
                 logger.info(f"Resumed session: {session_id}")
             except FileNotFoundError:
                 logger.warning(f"Session not found: {session_id}, creating new")
                 session = ResearchSession(session_id=session_id)
         else:
             session = ResearchSession()  # Creates NEW session with auto-generated ID!
     ```
   - **Issue**: When `session_id` is `None`, it creates a new session with auto-generated timestamp-based ID
   - **Result**: New session_id for the same batch_id

### Why This Happens

1. **Session Lookup is Incomplete**: The lookup only checks for phase0 existence, not all phases
2. **No Fallback to Batch ID**: If session lookup fails, it doesn't use `batch_id` as `session_id` (which is how sessions are initially created)
3. **Missing Progress Detection**: The system doesn't determine which phase/step the session is at before resuming
4. **No Resume Point Logic**: There's no logic to determine where to resume from based on completed phases

## Current Session Structure

### Session File Format
- Location: `data/research/sessions/session_{session_id}.json`
- Structure:
  ```json
  {
    "metadata": {
      "session_id": "20251117_072443",
      "batch_id": "20251117_072443",
      "created_at": "2025-11-17T15:24:44",
      "status": "in-progress",
      ...
    },
    "scratchpad": {
      "step_1": {...},
      "step_2": {...}
    },
    "phase_artifacts": {
      "phase0": {...},      // Scraping phase
      "phase0_5": {...},    // Role generation
      "phase1": {...},      // Goal discovery
      "phase2": {...},      // Plan finalization
      "phase3": {...},      // Execution (contains steps)
      "phase4": {...}       // Synthesis
    },
    "step_digests": [...]
  }
  ```

### Phase Detection Logic
- Location: `backend/app/routes/history.py:339` - `_infer_current_phase()`
- Determines current phase based on:
  - Status field
  - Phase artifacts presence
  - Phase3 step completion

## Required Fixes

### 1. Fix Session Lookup in Workflow Service

**Location**: `backend/app/services/workflow_service.py:1965-2006`

**Changes Needed**:
- Always find existing session by batch_id (regardless of phase)
- Use batch_id as session_id if no session found (since that's how they're created)
- Don't rely on phase0 existence to determine if session exists
- Set session_id before calling run_research_agent

**Proposed Fix**:
```python
# Check if this is a resume of an existing session
session_id = None
skip_scraping = False

# Try to find existing session for this batch_id
sessions_dir = project_root / "data" / "research" / "sessions"
if sessions_dir.exists():
    session_files = list(sessions_dir.glob("session_*.json"))
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            metadata = session_data.get("metadata", {})
            session_batch_id = metadata.get("batch_id")
            if session_batch_id == batch_id:
                session_id = metadata.get("session_id")
                phase_artifacts = session_data.get("phase_artifacts", {})
                has_phase0 = "phase0" in phase_artifacts
                if has_phase0:
                    skip_scraping = True
                break
        except Exception as e:
            logger.warning(f"Error checking session file {session_file}: {e}")
            continue

# FALLBACK: If no session found, use batch_id as session_id
# (This matches how sessions are initially created)
if session_id is None:
    session_id = batch_id
    logger.info(f"No existing session found for batch {batch_id}, will use batch_id as session_id")
```

### 2. Add Progress Detection Logic

**New Function Needed**: Determine which phase/step to resume from

**Location**: `backend/app/services/workflow_service.py` (new method)

**Logic**:
```python
def _determine_resume_point(self, session: ResearchSession) -> Dict[str, Any]:
    """
    Determine which phase and step to resume from based on session state.
    
    Returns:
        {
            "phase": "scraping" | "research" | "phase3" | "complete",
            "step_id": int | None,  # For phase3
            "skip_phases": List[str]  # Phases to skip
        }
    """
    phase_artifacts = session.phase_artifacts
    metadata = session.metadata
    
    # Check phase completion in order
    if "phase4" in phase_artifacts:
        return {"phase": "complete", "step_id": None, "skip_phases": []}
    
    if "phase3" in phase_artifacts:
        phase3_data = phase_artifacts["phase3"].get("data", {})
        phase3_result = phase3_data.get("phase3_result", {})
        completed_steps = phase3_result.get("completed_step_ids", [])
        next_step_id = phase3_result.get("next_step_id")
        
        if next_step_id:
            return {
                "phase": "phase3",
                "step_id": next_step_id,
                "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
            }
    
    if "phase2" in phase_artifacts:
        return {
            "phase": "phase3",
            "step_id": None,
            "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
        }
    
    if "phase1" in phase_artifacts:
        return {
            "phase": "phase2",
            "step_id": None,
            "skip_phases": ["phase0", "phase0_5", "phase1"]
        }
    
    if "phase0_5" in phase_artifacts:
        return {
            "phase": "phase1",
            "step_id": None,
            "skip_phases": ["phase0", "phase0_5"]
        }
    
    if "phase0" in phase_artifacts:
        return {
            "phase": "phase0_5",
            "step_id": None,
            "skip_phases": ["phase0"]
        }
    
    # Default: start from scraping
    return {
        "phase": "scraping",
        "step_id": None,
        "skip_phases": []
    }
```

### 3. Update Research Agent to Support Resume Points

**Location**: `research/agent.py:566`

**Changes Needed**:
- Accept resume point information
- Skip completed phases
- Resume from specific step in phase3

**Proposed Changes**:
```python
def run_research(
    self,
    batch_id: str,
    user_topic: Optional[str] = None,
    session_id: Optional[str] = None,
    resume_point: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # Load or create session
    if session_id:
        try:
            session = ResearchSession.load(session_id)
            logger.info(f"Resumed session: {session_id}")
        except FileNotFoundError:
            logger.warning(f"Session not found: {session_id}, creating new")
            session = ResearchSession(session_id=session_id)
    else:
        session = ResearchSession()
    
    # Determine resume point if not provided
    if resume_point is None:
        resume_point = self._determine_resume_point(session)
    
    skip_phases = resume_point.get("skip_phases", [])
    
    # Run phases conditionally based on resume point
    if "phase0" not in skip_phases:
        phase0_artifact = self.run_phase0_prepare(...)
    else:
        phase0_artifact = session.get_phase_artifact("phase0")
    
    # ... similar for other phases
    
    # For phase3, resume from specific step if provided
    if resume_point.get("phase") == "phase3" and resume_point.get("step_id"):
        phase3_result = self.run_phase3_execute(
            ...,
            resume_from_step=resume_point["step_id"]
        )
```

### 4. Create Resume Script

**New File**: `scripts/resume_session.py`

**Purpose**: Allow manual resumption of any session at any point

**Features**:
- List all sessions with their progress
- Resume a specific session
- Resume from a specific phase/step
- Force resume (ignore completion status)

**Proposed Structure**:
```python
#!/usr/bin/env python3
"""
Script to resume research sessions at any point.

Usage:
    python scripts/resume_session.py list
    python scripts/resume_session.py resume <session_id>
    python scripts/resume_session.py resume <session_id> --phase <phase>
    python scripts/resume_session.py resume <session_id> --step <step_id>
    python scripts/resume_session.py resume <session_id> --force
"""

import argparse
from pathlib import Path
import json
from research.session import ResearchSession
from research.agent import DeepResearchAgent

def list_sessions():
    """List all available sessions with their progress."""
    sessions_dir = Path("data/research/sessions")
    if not sessions_dir.exists():
        print("No sessions directory found")
        return
    
    sessions = []
    for session_file in sorted(sessions_dir.glob("session_*.json")):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            metadata = data.get("metadata", {})
            phase_artifacts = data.get("phase_artifacts", {})
            
            sessions.append({
                "session_id": metadata.get("session_id"),
                "batch_id": metadata.get("batch_id"),
                "status": metadata.get("status"),
                "phases": list(phase_artifacts.keys()),
                "created_at": metadata.get("created_at")
            })
        except Exception as e:
            print(f"Error reading {session_file}: {e}")
    
    # Print formatted list
    print(f"\n{'Session ID':<20} {'Batch ID':<20} {'Status':<15} {'Phases':<30}")
    print("-" * 85)
    for s in sessions:
        phases_str = ", ".join(s["phases"][:3])
        if len(s["phases"]) > 3:
            phases_str += "..."
        print(f"{s['session_id']:<20} {s['batch_id']:<20} {s['status']:<15} {phases_str:<30}")

def resume_session(session_id: str, phase: str = None, step_id: int = None, force: bool = False):
    """Resume a session from a specific point."""
    try:
        session = ResearchSession.load(session_id)
        batch_id = session.metadata.get("batch_id")
        
        if not batch_id:
            print(f"Error: Session {session_id} has no batch_id")
            return
        
        print(f"Resuming session {session_id} (batch: {batch_id})")
        
        # Determine resume point
        resume_point = {
            "phase": phase or "auto",
            "step_id": step_id,
            "force": force
        }
        
        # Create agent and resume
        agent = DeepResearchAgent()
        result = agent.run_research(
            batch_id=batch_id,
            session_id=session_id,
            resume_point=resume_point
        )
        
        print(f"\nResume completed: {result}")
        
    except FileNotFoundError:
        print(f"Error: Session {session_id} not found")
    except Exception as e:
        print(f"Error resuming session: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume research sessions")
    subparsers = parser.add_subparsers(dest="command")
    
    list_parser = subparsers.add_parser("list", help="List all sessions")
    
    resume_parser = subparsers.add_parser("resume", help="Resume a session")
    resume_parser.add_argument("session_id", help="Session ID to resume")
    resume_parser.add_argument("--phase", help="Phase to resume from")
    resume_parser.add_argument("--step", type=int, help="Step ID to resume from (for phase3)")
    resume_parser.add_argument("--force", action="store_true", help="Force resume even if completed")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_sessions()
    elif args.command == "resume":
        resume_session(args.session_id, args.phase, args.step, args.force)
    else:
        parser.print_help()
```

## Implementation Plan

### Phase 1: Fix Core Resume Logic
1. ✅ Fix session lookup in `workflow_service.py` to always find session by batch_id
2. ✅ Add fallback to use batch_id as session_id if no session found
3. ✅ Ensure session_id is always set before calling `run_research_agent`

### Phase 2: Add Progress Detection
1. ✅ Implement `_determine_resume_point()` method
2. ✅ Update workflow service to use resume point
3. ✅ Pass resume point to research agent

### Phase 3: Update Research Agent
1. ✅ Add resume_point parameter to `run_research()`
2. ✅ Implement phase skipping logic
3. ✅ Implement step resumption for phase3

### Phase 4: Create Resume Script
1. ✅ Create `scripts/resume_session.py`
2. ✅ Add list functionality
3. ✅ Add resume functionality with options
4. ✅ Test with various session states

## Testing Scenarios

1. **Resume Incomplete Scraping Session**
   - Session has batch_id but no phase0
   - Should resume from scraping

2. **Resume After Scraping Complete**
   - Session has phase0 but no phase1
   - Should resume from phase0_5 (role generation)

3. **Resume During Phase3**
   - Session has phase3 with some steps completed
   - Should resume from next incomplete step

4. **Resume Completed Session**
   - Session has phase4
   - Should not resume (or allow force resume)

5. **Resume Session with Missing Session File**
   - Batch_id exists but session file missing
   - Should create new session with batch_id as session_id

## Related Files

### Backend
- `backend/app/routes/history.py` - History API endpoints
- `backend/app/services/workflow_service.py` - Workflow orchestration
- `backend/app/routes/workflow.py` - Workflow API routes

### Research
- `research/agent.py` - Main research agent
- `research/session.py` - Session management

### Frontend
- `client/src/pages/HistoryPage.tsx` - History page with Continue button
- `client/src/services/api.ts` - API service

## Notes

- Sessions are initially created with `batch_id` as `session_id` during scraping
- The session lookup logic needs to be more robust
- Progress detection should be based on phase_artifacts, not just phase0
- The resume script should be a utility for manual intervention

