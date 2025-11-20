"""
Simplified workflow service using proven test functions.

This service uses the working code from tests/ folder directly,
with WebSocket progress callbacks for real-time updates.
"""
from typing import Dict, Optional, Any, List
from pathlib import Path
import sys
import asyncio
import queue
import time
import os
import json
from collections import defaultdict
from loguru import logger

# Ensure Playwright can spawn subprocesses on Windows by defaulting to Proactor policy.
if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.debug("Set WindowsProactorEventLoopPolicy for Playwright compatibility")
    except Exception as policy_err:  # pragma: no cover - defensive
        logger.warning(f"Could not set WindowsProactorEventLoopPolicy: {policy_err}")

# Debug mode flag
DEBUG_MODE = os.environ.get('WORKFLOW_DEBUG', 'false').lower() == 'true'

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import working test functions via backend.lib
from backend.lib import (
    run_all_scrapers,
    run_all_scrapers_direct,  # Direct execution with progress callbacks
    verify_scraper_results,
    run_research_agent,
)

# Import new control center version
from backend.lib.workflow_direct import run_all_scrapers_direct_v2
from research.agent import DeepResearchAgent
from research.session import ResearchSession
from app.websocket.manager import WebSocketManager
from app.services.progress_service import ProgressService
from app.services.conversation_service import ConversationContextService
from app.services.websocket_ui import WebSocketUI
from datetime import datetime
from core.config import Config


# Process count per link type
# v3: We only scrape transcripts; comment scraping has been disabled.
PROCESSES_PER_LINK_TYPE = {
    'youtube': 1,   # transcript only
    'bilibili': 1,  # transcript only
    'reddit': 1,
    'article': 1,
}


def calculate_total_scraping_processes(links_by_type: Dict[str, list]) -> Dict[str, Any]:
    """
    Calculate total number of scraping processes from links.
    
    This is the single source of truth for calculating total processes.
    
    Args:
        links_by_type: Dict mapping link_type -> list of {id, url} dicts
            Example: {
                'youtube': [{'id': 'yt1', 'url': '...'}, ...],
                'bilibili': [{'id': 'bili1', 'url': '...'}, ...],
                'reddit': [{'id': 'rd1', 'url': '...'}, ...],
                'article': [{'id': 'art1', 'url': '...'}, ...]
            }
    
    Returns:
        Dict with:
            - total_processes: int (total count)
            - total_links: int (total link count)
            - breakdown: Dict[str, int] (processes per type)
            - link_breakdown: Dict[str, int] (links per type)
            - process_mapping: List[Dict] (detailed process list)
    """
    total_links = sum(len(links) for links in links_by_type.values())
    
    breakdown = {}
    link_breakdown = {}
    process_mapping = []
    
    for link_type, links in links_by_type.items():
        link_count = len(links)
        process_count = link_count * PROCESSES_PER_LINK_TYPE.get(link_type, 1)
        
        link_breakdown[link_type] = link_count
        breakdown[link_type] = process_count
        
        # Build detailed process mapping
        # v3: All link types (including YouTube/Bilibili) are treated as single-process transcript scrapers.
        for link_info in links:
            process_mapping.append({
                'link_id': link_info.get('id') or link_info.get('link_id'),
                'url': link_info.get('url'),
                'scraper_type': link_type,
                'process_type': 'transcript'
            })
    
    expected_total = sum(breakdown.values())
    
    return {
        'expected_total': expected_total,  # Standardized name - total scraping processes expected
        'total_processes': expected_total,  # Keep for backward compatibility (deprecated)
        'total_links': total_links,
        'breakdown': breakdown,
        'link_breakdown': link_breakdown,
        'process_mapping': process_mapping
    }


