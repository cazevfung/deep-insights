"""Phase 0.5: Generate Research Role."""

import json
import re
from typing import Dict, Any, Optional
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages, load_schema


class Phase0_5RoleGeneration(BasePhase):
    """Phase 0.5: Automatically generate appropriate research role."""
    
    def execute(
        self,
        data_abstract: str,
        user_topic: Optional[str] = None,
        user_guidance: Optional[str] = None,
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
        
        # Resolve writing style for dynamic partials with a safe default
        # Map user/session style preferences to available partial filenames
        style_file_map = {
            "professional": "consultant",
            "consultant": "consultant",
            "creative": "creative",
            "persuasive": "persuasive",
            "explanatory": "explanatory",
        }
        session_style_pref = self.session.get_metadata("writing_style", "professional") if self.session else "professional"
        writing_style_name = style_file_map.get(session_style_pref, "consultant")
        
        context = {
            "system_role_description": "智能研究助理",  # Default role for Phase 0.5 itself
            "research_role_rationale": "",  # Empty since this phase generates the role
            "data_abstract": data_abstract,
            "user_topic": (
                f"**研究主题:**\n{user_topic}" if user_topic else ""
            ),
            "user_guidance": (
                f"**用户初始指导：**\n{user_guidance}" if user_guidance else ""
            ),
            # For dynamic partial resolution like {{> style_{writing_style}_cn.md}}
            "writing_style": writing_style_name,
        }
        messages = compose_messages("phase0_5_role_generation", context=context)
        
        # Progress marker: Calling AI (handled by _stream_with_callback)
        import time
        api_start_time = time.time()
        self.logger.info(f"[TIMING] Starting API call for Phase 0.5 at {api_start_time:.3f}")
        response = self._stream_with_callback(
            messages,
            stream_metadata={
                "component": "role_generation",
                "phase_label": "0.5",
            },
        )
        api_elapsed = time.time() - api_start_time
        self.logger.info(f"[TIMING] API call completed in {api_elapsed:.3f}s for Phase 0.5")
        
        # Progress marker: Parsing response
        if self.ui:
            self.ui.display_message("正在解析角色信息...", "info")
        
        parsed = None
        role_name = ""
        rationale = ""
        
        try:
            parsed = self.client.parse_json_from_stream(iter([response]))
            role_name = parsed.get("research_role", "")
            rationale = parsed.get("rationale", "")
        except ValueError as e:
            error_msg = str(e)
            self.logger.warning(f"JSON parsing error: {error_msg}")
            
            # Log more context for debugging
            self.logger.debug(f"Response length: {len(response)} characters")
            self.logger.debug(f"Response preview: {response[:300]}...")
            
            if self.ui:
                self.ui.display_message("JSON解析遇到问题，尝试手动提取...", "warning")
            
            # Try multiple fallback strategies
            fallback_success = False
            
            # Strategy 1: Try to extract JSON using regex (handles extra data)
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                try:
                    # Try to find the end of the first complete JSON object
                    json_str = json_match.group()
                    # Count braces to find where first object ends
                    brace_count = 0
                    json_end = -1
                    for i, char in enumerate(json_str):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i
                                break
                    
                    if json_end > 0:
                        first_json = json_str[:json_end + 1]
                        parsed = json.loads(first_json)
                        role_name = parsed.get("research_role", "")
                        rationale = parsed.get("rationale", "")
                        fallback_success = True
                        self.logger.info("Successfully extracted JSON using regex fallback")
                except (json.JSONDecodeError, ValueError, IndexError) as fallback_error:
                    self.logger.debug(f"Regex fallback failed: {fallback_error}")
            
            # Strategy 2: Try to find JSON object boundaries more carefully
            if not fallback_success:
                try:
                    # Find first { and try to find matching }
                    start_idx = response.find("{")
                    if start_idx >= 0:
                        brace_count = 0
                        json_end = -1
                        for i in range(start_idx, len(response)):
                            if response[i] == "{":
                                brace_count += 1
                            elif response[i] == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i
                                    break
                        
                        if json_end > start_idx:
                            json_str = response[start_idx:json_end + 1]
                            parsed = json.loads(json_str)
                            role_name = parsed.get("research_role", "")
                            rationale = parsed.get("rationale", "")
                            fallback_success = True
                            self.logger.info("Successfully extracted JSON using brace counting fallback")
                except (json.JSONDecodeError, ValueError, IndexError) as fallback_error:
                    self.logger.debug(f"Brace counting fallback failed: {fallback_error}")
            
            # Strategy 3: Last resort - extract role from text response
            if not fallback_success:
                self.logger.warning("All JSON extraction strategies failed, using text fallback")
                # Try to extract role name from text patterns
                role_patterns = [
                    r'"research_role"\s*:\s*"([^"]+)"',
                    r'research_role["\']?\s*[:=]\s*["\']?([^"\']+)',
                    r'角色[：:]\s*([^\n]+)',
                ]
                
                for pattern in role_patterns:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        role_name = match.group(1).strip()
                        break
                
                if not role_name:
                    # Ultimate fallback: use first meaningful text
                    role_name = response.strip()[:100] if response.strip() else "研究助理"
                
                rationale = ""
                parsed = {"research_role": role_name, "rationale": rationale}
                self.logger.warning(f"Using text fallback, extracted role: {role_name[:50]}...")
        
        except Exception as e:
            # Catch-all for any other unexpected errors
            self.logger.error(f"Unexpected error during JSON parsing: {e}", exc_info=True)
            if self.ui:
                self.ui.display_message(f"解析错误: {str(e)[:100]}", "error")
            
            # Last resort fallback
            role_name = "研究助理"
            rationale = ""
            parsed = {"research_role": role_name, "rationale": rationale}
        
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
        if user_guidance is not None:
            self.session.set_metadata("phase_feedback_pre_role", user_guidance)
        
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

