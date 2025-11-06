"""Base class for all research phases."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger

from research.client import QwenStreamingClient
from research.progress_tracker import ProgressTracker
from research.session import ResearchSession


class BasePhase(ABC):
    """Abstract base class for all research phases."""
    
    def __init__(
        self,
        client: QwenStreamingClient,
        session: ResearchSession,
        progress_tracker: Optional[ProgressTracker] = None,
        ui = None
    ):
        """
        Initialize phase.
        
        Args:
            client: Qwen streaming API client
            session: Research session
            progress_tracker: Optional progress tracker
            ui: Optional UI interface for progress updates
        """
        self.client = client
        self.session = session
        self.progress_tracker = progress_tracker
        self.ui = ui
        self.logger = logger.bind(phase=self.__class__.__name__)
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the phase.
        
        Returns:
            Phase results
        """
        pass
    
    def _stream_with_callback(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Stream API call with progress callback.
        
        Args:
            messages: API messages
            **kwargs: Additional arguments for stream_completion
            
        Returns:
            Full response text
        """
        import time
        
        # Send "starting" update
        if self.ui:
            self.ui.display_message("正在调用AI API...", "info")
        
        token_count = 0
        last_update_time = time.time()
        update_interval = 2.0  # Update every 2 seconds
        
        def callback(token: str):
            nonlocal token_count, last_update_time
            
            token_count += 1
            current_time = time.time()
            
            # Update progress tracker
            if self.progress_tracker:
                self.progress_tracker.stream_update(token)
            
            # Send periodic progress updates to UI
            if self.ui and (token_count % 10 == 0 or current_time - last_update_time >= update_interval):
                self.ui.display_message(f"正在接收响应... ({token_count} tokens)", "info")
                last_update_time = current_time
        
        response, usage = self.client.stream_and_collect(
            messages,
            callback=callback,
            **kwargs
        )
        
        # Send "parsing" update
        if self.ui:
            self.ui.display_message("正在解析结果...", "info")
        
        return response

