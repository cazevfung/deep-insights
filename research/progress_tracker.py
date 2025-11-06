"""Progress tracking for research execution."""

from typing import Dict, List, Callable, Optional
from datetime import datetime
from loguru import logger


class ProgressTracker:
    """Track execution progress with real-time updates."""
    
    def __init__(self, total_steps: int):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps to track
        """
        self.total_steps = total_steps
        self.completed_steps = 0
        self.current_step_id = None
        self.current_step_goal = None
        self.status_callbacks: List[Callable] = []
        self.step_complete_callbacks: List[Callable] = []  # New: for step completion with findings
        self.steps_status: Dict[int, Dict] = {}
        self.start_time = datetime.now()
        self.current_step_start_time = None
        
        logger.info(f"Initialized ProgressTracker with {total_steps} total steps")
    
    def add_callback(self, callback: Callable):
        """Add a callback for status updates."""
        self.status_callbacks.append(callback)
    
    def add_step_complete_callback(self, callback: Callable):
        """Add a callback for step completion with findings."""
        self.step_complete_callbacks.append(callback)
    
    def _notify_callbacks(self, status: Dict):
        """Notify all callbacks of status change."""
        for callback in self.status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.warning(f"Callback error: {str(e)}")
    
    def start_step(self, step_id: int, goal: str):
        """
        Mark step as started.
        
        Args:
            step_id: Step identifier
            goal: Step goal description
        """
        self.current_step_id = step_id
        self.current_step_goal = goal
        self.current_step_start_time = datetime.now()
        
        self.steps_status[step_id] = {
            "step_id": step_id,
            "goal": goal,
            "status": "in_progress",
            "start_time": self.current_step_start_time.isoformat(),
            "findings": None,
            "error": None
        }
        
        status = self.get_status()
        self._notify_callbacks(status)
        
        logger.info(f"Started step {step_id}: {goal}")
    
    def complete_step(self, step_id: int, findings: Optional[Dict] = None):
        """
        Mark step as completed.
        
        Args:
            step_id: Step identifier
            findings: Optional findings from this step
        """
        if step_id not in self.steps_status:
            logger.warning(f"Cannot complete step {step_id}: not started")
            return
        
        end_time = datetime.now()
        duration = (end_time - self.current_step_start_time).total_seconds() if self.current_step_start_time else 0
        
        self.steps_status[step_id].update({
            "status": "completed",
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "findings": findings
        })
        
        self.completed_steps += 1
        
        # Reset current step if this was the current one
        if step_id == self.current_step_id:
            self.current_step_id = None
            self.current_step_goal = None
            self.current_step_start_time = None
        
        status = self.get_status()
        self._notify_callbacks(status)
        
        # Notify step completion callbacks - always send, even without findings
        # This ensures all steps are sent to the frontend
        step_data = {
            "step_id": step_id,
            "findings": findings.get("findings", {}) if isinstance(findings, dict) and findings else {},
            "insights": findings.get("insights", "") if isinstance(findings, dict) and findings else "",
            "confidence": findings.get("confidence", 0.0) if isinstance(findings, dict) and findings else 0.0,
            "timestamp": end_time.isoformat(),
        }
        for callback in self.step_complete_callbacks:
            try:
                callback(step_data)
                logger.debug(f"Notified step complete callback for step {step_id}")
            except Exception as e:
                logger.warning(f"Step complete callback error: {str(e)}")
        
        logger.info(f"Completed step {step_id} in {duration:.2f}s")
    
    def fail_step(self, step_id: int, error: str):
        """
        Mark step as failed.
        
        Args:
            step_id: Step identifier
            error: Error message
        """
        if step_id not in self.steps_status:
            logger.warning(f"Cannot fail step {step_id}: not started")
            return
        
        end_time = datetime.now()
        duration = (end_time - self.current_step_start_time).total_seconds() if self.current_step_start_time else 0
        
        self.steps_status[step_id].update({
            "status": "failed",
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "error": error
        })
        
        # Reset current step if this was the current one
        if step_id == self.current_step_id:
            self.current_step_id = None
            self.current_step_goal = None
            self.current_step_start_time = None
        
        status = self.get_status()
        self._notify_callbacks(status)
        
        logger.error(f"Step {step_id} failed: {error}")
    
    def stream_update(self, token: str):
        """
        Update streaming progress.
        
        Args:
            token: Token received from stream
        """
        status = self.get_status()
        status["current_stream_token"] = token
        self._notify_callbacks(status)
    
    def get_status(self) -> Dict:
        """
        Get current status.
        
        Returns:
            Status dictionary with progress information
        """
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        progress_percentage = (self.completed_steps / self.total_steps * 100) if self.total_steps > 0 else 0
        
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "progress_percentage": round(progress_percentage, 1),
            "current_step_id": self.current_step_id,
            "current_step_goal": self.current_step_goal,
            "elapsed_time_seconds": round(elapsed_time, 2),
            "steps_status": self.steps_status,
            "is_complete": self.completed_steps >= self.total_steps
        }
    
    def get_progress_bar(self, width: int = 20) -> str:
        """
        Generate a text progress bar.
        
        Args:
            width: Width of progress bar in characters
            
        Returns:
            Progress bar string
        """
        if self.total_steps == 0:
            return "[" + " " * width + "]"
        
        filled = int(self.completed_steps / self.total_steps * width)
        bar = "█" * filled + "░" * (width - filled)
        
        return f"[{bar}] {self.completed_steps}/{self.total_steps} ({self.get_status()['progress_percentage']}%)"

