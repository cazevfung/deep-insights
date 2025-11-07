"""Phase 1: Discover and Suggest Research Goals."""

import json
from typing import Dict, Any, Optional, Union
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages, load_schema
from research.prompts.context_formatters import format_research_role_for_context
from research.utils.marker_formatter import format_marker_overview


class Phase1Discover(BasePhase):
    """Phase 1: Generate research goal suggestions."""
    
    def execute(
        self,
        data_abstract: str,
        user_topic: Optional[str] = None,
        research_role: Optional[str] = None,
        amendment_feedback: Optional[str] = None,
        batch_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Phase 1: Generate research goal suggestions.
        
        Args:
            data_abstract: Abstract of the available data (legacy, kept for backward compatibility)
            user_topic: Optional user-specified research topic or guidance note
            research_role: Optional research role/persona (dict with 'role' and 'rationale' or legacy string)
            amendment_feedback: Optional free-text feedback to amend/refine goals
            batch_data: Optional batch data with summaries (preferred for marker overview)
            
        Returns:
            Dict with suggested_goals and raw_response (full output object)
        """
        self.logger.info("Phase 1: Generating research goals")
        
        # Progress marker: Building prompt
        if self.ui:
            self.ui.display_message("正在构建提示词...", "info")
        
        # Format research_role for prompt context (handle both structured dict and legacy string)
        role_context = format_research_role_for_context(research_role)
        
        # Use marker overview if batch_data is available, otherwise fall back to data_abstract
        if batch_data:
            try:
                if self.ui:
                    self.ui.display_message("正在格式化数据概览...", "info")
                marker_overview = format_marker_overview(batch_data)
                self.logger.info("Using marker overview for Phase 1")
            except Exception as e:
                self.logger.warning(f"Failed to format marker overview, falling back to data_abstract: {e}")
                marker_overview = data_abstract
        else:
            marker_overview = data_abstract
            self.logger.info("Using data_abstract for Phase 1 (no batch_data provided)")
        
        # Compose messages from externalized prompt templates
        amendment_note = f"\n\n**用户修改意见:**\n{amendment_feedback}" if amendment_feedback else ""
        context = {
            "marker_overview": marker_overview,  # Use marker_overview instead of data_abstract
            "data_abstract": data_abstract,  # Keep for backward compatibility in prompts
            "user_topic": (
                f"**可选的研究主题（如果用户未指定则省略）:**\n{user_topic}" if user_topic else ""
            ) + amendment_note,
            "research_role_display": role_context["research_role_display"],
            "research_role_rationale": role_context["research_role_rationale"],
            "avoid_list": "",
        }
        messages = compose_messages("phase1_discover", context=context)

        # Progress marker: Calling AI (handled by _stream_with_callback)
        # Stream and parse JSON response (with one retry if overlap detected)
        import time
        api_start_time = time.time()
        self.logger.info(f"[TIMING] Starting API call for Phase 1 at {api_start_time:.3f}")
        response = self._stream_with_callback(messages)
        api_elapsed = time.time() - api_start_time
        self.logger.info(f"[TIMING] API call completed in {api_elapsed:.3f}s for Phase 1")

        # Progress marker: Parsing response
        if self.ui:
            self.ui.display_message("正在解析研究目标...", "info")
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response
            parsed = self.client.parse_json_from_stream(iter([response]))
            goals = parsed.get("suggested_goals", [])
        except Exception as e:
            self.logger.warning(f"JSON parsing error, trying to extract manually: {e}")
            if self.ui:
                self.ui.display_message("JSON解析失败，尝试手动提取...", "warning")
            # Fallback: try to find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                goals = parsed.get("suggested_goals", [])
            else:
                raise ValueError(f"Could not parse goals from response: {response[:200]}")
        
        # Progress marker: Validating
        if self.ui:
            self.ui.display_message("正在验证目标数据...", "info")
        
        # Optional schema validation using prompts/phase1_discover/output_schema.json
        schema = load_schema("phase1_discover", name="output_schema.json")
        if schema:
            self._validate_against_schema(parsed, schema)
        
        # Basic overlap detection (lexical Jaccard over word sets); retry once with avoid list
        def _tokenize(text: str) -> set:
            import re
            words = re.findall(r"[\w\u4e00-\u9fff]+", text)
            return set(w.lower() for w in words)

        def _jaccard(a: str, b: str) -> float:
            sa, sb = _tokenize(a), _tokenize(b)
            if not sa or not sb:
                return 0.0
            inter = len(sa & sb)
            union = len(sa | sb)
            return inter / union if union else 0.0

        def _has_overlap(items: list, threshold: float = 0.6) -> bool:
            n = len(items)
            for i in range(n):
                for j in range(i + 1, n):
                    if _jaccard(items[i]["goal_text"], items[j]["goal_text"]) >= threshold:
                        return True
            return False

        if len(goals) >= 2 and _has_overlap(goals):
            self.logger.info("Detected overlap in goals, retrying with avoid list")
            if self.ui:
                self.ui.display_message("检测到目标重叠，正在重新生成...", "warning")
            avoid_text = "请避免与以下表述重叠或等价：\n" + "\n".join(
                f"- {g['goal_text']}" for g in goals
            )
            context["avoid_list"] = avoid_text
            messages = compose_messages("phase1_discover", context=context)
            api_retry_start = time.time()
            self.logger.info(f"[TIMING] Starting retry API call for Phase 1 at {api_retry_start:.3f}")
            response_retry = self._stream_with_callback(messages)
            api_retry_elapsed = time.time() - api_retry_start
            self.logger.info(f"[TIMING] Retry API call completed in {api_retry_elapsed:.3f}s for Phase 1")
            try:
                parsed_retry = self.client.parse_json_from_stream(iter([response_retry]))
                goals_retry = parsed_retry.get("suggested_goals", [])
                if goals_retry and not _has_overlap(goals_retry):
                    response = response_retry
                    goals = goals_retry
                    if self.ui:
                        self.ui.display_message("重新生成完成", "success")
            except Exception:
                pass

        result = {
            "suggested_goals": goals,
            "raw_response": response,
        }
        
        # Progress marker: Complete
        if self.ui:
            self.ui.display_message(f"研究目标生成完成: 共 {len(goals)} 个目标", "success")
        
        self.logger.info(f"Phase 1 complete: Generated {len(goals)} research goals")
        
        return result

    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Minimal validator for the expected Phase 1 schema.
        Raises ValueError if validation fails.
        """
        # Top-level required
        required_keys = schema.get("required", [])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Schema validation failed: missing required key '{key}'")

        # suggested_goals specifics
        goals = data.get("suggested_goals")
        if not isinstance(goals, list):
            raise ValueError("Schema validation failed: 'suggested_goals' must be a list")

        item_schema = schema.get("properties", {}).get("suggested_goals", {}).get("items", {})
        item_required = item_schema.get("required", ["id", "goal_text"])  # sensible default
        for idx, item in enumerate(goals):
            if not isinstance(item, dict):
                raise ValueError(f"Schema validation failed: item {idx} in 'suggested_goals' must be an object")
            for req in item_required:
                if req not in item:
                    raise ValueError(f"Schema validation failed: item {idx} missing '{req}'")
            # type checks (best-effort)
            if not isinstance(item.get("id"), int):
                raise ValueError(f"Schema validation failed: item {idx} 'id' must be an integer")
            if not isinstance(item.get("goal_text"), str):
                raise ValueError(f"Schema validation failed: item {idx} 'goal_text' must be a string")

