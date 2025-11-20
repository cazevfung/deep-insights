"""
Editor service for AI-powered content editing.
"""
import os
import json
from typing import Optional, Dict, Any, List, AsyncIterator, Union
from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    from research.session import ResearchSession
    from research.client import QwenStreamingClient
    from core.config import Config
except ImportError as e:
    logger.warning(f"Unable to import required modules: {e}")
    ResearchSession = None  # type: ignore
    QwenStreamingClient = None  # type: ignore
    Config = None  # type: ignore


class EditorService:
    def __init__(self, config: Config):
        self.config = config
        self.editor_config = config.get_editor_config()
        self._qwen_client: Optional[QwenStreamingClient] = None
        # NEW: Feature flags to control editing per phase
        self.feature_flags = {
            'phase1_editing_enabled': True,   # Enable now that field-level editing is implemented
            'phase2_editing_enabled': True,   # Enable now that field-level editing is implemented
            'phase3_editing_enabled': True,   # Enable with caution (may work for simple cases)
            'phase4_editing_enabled': True,   # Enable (should work for string content)
        }
    
    def _get_qwen_client(self) -> QwenStreamingClient:
        """Lazy initialization of Qwen client."""
        if QwenStreamingClient is None:
            raise RuntimeError("QwenStreamingClient unavailable")
        
        if self._qwen_client is None:
            api_key = self.config.get('qwen.api_key') or os.getenv('DASHSCOPE_API_KEY')
            if not api_key:
                raise ValueError("Qwen API key not configured")
            model = self.editor_config['model']
            self._qwen_client = QwenStreamingClient(api_key=api_key, model=model)
        return self._qwen_client
    
    def _load_session(self, batch_id: str) -> ResearchSession:
        """Load ResearchSession for batch_id.
        
        Note: batch_id is typically used as session_id in this system.
        """
        if ResearchSession is None:
            raise RuntimeError("ResearchSession unavailable")
        
        # In this system, batch_id is typically the same as session_id
        # ResearchSession.load() expects session_id and loads from:
        # data/research/sessions/session_{session_id}.json
        try:
            return ResearchSession.load(batch_id)
        except Exception as e:
            # Fallback: try create_or_load if session doesn't exist yet
            logger.warning(f"Failed to load session {batch_id}, trying create_or_load: {e}")
            return ResearchSession.create_or_load(batch_id)
    
    def _get_phase_key(self, phase: str, step_id: Optional[str] = None) -> str:
        """Get phase artifact key."""
        if phase == 'phase3' and step_id:
            return f"phase3_step_{step_id}"
        return phase
    
    def _extract_content_from_artifact(self, artifact: Dict[str, Any], phase: str) -> str:
        """Extract content string from phase artifact."""
        # Handle different artifact structures
        data = artifact.get('data', artifact) if isinstance(artifact, dict) else {}
        
        if phase == 'phase1':
            # Try different possible keys
            if isinstance(data, dict):
                goals = data.get('goals')
                # NEW: Validate type - prevent data corruption
                if isinstance(goals, list):
                    logger.error(
                        f"Phase 1 artifact contains goals array, not string. "
                        f"Cannot use string-based editing. Use field-level editing instead."
                    )
                    raise ValueError(
                        "Phase 1 goals are stored as an array. "
                        "String-based editing is not supported. "
                        "Please use field-level editing (metadata required)."
                    )
                return data.get('content', data.get('output', ''))
            return str(data) if data else ''
        elif phase == 'phase2':
            if isinstance(data, dict):
                plan = data.get('plan')
                # NEW: Validate type - prevent data corruption
                if isinstance(plan, list):
                    logger.error(
                        f"Phase 2 artifact contains plan array, not string. "
                        f"Cannot use string-based editing. Use field-level editing instead."
                    )
                    raise ValueError(
                        "Phase 2 plan is stored as an array. "
                        "String-based editing is not supported. "
                        "Please use field-level editing (metadata required)."
                    )
                return data.get('questions', data.get('content', ''))
            return str(data) if data else ''
        elif phase == 'phase3':
            if isinstance(data, dict):
                return data.get('content', data.get('step_content', data.get('output', '')))
            return str(data) if data else ''
        elif phase == 'phase4':
            if isinstance(data, dict):
                return data.get('content', data.get('report', data.get('output', '')))
            return str(data) if data else ''
        
        # Fallback: try to find any string content
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # Try common keys
            for key in ['content', 'output', 'text', 'result']:
                if key in data and isinstance(data[key], str):
                    return data[key]
        
        return str(data) if data else ''
    
    def _extract_field_from_artifact(
        self,
        artifact: Dict[str, Any],
        field_path: List[Union[str, int]],
        phase: str,
        session: Optional[ResearchSession] = None,
        batch_id: Optional[str] = None
    ) -> Optional[str]:
        """Extract specific field value from artifact using field path.
        
        Args:
            artifact: Phase artifact
            field_path: Path to field, e.g., ['goals', 0, 'goal_text'] or ['phase3_step_1', 'summary']
            phase: Phase identifier
            session: Optional session for loading step artifacts (Phase 3)
            batch_id: Optional batch_id for loading step artifacts (Phase 3)
        
        Returns:
            Field value as string, or None if not found
        """
        # For Phase 3 step artifacts, field_path might be ['phase3_step_1', 'summary']
        # Need to load the step artifact separately
        if phase == 'phase3' and len(field_path) >= 2:
            phase_key = field_path[0]
            if isinstance(phase_key, str) and phase_key.startswith('phase3_step_'):
                # This is a step artifact, load it separately
                if session is None and batch_id:
                    session = self._load_session(batch_id)
                
                if session:
                    step_artifact = session.get_phase_artifact(phase_key, {})
                    if step_artifact:
                        # Continue with remaining path
                        remaining_path = field_path[1:]
                        return self._extract_field_from_artifact(
                            step_artifact, remaining_path, phase, session, batch_id
                        )
                return None
        
        data = artifact.get('data', artifact) if isinstance(artifact, dict) else {}
        
        # Navigate path
        current = data
        for segment in field_path:
            if isinstance(segment, int):
                # Array index
                if isinstance(current, list) and 0 <= segment < len(current):
                    current = current[segment]
                else:
                    return None
            else:
                # Object key
                if isinstance(current, dict):
                    current = current.get(segment)
                else:
                    return None
            
            if current is None:
                return None
        
        # Convert to string
        if isinstance(current, str):
            return current
        elif isinstance(current, (int, float, bool)):
            return str(current)
        else:
            # For complex types, return JSON string
            return json.dumps(current, ensure_ascii=False)
        
        return None
    
    def _update_field_in_artifact(
        self,
        artifact: Dict[str, Any],
        field_path: List[Union[str, int]],
        new_value: str,
        phase: str,
        session: Optional[ResearchSession] = None,
        batch_id: Optional[str] = None,
        phase_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update specific field in artifact using field path.
        
        Args:
            artifact: Phase artifact
            field_path: Path to field, e.g., ['goals', 0, 'goal_text'] or ['phase3_step_1', 'summary']
            new_value: New field value
            phase: Phase identifier
            session: Optional session for updating step artifacts (Phase 3)
            batch_id: Optional batch_id for loading step artifacts (Phase 3)
            phase_key: Optional phase_key for saving step artifacts (Phase 3)
        
        Returns:
            Updated artifact
        """
        # For Phase 3 step artifacts, field_path might be ['phase3_step_1', 'summary']
        # Need to load and update the step artifact separately
        if phase == 'phase3' and len(field_path) >= 2:
            step_phase_key = field_path[0]
            if isinstance(step_phase_key, str) and step_phase_key.startswith('phase3_step_'):
                # This is a step artifact, load and update it separately
                if session is None and batch_id:
                    session = self._load_session(batch_id)
                
                if session:
                    step_artifact = session.get_phase_artifact(step_phase_key, {})
                    if not step_artifact:
                        # Create new step artifact if it doesn't exist
                        step_artifact = {'data': {}}
                    
                    # Update the step artifact with remaining path
                    remaining_path = field_path[1:]
                    updated_step_artifact = self._update_field_in_artifact(
                        step_artifact, remaining_path, new_value, phase, session, batch_id, step_phase_key
                    )
                    
                    # Save the updated step artifact
                    step_artifact_data = updated_step_artifact.get('data', updated_step_artifact)
                    session.save_phase_artifact(step_phase_key, step_artifact_data, autosave=True)
                    
                    # Return the updated step artifact
                    return updated_step_artifact
                else:
                    raise ValueError("Session required for Phase 3 step artifact updates")
        
        # Ensure artifact has proper structure
        if not isinstance(artifact, dict):
            artifact = {'data': artifact}
        
        data = artifact.get('data', {})
        if not isinstance(data, dict):
            data = {'content': data}
            artifact['data'] = data
        
        # Navigate to parent of target field
        current = data
        for i, segment in enumerate(field_path[:-1]):
            if isinstance(segment, int):
                if isinstance(current, list) and 0 <= segment < len(current):
                    current = current[segment]
                else:
                    raise ValueError(f"Invalid path segment: {segment} (index out of range)")
            else:
                if isinstance(current, dict):
                    current = current[segment]
                else:
                    raise ValueError(f"Invalid path segment: {segment} (not a dict)")
            
            if current is None:
                raise ValueError(f"Path segment {segment} is None")
        
        # Update target field
        target_field = field_path[-1]
        if isinstance(current, dict):
            current[target_field] = new_value
        else:
            raise ValueError(f"Cannot update field in non-dict: {type(current)}")
        
        artifact['data'] = data
        return artifact
    
    def _validate_artifact_structure(self, artifact: Dict[str, Any], phase: str) -> None:
        """Validate that artifact structure is correct after update."""
        data = artifact.get('data', {})
        
        if phase == 'phase1':
            goals = data.get('goals')
            if not isinstance(goals, list):
                raise ValueError(
                    f"Phase 1 artifact structure corrupted: goals is {type(goals)}, expected list"
                )
            # Validate each goal has required fields
            for i, goal in enumerate(goals):
                if not isinstance(goal, dict):
                    raise ValueError(f"Phase 1 goal {i} is not a dict: {type(goal)}")
                if 'goal_text' not in goal:
                    raise ValueError(f"Phase 1 goal {i} missing 'goal_text' field")
        
        elif phase == 'phase2':
            plan = data.get('plan')
            if not isinstance(plan, list):
                raise ValueError(
                    f"Phase 2 artifact structure corrupted: plan is {type(plan)}, expected list"
                )
            # Validate each step has required fields
            for i, step in enumerate(plan):
                if not isinstance(step, dict):
                    raise ValueError(f"Phase 2 step {i} is not a dict: {type(step)}")
                if 'goal' not in step:
                    raise ValueError(f"Phase 2 step {i} missing 'goal' field")
    
    def _update_content_in_artifact(
        self, 
        artifact: Dict[str, Any], 
        phase: str, 
        selected_range: Dict[str, int],
        replacement_text: str
    ) -> Dict[str, Any]:
        """Update artifact content with replacement text."""
        # Ensure artifact has proper structure
        if not isinstance(artifact, dict):
            artifact = {'data': artifact}
        
        data = artifact.get('data', {})
        
        # NEW: Validate structure before update - prevent data corruption
        if phase == 'phase1':
            if isinstance(data.get('goals'), list):
                raise ValueError(
                    "Cannot update goals array using string replacement. "
                    "Use field-level editing instead (metadata required)."
                )
        elif phase == 'phase2':
            if isinstance(data.get('plan'), list):
                raise ValueError(
                    "Cannot update plan array using string replacement. "
                    "Use field-level editing instead (metadata required)."
                )
        
        current_content = self._extract_content_from_artifact(artifact, phase)
        
        # Replace selected range
        start = selected_range['start']
        end = selected_range['end']
        updated_content = current_content[:start] + replacement_text + current_content[end:]
        
        # Update artifact structure based on phase
        if not isinstance(data, dict):
            data = {'content': data}
        
        if phase == 'phase1':
            if 'goals' in data:
                data['goals'] = updated_content
            else:
                data['content'] = updated_content
        elif phase == 'phase2':
            if 'plan' in data:
                data['plan'] = updated_content
            else:
                data['content'] = updated_content
        elif phase == 'phase3':
            data['content'] = updated_content
        elif phase == 'phase4':
            data['content'] = updated_content
        
        artifact['data'] = data
        return artifact
    
    async def chat_with_selection(
        self,
        batch_id: str,
        phase: str,
        selected_text: str,
        full_context: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        step_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream AI response for selected content editing."""
        try:
            # Load session and artifact for context
            session = self._load_session(batch_id)
            phase_key = self._get_phase_key(phase, step_id)
            artifact = session.get_phase_artifact(phase_key, {})
            
            # Load system prompt
            system_prompt_path = Path(self.editor_config['system_prompt_path'])
            if not system_prompt_path.is_absolute():
                # Make relative to project root
                from core.config import find_project_root
                project_root = find_project_root()
                system_prompt_path = project_root / system_prompt_path
            
            if system_prompt_path.exists():
                with open(system_prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
            else:
                system_prompt = "你是一个专业的研究内容编辑助手。"
            
            # Construct user prompt
            user_prompt = f"""以下是用户选中的文本：
---
{selected_text}
---

以下是该文本的完整上下文（来自{phase}阶段）：
---
{full_context}
---

用户请求：
{user_message}

请根据上下文和用户请求，提供修改建议或回答问题。"""
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Add conversation history if provided
            if conversation_history:
                messages = [messages[0]] + conversation_history + [messages[1]]
            
            # Stream response from Qwen
            client = self._get_qwen_client()
            temperature = self.editor_config.get('temperature', 0.7)
            max_tokens = self.editor_config.get('max_tokens', 4000)
            
            # Use stream_completion which is synchronous but yields tokens
            for token in client.stream_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                exclude_reasoning_from_yield=True
            ):
                yield token
            
        except Exception as e:
            logger.error(f"Error in chat_with_selection: {e}", exc_info=True)
            raise
    
    def _detect_phase3_goal_change(
        self,
        session: ResearchSession,
        selected_text: str,
        replacement_text: str
    ) -> Optional[Dict[str, Any]]:
        """Detect if a Phase 3 step goal was changed by parsing the selected/replacement text.
        
        Looks for patterns like "步骤 X: goal" or just the goal text, and matches it
        against the plan to find which step was edited.
        """
        try:
            phase3_artifact = session.get_phase_artifact("phase3", {})
            if not phase3_artifact:
                return None
            
            # Handle both direct artifact and wrapped artifact
            phase3_data = phase3_artifact.get('data', phase3_artifact) if isinstance(phase3_artifact, dict) else {}
            plan = phase3_data.get('plan', [])
            
            if not plan or not isinstance(plan, list):
                return None
            
            # Try to extract step_id from selected text or replacement text
            import re
            
            # Pattern 1: "步骤 {step_id}: {goal}"
            step_pattern = re.compile(r'步骤\s*(\d+)\s*[:：]\s*(.+)', re.MULTILINE)
            
            # Check replacement text first (most likely to have the new goal)
            match = step_pattern.search(replacement_text)
            if not match:
                # Check selected text
                match = step_pattern.search(selected_text)
            
            if match:
                step_id = int(match.group(1))
                new_goal = match.group(2).strip()
                
                # Find the step in plan
                for step in plan:
                    if step.get('step_id') == step_id:
                        old_goal = step.get('goal', '').strip()
                        if old_goal != new_goal:
                            logger.info(
                                f"Detected Phase 3 step {step_id} goal change: "
                                f"'{old_goal[:50]}...' -> '{new_goal[:50]}...'"
                            )
                            return {
                                'step_id': step_id,
                                'old_goal': old_goal,
                                'new_goal': new_goal,
                                'needs_rerun': True
                            }
                        break
            
            # Pattern 2: If replacement is just the goal text (no step prefix),
            # try to match by finding which step's goal was closest to the selected text
            # This is a fallback for when user edits just the goal portion
            if not match and selected_text:
                # Try to find step by matching selected text with existing goals
                for step in plan:
                    step_id = step.get('step_id')
                    old_goal = step.get('goal', '').strip()
                    
                    # Check if selected text contains or is contained in the goal
                    if old_goal and (
                        selected_text.strip() in old_goal or 
                        old_goal in selected_text.strip()
                    ):
                        # Assume replacement_text is the new goal
                        new_goal = replacement_text.strip()
                        if old_goal != new_goal:
                            logger.info(
                                f"Detected Phase 3 step {step_id} goal change (pattern 2): "
                                f"'{old_goal[:50]}...' -> '{new_goal[:50]}...'"
                            )
                            return {
                                'step_id': step_id,
                                'old_goal': old_goal,
                                'new_goal': new_goal,
                                'needs_rerun': True
                            }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error detecting Phase 3 goal change: {e}", exc_info=True)
            return None
    
    async def apply_changes(
        self,
        batch_id: str,
        phase: str,
        selected_range: Dict[str, int],
        replacement_text: str,
        step_id: Optional[str] = None,
        # NEW: Metadata parameters for field-level editing
        item_id: Optional[Union[int, str]] = None,
        item_index: Optional[int] = None,
        field_name: Optional[str] = None,
        field_path: Optional[List[Union[str, int]]] = None
    ) -> Dict[str, Any]:
        """Apply changes to phase content and immediately persist.
        
        For Phase 3, if a step goal is changed, automatically triggers step rerun.
        """
        try:
            # NEW: Check feature flag
            flag_key = f'{phase}_editing_enabled'
            if not self.feature_flags.get(flag_key, False):
                raise ValueError(
                    f"Editing for {phase} is currently disabled. "
                    f"Please wait for the fix to be deployed."
                )
            
            # Load session
            session = self._load_session(batch_id)
            phase_key = self._get_phase_key(phase, step_id)
            
            # Load current artifact
            artifact = session.get_phase_artifact(phase_key, {})
            if not artifact:
                raise ValueError(f"Phase artifact {phase_key} not found for batch {batch_id}")
            
            # NEW: Use field-level update if metadata is available
            if field_path and field_name:
                # For Phase 3, extract step_id from field_path if available
                if phase == 'phase3' and len(field_path) >= 1:
                    step_phase_key = field_path[0]
                    if isinstance(step_phase_key, str) and step_phase_key.startswith('phase3_step_'):
                        # Extract step_id from phase key (e.g., "phase3_step_1" -> "1")
                        step_id_from_path = step_phase_key.replace('phase3_step_', '')
                        if not step_id:
                            step_id = step_id_from_path
                
                # Field-level update
                updated_artifact = self._update_field_in_artifact(
                    artifact, field_path, replacement_text, phase, session, batch_id, phase_key
                )
                
                # Validate structure is preserved (only for phase1/phase2)
                if phase in ['phase1', 'phase2']:
                    self._validate_artifact_structure(updated_artifact, phase)
                
                # Extract updated content for response
                updated_content = self._extract_field_from_artifact(
                    updated_artifact, field_path, phase, session, batch_id
                ) or replacement_text
                
                # Save immediately (for phase1/phase2, phase3 step artifacts are saved in _update_field_in_artifact)
                if phase in ['phase1', 'phase2']:
                    artifact_data = updated_artifact.get('data', updated_artifact)
                    session.save_phase_artifact(phase_key, artifact_data, autosave=True)
                
            else:
                # Fallback to string-based update (for Phase 4 and simple cases)
                # But first validate it's safe
                if phase in ['phase1', 'phase2']:
                    raise ValueError(
                        f"Field-level editing required for {phase}. "
                        f"Metadata (item_id, field_name) must be provided."
                    )
                
                # For Phase 3, check if a step goal was changed
                step_rerun_info = None
                if phase == 'phase3':
                    # Get the original content to extract selected text
                    original_content = self._extract_content_from_artifact(artifact, phase)
                    selected_text = original_content[selected_range['start']:selected_range['end']]
                    
                    step_rerun_info = self._detect_phase3_goal_change(
                        session, selected_text, replacement_text
                    )
                
                # Existing string-based logic for Phase 3/4
                updated_artifact = self._update_content_in_artifact(
                    artifact, phase, selected_range, replacement_text
                )
                
                # Extract updated content for response
                updated_content = self._extract_content_from_artifact(updated_artifact, phase)
            
            # Initialize step_rerun_info (only used for Phase 3 string-based updates)
            step_rerun_info = None
            
            # If Phase 3 goal was changed, update the plan in phase3 artifact
            if step_rerun_info and step_rerun_info.get('needs_rerun'):
                phase3_artifact = session.get_phase_artifact("phase3", {})
                if phase3_artifact:
                    phase3_data = phase3_artifact.get('data', {})
                    phase3_result = phase3_data.get('phase3_result', {})
                    plan = phase3_result.get('plan', [])
                    
                    # Update the goal in the plan
                    target_step_id = step_rerun_info['step_id']
                    for step in plan:
                        if step.get('step_id') == target_step_id:
                            step['goal'] = step_rerun_info['new_goal']
                            break
                    
                    # Save updated plan
                    phase3_result['plan'] = plan
                    phase3_data['phase3_result'] = phase3_result
                    phase3_artifact['data'] = phase3_data
                    session.save_phase_artifact("phase3", phase3_data, autosave=True)
            
            # Save immediately (this persists to session.json)
            # Extract just the data part for saving
            artifact_data = updated_artifact.get('data', updated_artifact)
            session.save_phase_artifact(phase_key, artifact_data, autosave=True)
            
            response_metadata = {
                "edit_timestamp": datetime.now().isoformat(),
                "persisted": True,
                "will_affect_future_phases": True,
                "phase": phase,
                "step_id": step_id,
                "field_updated": field_name,
                "item_id": item_id
            }
            
            # Add rerun info if applicable
            if step_rerun_info and step_rerun_info.get('needs_rerun'):
                response_metadata['step_rerun_required'] = True
                response_metadata['step_rerun_id'] = step_rerun_info['step_id']
                response_metadata['old_goal'] = step_rerun_info['old_goal']
                response_metadata['new_goal'] = step_rerun_info['new_goal']
            
            return {
                "status": "success",
                "updated_content": updated_content,
                "metadata": response_metadata
            }
            
        except Exception as e:
            logger.error(f"Error in apply_changes: {e}", exc_info=True)
            raise

