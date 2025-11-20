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
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.session import ResearchSession
from research.agent import DeepResearchAgent
from core.config import Config
from loguru import logger


def list_sessions() -> None:
    """List all available sessions with their progress."""
    sessions_dir = project_root / "data" / "research" / "sessions"
    if not sessions_dir.exists():
        print("No sessions directory found")
        return
    
    sessions: List[Dict[str, Any]] = []
    for session_file in sorted(sessions_dir.glob("session_*.json")):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            metadata = data.get("metadata", {})
            phase_artifacts = data.get("phase_artifacts", {})
            
            # Determine current phase
            current_phase = "unknown"
            if "phase4" in phase_artifacts:
                current_phase = "phase4 (complete)"
            elif "phase3" in phase_artifacts:
                phase3_data = phase_artifacts.get("phase3", {})
                phase3_result = phase3_data.get("data", {}).get("phase3_result", {})
                completed_steps = phase3_result.get("completed_step_ids", [])
                total_steps = len(phase3_result.get("plan", []))
                if total_steps > 0:
                    current_phase = f"phase3 (step {len(completed_steps)}/{total_steps})"
                else:
                    current_phase = "phase3"
            elif "phase2" in phase_artifacts:
                current_phase = "phase2"
            elif "phase1" in phase_artifacts:
                current_phase = "phase1"
            elif "phase0_5" in phase_artifacts:
                current_phase = "phase0_5"
            elif "phase0" in phase_artifacts:
                current_phase = "phase0"
            else:
                current_phase = "initialized"
            
            sessions.append({
                "session_id": metadata.get("session_id"),
                "batch_id": metadata.get("batch_id"),
                "status": metadata.get("status", "unknown"),
                "current_phase": current_phase,
                "phases": list(phase_artifacts.keys()),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at")
            })
        except Exception as e:
            print(f"Error reading {session_file}: {e}")
    
    if not sessions:
        print("No sessions found")
        return
    
    # Print formatted list
    print(f"\n{'Session ID':<20} {'Batch ID':<20} {'Status':<15} {'Current Phase':<25}")
    print("-" * 80)
    for s in sessions:
        print(f"{s['session_id']:<20} {s['batch_id']:<20} {s['status']:<15} {s['current_phase']:<25}")


def determine_resume_point(session: ResearchSession, phase: Optional[str] = None, step_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Determine resume point from session or user input.
    
    Args:
        session: ResearchSession instance
        phase: Optional phase to resume from (overrides auto-detection)
        step_id: Optional step ID to resume from (for phase3)
        
    Returns:
        Resume point dictionary
    """
    if phase:
        # User specified phase
        skip_phases = []
        phase_order = ["phase0", "phase0_5", "phase1", "phase2", "phase3", "phase4"]
        if phase in phase_order:
            phase_index = phase_order.index(phase)
            skip_phases = phase_order[:phase_index]
        
        return {
            "phase": phase,
            "step_id": step_id,
            "skip_phases": skip_phases
        }
    
    # Auto-detect from session
    phase_artifacts = session.phase_artifacts
    
    if "phase4" in phase_artifacts:
        return {
            "phase": "complete",
            "step_id": None,
            "skip_phases": ["phase0", "phase0_5", "phase1", "phase2", "phase3", "phase4"]
        }
    
    if "phase3" in phase_artifacts:
        phase3_entry = phase_artifacts.get("phase3", {})
        phase3_data = phase3_entry.get("data", {}) if isinstance(phase3_entry, dict) else {}
        phase3_result = phase3_data.get("phase3_result", {})
        
        completed_steps = phase3_result.get("completed_step_ids", [])
        next_step_id = phase3_result.get("next_step_id")
        
        if step_id is not None:
            # User specified step
            return {
                "phase": "phase3",
                "step_id": step_id,
                "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
            }
        
        if next_step_id is not None:
            return {
                "phase": "phase3",
                "step_id": next_step_id,
                "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
            }
        
        # Find first incomplete step
        plan = phase3_result.get("plan", [])
        if isinstance(plan, list) and len(plan) > 0:
            step_ids = [step.get("step_id") for step in plan if isinstance(step, dict)]
            for sid in step_ids:
                if sid not in completed_steps:
                    return {
                        "phase": "phase3",
                        "step_id": sid,
                        "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
                    }
        
        return {
            "phase": "phase3",
            "step_id": None,
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
    
    # Default: start from beginning
    return {
        "phase": "scraping",
        "step_id": None,
        "skip_phases": []
    }


def resume_session(session_id: str, phase: Optional[str] = None, step_id: Optional[int] = None, force: bool = False) -> None:
    """Resume a session from a specific point."""
    try:
        session = ResearchSession.load(session_id)
        batch_id = session.metadata.get("batch_id")
        
        if not batch_id:
            print(f"Error: Session {session_id} has no batch_id")
            return
        
        status = session.metadata.get("status", "unknown")
        if status == "completed" and not force:
            print(f"Warning: Session {session_id} is marked as completed.")
            print("Use --force to resume anyway.")
            return
        
        print(f"Resuming session {session_id} (batch: {batch_id})")
        
        # Determine resume point
        resume_point = determine_resume_point(session, phase, step_id)
        print(f"Resume point: phase={resume_point['phase']}, step_id={resume_point.get('step_id')}, skip_phases={resume_point.get('skip_phases', [])}")
        
        # Get API key
        config = Config()
        api_key = config.get("qwen.api_key")
        if not api_key:
            api_key = __import__("os").environ.get("DASHSCOPE_API_KEY") or __import__("os").environ.get("QWEN_API_KEY")
        
        if not api_key:
            print("Error: API key not found. Set DASHSCOPE_API_KEY or configure in config.yaml")
            return
        
        # Create agent
        agent = DeepResearchAgent(api_key=api_key)
        
        # Resume
        print("Starting resume...")
        result = agent.run_research(
            batch_id=batch_id,
            session_id=session_id,
            resume_point=resume_point
        )
        
        if result.get("status") == "completed":
            print(f"\n✓ Resume completed successfully")
            print(f"  Session ID: {session_id}")
            print(f"  Batch ID: {batch_id}")
        elif result.get("status") == "cancelled":
            print(f"\n✗ Resume was cancelled")
        else:
            print(f"\n✗ Resume did not complete. Status: {result.get('status')}")
        
    except FileNotFoundError:
        print(f"Error: Session {session_id} not found")
    except Exception as e:
        print(f"Error resuming session: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume research sessions")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    list_parser = subparsers.add_parser("list", help="List all sessions")
    
    resume_parser = subparsers.add_parser("resume", help="Resume a session")
    resume_parser.add_argument("session_id", help="Session ID to resume")
    resume_parser.add_argument("--phase", help="Phase to resume from (phase0, phase0_5, phase1, phase2, phase3, phase4)")
    resume_parser.add_argument("--step", type=int, help="Step ID to resume from (for phase3)")
    resume_parser.add_argument("--force", action="store_true", help="Force resume even if completed")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_sessions()
    elif args.command == "resume":
        resume_session(args.session_id, args.phase, args.step, args.force)
    else:
        parser.print_help()