def _run_scrapers_in_thread(progress_callback, batch_id, cancellation_checker=None):
    """
    Wrapper function to run scrapers in a thread with proper Playwright initialization.
    
    This ensures Playwright/Chromium can be launched properly when called from asyncio.to_thread().
    The function runs in a separate thread, so Playwright can initialize its browser process.
    
    Args:
        progress_callback: Progress callback function
        batch_id: Batch ID
        cancellation_checker: Optional function that returns True if cancelled
        
    Returns:
        Result dictionary from run_all_scrapers_direct
    """
    try:
        # Ensure we're in a proper thread context
        import threading
        import os
        current_thread = threading.current_thread()
        logger.info(f"Running scrapers in thread: {current_thread.name} (ID: {current_thread.ident})")
        
        # Log environment info for debugging
        logger.debug(f"Current working directory: {os.getcwd()}")
        logger.debug(f"Python executable: {sys.executable}")
        logger.debug(f"Thread name: {current_thread.name}")

        # On Windows, ensure we use a Proactor event loop so Playwright can spawn subprocesses.
        # Uvicorn's reload mode switches the global policy to WindowsSelectorEventLoopPolicy,
        # which breaks asyncio.create_subprocess_exec used by Playwright.
        if os.name == "nt":
            try:
                from asyncio import windows_events  # type: ignore
                current_loop: Optional[asyncio.AbstractEventLoop] = None
                try:
                    current_loop = asyncio.get_event_loop()
                except RuntimeError:
                    current_loop = None

                if current_loop and current_loop.is_running():
                    logger.debug("Existing event loop already running; skipping loop swap")
                elif current_loop and isinstance(current_loop, windows_events.ProactorEventLoop):
                    logger.debug("ProactorEventLoop already configured for this thread")
                else:
                    if current_loop is not None:
                        try:
                            current_loop.close()
                        except Exception:
                            pass
                    proactor_loop = windows_events.ProactorEventLoop()
                    asyncio.set_event_loop(proactor_loop)
                    logger.debug("Configured ProactorEventLoop for Playwright compatibility on Windows")
            except Exception as loop_err:  # pragma: no cover - best effort safeguard
                logger.warning(f"Could not configure ProactorEventLoop on Windows: {loop_err}")
        
        # Ensure Playwright can find its browser
        # Check if PLAYWRIGHT_BROWSERS_PATH is set
        playwright_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        if playwright_path:
            logger.debug(f"PLAYWRIGHT_BROWSERS_PATH: {playwright_path}")
        else:
            logger.debug("PLAYWRIGHT_BROWSERS_PATH not set (using default)")
        
        # Create batch directory immediately when scraping starts
        # This ensures the directory exists before any files are saved
        from pathlib import Path
        # Use configured batches directory
        config = Config()
        output_dir = config.get_batches_dir()
        output_dir.mkdir(exist_ok=True, parents=True)
        batch_folder = output_dir / f"run_{batch_id}"
        batch_folder.mkdir(exist_ok=True)
        logger.info(f"Created batch directory: {batch_folder}")
        
        # Run the scrapers - Playwright will initialize in this thread
        logger.info(f"Starting scrapers execution in thread...")
        
        # Get worker pool size from config or environment variable
        worker_pool_size = 8
        max_concurrent_scrapers = None
        try:
            config_obj = Config()
            scraping_config = config_obj.get('scraping', {}).get('control_center', {})
            worker_pool_size = scraping_config.get('worker_pool_size', 8)
            max_concurrent_scrapers = scraping_config.get('max_concurrent_scrapers')
            # If max_concurrent_scrapers is set and valid, cap worker_pool_size
            if max_concurrent_scrapers and max_concurrent_scrapers > 0:
                if worker_pool_size > max_concurrent_scrapers:
                    logger.info(f"Capping worker_pool_size from {worker_pool_size} to {max_concurrent_scrapers} (max_concurrent_scrapers limit)")
                    worker_pool_size = max_concurrent_scrapers
        except Exception:
            pass
        
        # Check environment variable override
        env_worker_size = os.environ.get('SCRAPING_WORKER_POOL_SIZE', '')
        if env_worker_size:
            worker_pool_size = int(env_worker_size)
            # Still respect max_concurrent_scrapers if set
            if max_concurrent_scrapers and max_concurrent_scrapers > 0:
                if worker_pool_size > max_concurrent_scrapers:
                    logger.info(f"Capping worker_pool_size from {worker_pool_size} to {max_concurrent_scrapers} (max_concurrent_scrapers limit)")
                    worker_pool_size = max_concurrent_scrapers
        
        # Use new control center system
        logger.info(f"Using control center with {worker_pool_size} workers")
        result = run_all_scrapers_direct_v2(
            progress_callback=progress_callback,
            batch_id=batch_id,
            cancellation_checker=cancellation_checker,
            worker_pool_size=worker_pool_size
        )
        
        logger.info(f"Scrapers completed in thread: {current_thread.name}")
        return result
        
    except Exception as e:
        logger.error(f"Error running scrapers in thread: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


class WorkflowService:
    """
    Simplified workflow service using proven test functions.
    
    This service directly uses the working code from tests/ folder,
    with progress callbacks for real-time WebSocket updates.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.progress_service = ProgressService(websocket_manager)
        self.conversation_service = ConversationContextService()
        self.ws_manager.set_conversation_service(self.conversation_service)
        self.conversation_service.set_websocket_manager(self.ws_manager)
        # Track link context for progress callbacks
        # Maps batch_id -> scraper_type -> list of {link_id, url}
        self.link_context: Dict[str, Dict[str, list]] = {}
        
        # Track total counts per batch
        # Maps batch_id -> {
        #     'total_processes': int,
        #     'total_links': int,
        #     'breakdown': Dict[str, int],
        #     'link_breakdown': Dict[str, int],
        #     'calculated_at': datetime,
        #     'source': 'user_input' | 'test_links_loader'
        # }
        self.batch_totals: Dict[str, Dict[str, Any]] = {}
        
        # Track streaming summarization managers per batch
        # Maps batch_id -> StreamingSummarizationManager instance
        self.streaming_managers: Dict[str, Any] = {}
        
        # Debug tracking
        if DEBUG_MODE:
            self._queue_stats: Dict[str, Dict] = defaultdict(lambda: {
                'messages_processed': 0,
                'messages_dropped': 0,
                'max_queue_size': 0,
                'queue_size_history': [],
                'processing_times': []
            })
            self._link_id_transformations: Dict[str, list] = defaultdict(list)
            self._message_sequence: Dict[str, int] = defaultdict(int)

    def _normalize_phase_key(self, phase: str) -> str:
        phase = (phase or "").lower()
        mapping = {
            "phase0.5": "phase0_5",
            "phase0-5": "phase0_5",
            "phase0_5": "phase0_5",
        }
        normalized = mapping.get(phase, phase)
        valid = {"phase0", "phase0_5", "phase1", "phase2", "phase3", "phase4"}
        if normalized not in valid:
            raise ValueError(f"Unsupported phase '{phase}'")
        return normalized

    def _resolve_phase_sequence(self, phase: str, rerun_downstream: bool = True) -> List[str]:
        order = ["phase0", "phase0_5", "phase1", "phase2", "phase3", "phase4"]
        phase_key = self._normalize_phase_key(phase)
        if phase_key not in order:
            raise ValueError(f"Unsupported phase '{phase}'")
        if not rerun_downstream:
            return [phase_key]
        start_index = order.index(phase_key)
        return order[start_index:]

    def _load_artifact(self, session: ResearchSession, cache: Dict[str, Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
        if key in cache:
            return cache[key]
        cached = session.get_phase_artifact(key)
        if cached:
            cache[key] = cached
        return cached

    def _determine_resume_point(self, session_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine which phase and step to resume from based on session state.
        
        Args:
            session_data: Session data dictionary (from JSON file) or None
            
        Returns:
            {
                "phase": "scraping" | "research" | "phase3" | "complete",
                "step_id": int | None,  # For phase3
                "skip_phases": List[str]  # Phases to skip
            }
        """
        if not session_data:
            # No session data - start from beginning
            return {
                "phase": "scraping",
                "step_id": None,
                "skip_phases": []
            }
        
        phase_artifacts = session_data.get("phase_artifacts", {})
        if not isinstance(phase_artifacts, dict):
            phase_artifacts = {}
        
        # Check phase completion in order (most complete first)
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
            
            # Check for completed steps (can be either a count or array) and next step
            completed_steps_value = phase3_result.get("completed_steps", phase3_result.get("completed_step_ids", []))
            next_step_id = phase3_result.get("next_step_id")
            
            # If there's a next_step_id, resume from that step
            if next_step_id is not None:
                return {
                    "phase": "phase3",
                    "step_id": next_step_id,
                    "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
                }
            
            # If phase3 exists but no next step, check if all steps are done
            plan = phase3_result.get("plan", [])
            if isinstance(plan, list) and len(plan) > 0:
                total_steps = len(plan)
                
                # Handle both formats: completed_steps as count or as array of IDs
                if isinstance(completed_steps_value, int):
                    completed_count = completed_steps_value
                elif isinstance(completed_steps_value, list):
                    completed_count = len(completed_steps_value)
                else:
                    completed_count = 0
                
                if completed_count >= total_steps:
                    # All steps done, move to phase4
                    return {
                        "phase": "phase4",
                        "step_id": None,
                        "skip_phases": ["phase0", "phase0_5", "phase1", "phase2", "phase3"]
                    }
                else:
                    # Some steps incomplete, find first incomplete step
                    if isinstance(completed_steps_value, list):
                        # If we have an array of completed step IDs, find missing ones
                        step_ids = [step.get("step_id") for step in plan if isinstance(step, dict)]
                        for step_id in step_ids:
                            if step_id not in completed_steps_value:
                                return {
                                    "phase": "phase3",
                                    "step_id": step_id,
                                    "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
                                }
                    else:
                        # If we only have a count, resume from next step after completed count
                        if completed_count < total_steps and completed_count >= 0:
                            next_step = plan[completed_count] if completed_count < len(plan) else plan[-1]
                            return {
                                "phase": "phase3",
                                "step_id": next_step.get("step_id") if isinstance(next_step, dict) else None,
                                "skip_phases": ["phase0", "phase0_5", "phase1", "phase2"]
                            }
            
            # Phase3 exists but unclear state - resume from phase3 start
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
        
        # Default: start from scraping
        return {
            "phase": "scraping",
            "step_id": None,
            "skip_phases": []
        }

    def _execute_phase_sequence(
        self,
        *,
        agent: DeepResearchAgent,
        session: ResearchSession,
        batch_id: str,
        user_topic: Optional[str],
        phases: List[str],
    ) -> Dict[str, Any]:
        artifacts: Dict[str, Dict[str, Any]] = {}

        if user_topic is None:
            user_topic = session.get_metadata("user_topic", None)

        for phase_name in phases:
            if phase_name == "phase0":
                artifacts["phase0"] = agent.run_phase0_prepare(
                    batch_id=batch_id,
                    session=session,
                    force=True,
                )
            elif phase_name == "phase0_5":
                phase0 = artifacts.get("phase0") or self._load_artifact(session, artifacts, "phase0")
                if not phase0:
                    raise ValueError("Phase 0 artifacts missing; cannot rerun Phase 0.5")
                artifacts["phase0_5"] = agent.run_phase0_5_role_generation(
                    session=session,
                    combined_abstract=phase0["combined_abstract"],
                    user_topic=user_topic,
                    force=True,
                )
            elif phase_name == "phase1":
                phase0 = artifacts.get("phase0") or self._load_artifact(session, artifacts, "phase0")
                if not phase0:
                    raise ValueError("Phase 0 artifacts missing; cannot rerun Phase 1")
                phase0_5 = artifacts.get("phase0_5") or self._load_artifact(session, artifacts, "phase0_5")
                batch_data = phase0["batch_data"]
                artifacts["phase1"] = agent.run_phase1_discover(
                    session=session,
                    combined_abstract=phase0["combined_abstract"],
                    user_topic=user_topic,
                    research_role=phase0_5.get("research_role") if phase0_5 else None,
                    pre_role_feedback=(phase0_5 or {}).get("pre_role_feedback"),
                    batch_data=batch_data,
                    force=True,
                )
            elif phase_name == "phase2":
                phase0 = artifacts.get("phase0") or self._load_artifact(session, artifacts, "phase0")
                phase1_artifact = artifacts.get("phase1") or self._load_artifact(session, artifacts, "phase1")
                phase0_5 = artifacts.get("phase0_5") or self._load_artifact(session, artifacts, "phase0_5")
                if not phase0 or not phase1_artifact:
                    raise ValueError("Phase 0 and Phase 1 artifacts required for Phase 2 rerun")
                artifacts["phase2"] = agent.run_phase2_synthesize(
                    session=session,
                    phase1_artifact=phase1_artifact,
                    combined_abstract=phase0["combined_abstract"],
                    user_topic=user_topic,
                    pre_role_feedback=(phase0_5 or {}).get("pre_role_feedback"),
                    force=True,
                )
            elif phase_name == "phase3":
                phase0 = artifacts.get("phase0") or self._load_artifact(session, artifacts, "phase0")
                phase2_artifact = artifacts.get("phase2") or self._load_artifact(session, artifacts, "phase2")
                if not phase0 or not phase2_artifact:
                    raise ValueError("Phase 0 and Phase 2 artifacts required for Phase 3 rerun")
                plan = phase2_artifact.get("plan", [])
                if not plan:
                    raise ValueError("Plan missing from Phase 2 artifacts")
                artifacts["phase3"] = agent.run_phase3_execute(
                    session=session,
                    plan=plan,
                    batch_data=phase0["batch_data"],
                    force=True,
                    require_confirmation=False,
                )
            elif phase_name == "phase4":
                phase2_artifact = artifacts.get("phase2") or self._load_artifact(session, artifacts, "phase2")
                phase3_artifact = artifacts.get("phase3") or self._load_artifact(session, artifacts, "phase3")
                if not phase2_artifact or not phase3_artifact:
                    raise ValueError("Phase 2 and Phase 3 artifacts required for Phase 4 rerun")
                artifacts["phase4"] = agent.run_phase4_synthesize(
                    session=session,
                    phase2_artifact=phase2_artifact,
                    phase3_artifact=phase3_artifact,
                    batch_id=batch_id,
                    force=True,
                )
            else:
                raise ValueError(f"Unsupported phase '{phase_name}'")

        return artifacts

    def _execute_phase3_step(
        self,
        *,
        agent: DeepResearchAgent,
        session: ResearchSession,
        batch_id: str,
        step_id: int,
        regenerate_report: bool,
    ) -> Dict[str, Any]:
        phase0 = session.get_phase_artifact("phase0")
        if not phase0:
            phase0 = agent.run_phase0_prepare(batch_id=batch_id, session=session, force=True)

        phase2 = session.get_phase_artifact("phase2")
        if not phase2 or not phase2.get("plan"):
            raise ValueError("Phase 2 artifacts missing or invalid; cannot rerun step")

        plan = phase2.get("plan", [])
        batch_data = phase0.get("batch_data", {})
        artifacts = {}

        artifacts["phase3"] = agent.rerun_phase3_step(
            session=session,
            plan=plan,
            batch_data=batch_data,
            step_id=step_id,
        )

        if regenerate_report:
            phase3 = artifacts["phase3"]
            artifacts["phase4"] = agent.run_phase4_synthesize(
                session=session,
                phase2_artifact=phase2,
                phase3_artifact=phase3,
                batch_id=batch_id,
                force=True,
            )

        return artifacts

    async def rerun_phase(
        self,
        batch_id: str,
        session_id: str,
        phase: str,
        *,
        rerun_downstream: bool = True,
        user_topic: Optional[str] = None,
    ):
        sequence = self._resolve_phase_sequence(phase, rerun_downstream)
        await self.ws_manager.broadcast(batch_id, {
            "type": "research:phase_rerun_started",
            "batch_id": batch_id,
            "session_id": session_id,
            "phase": sequence[0],
            "phases": sequence,
        })

        loop = asyncio.get_running_loop()
        ui = WebSocketUI(
            self.ws_manager,
            batch_id,
            main_loop=loop,
            conversation_service=self.conversation_service,
        )
        self.ws_manager.register_ui(batch_id, ui)

        try:
            agent = DeepResearchAgent(ui=ui)
            session = ResearchSession.load(session_id)
            artifacts = await asyncio.to_thread(
                self._execute_phase_sequence,
                agent=agent,
                session=session,
                batch_id=batch_id,
                user_topic=user_topic,
                phases=sequence,
            )
            response_payload: Dict[str, Any] = {
                "type": "research:phase_rerun_complete",
                "batch_id": batch_id,
                "session_id": session_id,
                "phase": sequence[0],
                "phases": sequence,
            }
            if "phase2" in artifacts:
                response_payload["plan"] = artifacts["phase2"].get("plan")
            if "phase4" in artifacts:
                response_payload["report_path"] = artifacts["phase4"].get("report_path")
                response_payload["additional_report_paths"] = artifacts["phase4"].get("additional_report_paths")
                response_payload["report_stale"] = False
                # If phase4 was rerun, send research:complete signal
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:complete",
                    "batch_id": batch_id,
                    "session_id": session_id,
                    "status": "completed",
                    "message": "研究完成",
                })
            elif "phase3" in artifacts:
                response_payload["report_stale"] = True
            await self.ws_manager.broadcast(batch_id, response_payload)
        except Exception as exc:
            logger.error(f"Phase rerun failed: {exc}", exc_info=True)
            await self.ws_manager.broadcast(batch_id, {
                "type": "research:phase_rerun_error",
                "batch_id": batch_id,
                "session_id": session_id,
                "phase": sequence[0],
                "message": str(exc),
            })
            raise
        finally:
            self.ws_manager.unregister_ui(batch_id)

    async def rerun_phase3_step(
        self,
        batch_id: str,
        session_id: str,
        step_id: int,
        *,
        regenerate_report: bool = True,
    ):
        await self.ws_manager.broadcast(batch_id, {
            "type": "research:step_rerun_started",
            "batch_id": batch_id,
            "session_id": session_id,
            "step_id": step_id,
            "regenerate_report": regenerate_report,
        })

        loop = asyncio.get_running_loop()
        ui = WebSocketUI(
            self.ws_manager,
            batch_id,
            main_loop=loop,
            conversation_service=self.conversation_service,
        )
        self.ws_manager.register_ui(batch_id, ui)

        try:
            agent = DeepResearchAgent(ui=ui)
            session = ResearchSession.load(session_id)
            artifacts = await asyncio.to_thread(
                self._execute_phase3_step,
                agent=agent,
                session=session,
                batch_id=batch_id,
                step_id=step_id,
                regenerate_report=regenerate_report,
            )

            response_payload: Dict[str, Any] = {
                "type": "research:step_rerun_complete",
                "batch_id": batch_id,
                "session_id": session_id,
                "step_id": step_id,
                "regenerate_report": regenerate_report,
            }
            if "phase3" in artifacts:
                response_payload["updated_phase3"] = {
                    "plan": artifacts["phase3"].get("plan"),
                    "plan_hash": artifacts["phase3"].get("plan_hash"),
                }
            if regenerate_report and "phase4" in artifacts:
                response_payload["report_path"] = artifacts["phase4"].get("report_path")
                response_payload["additional_report_paths"] = artifacts["phase4"].get("additional_report_paths")
                response_payload["report_stale"] = False
                # If report was regenerated, send research:complete signal
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:complete",
                    "batch_id": batch_id,
                    "session_id": session_id,
                    "status": "completed",
                    "message": "研究完成",
                })
            else:
                response_payload["report_stale"] = True
            await self.ws_manager.broadcast(batch_id, response_payload)
        except Exception as exc:
            logger.error(f"Step rerun failed: {exc}", exc_info=True)
            await self.ws_manager.broadcast(batch_id, {
                "type": "research:step_rerun_error",
                "batch_id": batch_id,
                "session_id": session_id,
                "step_id": step_id,
                "message": str(exc),
            })
            raise
        finally:
            self.ws_manager.unregister_ui(batch_id)
    
    async def _load_link_context(self, batch_id: str):
        """
        Load link context from TestLinksLoader for this batch_id.
        Also pre-registers all expected links in the progress service to ensure accurate total count.
        
        Args:
            batch_id: Batch ID to load links for
        """
        try:
            from tests.test_links_loader import TestLinksLoader
            loader = TestLinksLoader()
            
            # Verify batch_id matches
            loader_batch_id = loader.get_batch_id()
            if loader_batch_id != batch_id:
                logger.warning(f"Batch ID mismatch: loader has {loader_batch_id}, expected {batch_id}")
            
            # Build link context mapping: scraper_type -> list of {link_id, url}
            context: Dict[str, list] = {}
            all_expected_processes = []  # Collect all expected PROCESSES (not just links)
            
            for link_type in ['youtube', 'bilibili', 'reddit', 'article']:
                links = loader.get_links(link_type)
                link_list = [
                    {'link_id': link['id'], 'url': link['url']}
                    for link in links
                ]
                context[link_type] = link_list
                
                # Count expected processes based on link type:
                # v3: All sources use a single transcript-only scraping process per link.
                for link_info in link_list:
                    all_expected_processes.append({
                        'link_id': link_info['link_id'],
                        'url': link_info['url'],
                        'scraper_type': link_type,  # 'youtube', 'bilibili', 'reddit', 'article'
                        'process_type': 'transcript'
                    })
            
            self.link_context[batch_id] = context
            
            # Calculate total processes using centralized function
            totals = calculate_total_scraping_processes(context)
            total_links = totals['total_links']
            # Use expected_total as the standardized name (total_processes is deprecated but kept for backward compatibility)
            expected_total = totals['expected_total']
            
            # Store totals in batch_totals
            self.batch_totals[batch_id] = {
                'expected_total': expected_total,  # Standardized name - primary field
                'total_processes': expected_total,  # Deprecated - kept for backward compatibility
                'total_links': total_links,
                'breakdown': totals['breakdown'],
                'link_breakdown': totals['link_breakdown'],
                'calculated_at': datetime.now().isoformat(),
                'source': 'test_links_loader'
            }
            
            logger.info(f"Loaded link context for batch {batch_id}: {total_links} links → {expected_total} expected processes")
            
            # Debug: Log link context details
            if DEBUG_MODE:
                logger.debug(f"[CONTEXT] Batch {batch_id} link context:")
                for link_type, links in context.items():
                    logger.debug(f"  {link_type}: {len(links)} links")
                    for link in links:
                        logger.debug(f"    - {link['link_id']}: {link['url']}")
                
                logger.debug(f"[CONTEXT] Batch {batch_id} expected processes: {len(all_expected_processes)}")
                for proc in all_expected_processes:
                    logger.debug(
                        f"  - {proc['link_id']} ({proc['scraper_type']}, {proc['process_type']})"
                    )
            
            # Pre-register all expected processes in progress service
            # This ensures total count is accurate from the start, preventing premature completion
            registered_count = self.progress_service.initialize_expected_links(batch_id, all_expected_processes)
            logger.info(f"Pre-registered {registered_count} expected processes in progress tracker for batch {batch_id}")
            
            if DEBUG_MODE:
                if registered_count != expected_total:
                    logger.warning(
                        f"[CONTEXT] Mismatch: expected {expected_total} processes, "
                        f"registered {registered_count}"
                    )
            
            # Send batch:initialized message with total count
            # Use expected_total as primary field (consistent with scraping:status)
            # Keep total_processes temporarily for backward compatibility (can be removed later)
            await self.ws_manager.broadcast(batch_id, {
                'type': 'batch:initialized',
                'batch_id': batch_id,
                'expected_total': expected_total,  # Standardized name - primary field
                'total_processes': expected_total,  # Deprecated - kept for backward compatibility only
                'total_links': total_links,
                'breakdown': totals['breakdown'],
                'link_breakdown': totals['link_breakdown'],
                'timestamp': datetime.now().isoformat(),
                'message': f'已初始化批次，共 {expected_total} 个抓取任务'
            })
            
            # Send initial batch status update with correct total
            await self.progress_service._update_batch_status(batch_id)
            
        except Exception as e:
            error_msg = f"Failed to load link context for batch {batch_id}: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Initialize empty context to indicate failure
            # This will be caught by validation in start_workflow
            self.link_context[batch_id] = {}
            logger.warning(f"Initialized empty link context for batch {batch_id} due to error")
    
    def _normalize_scraper_type(self, scraper_type: str) -> str:
        """
        Normalize scraper type to match link types in TestLinksLoader.
        
        Args:
            scraper_type: Scraper type from class name (e.g., 'youtubecomments', 'bilibilicomments')
            
        Returns:
            Normalized type (e.g., 'youtube', 'bilibili')
        """
        # Map comments scrapers to their base types
        if scraper_type == 'youtubecomments':
            return 'youtube'
        elif scraper_type == 'bilibilicomments':
            return 'bilibili'
        # Other types match directly
        return scraper_type
    
    def _find_link_info(self, batch_id: str, scraper_type: str, link_id: Optional[str] = None, url: Optional[str] = None):
        """
        Find link_id and url from context or provided parameters.
        
        Args:
            batch_id: Batch ID
            scraper_type: Scraper type (e.g., 'bilibili', 'youtube', 'youtubecomments')
            link_id: Optional link_id from progress message
            url: Optional url from progress message
            
        Returns:
            Tuple of (link_id, url) or (None, None) if not found
        """
        original_link_id = link_id
        original_url = url
        
        # If both provided, use them
        if link_id and url:
            if DEBUG_MODE:
                logger.debug(
                    f"[FIND_LINK] Using provided values: batch_id={batch_id}, "
                    f"scraper={scraper_type}, link_id={link_id}, url={url}"
                )
            return link_id, url
        
        # Normalize scraper type to match link types
        normalized_type = self._normalize_scraper_type(scraper_type)
        
        # Try to find from context
        if batch_id in self.link_context:
            links = self.link_context[batch_id].get(normalized_type, [])
            
            # If link_id provided, find matching url
            if link_id:
                for link in links:
                    if link['link_id'] == link_id:
                        result_link_id, result_url = link_id, link['url']
                        if DEBUG_MODE:
                            logger.debug(
                                f"[FIND_LINK] Found by link_id: batch_id={batch_id}, "
                                f"scraper={scraper_type}, link_id={result_link_id}, url={result_url}"
                            )
                        return result_link_id, result_url
            
            # If url provided, find matching link_id
            if url:
                for link in links:
                    if link['url'] == url:
                        result_link_id, result_url = link['link_id'], url
                        if DEBUG_MODE:
                            logger.debug(
                                f"[FIND_LINK] Found by url: batch_id={batch_id}, "
                                f"scraper={scraper_type}, link_id={result_link_id}, url={result_url}"
                            )
                        return result_link_id, result_url
            
            # If neither provided, try first link of this type
            if links:
                result_link_id, result_url = links[0]['link_id'], links[0]['url']
                if DEBUG_MODE:
                    logger.debug(
                        f"[FIND_LINK] Using first link: batch_id={batch_id}, "
                        f"scraper={scraper_type}, link_id={result_link_id}, url={result_url}"
                    )
                return result_link_id, result_url
        
        # Fallback: generate link_id from scraper_type
        if not link_id:
            link_id = f"{scraper_type}_unknown"
        if not url:
            url = f"unknown_{scraper_type}_url"
        
        if DEBUG_MODE:
            logger.warning(
                f"[FIND_LINK] Fallback used: batch_id={batch_id}, scraper={scraper_type}, "
                f"original_link_id={original_link_id}, original_url={original_url}, "
                f"fallback_link_id={link_id}, fallback_url={url}"
            )
        
        return link_id, url
    
    def _create_progress_callback(self, batch_id: str, message_queue: queue.Queue):
        """
        Create a sync progress callback that converts scraper format to ProgressService format.
        
        Args:
            batch_id: Batch ID for messages
            message_queue: Queue to put messages in
            
        Returns:
            Sync callback function
        """
        def progress_callback(message: dict):
            """Sync callback that converts and queues messages."""
            try:
                message_type = message.get('type', '')
                scraper_type = message.get('scraper', 'unknown')
                
                logger.info(f"[WorkflowService] Progress callback received: type={message_type}, scraper={scraper_type}, keys={list(message.keys())}")
                
                # Handle different message types from workflow_direct.py
                if message_type == 'scraping:start_link':
                    # Link just started - set stage based on scraper type
                    stage = 'loading'  # Initial stage for all scrapers
                    progress = 0.0
                    message_text = message.get('message', '')
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # NOTE: link_id from control center already has '_comments' suffix for comments scrapers
                    # (set in workflow_direct.py when creating tasks), so no transformation needed here
                    
                    logger.info(f"[WorkflowService] Processing scraping:start_link - stage={stage}, link_id={callback_link_id}, url={callback_url}, scraper={scraper_type}")
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # NOTE: _find_link_info may return link_id without '_comments' suffix for comments scrapers
                        # In that case, we need to append it to match pre-registered IDs
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                original_link_id = callback_link_id
                                callback_link_id = f"{callback_link_id}_comments"
                                if DEBUG_MODE:
                                    self._link_id_transformations[batch_id].append({
                                        'operation': 'scraping:start_link',
                                        'scraper': scraper_type,
                                        'original': original_link_id,
                                        'transformed': callback_link_id,
                                        'reason': 'comments_scraper_suffix_after_find_link_info'
                                    })
                                    logger.debug(
                                        f"[TRANSFORM] {original_link_id} -> {callback_link_id} "
                                        f"(scraper={scraper_type}, reason=comments_scraper_suffix_after_find_link_info)"
                                    )
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type
                        }
                    }
                    message_queue.put_nowait(converted_message)
                    return  # Done processing this message
                    
                elif message_type == 'scraping:complete_link':
                    # Link completed (success or failed)
                    status = message.get('status', 'unknown')
                    if status == 'success':
                        stage = 'completed'
                        progress = 100.0
                    else:
                        stage = 'failed'
                        progress = 0.0
                    
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # NOTE: link_id from control center already has '_comments' suffix for comments scrapers
                    # (set in workflow_direct.py when creating tasks), so no transformation needed here
                    
                    logger.info(f"[WorkflowService] Processing scraping:complete_link - status={status}, stage={stage}, link_id={callback_link_id}, scraper={scraper_type}")
                    
                    # Extract error message from the message or error field
                    error_msg = message.get('error') or (message.get('message', '').split(' - ')[-1] if ' - ' in message.get('message', '') else None)
                    message_text = message.get('message', '')
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # NOTE: _find_link_info may return link_id without '_comments' suffix for comments scrapers
                        # In that case, we need to append it to match pre-registered IDs
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                original_link_id = callback_link_id
                                callback_link_id = f"{callback_link_id}_comments"
                                if DEBUG_MODE:
                                    self._link_id_transformations[batch_id].append({
                                        'operation': 'scraping:complete_link',
                                        'scraper': scraper_type,
                                        'original': original_link_id,
                                        'transformed': callback_link_id,
                                        'reason': 'comments_scraper_suffix_after_find_link_info'
                                    })
                                    logger.debug(
                                        f"[TRANSFORM] {original_link_id} -> {callback_link_id} "
                                        f"(scraper={scraper_type}, reason=comments_scraper_suffix_after_find_link_info)"
                                    )
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    word_count = message.get('word_count', 0)  # Extract word_count from completion message
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type,
                            'word_count': word_count
                        }
                    }
                    message_queue.put_nowait(converted_message)
                    logger.debug(
                        f"[WorkflowService] Queued update_link_progress for link_id={callback_link_id}, "
                        f"stage={stage}, progress={progress}, word_count={word_count}"
                    )
                    
                    # Route to streaming summarization manager if available
                    if callback_batch_id in self.streaming_managers and status == 'success':
                        logger.info(f"[WorkflowService] Routing {callback_link_id} to streaming summarization (batch={callback_batch_id})")
                        streaming_manager = self.streaming_managers[callback_batch_id]
                        
                        # Extract base link_id (remove _comments suffix for data loading)
                        base_link_id = callback_link_id
                        if callback_link_id.endswith('_comments'):
                            base_link_id = callback_link_id[:-9]  # Remove '_comments'
                        
                        # FIX RACE #9: REMOVED DEADLOCK - Don't acquire completed_lock here!
                        # The on_scraping_complete() method handles its own locking.
                        # Acquiring the lock here and then calling on_scraping_complete (which also
                        # acquires the lock) causes a deadlock because threading.Lock is non-reentrant.
                        # This was causing all threads after the first to block forever at lock acquisition.
                        try:
                            # Load scraped data for this link
                            from research.data_loader import ResearchDataLoader
                            data_loader = ResearchDataLoader()
                            
                            logger.debug(f"[WorkflowService] Loading scraped data for {base_link_id} (from {callback_link_id})")
                            
                            # FIX 2: Verify file is written before loading
                            # Add a small delay and retry to ensure file is fully written
                            # Note: time module is already imported at module level
                            from pathlib import Path
                            
                            # Use the same path as ResearchDataLoader to ensure consistency
                            output_dir = data_loader.results_base_path
                            batch_folder = output_dir / f"run_{callback_batch_id}"
                            
                            # FIX RACE #4: Increase retries and add longer delays to ensure file is fully written
                            # Try to find the file (could be transcript or comments)
                            file_found = False
                            max_file_wait_retries = 10  # Increased from 5 to 10
                            file_wait_delay = 0.3  # Increased from 0.2 to 0.3
                            
                            # Determine type prefix based on scraper type (handle comment scrapers too)
                            if scraper_type == 'youtube' or scraper_type == 'youtubecomments':
                                type_prefix = 'YT'
                            elif scraper_type == 'bilibili' or scraper_type == 'bilibilicomments':
                                type_prefix = 'BILI'
                            elif scraper_type == 'article':
                                type_prefix = 'AR'
                            else:
                                type_prefix = 'RD'  # Default to Reddit
                            
                            suffix = 'tsct'
                            if scraper_type in ['youtubecomments', 'bilibilicomments']:
                                suffix = 'cmts' if scraper_type == 'youtubecomments' else 'cmt'
                            
                            expected_filename = batch_folder / f"{callback_batch_id}_{type_prefix}_{callback_link_id}_{suffix}.json"
                            
                            logger.info(
                                f"[WorkflowService] Verifying file for {base_link_id} "
                                f"(scraper_type={scraper_type}, callback_link_id={callback_link_id}): "
                                f"expected={expected_filename.name}, batch_folder={batch_folder}"
                            )
                            
                            for retry in range(max_file_wait_retries):
                                logger.debug(
                                    f"[WorkflowService] File check attempt {retry + 1}/{max_file_wait_retries} "
                                    f"for {base_link_id}: checking {expected_filename}"
                                )
                                
                                if expected_filename.exists():
                                    # Try to read it to verify it's complete
                                    try:
                                        with open(expected_filename, 'r', encoding='utf-8') as f:
                                            import json
                                            json.load(f)  # Verify it's valid JSON
                                        file_found = True
                                        logger.info(f"[WorkflowService] ✓ File verified for {base_link_id}: {expected_filename.name}")
                                        break
                                    except (IOError, json.JSONDecodeError) as e:
                                        # File exists but not fully written yet
                                        logger.debug(
                                            f"[WorkflowService] File exists but not readable yet for {base_link_id} "
                                            f"(attempt {retry + 1}/{max_file_wait_retries}): {e}"
                                        )
                                        if retry < max_file_wait_retries - 1:
                                            time.sleep(file_wait_delay)
                                            continue
                                else:
                                    logger.debug(
                                        f"[WorkflowService] File not found for {base_link_id} "
                                        f"(attempt {retry + 1}/{max_file_wait_retries}): {expected_filename}"
                                    )
                                
                                # If not found, wait and retry
                                if retry < max_file_wait_retries - 1:
                                    time.sleep(file_wait_delay)
                            
                            if not file_found:
                                # List actual files in directory for debugging
                                actual_files = []
                                if batch_folder.exists():
                                    actual_files = [f.name for f in batch_folder.glob("*.json")]
                                
                                logger.warning(
                                    f"[WorkflowService] ✗ File verification failed for {base_link_id} "
                                    f"(expected: {expected_filename.name}, batch_folder: {batch_folder}). "
                                    f"Actual files in directory ({len(actual_files)}): {actual_files[:10]}{'...' if len(actual_files) > 10 else ''}"
                                )
                            else:
                                # File verified, load it directly instead of using data_loader's retry logic
                                # This avoids blocking on retries since we already know the file exists
                                try:
                                    with open(expected_filename, 'r', encoding='utf-8') as f:
                                        import json
                                        file_data = json.load(f)
                                    
                                    # Convert file data to the format expected by streaming manager
                                    # The file format depends on file type (tsct vs cmts/cmt)
                                    scraped_data = {}
                                    
                                    if suffix in ['tsct', 'article']:
                                        # Transcript/article file
                                        scraped_data['transcript'] = file_data.get('content', '')
                                        scraped_data['metadata'] = {
                                            'title': file_data.get('title', ''),
                                            'author': file_data.get('author', ''),
                                            'url': file_data.get('url', ''),
                                            'word_count': file_data.get('word_count', 0),
                                            'publish_date': file_data.get('publish_date', '')
                                        }
                                        if 'summary' in file_data:
                                            scraped_data['summary'] = file_data['summary']
                                    elif suffix in ['cmts', 'cmt']:
                                        # Comments file
                                        comments = file_data.get('comments', [])
                                        if scraper_type == 'youtubecomments' and comments:
                                            # YouTube: extract content from comment objects if needed
                                            if isinstance(comments[0], dict) and 'content' in comments[0]:
                                                comments = [c.get('content', '') for c in comments]
                                        scraped_data['comments'] = comments
                                    
                                    # Set source
                                    source_mapping = {
                                        'YT': 'youtube',
                                        'BILI': 'bilibili',
                                        'RD': 'reddit',
                                        'AR': 'article'
                                    }
                                    scraped_data['source'] = source_mapping.get(type_prefix, scraper_type)
                                    
                                    logger.info(f"[WorkflowService] ✓ Loaded data directly from {expected_filename.name} for {base_link_id}")
                                    
                                    # V2 Integration: DON'T merge files here - let DataMerger in adapter handle it!
                                    # The adapter needs to receive transcript and comments separately to merge properly.
                                    # Commenting out the auto-merge logic:
                                    #
                                    # OLD BEHAVIOR (V1): Auto-merge transcript + comments files
                                    # NEW BEHAVIOR (V2): Load only the requested file, send separately to adapter
                                    #
                                    # The DataMerger will receive:
                                    #   - callback_link_id="yt_req1" with transcript → DataMerger.on_transcript_complete()
                                    #   - callback_link_id="yt_req1_comments" with comments → DataMerger.on_comments_complete()
                                    #   - DataMerger merges when both arrive → sends to V2
                                    #
                                    # This ensures clean separation and proper merge tracking!
                                    
                                except Exception as e:
                                    logger.error(f"[WorkflowService] ✗ Error loading file {expected_filename}: {e}", exc_info=True)
                                    scraped_data = None
                                
                                if scraped_data:
                                    # Notify streaming manager (always use base_link_id for manager tracking)
                                    transcript_len = len(scraped_data.get('transcript', '')) if scraped_data.get('transcript') else 0
                                    comments_count = len(scraped_data.get('comments', [])) if scraped_data.get('comments') else 0
                                    logger.info(
                                        f"[WorkflowService] ✓ Data loaded for {base_link_id}: "
                                        f"{transcript_len} chars transcript, {comments_count} comments. "
                                        f"Routing to streaming summarization..."
                                    )
                                    try:
                                        # FIX RACE #4: Add detailed logging before calling on_scraping_complete
                                        # Check if streaming manager is ready
                                        active_workers = [w for w in streaming_manager.workers if w.is_alive()]
                                        queue_size_before = streaming_manager.summarization_queue.qsize()
                                        logger.info(
                                            f"[WorkflowService] 📊 Streaming manager state before routing {base_link_id}: "
                                            f"active_workers={len(active_workers)}/{len(streaming_manager.workers)}, "
                                            f"queue_size={queue_size_before}, "
                                            f"items_in_queue={len(streaming_manager.items_in_queue)}, "
                                            f"items_processing={len(streaming_manager.items_processing)}, "
                                            f"expected_items={len(streaming_manager.expected_items)}"
                                        )
                                        
                                        # V2 Integration: Pass original callback_link_id (with _comments suffix) so adapter can route correctly
                                        streaming_manager.on_scraping_complete(callback_link_id, scraped_data)
                                        
                                        # Verify item was queued
                                        queue_size_after = streaming_manager.summarization_queue.qsize()
                                        logger.info(
                                            f"[WorkflowService] ✓ Successfully routed {base_link_id} to streaming summarization. "
                                            f"Queue size: {queue_size_before} → {queue_size_after}"
                                        )
                                        
                                        # If queue size didn't increase and item wasn't already in queue/processing, log warning
                                        if queue_size_after == queue_size_before:
                                            with streaming_manager.completed_lock:
                                                if base_link_id not in streaming_manager.items_in_queue and \
                                                   base_link_id not in streaming_manager.items_processing and \
                                                   not streaming_manager.item_states.get(base_link_id, {}).get('summarized', False):
                                                    logger.warning(
                                                        f"[WorkflowService] ⚠️ Item {base_link_id} was NOT queued for summarization! "
                                                        f"This may indicate a problem in on_scraping_complete. "
                                                        f"Item state: {streaming_manager.item_states.get(base_link_id, {})}"
                                                    )
                                    except Exception as e:
                                        logger.error(f"[WorkflowService] ✗ Error calling on_scraping_complete for {base_link_id}: {e}", exc_info=True)
                                else:
                                    logger.warning(
                                        f"[WorkflowService] ✗ Could not load data for {base_link_id} "
                                        f"(expected file: {expected_filename.name}, batch_id={callback_batch_id}), skipping summarization. "
                                        f"Check if file exists in batch directory."
                                    )
                        except Exception as e:
                            logger.error(f"[WorkflowService] ✗ Error routing {base_link_id} to streaming manager: {e}", exc_info=True)
                    elif callback_batch_id not in self.streaming_managers:
                        logger.debug(f"[WorkflowService] No streaming manager for batch {callback_batch_id}, skipping summarization routing")
                    elif status != 'success':
                        logger.debug(f"[WorkflowService] Scraping status is '{status}' (not 'success'), skipping summarization routing for {callback_link_id}")
                    
                    # Update link status for both success and failed links
                    # This ensures frontend receives completion notifications
                    if status == 'success':
                        # Queue a status update for successful links
                        status_message = {
                            'action': 'update_link_status',
                            'batch_id': callback_batch_id,
                            'link_id': callback_link_id,
                            'url': callback_url,
                            'status': 'completed',
                            'error': None,
                            'metadata': {
                                'bytes_downloaded': bytes_downloaded,
                                'total_bytes': total_bytes,
                                'source': scraper_type,
                                'word_count': word_count
                            }
                        }
                        try:
                            message_queue.put_nowait(status_message)
                            logger.debug(
                                f"[WorkflowService] Queued update_link_status (completed) for link_id={callback_link_id}, "
                                f"word_count={word_count}"
                            )
                        except queue.Full:
                            logger.warning(f"[WorkflowService] Queue full when trying to queue status update for link_id={callback_link_id}")
                    elif status == 'failed':
                        # Queue a status update for failed links
                        status_message = {
                            'action': 'update_link_status',
                            'batch_id': callback_batch_id,
                            'link_id': callback_link_id,
                            'url': callback_url,
                            'status': 'failed',
                            'error': error_msg or message_text,
                            'metadata': {
                                'source': scraper_type,
                                'word_count': 0
                            }
                        }
                        try:
                            message_queue.put_nowait(status_message)
                            logger.debug(
                                f"[WorkflowService] Queued update_link_status (failed) for link_id={callback_link_id}, "
                                f"error={error_msg}"
                            )
                        except queue.Full:
                            logger.warning(f"[WorkflowService] Queue full when trying to queue status update for link_id={callback_link_id}")
                    return  # Done processing this message
                    
                elif message_type in ['scraping:start', 'scraping:discover', 'scraping:complete', 'scraping:start_type']:
                    # Batch-level messages - don't convert to link progress, just broadcast
                    # These don't have link_id/url, so skip progress conversion
                    logger.info(f"[WorkflowService] Handling batch-level message: {message_type}")
                    try:
                        # Broadcast directly (these are handled by the frontend)
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for batch-level messages
                
                elif message_type == 'scraping:verify_completion':
                    # Request from scraping service to verify and send confirmation
                    # This is called after scraping:complete to ensure all processes are done
                    verify_batch_id = message.get('batch_id', batch_id)
                    logger.info(f"[VERIFY] Received verify_completion request for batch {verify_batch_id}")
                    if DEBUG_MODE:
                        logger.debug(
                            f"[VERIFY] Queueing verify_completion action for batch {verify_batch_id}, "
                            f"queue_size={message_queue.qsize()}"
                        )
                    try:
                        # Schedule async verification (can't await in sync callback)
                        # We'll queue a special action that the async processor will handle
                        message_queue.put_nowait({
                            'action': 'verify_completion',
                            'batch_id': verify_batch_id,
                            '_debug_timestamp': time.time()
                        })
                    except queue.Full:
                        logger.error(
                            f"[VERIFY] Queue full, cannot queue verify_completion for batch {verify_batch_id}"
                        )
                    return  # Don't process further - async handler will verify
                
                elif message_type == 'scraping:all_complete_confirmed':
                    # Confirmation signal - broadcast and mark as received
                    logger.info(f"[WorkflowService] Received scraping completion confirmation for batch {batch_id}")
                    try:
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for confirmation messages
                
                elif message_type.startswith('research:'):
                    # Research-related messages are batch-level, not link-level
                    # Don't convert to link progress - broadcast directly
                    logger.info(f"[WorkflowService] Handling research message: {message_type}")
                    try:
                        message_queue.put_nowait({
                            'action': 'broadcast',
                            'message': message
                        })
                    except queue.Full:
                        pass
                    return  # Don't process further for research messages
                    
                else:
                    # Direct progress report from scraper (has stage field)
                    # Or unknown message type - log it for debugging
                    if not message_type:
                        logger.warning(f"[WorkflowService] Received message without type field: {list(message.keys())}")
                    else:
                        logger.info(f"[WorkflowService] Handling unknown message type: {message_type}")
                    
                    stage = message.get('stage', 'unknown')
                    progress = message.get('progress', 0.0)
                    message_text = message.get('message', '')
                    callback_batch_id = message.get('batch_id') or batch_id
                    callback_link_id = message.get('link_id')
                    callback_url = message.get('url')
                    
                    # For comments scrapers, append '_comments' to link_id to match pre-registered IDs
                    original_link_id = callback_link_id
                    if scraper_type in ['youtubecomments', 'bilibilicomments']:
                        if callback_link_id and not callback_link_id.endswith('_comments'):
                            callback_link_id = f"{callback_link_id}_comments"
                            if DEBUG_MODE:
                                logger.debug(
                                    f"[TRANSFORM] {original_link_id} -> {callback_link_id} "
                                    f"(scraper={scraper_type}, reason=comments_scraper_suffix)"
                                )
                    
                    # Get link context if not already provided
                    if not callback_link_id or not callback_url:
                        callback_link_id, callback_url = self._find_link_info(
                            callback_batch_id,
                            scraper_type,
                            callback_link_id,
                            callback_url
                        )
                        # Apply _comments suffix for comments scrapers after finding link info
                        if scraper_type in ['youtubecomments', 'bilibilicomments']:
                            if callback_link_id and not callback_link_id.endswith('_comments'):
                                original_before_suffix = callback_link_id
                                callback_link_id = f"{callback_link_id}_comments"
                                if DEBUG_MODE:
                                    logger.debug(
                                        f"[TRANSFORM] {original_before_suffix} -> {callback_link_id} "
                                        f"(scraper={scraper_type}, reason=comments_scraper_suffix_after_find)"
                                    )
                    
                    # Extract metadata
                    bytes_downloaded = message.get('bytes_downloaded', 0)
                    total_bytes = message.get('total_bytes', 0)
                    
                    # Convert to ProgressService format and queue
                    converted_message = {
                        'action': 'update_link_progress',
                        'batch_id': callback_batch_id,
                        'link_id': callback_link_id,
                        'url': callback_url,
                        'stage': stage,
                        'stage_progress': progress,
                        'overall_progress': progress,
                        'message': message_text,
                        'metadata': {
                            'bytes_downloaded': bytes_downloaded,
                            'total_bytes': total_bytes,
                            'source': scraper_type
                        }
                    }
                    # Track message sequence
                    if DEBUG_MODE:
                        self._message_sequence[batch_id] += 1
                        converted_message['_debug_sequence'] = self._message_sequence[batch_id]
                        converted_message['_debug_timestamp'] = time.time()
                    
                    message_queue.put_nowait(converted_message)
            except queue.Full:
                queue_size = message_queue.qsize()
                logger.warning(
                    f"Progress queue full (size={queue_size}), dropping message: "
                    f"{message.get('type', 'unknown')}"
                )
                if DEBUG_MODE:
                    self._queue_stats[batch_id]['messages_dropped'] += 1
            except Exception as e:
                logger.error(
                    f"Error in progress callback (batch_id={batch_id}, "
                    f"message_type={message.get('type', 'unknown')}): {e}",
                    exc_info=True
                )
        
        return progress_callback
    
    async def wait_for_scraping_confirmation(
        self,
        progress_queue: queue.Queue,
        batch_id: str,
        max_wait_seconds: float = 15.0,
        check_interval: float = 0.2
    ) -> Dict:
        """
        Wait for scraping:all_complete_confirmed signal from scraping service.
        
        Args:
            progress_queue: Queue to check for confirmation message
            batch_id: Batch ID to wait for
            max_wait_seconds: Maximum time to wait (default: 60 seconds)
            check_interval: Time between checks (default: 0.5 seconds)
            
        Returns:
            Dict with confirmation details if received, or None if timeout
        """
        start_time = time.time()
        last_log_time = 0
        logger.info(f"Waiting for scraping completion confirmation for batch {batch_id}...")
        
        # Also check progress service directly as fallback
        confirmation_received = False
        confirmation_data = None
        
        while time.time() - start_time < max_wait_seconds:
            # Check queue for confirmation message
            try:
                # Peek at queue without removing items
                queue_items = []
                temp_items = []
                while True:
                    try:
                        item = progress_queue.get_nowait()
                        temp_items.append(item)
                        if item.get('action') == 'broadcast':
                            message = item.get('message', {})
                            if message.get('type') == 'scraping:all_complete_confirmed':
                                confirmation_received = True
                                confirmation_data = message
                                logger.info(f"Received scraping completion confirmation for batch {batch_id}")
                        queue_items.append(item)
                    except queue.Empty:
                        break
                
                # Put items back
                for item in queue_items:
                    try:
                        progress_queue.put_nowait(item)
                    except queue.Full:
                        pass
                
                if confirmation_received:
                    break
            except Exception as e:
                logger.debug(f"Error checking queue for confirmation: {e}")
            
            # Fallback: Check progress service directly
            if not confirmation_received:
                try:
                    confirmation_result = await self.progress_service.confirm_all_scraping_complete(batch_id)
                    if confirmation_result.get('confirmed'):
                        confirmation_received = True
                        confirmation_data = {
                            'type': 'scraping:all_complete_confirmed',
                            'batch_id': batch_id,
                            **confirmation_result
                        }
                        logger.info(f"Confirmed scraping completion via direct check for batch {batch_id}")
                        break
                except Exception as e:
                    logger.debug(f"Error checking completion directly: {e}")
            
            # Log progress periodically
            elapsed = time.time() - start_time
            if int(elapsed) > last_log_time:
                last_log_time = int(elapsed)
                pending_count = self.progress_service.get_pending_links_count(batch_id)
                logger.debug(
                    f"Waiting for confirmation: elapsed={elapsed:.1f}s, "
                    f"pending_links={pending_count}, queue_size={progress_queue.qsize()}"
                )
            
            await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        
        if confirmation_received and confirmation_data:
            logger.info(
                f"Scraping completion confirmed for batch {batch_id} after {elapsed:.2f}s: "
                f"{confirmation_data.get('completed_count', 0)} completed, "
                f"{confirmation_data.get('failed_count', 0)} failed out of "
                f"{confirmation_data.get('expected_total', 0)} expected"
            )
            return confirmation_data
        else:
            # Timeout - check final status
            logger.warning(
                f"Timeout waiting for scraping confirmation after {elapsed:.2f}s for batch {batch_id}. "
                f"Checking final status..."
            )
            confirmation_result = await self.progress_service.confirm_all_scraping_complete(batch_id)
            if confirmation_result.get('confirmed'):
                logger.info(f"Scraping completion confirmed via final check for batch {batch_id}")
                return {
                    'type': 'scraping:all_complete_confirmed',
                    'batch_id': batch_id,
                    **confirmation_result
                }
            else:
                logger.warning(
                    f"Scraping completion NOT confirmed for batch {batch_id}: "
                    f"{confirmation_result.get('registered_count', 0)}/{confirmation_result.get('expected_total', 0)} registered, "
                    f"{confirmation_result.get('completed_count', 0)} completed, "
                    f"{confirmation_result.get('failed_count', 0)} failed"
                )
                return None
    
    async def wait_for_100_percent_completion(
        self,
        batch_id: str,
        max_wait_seconds: float = 10.0,
        check_interval: float = 0.5
    ) -> bool:
        """
        Poll ProgressService until 100% completion rate is reached.
        
        This is a backup verification to catch timing issues where status updates
        might still be in flight when initial confirmation happens.
        
        Args:
            batch_id: Batch ID to check
            max_wait_seconds: Maximum time to wait (default: 10 seconds)
            check_interval: Time between checks (default: 0.5 seconds)
        
        Returns:
            True if 100% reached, False if timeout
        """
        start_time = time.time()
        logger.info(f"Polling for 100% completion for batch {batch_id}...")
        
        while time.time() - start_time < max_wait_seconds:
            result = await self.progress_service.confirm_all_scraping_complete(batch_id)
            
            completion_rate = result.get('completion_rate', 0.0)
            is_100_percent = result.get('is_100_percent', False)
            total_final = result.get('total_final', 0)
            expected_total = result.get('expected_total', 0)
            
            if is_100_percent and total_final == expected_total and result.get('confirmed'):
                logger.info(
                    f"100% completion confirmed via polling: {completion_rate * 100:.1f}% "
                    f"({total_final}/{expected_total})"
                )
                return True
            
            elapsed = time.time() - start_time
            logger.debug(
                f"Waiting for 100%: {completion_rate * 100:.1f}% "
                f"({total_final}/{expected_total}), elapsed={elapsed:.1f}s"
            )
            
            await asyncio.sleep(check_interval)
        
        # Final check
        result = await self.progress_service.confirm_all_scraping_complete(batch_id)
        is_100_percent = result.get('is_100_percent', False)
        total_final = result.get('total_final', 0)
        expected_total = result.get('expected_total', 0)
        
        if is_100_percent and total_final == expected_total:
            logger.info(f"100% completion confirmed on final check")
            return True
        
        logger.warning(
            f"100% completion not reached after {max_wait_seconds}s: "
            f"{result.get('completion_percentage', 0):.1f}% ({total_final}/{expected_total})"
        )
        return False
    
    async def _wait_for_status_updates(
        self,
        message_queue: queue.Queue,
        batch_id: str,
        max_wait_seconds: float = 10.0,
        check_interval: float = 0.1
    ) -> bool:
        """
        Wait for all queued status updates to be processed.
        
        Args:
            message_queue: Queue to check for remaining messages
            batch_id: Batch ID to check status for
            max_wait_seconds: Maximum time to wait (default: 30 seconds)
            check_interval: Time between checks (default: 0.2 seconds)
            
        Returns:
            True if all links have final status, False if timeout
        """
        start_time = time.time()
        last_log_time = 0
        logger.info(f"Waiting for status updates to complete for batch {batch_id}...")
        
        while time.time() - start_time < max_wait_seconds:
            # Check if queue is empty (or has only non-status messages)
            queue_empty = True
            queue_size = 0
            try:
                # Check queue size (approximate)
                queue_size = message_queue.qsize()
                if queue_size > 0:
                    # Check if there are status update messages
                    # We can't peek, so we'll check by trying to get one
                    # But we'll put it back if it's not a status update
                    try:
                        test_message = message_queue.get_nowait()
                        if test_message.get('action') in ['update_link_progress', 'update_link_status']:
                            # Put it back - it's a status update that needs processing
                            message_queue.put_nowait(test_message)
                            queue_empty = False
                        else:
                            # Put it back - it's not a status update
                            message_queue.put_nowait(test_message)
                            queue_empty = True
                    except queue.Empty:
                        queue_empty = True
                else:
                    queue_empty = True
            except Exception as e:
                logger.warning(f"Error checking queue: {e}")
                queue_empty = True
            
            # Check if all links have final status
            all_final = self.progress_service.all_links_have_final_status(batch_id)
            
            if queue_empty and all_final:
                elapsed = time.time() - start_time
                logger.info(f"All status updates processed in {elapsed:.2f}s for batch {batch_id}")
                return True
            
            # Log progress periodically (every second)
            elapsed = time.time() - start_time
            if int(elapsed) > last_log_time:
                last_log_time = int(elapsed)
                pending_count = self.progress_service.get_pending_links_count(batch_id)
                logger.debug(f"Waiting for status updates: queue_size={queue_size}, pending_links={pending_count}, elapsed={elapsed:.1f}s")
            
            await asyncio.sleep(check_interval)
        
        # Timeout - check final status
        elapsed = time.time() - start_time
        pending_count = self.progress_service.get_pending_links_count(batch_id)
        all_final = self.progress_service.all_links_have_final_status(batch_id)
        
        if all_final:
            logger.info(f"All status updates processed (after timeout) in {elapsed:.2f}s for batch {batch_id}")
            return True
        else:
            logger.warning(f"Timeout waiting for status updates after {elapsed:.2f}s for batch {batch_id}: {pending_count} links still pending")
            # Force update batch status to ensure frontend has latest state
            await self.progress_service._update_batch_status(batch_id)
            return False
    
    async def _process_progress_queue(self, message_queue: queue.Queue, batch_id: str):
        """
        Process messages from queue and call ProgressService.
        
        Args:
            message_queue: Queue to poll for messages
            batch_id: Batch ID for broadcasting
        """
        max_retries = 3
        retry_delay = 0.5
        consecutive_errors = 0
        max_consecutive_errors = 10
        last_queue_log_time = 0
        queue_log_interval = 5.0  # Log queue stats every 5 seconds
        
        while True:
            try:
                # Monitor queue size periodically
                if DEBUG_MODE:
                    current_time = time.time()
                    if current_time - last_queue_log_time >= queue_log_interval:
                        queue_size = message_queue.qsize()
                        stats = self._queue_stats[batch_id]
                        stats['max_queue_size'] = max(stats['max_queue_size'], queue_size)
                        stats['queue_size_history'].append((current_time, queue_size))
                        # Keep only last 100 entries
                        if len(stats['queue_size_history']) > 100:
                            stats['queue_size_history'] = stats['queue_size_history'][-100:]
                        
                        logger.debug(
                            f"[QUEUE] Batch {batch_id}: size={queue_size}, "
                            f"processed={stats['messages_processed']}, "
                            f"dropped={stats['messages_dropped']}, "
                            f"max_size={stats['max_queue_size']}"
                        )
                        last_queue_log_time = current_time
                
                # Try to get message (non-blocking)
                try:
                    message = message_queue.get_nowait()
                    consecutive_errors = 0  # Reset error counter on success
                    
                    # Log queue size if large
                    queue_size = message_queue.qsize()
                    if queue_size > 10:
                        logger.warning(f"[QUEUE] Large queue size: {queue_size} messages for batch {batch_id}")
                    
                    if DEBUG_MODE:
                        self._queue_stats[batch_id]['messages_processed'] += 1
                        processing_start = time.time()
                    else:
                        processing_start = time.time()
                    
                    # Check if this is a ProgressService update action
                    if message.get('action') == 'update_link_progress':
                        # Retry logic for progress updates
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Call ProgressService.update_link_progress()
                                await self.progress_service.update_link_progress(
                                    batch_id=message['batch_id'],
                                    link_id=message['link_id'],
                                    url=message['url'],
                                    stage=message['stage'],
                                    stage_progress=message['stage_progress'],
                                    overall_progress=message['overall_progress'],
                                    message=message['message'],
                                    metadata=message.get('metadata')
                                )
                                success = True
                                
                                processing_time = time.time() - processing_start
                                if processing_time > 1.0:
                                    logger.warning(f"[QUEUE] Slow message processing: {processing_time:.3f}s for {message.get('action')} (batch {batch_id})")
                                
                                if DEBUG_MODE:
                                    self._queue_stats[batch_id]['processing_times'].append(processing_time)
                                    # Keep only last 100 processing times
                                    if len(self._queue_stats[batch_id]['processing_times']) > 100:
                                        self._queue_stats[batch_id]['processing_times'] = \
                                            self._queue_stats[batch_id]['processing_times'][-100:]
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Progress update failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Progress update failed after {max_retries} attempts: {e}")
                                    # Don't re-queue to avoid infinite loops - log and move on
                    
                    elif message.get('action') == 'update_link_status':
                        # Retry logic for status updates
                        retry_count = 0
                        success = False
                        
                        logger.info(
                            f"🔄 [WorkflowService] Processing update_link_status: "
                            f"batch_id={message.get('batch_id')}, link_id={message.get('link_id')}, "
                            f"status={message.get('status')}, word_count={message.get('metadata', {}).get('word_count', 'N/A')}"
                        )
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Call ProgressService.update_link_status()
                                await self.progress_service.update_link_status(
                                    batch_id=message['batch_id'],
                                    link_id=message['link_id'],
                                    url=message['url'],
                                    status=message['status'],
                                    error=message.get('error'),
                                    metadata=message.get('metadata')
                                )
                                success = True
                                logger.debug(
                                    f"✅ [WorkflowService] Successfully updated link status: "
                                    f"link_id={message.get('link_id')}, status={message.get('status')}"
                                )
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Status update failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Status update failed after {max_retries} attempts: {e}")
                                    # Don't re-queue to avoid infinite loops - log and move on
                    
                    elif message.get('action') == 'verify_completion':
                        # Verify scraping completion and send confirmation signal
                        verify_batch_id = message.get('batch_id', batch_id)
                        verify_start_time = message.get('_debug_timestamp', time.time())
                        logger.info(f"[VERIFY] Processing verify_completion for batch {verify_batch_id}")
                        
                        if DEBUG_MODE:
                            logger.debug(
                                f"[VERIFY] Verification request queued at {verify_start_time}, "
                                f"processing now (delay={time.time() - verify_start_time:.3f}s)"
                            )
                        
                        try:
                            # Wait a bit for any pending status updates
                            await asyncio.sleep(0.5)
                            
                            # Verify completion
                            logger.debug(f"[VERIFY] Calling confirm_all_scraping_complete for batch {verify_batch_id}")
                            confirmation_result = await self.progress_service.confirm_all_scraping_complete(verify_batch_id)
                            
                            if DEBUG_MODE:
                                logger.info(
                                    f"[VERIFY] Confirmation result for batch {verify_batch_id}: "
                                    f"confirmed={confirmation_result.get('confirmed')}, "
                                    f"expected={confirmation_result.get('expected_total', 0)}, "
                                    f"registered={confirmation_result.get('registered_count', 0)}, "
                                    f"completed={confirmation_result.get('completed_count', 0)}, "
                                    f"failed={confirmation_result.get('failed_count', 0)}, "
                                    f"pending={confirmation_result.get('pending_count', 0)}"
                                )
                            
                            # Send confirmation signal
                            confirmation_message = {
                                'type': 'scraping:all_complete_confirmed',
                                'batch_id': verify_batch_id,
                                **confirmation_result
                            }
                            
                            # Broadcast confirmation
                            await self.ws_manager.broadcast(verify_batch_id, confirmation_message)
                            
                            # Also queue it for the wait_for_scraping_confirmation to pick up
                            try:
                                message_queue.put_nowait({
                                    'action': 'broadcast',
                                    'message': confirmation_message
                                })
                            except queue.Full:
                                logger.warning(
                                    f"[VERIFY] Queue full, cannot queue confirmation message for batch {verify_batch_id}"
                                )
                            
                            # Send explicit 100% completion signal if confirmed
                            if confirmation_result.get('is_100_percent') and confirmation_result.get('confirmed'):
                                completion_rate = confirmation_result.get('completion_rate', 0.0)
                                completion_percentage = confirmation_result.get('completion_percentage', 0.0)
                                total_final = confirmation_result.get('total_final', 0)
                                expected_total = confirmation_result.get('expected_total', 0)
                                
                                if total_final == expected_total:
                                    logger.info(
                                        f"[100%] Sending 100% completion signal for batch {verify_batch_id}: "
                                        f"{completion_percentage:.1f}% ({total_final}/{expected_total})"
                                    )
                                    
                                    await self.ws_manager.broadcast(verify_batch_id, {
                                        'type': 'scraping:100_percent_complete',
                                        'batch_id': verify_batch_id,
                                        'completion_rate': completion_rate,
                                        'completion_percentage': completion_percentage,
                                        'completed_count': confirmation_result.get('completed_count', 0),
                                        'failed_count': confirmation_result.get('failed_count', 0),
                                        'expected_total': expected_total,
                                        'message': '所有抓取任务已完成 (100%)',
                                        'timestamp': datetime.now().isoformat()
                                    })
                            
                            verify_elapsed = time.time() - verify_start_time
                            logger.info(
                                f"[VERIFY] Sent scraping completion confirmation for batch {verify_batch_id}: "
                                f"confirmed={confirmation_result.get('confirmed')}, elapsed={verify_elapsed:.3f}s"
                            )
                        except Exception as e:
                            verify_elapsed = time.time() - verify_start_time
                            logger.error(
                                f"[VERIFY] Error verifying completion for batch {verify_batch_id} "
                                f"(elapsed={verify_elapsed:.3f}s): {e}",
                                exc_info=True
                            )
                    
                    elif message.get('action') == 'broadcast':
                        # Broadcast batch-level messages directly
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                # Broadcast the nested message
                                await self.ws_manager.broadcast(batch_id, message.get('message', message))
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count < max_retries:
                                    logger.warning(f"Broadcast failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                    await asyncio.sleep(retry_delay)
                                else:
                                    logger.error(f"Broadcast failed after {max_retries} attempts: {e}")
                    
                    else:
                        # Retry logic for other messages (with type field)
                        if 'type' in message:
                            retry_count = 0
                            success = False
                            
                            while retry_count < max_retries and not success:
                                try:
                                    # Broadcast messages with type field directly
                                    await self.ws_manager.broadcast(batch_id, message)
                                    success = True
                                except Exception as e:
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        logger.warning(f"Broadcast failed (attempt {retry_count}/{max_retries}): {e}, retrying in {retry_delay}s")
                                        await asyncio.sleep(retry_delay)
                                    else:
                                        logger.error(f"Broadcast failed after {max_retries} attempts: {e}")
                        else:
                            # Skip messages without type or action (internal messages)
                            # Also skip messages with action that aren't handled above
                            if message.get('action'):
                                logger.debug(f"Skipping unhandled action message: {message.get('action')}, keys: {list(message.keys())}")
                            else:
                                logger.debug(f"Skipping message without type or action: {message.keys()}")
                        
                except queue.Empty:
                    # No message, wait a bit
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error processing progress queue (consecutive errors: {consecutive_errors}): {e}")
                
                # If too many consecutive errors, wait longer before retrying
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), waiting longer before retry")
                    await asyncio.sleep(1.0)
                    consecutive_errors = 0  # Reset after waiting
                else:
                    await asyncio.sleep(0.1)
    
    async def run_workflow(self, batch_id: str) -> Dict:
        """
        Run full workflow using proven test functions with progress updates.
        
        Args:
            batch_id: Batch ID to process
            
        Returns:
            Result dictionary from the workflow
        """
        try:
            # Check for cancellation before starting
            if self.progress_service.is_cancelled(batch_id):
                logger.info(f"Batch {batch_id} was cancelled before workflow started")
                return {'success': False, 'error': 'Cancelled by user'}
            
            # Check if this is a resume of an existing session
            # Always try to find existing session by batch_id
            session_id = None
            skip_scraping = False
            existing_session_data = None
            logger.info(f"[RESUME] Checking for existing session with batch_id={batch_id}")
            try:
                # Try to find existing session for this batch_id
                sessions_dir = project_root / "data" / "research" / "sessions"
                logger.info(f"[RESUME] Sessions dir exists: {sessions_dir.exists()}, path: {sessions_dir}")
                if sessions_dir.exists():
                    # Look for session files for this batch
                    session_files = list(sessions_dir.glob("session_*.json"))
                    logger.info(f"[RESUME] Found {len(session_files)} session files to check")
                    
                    # Collect all matching sessions for this batch
                    matching_sessions = []
                    for session_file in session_files:
                        try:
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                            metadata = session_data.get("metadata", {})
                            session_batch_id = metadata.get("batch_id")
                            logger.info(f"[RESUME] Checking {session_file.name}: batch_id={session_batch_id}, looking for={batch_id}, match={session_batch_id == batch_id}")
                            if session_batch_id == batch_id:
                                # Found a matching session
                                phase_artifacts = session_data.get("phase_artifacts", {})
                                matching_sessions.append({
                                    "file": session_file,
                                    "session_id": metadata.get("session_id"),
                                    "session_data": session_data,
                                    "phase_artifacts": phase_artifacts,
                                    "phase_count": len(phase_artifacts),
                                    "updated_at": metadata.get("updated_at", ""),
                                })
                                logger.info(f"[RESUME] Found matching session {metadata.get('session_id')}: {len(phase_artifacts)} phases ({list(phase_artifacts.keys())})")
                        except Exception as e:
                            logger.warning(f"[RESUME] Error checking session file {session_file}: {e}")
                            continue
                    
                    # If multiple sessions found, select the one with most progress
                    if matching_sessions:
                        if len(matching_sessions) > 1:
                            logger.info(f"[RESUME] Found {len(matching_sessions)} sessions for batch {batch_id}, selecting most complete...")
                            # Sort by phase count (descending), then by updated_at (descending)
                            matching_sessions.sort(key=lambda s: (s["phase_count"], s["updated_at"]), reverse=True)
                            logger.info(f"[RESUME] Selected session {matching_sessions[0]['session_id']} with {matching_sessions[0]['phase_count']} phases")
                        
                        best_session = matching_sessions[0]
                        session_id = best_session["session_id"]
                        existing_session_data = best_session["session_data"]
                        phase_artifacts = best_session["phase_artifacts"]
                        has_phase0 = "phase0" in phase_artifacts
                        
                        logger.info(f"[RESUME] ✓ MATCH! session_id={session_id}, has phase0={has_phase0}, phase_artifacts keys={list(phase_artifacts.keys())}")
                        
                        # If phase0 exists, scraping is done
                        if has_phase0:
                            skip_scraping = True
                            logger.info(f"[RESUME] ✓ SKIPPING SCRAPING - Found existing session {session_id} with phase0 complete")
                        else:
                            logger.info(f"[RESUME] ✗ NOT SKIPPING - phase0 not found in artifacts")
                else:
                    logger.warning(f"[RESUME] Sessions directory does not exist: {sessions_dir}")
            except Exception as e:
                logger.error(f"[RESUME] Error checking for existing session: {e}", exc_info=True)
            
            # FALLBACK: If no session found, use batch_id as session_id
            # (This matches how sessions are initially created during scraping)
            if session_id is None:
                session_id = batch_id
                logger.info(f"[RESUME] No existing session found for batch {batch_id}, will use batch_id as session_id")
            
            # Determine resume point based on existing session data
            resume_point = self._determine_resume_point(existing_session_data)
            logger.info(f"[RESUME] Resume point determined: phase={resume_point['phase']}, step_id={resume_point.get('step_id')}, skip_phases={resume_point.get('skip_phases', [])}")

            if resume_point.get("phase") == "complete":
                logger.info(f"[RESUME] Batch {batch_id} already complete - skipping workflow resume")
                return {
                    "success": True,
                    "status": "already_complete",
                    "session_id": session_id,
                    "batch_id": batch_id,
                }
            
            logger.info(f"[RESUME] Final decision: skip_scraping={skip_scraping}, session_id={session_id}")
            
            # Load link context for this batch
            await self._load_link_context(batch_id)
            
            # Validate that links were loaded successfully
            if batch_id not in self.link_context:
                error_msg = f"Failed to load link context for batch {batch_id}"
                logger.error(error_msg)
                await self.ws_manager.broadcast(batch_id, {
                    "type": "error",
                    "batch_id": batch_id,
                    "message": f"无法加载链接上下文: {error_msg}",
                    "error": error_msg
                })
                return {'success': False, 'error': error_msg}
            
            # Check if we have any links to process
            link_context = self.link_context[batch_id]
            total_links = sum(len(links) for links in link_context.values())
            if total_links == 0:
                error_msg = f"No links found for batch {batch_id}. Please ensure test_links.json contains valid links."
                logger.error(error_msg)
                await self.ws_manager.broadcast(batch_id, {
                    "type": "error",
                    "batch_id": batch_id,
                    "message": f"未找到任何链接: 请确保 test_links.json 包含有效的链接",
                    "error": error_msg
                })
                return {'success': False, 'error': error_msg}
            
            logger.info(f"[WorkflowService] ✓ Link context loaded successfully: {total_links} total links for batch {batch_id}")
            
            # Create progress queue for thread-safe communication
            progress_queue = queue.Queue()
            progress_callback = self._create_progress_callback(batch_id, progress_queue)
            
            # Start progress processor task
            progress_task = asyncio.create_task(
                self._process_progress_queue(progress_queue, batch_id)
            )
            
            try:
                # Step 1: Run all scrapers (or skip if already done)
                logger.info(f"[RESUME DEBUG] About to check skip_scraping={skip_scraping}")
                if skip_scraping:
                    # Scraping already complete - skip directly to research
                    logger.info(f"[RESUME DEBUG] ✓✓✓ TAKING SKIP PATH - Skipping scraping for batch {batch_id} - already complete (phase0 exists)")
                    
                    # Notify frontend that scraping is already complete
                    await self.ws_manager.broadcast(batch_id, {
                        "type": "scraping:already_complete",
                        "batch_id": batch_id,
                        "message": "抓取已完成，直接进入研究阶段",
                    })
                else:
                    # Run scrapers normally
                    logger.info(f"[RESUME DEBUG] ✗✗✗ TAKING SCRAPING PATH - Starting scrapers for batch: {batch_id}")
                    
                    # Notify frontend that we're in scraping phase
                    await self.ws_manager.broadcast(batch_id, {
                        "type": "research:phase_change",
                        "phase": "scraping",
                        "phase_name": "抓取进度",
                        "message": "开始抓取内容",
                    })
                    
                    # Initialize streaming summarization manager
                    # This starts Phase 0 immediately, in parallel with scraping
                    logger.info(f"[WorkflowService] About to initialize streaming summarization for batch {batch_id}")
                    logger.info(f"[WorkflowService] link_context keys: {list(self.link_context.keys())}")
                    logger.info(f"[WorkflowService] batch_id in link_context: {batch_id in self.link_context}")
                    
                    try:
                        # V3 Integration: Use v3 workflow manager for scraping → summarization.
                        # This currently builds on top of the proven V2 manager + adapter.
                        from research.phases.streaming_summarization_manager_v3 import (
                            StreamingSummarizationManagerV3 as StreamingSummarizationManager,
                        )
                        from research.client import QwenStreamingClient
                        from core.config import Config
                        from research.session import ResearchSession
                        
                        # Get all expected link_ids from link context
                        all_link_ids = []
                        if batch_id in self.link_context:
                            logger.info(f"[WorkflowService] link_context[{batch_id}] keys: {list(self.link_context[batch_id].keys())}")
                            for link_type, links in self.link_context[batch_id].items():
                                logger.debug(f"[WorkflowService] Processing link_type={link_type}, links count={len(links)}")
                                for link_info in links:
                                    link_id = link_info.get('link_id')
                                    if link_id:
                                        # For YouTube/Bilibili, we track base link_id (not _comments)
                                        if link_type in ['youtube', 'bilibili']:
                                            # Only add base link_id once (comments are part of same item)
                                            if link_id not in all_link_ids:
                                                all_link_ids.append(link_id)
                                        else:
                                            all_link_ids.append(link_id)
                        else:
                            logger.warning(f"[WorkflowService] batch_id {batch_id} not found in link_context! Available keys: {list(self.link_context.keys())}")
                        
                        logger.info(f"[WorkflowService] Collected {len(all_link_ids)} link_ids for streaming summarization: {all_link_ids[:5]}...")
                        
                        # V2 Integration: Collect source types for data merger
                        source_types = {}
                        if batch_id in self.link_context:
                            for link_type, links in self.link_context[batch_id].items():
                                for link_info in links:
                                    link_id = link_info.get('link_id')
                                    if link_id:
                                        source_types[link_id] = link_type
                        logger.info(f"[WorkflowService] Collected source types for {len(source_types)} items")
                        
                        if all_link_ids:
                            logger.info(f"[WorkflowService] Initializing streaming summarization for {len(all_link_ids)} items")
                            
                            # Create UI for streaming manager
                            main_loop = asyncio.get_running_loop()
                            ui = WebSocketUI(
                                self.ws_manager,
                                batch_id,
                                main_loop=main_loop,
                                conversation_service=self.conversation_service,
                            )
                            
                            # Create or load session
                            session = ResearchSession.create_or_load(batch_id)
                            
                            # Create Qwen client
                            config = Config()
                            api_key = config.get("qwen.api_key")
                            if not api_key:
                                api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
                            
                            if api_key:
                                client = QwenStreamingClient(api_key=api_key)
                                
                                # Create streaming manager
                                streaming_manager = StreamingSummarizationManager(
                                    client=client,
                                    config=config,
                                    ui=ui,
                                    session=session,
                                    batch_id=batch_id
                                )
                                
                                # Register expected items (V2: pass source types for merger)
                                streaming_manager.register_expected_items(all_link_ids, sources=source_types)
                                
                                # Start workers (V2: starts 1 worker via adapter)
                                streaming_manager.start_workers()
                                
                                # Store manager
                                self.streaming_managers[batch_id] = streaming_manager
                                
                                logger.info(f"[WorkflowService] Streaming summarization started for batch {batch_id}")
                            else:
                                logger.warning("[WorkflowService] No API key found, skipping streaming summarization")
                        else:
                            logger.warning(f"[WorkflowService] No link_ids found for batch {batch_id}, skipping streaming summarization")
                            # Notify frontend about missing links for summarization
                            context_keys = list(self.link_context.get(batch_id, {}).keys())
                            await self.ws_manager.broadcast(batch_id, {
                                "type": "warning",
                                "batch_id": batch_id,
                                "message": f"未找到链接ID，跳过流式摘要初始化。链接上下文: {context_keys}",
                            })
                    except Exception as e:
                        error_msg = f"Failed to initialize streaming summarization for batch {batch_id}: {e}"
                        logger.error(error_msg, exc_info=True)
                        import traceback
                        logger.error(f"[WorkflowService] Full traceback: {traceback.format_exc()}")
                        # Notify frontend about the error but continue without streaming mode
                        await self.ws_manager.broadcast(batch_id, {
                            "type": "warning",
                            "batch_id": batch_id,
                            "message": f"流式摘要初始化失败，将使用批处理模式: {str(e)}",
                        })
                        # Continue without streaming mode - will fall back to batch mode
                    
                    # Check cancellation before scraping
                    if self.progress_service.is_cancelled(batch_id):
                        logger.info(f"Batch {batch_id} was cancelled before scraping")
                        return {'success': False, 'error': 'Cancelled by user'}
                    
                    # Use direct execution to pass progress callbacks to scrapers
                    # Run in thread pool - Playwright needs to be initialized in the thread
                    # Note: Playwright browser processes are created in the thread, so this should work
                    logger.info(f"[WorkflowService] Starting scraping execution for batch {batch_id} with {total_links} links")
                    try:
                        scrapers_result = await asyncio.to_thread(
                            _run_scrapers_in_thread,
                            progress_callback=progress_callback,
                            batch_id=batch_id,
                            cancellation_checker=lambda: self.progress_service.is_cancelled(batch_id)
                        )
                        logger.info(f"[WorkflowService] ✓ Scraping execution completed for batch {batch_id}: {scrapers_result}")
                    except Exception as scraping_error:
                        error_msg = f"Failed to start scraping for batch {batch_id}: {str(scraping_error)}"
                        logger.error(error_msg, exc_info=True)
                        await self.ws_manager.broadcast(batch_id, {
                            "type": "error",
                            "batch_id": batch_id,
                            "message": f"抓取启动失败: {str(scraping_error)}",
                            "error": error_msg
                        })
                        raise
                    
                    # Check cancellation after scraping
                    if self.progress_service.is_cancelled(batch_id):
                        logger.info(f"Batch {batch_id} was cancelled during scraping")
                        cancellation_info = self.progress_service.get_cancellation_info(batch_id)
                        return {
                            'success': False,
                            'error': 'Cancelled by user',
                            'cancellation_info': cancellation_info
                        }
                    
                    if not scrapers_result.get("success"):
                        logger.error(f"Scrapers failed: {scrapers_result}")
                        raise Exception("Scrapers failed")
                    
                    scraping_end_time = time.time()
                    logger.info(f"[TIMING] Scraping completed at {scraping_end_time:.3f}: {scrapers_result.get('passed', 0)}/{scrapers_result.get('total', 0)} succeeded")
                    
                    # Wait for all status updates to be processed before transitioning
                    # This ensures all links have final status before research phase starts
                    status_wait_start = time.time()
                    logger.info(f"[TIMING] Starting status updates wait at {status_wait_start:.3f} for batch {batch_id}")
                    logger.info(f"Waiting for status updates to complete for batch {batch_id}...")
                    all_status_complete = await self._wait_for_status_updates(progress_queue, batch_id, max_wait_seconds=10.0)
                    status_wait_elapsed = time.time() - status_wait_start
                    logger.info(f"[TIMING] Status updates wait completed in {status_wait_elapsed:.3f}s for batch {batch_id}")
                    
                    # Force a final batch status update to ensure frontend has accurate state
                    await self.progress_service._update_batch_status(batch_id)
                    
                    # CRITICAL: Wait for explicit confirmation signal from scraping service
                    # This ensures all expected processes (not just started ones) are complete
                    confirmation_start = time.time()
                    logger.info(f"[TIMING] Starting confirmation wait at {confirmation_start:.3f} for batch {batch_id}")
                    logger.info(f"Waiting for scraping completion confirmation for batch {batch_id}...")
                    confirmation = await self.wait_for_scraping_confirmation(progress_queue, batch_id, max_wait_seconds=15.0)
                    confirmation_elapsed = time.time() - confirmation_start
                    logger.info(f"[TIMING] Confirmation wait completed in {confirmation_elapsed:.3f}s for batch {batch_id}")
                    
                    if not confirmation or not confirmation.get('confirmed'):
                        # Confirmation not received or not confirmed
                        if confirmation:
                            logger.error(
                                f"Scraping completion NOT confirmed for batch {batch_id}: "
                                f"Expected {confirmation.get('expected_total', 0)}, "
                                f"Registered {confirmation.get('registered_count', 0)}, "
                                f"Completed {confirmation.get('completed_count', 0)}, "
                                f"Failed {confirmation.get('failed_count', 0)}, "
                                f"Pending {confirmation.get('pending_count', 0)}, "
                                f"In Progress {confirmation.get('in_progress_count', 0)}"
                            )
                            if confirmation.get('non_final_statuses'):
                                logger.error(f"Non-final statuses: {confirmation.get('non_final_statuses')}")
                        else:
                            logger.error(f"Scraping completion confirmation timeout for batch {batch_id}")
                        
                        # Don't proceed to research phase - this is a critical error
                        raise Exception(
                            f"Scraping completion not confirmed for batch {batch_id}. "
                            f"Cannot proceed to research phase until all expected processes complete."
                        )
                    
                    # Explicit 100% completion check
                    completion_rate = confirmation.get('completion_rate', 0.0)
                    completion_percentage = confirmation.get('completion_percentage', 0.0)
                    is_100_percent = confirmation.get('is_100_percent', False)
                    total_final = confirmation.get('total_final', 0)
                    expected_total = confirmation.get('expected_total', 0)
                    
                    # Require explicit 100% completion
                    if not (is_100_percent and total_final == expected_total and completion_percentage >= 100.0):
                        logger.error(
                            f"Completion rate not 100%: {completion_percentage:.1f}% "
                            f"({total_final}/{expected_total})"
                        )
                        raise Exception(
                            f"Scraping not 100% complete: {completion_percentage:.1f}% "
                            f"({total_final}/{expected_total}). Cannot proceed to research phase."
                        )
                    
                    logger.info(
                        f"Scraping 100% COMPLETE for batch {batch_id}: "
                        f"{completion_percentage:.1f}% ({total_final}/{expected_total}) - "
                        f"{confirmation.get('completed_count', 0)} completed, "
                        f"{confirmation.get('failed_count', 0)} failed"
                    )
                    
                    # Additional polling check as backup to catch timing issues
                    is_100_percent_polled = await self.wait_for_100_percent_completion(
                        batch_id,
                        max_wait_seconds=10.0
                    )
                    
                    if not is_100_percent_polled:
                        logger.error("100% completion not reached after polling")
                        raise Exception("Scraping not 100% complete after polling. Cannot proceed to research phase.")
                    
                    # Wait for Phase 0 (streaming summarization) to complete if it was started
                    if batch_id in self.streaming_managers:
                        logger.info(f"[WorkflowService] Waiting for Phase 0 (streaming summarization) to complete for batch {batch_id}")
                        streaming_manager = self.streaming_managers[batch_id]
                        
                        # Wait for completion (with timeout)
                        phase0_complete = await asyncio.to_thread(
                            streaming_manager.wait_for_completion,
                            timeout=300.0  # 5 minute timeout
                        )
                        
                        if phase0_complete:
                            stats = streaming_manager.get_statistics()
                            
                            # Use the is_complete flag which uses (completed + failed) / successfully_scraped == 100%
                            # This avoids race conditions by checking terminal states
                            is_complete = stats.get('is_complete', False)
                            successfully_scraped = stats.get('successfully_scraped', stats.get('scraped', 0))
                            summarized_count = stats.get('summarized_count', stats.get('summarized', 0))
                            failed_count = stats.get('failed_count', stats.get('failed', 0))
                            completion_percentage = stats.get('completion_percentage', 0.0)
                            summaries_created = stats.get('created', 0)
                            summaries_reused = stats.get('reused', 0)
                            total_registered = stats.get('total', 0)
                            
                            terminal_count = summarized_count + failed_count
                            
                            logger.info(
                                f"[WorkflowService] Phase 0 (streaming) completion check: "
                                f"{summarized_count} summarized, {failed_count} failed "
                                f"({terminal_count}/{successfully_scraped} = {completion_percentage:.1f}%) "
                                f"out of {total_registered} total registered "
                                f"({summaries_created} created, {summaries_reused} reused)"
                            )
                            
                            # Verify all successfully scraped items reached terminal states
                            # Failed scrapes cannot be summarized, so they are excluded
                            if not is_complete:
                                logger.error(
                                    f"[WorkflowService] Phase 0 incomplete: "
                                    f"{terminal_count}/{successfully_scraped} successfully scraped items reached terminal states. "
                                    f"Completion: {completion_percentage:.1f}%. "
                                    f"Cannot proceed to Phase 0.5/1."
                                )
                                raise Exception(
                                    f"Phase 0 incomplete: {terminal_count}/{successfully_scraped} successfully scraped items "
                                    f"reached terminal states (completion: {completion_percentage:.1f}%). "
                                    f"Cannot proceed to research phases."
                                )
                            
                            # Complete Phase 0 by running Phase0Prepare with streaming manager
                            # This creates abstracts and finalizes the phase0 artifact
                            try:
                                from research.phases.phase0_prepare import Phase0Prepare
                                
                                # Get the session that was used for streaming
                                session = streaming_manager.session
                                
                                # Create Phase0Prepare instance
                                phase0 = Phase0Prepare(
                                    client=streaming_manager.client,
                                    session=session,
                                    ui=streaming_manager.ui
                                )
                                
                                # Execute Phase 0 in streaming mode
                                phase0_result = await asyncio.to_thread(
                                    phase0.execute,
                                    batch_id=batch_id,
                                    streaming_mode=True,
                                    streaming_manager=streaming_manager
                                )
                                
                                # Format the artifact in the same way as run_phase0_prepare does
                                batch_data = phase0_result.get("data", {})
                                abstracts = phase0_result.get("abstracts", {})
                                
                                # Create combined abstract
                                combined_abstract = "\n\n---\n\n".join([
                                    f"**来源: {link_id}**\n{abstract}"
                                    for link_id, abstract in abstracts.items()
                                ])
                                
                                MAX_ABSTRACT_LENGTH = 80000
                                if len(combined_abstract) > MAX_ABSTRACT_LENGTH:
                                    logger.warning(
                                        f"Combined abstract too large ({len(combined_abstract)} chars), "
                                        f"truncating to {MAX_ABSTRACT_LENGTH} chars"
                                    )
                                    combined_abstract = combined_abstract[:MAX_ABSTRACT_LENGTH] + "\n\n[注意: 摘要已截断]"
                                
                                # Create data summary
                                sources = list(set([data.get("source", "unknown") for data in batch_data.values()]))
                                total_words = sum([data.get("metadata", {}).get("word_count", 0) for data in batch_data.values()])
                                total_comments = sum([
                                    len(data.get("comments") or [])
                                    for data in batch_data.values()
                                ])
                                
                                quality_assessment = phase0_result.get("quality_assessment", {})
                                
                                transcript_sizes = []
                                for data in batch_data.values():
                                    transcript = data.get("transcript", "")
                                    if transcript:
                                        word_count = len(transcript.split())
                                        transcript_sizes.append(word_count)
                                
                                transcript_size_analysis = {}
                                if transcript_sizes:
                                    transcript_size_analysis = {
                                        "max_transcript_words": max(transcript_sizes),
                                        "avg_transcript_words": int(sum(transcript_sizes) / len(transcript_sizes)),
                                        "large_transcript_count": sum(1 for s in transcript_sizes if s > 5000),
                                        "total_transcripts": len(transcript_sizes)
                                    }
                                
                                data_summary = {
                                    "sources": sources,
                                    "total_words": total_words,
                                    "total_comments": total_comments,
                                    "num_items": len(batch_data),
                                    "quality_assessment": quality_assessment,
                                    "transcript_size_analysis": transcript_size_analysis
                                }
                                
                                # Save artifact in the format expected by run_phase0_prepare
                                artifact = {
                                    "phase0_result": phase0_result,
                                    "combined_abstract": combined_abstract,
                                    "batch_data": batch_data,
                                    "data_summary": data_summary,
                                    "streaming_mode": True
                                }
                                
                                session.save_phase_artifact("phase0", artifact)
                                
                                # Shutdown workers after artifact is saved
                                streaming_manager.shutdown()
                                
                                logger.info(
                                    f"[WorkflowService] Phase 0 (streaming) finalized and saved to session with {len(batch_data)} items. "
                                    f"All {successfully_scraped} successfully scraped items processed ({summarized_count} summarized, {failed_count} failed)."
                                )
                            except Exception as e:
                                logger.error(f"[WorkflowService] Error finalizing Phase 0 (streaming): {e}", exc_info=True)
                                
                                # Try to save a partial artifact with streaming_mode flag so batch mode knows not to re-summarize
                                try:
                                    # Get summarized data even if Phase0Prepare.execute failed
                                    batch_data = streaming_manager.get_all_summarized_data()
                                    if batch_data:
                                        # Create minimal artifact to indicate streaming mode was used
                                        partial_artifact = {
                                            "streaming_mode": True,
                                            "phase0_result": {
                                                "batch_id": batch_id,
                                                "data": batch_data,
                                                "num_items": len(batch_data),
                                                "error": str(e)
                                            },
                                            "batch_data": batch_data,
                                            "data_summary": {
                                                "num_items": len(batch_data),
                                                "sources": list(set([data.get("source", "unknown") for data in batch_data.values()]))
                                            }
                                        }
                                        session.save_phase_artifact("phase0", partial_artifact)
                                        logger.info(
                                            f"[WorkflowService] Saved partial Phase 0 artifact with {len(batch_data)} items "
                                            f"(streaming_mode=True) despite error. Batch mode will skip re-summarization."
                                        )
                                except Exception as save_error:
                                    logger.error(f"[WorkflowService] Failed to save partial artifact: {save_error}", exc_info=True)
                                
                                # Continue anyway - batch mode will handle it, but now it knows summaries exist
                        else:
                            logger.warning("[WorkflowService] Phase 0 (streaming) timeout, continuing with available data")
                    
                    # Step 2: Verify scraper results (using proven test function)
                    verify_start = time.time()
                    logger.info(f"[TIMING] Starting verification at {verify_start:.3f} for batch {batch_id}")
                    logger.info(f"Verifying scraper results for batch: {batch_id}")
                    
                    verified = await asyncio.to_thread(
                        verify_scraper_results,
                        batch_id,
                        progress_callback=progress_callback
                    )
                    verify_elapsed = time.time() - verify_start
                    logger.info(f"[TIMING] Verification completed in {verify_elapsed:.3f}s for batch {batch_id}")
                    
                    if not verified:
                        await self.ws_manager.broadcast(batch_id, {
                            "type": "error",
                            "phase": "verification",
                            "message": "抓取结果验证失败",
                        })
                        raise Exception("Scraper results verification failed")
                
                # Step 3: Run research agent (using proven test function)
                phase_change_start = time.time()
                logger.info(f"[TIMING] Sending phase change at {phase_change_start:.3f} for batch {batch_id}")
                logger.info(f"Starting research agent for batch: {batch_id}")
                
                # NOW send phase change (after all scraping status is finalized)
                # This ensures frontend has received all status updates before Research Agent tab appears
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:phase_change",
                    "phase": "research",
                    "phase_name": "研究代理",
                    "message": "开始研究阶段",
                })
                phase_change_elapsed = time.time() - phase_change_start
                logger.info(f"[TIMING] Phase change sent in {phase_change_elapsed:.3f}s for batch {batch_id}")
                
                # Create UI with WebSocket callbacks and main event loop reference
                main_loop = asyncio.get_running_loop()
                ui = WebSocketUI(
                    self.ws_manager,
                    batch_id,
                    main_loop=main_loop,
                    conversation_service=self.conversation_service,
                )
                
                # Register UI instance with WebSocket manager for user input delivery
                self.ws_manager.register_ui(batch_id, ui)
                
                # Notify UI that research is starting
                ui.notify_phase_change("research", "研究代理")
                
                # Run research agent with progress callbacks
                result = await asyncio.to_thread(
                    run_research_agent,
                    batch_id,
                    ui=ui,
                    progress_callback=progress_callback,
                    session_id=session_id,  # Pass session_id to resume existing session if found
                    resume_point=resume_point  # Pass resume point information
                )
                
                if not result:
                    raise Exception("Research agent failed")

                session_id = result.get("session_id")
                if session_id:
                    self.conversation_service.set_session_id(batch_id, session_id)
                
                # Send research:complete signal to indicate research agent has finished
                await self.ws_manager.broadcast(batch_id, {
                    "type": "research:complete",
                    "batch_id": batch_id,
                    "session_id": session_id,
                    "status": "completed",
                    "message": "研究完成",
                })
                
                await self.ws_manager.broadcast(batch_id, {
                    "type": "workflow:complete",
                    "batch_id": batch_id,
                    "result": result,
                })
                
                return result
                
            finally:
                # Unregister UI instance when workflow completes
                self.ws_manager.unregister_ui(batch_id)
                # Cancel progress processor (will finish processing remaining messages)
                progress_task.cancel()
                try:
                    await asyncio.wait_for(progress_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                # Process any remaining messages (only broadcast if they have a 'type' field)
                # Skip ALL internal action messages (update_link_progress, update_link_status, etc.)
                while True:
                    try:
                        message = progress_queue.get_nowait()
                        # Only broadcast messages with 'type' field (WebSocket messages)
                        # Skip ALL internal action messages - they should be processed by ProgressService, not broadcast
                        if message.get('action') in ['update_link_progress', 'update_link_status']:
                            # These are internal messages - skip them (they should have been processed already)
                            logger.debug(f"Skipping internal action message in cleanup: {message.get('action')}")
                            continue
                        elif 'type' in message:
                            await self.ws_manager.broadcast(batch_id, message)
                        elif message.get('action') == 'broadcast':
                            # Handle broadcast action messages
                            await self.ws_manager.broadcast(batch_id, message.get('message', message))
                    except queue.Empty:
                        break
            
        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            error_message = str(e)
            
            # Provide more detailed error messages
            if "Research agent failed" in error_message or "prompt_user" in error_message.lower():
                detailed_message = f"工作流错误: 研究代理失败 - 可能是用户输入超时或连接问题。错误详情: {error_message}"
            else:
                detailed_message = f"工作流错误: {error_message}"
            
            await self.ws_manager.broadcast(batch_id, {
                "type": "error",
                "phase": "workflow",
                "message": detailed_message,
            })
            raise


