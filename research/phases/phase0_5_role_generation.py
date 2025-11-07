"""Phase 0.5: Generate Research Role."""

import json
from typing import Dict, Any, Optional
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages, load_schema


class Phase0_5RoleGeneration(BasePhase):
    """Phase 0.5: Automatically generate appropriate research role."""
    
    def execute(
        self,
        data_abstract: str,
        user_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate appropriate research role based on data and topic.
        
        Args:
            data_abstract: Abstract of the available data
            user_topic: Optional user-specified research topic
            
        Returns:
            Dict with generated research_role
        """
        self.logger.info("Phase 0.5: Generating research role")
        
        # Progress marker: Building prompt
        if self.ui:
            self.ui.display_message("正在构建提示词...", "info")
        
        context = {
            "data_abstract": data_abstract,
            "user_topic": (
                f"**研究主题:**\n{user_topic}" if user_topic else ""
            ),
        }
        messages = compose_messages("phase0_5_role_generation", context=context)
        
        # Progress marker: Calling AI (handled by _stream_with_callback)
        import time
        api_start_time = time.time()
        self.logger.info(f"[TIMING] Starting API call for Phase 0.5 at {api_start_time:.3f}")
        response = self._stream_with_callback(messages)
        api_elapsed = time.time() - api_start_time
        self.logger.info(f"[TIMING] API call completed in {api_elapsed:.3f}s for Phase 0.5")
        
        # Progress marker: Parsing response
        if self.ui:
            self.ui.display_message("正在解析角色信息...", "info")
        
        try:
            parsed = self.client.parse_json_from_stream(iter([response]))
            role_name = parsed.get("research_role", "")
            rationale = parsed.get("rationale", "")
        except Exception as e:
            self.logger.warning(f"JSON parsing error: {e}")
            if self.ui:
                self.ui.display_message("JSON解析失败，尝试手动提取...", "warning")
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                role_name = parsed.get("research_role", "")
                rationale = parsed.get("rationale", "")
            else:
                # Fallback: extract role from text response
                role_name = response.strip()[:100]  # First 100 chars as fallback
                rationale = ""
        
        # Progress marker: Validating
        if self.ui:
            self.ui.display_message("正在验证角色数据...", "info")
        
        # Optional schema validation
        schema = load_schema("phase0_5_role_generation", name="output_schema.json")
        if schema:
            self._validate_against_schema(parsed, schema)
        
        # Structure research_role as an object for future extensibility
        research_role = {
            "role": role_name,
            "rationale": rationale
        }
        
        # Store in session
        self.session.set_metadata("research_role", research_role)
        
        result = {
            "research_role": research_role,
            "raw_response": response
        }
        
        # Progress marker: Complete
        if self.ui:
            self.ui.display_message("角色生成完成", "success")
        
        self.logger.info(f"Phase 0.5 complete: Generated role '{role_name}'")
        
        return result
    
    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Minimal validator for the expected Phase 0.5 schema.
        Raises ValueError if validation fails.
        """
        # Top-level required
        required_keys = schema.get("required", [])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Schema validation failed: missing required key '{key}'")
        
        # research_role specifics - validate both role and rationale from input
        role_name = data.get("research_role", "")
        rationale = data.get("rationale", "")
        
        if not isinstance(role_name, str):
            raise ValueError("Schema validation failed: 'research_role' must be a string")
        
        if not role_name or not role_name.strip():
            raise ValueError("Schema validation failed: 'research_role' cannot be empty")
        
        # Rationale is optional but recommended
        if rationale and not isinstance(rationale, str):
            raise ValueError("Schema validation failed: 'rationale' must be a string")

