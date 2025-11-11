"""Phase 2: Create Detailed Research Plan."""

import json
from typing import Dict, Any, List, Optional
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages, load_schema
from research.prompts.context_formatters import (
    format_suggested_goals_for_context,
    format_synthesized_goal_for_context
)
from research.utils.marker_formatter import format_marker_overview


class Phase2Plan(BasePhase):
    """Phase 2: Create detailed execution plan."""
    
    def execute(
        self,
        phase1_output: Dict[str, Any],
        phase1_5_output: Dict[str, Any],
        data_summary: Dict[str, Any],
        component_questions: Optional[List[str]] = None,
        selected_goal: Optional[str] = None,  # For backwards compatibility
        batch_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Phase 2: Create detailed research plan.
        
        Args:
            phase1_output: Full Phase 1 output object containing suggested_goals
            phase1_5_output: Full Phase 1.5 output object containing synthesized_goal
            data_summary: Summary of available data
            component_questions: Optional list of component questions (extracted from synthesized_goal if not provided)
            selected_goal: Deprecated - extracted from synthesized_goal if not provided
            batch_data: Optional batch data with summaries (for marker overview)
            
        Returns:
            Dict with research_plan and raw_response (full output object)
        """
        self.logger.info("Phase 2: Creating research plan")
        
        # Extract from full output objects (backward compatible)
        suggested_goals = phase1_output.get("suggested_goals", [])
        if not suggested_goals and isinstance(phase1_output, list):
            # Backward compatibility: accept list directly
            suggested_goals = phase1_output
        
        synthesized_goal = phase1_5_output.get("synthesized_goal", {})
        if not synthesized_goal and isinstance(phase1_5_output, dict) and "comprehensive_topic" in phase1_5_output:
            # Backward compatibility: accept synthesized_goal dict directly
            synthesized_goal = phase1_5_output
        
        # Extract comprehensive_topic from synthesized_goal if selected_goal not provided
        if selected_goal is None:
            selected_goal = synthesized_goal.get("comprehensive_topic", "")
        
        # Extract component_questions from synthesized_goal if not provided
        if component_questions is None:
            component_questions = synthesized_goal.get("component_questions", [])
        
        # Format suggested goals for prompt context using formatter
        suggested_goals_list = format_suggested_goals_for_context(suggested_goals)
        
        # Format synthesized goal for prompt context using formatter
        goal_context = format_synthesized_goal_for_context(synthesized_goal)
        
        # Build data summary context and compose messages from external templates
        sources = data_summary.get("sources", [])
        total_words = data_summary.get("total_words", 0)
        total_comments = data_summary.get("total_comments", 0)
        sources_list = ", ".join(sources) if sources else "未指定"

        # Prepare quality information for context (enhancement #4)
        quality_assessment = data_summary.get("quality_assessment", {})
        quality_warnings = []
        if quality_assessment:
            quality_flags = quality_assessment.get("quality_flags", [])
            quality_warnings = [
                f["message"] 
                for f in quality_flags 
                if f["severity"] in ["warning", "error"]
            ]
        
        quality_info = ""
        if quality_warnings:
            quality_info = f"\n\n**数据质量注意事项**:\n" + "\n".join([f"- {w}" for w in quality_warnings[:3]])
        elif quality_assessment.get("quality_score", 1.0) < 0.7:
            quality_info = f"\n\n**数据质量评分**: {quality_assessment.get('quality_score', 1.0):.2f} (请注意数据质量)"
        
        # Format component questions context
        if component_questions:
            component_questions_context = "**需要涵盖的组成问题：**\n"
            for i, question in enumerate(component_questions, 1):
                component_questions_context += f"{i}. {question}\n"
            component_questions_context += "\n**重要要求：**\n"
            component_questions_context += "- 研究计划必须确保所有组成问题都得到充分探索\n"
            component_questions_context += "- 计划中的步骤应该自然地覆盖所有方面\n"
            component_questions_context += "- 可以创建专门步骤来回答特定问题，或者将多个问题整合在单个步骤中\n"
            component_questions_context += "- 确保最终报告能够全面回答综合主题，包括所有组成问题"
        else:
            component_questions_context = ""
        
        # Generate transcript size guidance (Solution 5)
        transcript_size_analysis = data_summary.get("transcript_size_analysis", {})
        transcript_size_guidance = ""
        if transcript_size_analysis:
            max_words = transcript_size_analysis.get("max_transcript_words", 0)
            avg_words = transcript_size_analysis.get("avg_transcript_words", 0)
            large_count = transcript_size_analysis.get("large_transcript_count", 0)
            
            transcript_size_guidance = f"""
**转录本大小分析：**
- 最大转录本: {max_words} 字
- 平均转录本: {avg_words} 字
- 大型转录本（>5,000字）: {large_count} 个
- 转录本总数: {transcript_size_analysis.get('total_transcripts', 0)} 个

**策略建议：**
- 如果有大型转录本（>5,000字），必须使用"sequential"策略确保全面覆盖
- 建议chunk_size: 3000-5000字（充分利用新的50K字符限制，避免过度分块）
- 对于大转录本，必须在计划最后添加"previous_findings"类型的综合步骤
"""
        else:
            transcript_size_guidance = ""
        
        # Build context from formatted synthesized goal
        synthesized_goal_context = (
            f"**综合主题**: {goal_context.get('synthesized_topic', '')}\n\n"
            f"**组成问题**:\n{goal_context.get('component_questions_list', '')}\n\n"
        )
        if goal_context.get("unifying_theme"):
            synthesized_goal_context += f"**统一主题**: {goal_context.get('unifying_theme')}\n\n"
        if goal_context.get("research_scope"):
            synthesized_goal_context += f"**研究范围**: {goal_context.get('research_scope')}\n"
        
        # Format marker overview if batch_data is available
        marker_overview = ""
        if batch_data:
            try:
                marker_overview = format_marker_overview(batch_data)
                self.logger.info("Including marker overview in Phase 2 context")
            except Exception as e:
                self.logger.warning(f"Failed to format marker overview for Phase 2: {e}")
        
        # Get research role from session metadata
        research_role = self.session.get_metadata("research_role") if self.session else None
        role_display = ""
        if research_role:
            if isinstance(research_role, dict):
                role_display = research_role.get("role", "")
            else:
                role_display = str(research_role)
        
        context = {
            "suggested_goals_list": suggested_goals_list,
            "synthesized_goal_context": synthesized_goal_context,
            "component_questions_context": component_questions_context,
            "total_words": total_words,
            "total_comments": total_comments,
            "sources_list": sources_list,
            "quality_info": quality_info,  # Enhancement #4
            "transcript_size_guidance": transcript_size_guidance,  # New: Solution 5
            "marker_overview": marker_overview,  # New: Marker overview for Phase 2
            "system_role_description": role_display or "资深数据分析专家",
        }
        messages = compose_messages("phase2_plan", context=context)
        
        # Retry logic for LLM call and validation
        max_retries = 2
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Stream and parse JSON response
                response = self._stream_with_callback(messages)
                
                # Parse JSON from response
                try:
                    parsed = self.client.parse_json_from_stream(iter([response]))
                    plan = parsed.get("research_plan", [])
                except Exception as e:
                    self.logger.warning(f"JSON parsing error: {e}")
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        plan = parsed.get("research_plan", [])
                    else:
                        raise ValueError(f"Could not parse plan from response")

                # Optional schema validation for Phase 2
                schema = load_schema("phase2_plan", name="output_schema.json")
                auto_converted = False
                if schema:
                    auto_converted = self._validate_phase2_schema(parsed, schema, allow_auto_convert=True)
                
                # If auto-conversion happened, retry once to get correct format from AI
                if auto_converted and retry_count == 0:
                    retry_count += 1
                    self.logger.warning(f"Auto-conversion applied (attempt {retry_count}/{max_retries + 1}). Retrying to get correct format from AI...")
                    
                    # Update context with feedback about correct format
                    validation_feedback = f"\n\n**格式修正**: 请确保输出格式正确：\n"
                    validation_feedback += f"- 'required_data' 必须是字符串（如 'transcript'），不能是数组/列表\n"
                    validation_feedback += f"- 'required_data' 只能从以下值中选择一个: 'transcript', 'transcript_with_comments', 'metadata', 'previous_findings'\n"
                    
                    # Update context with feedback
                    context_with_feedback = context.copy()
                    if "marker_overview" in context_with_feedback:
                        context_with_feedback["marker_overview"] += validation_feedback
                    else:
                        context_with_feedback["marker_overview"] = validation_feedback
                    
                    # Regenerate messages with feedback
                    messages = compose_messages("phase2_plan", context=context_with_feedback)
                    continue
                
                # Success - break out of retry loop
                break
                
            except ValueError as e:
                last_error = e
                error_msg = str(e)
                
                # Check if it's a validation error that we should retry
                if "Schema validation failed" in error_msg and retry_count < max_retries:
                    retry_count += 1
                    self.logger.warning(f"Schema validation failed (attempt {retry_count}/{max_retries + 1}): {error_msg}")
                    self.logger.info("Retrying Phase 2 plan generation with corrected instructions...")
                    
                    # Update context with validation error feedback for retry
                    validation_feedback = f"\n\n**重要修正**: 之前的输出格式不正确。请确保：\n"
                    validation_feedback += f"- 'required_data' 必须是字符串（如 'transcript'），不能是数组/列表\n"
                    validation_feedback += f"- 'required_data' 只能从以下值中选择一个: 'transcript', 'transcript_with_comments', 'metadata', 'previous_findings'\n"
                    validation_feedback += f"- 错误详情: {error_msg}\n"
                    validation_feedback += f"- 请重新生成符合JSON schema格式的研究计划\n"
                    
                    # Update context with feedback
                    context_with_feedback = context.copy()
                    if "marker_overview" in context_with_feedback:
                        context_with_feedback["marker_overview"] += validation_feedback
                    else:
                        context_with_feedback["marker_overview"] = validation_feedback
                    
                    # Regenerate messages with feedback
                    messages = compose_messages("phase2_plan", context=context_with_feedback)
                    continue
                else:
                    # Not a retryable error or max retries reached
                    raise
            except Exception as e:
                # Other errors - don't retry
                raise
        
        # If we exhausted retries, raise the last error
        if retry_count > max_retries and last_error:
            raise last_error
        
        # Store in session
        self.session.set_metadata("selected_goal", selected_goal)
        self.session.set_metadata("research_plan", plan)
        
        result = {
            "research_plan": plan,
            "raw_response": response
        }
        
        self.logger.info(f"Phase 2 complete: Created plan with {len(plan)} steps")
        
        return result

    def _validate_phase2_schema(self, data: Dict[str, Any], schema: Dict[str, Any], allow_auto_convert: bool = True) -> bool:
        """
        Minimal schema validation for Phase 2 research plan.
        
        Args:
            data: The parsed JSON data
            schema: The JSON schema to validate against
            allow_auto_convert: If True, auto-convert lists to strings. If False, raise error immediately.
            
        Returns:
            bool: True if validation passed (possibly after auto-conversion), False if should retry
            
        Raises:
            ValueError: If validation fails and cannot be auto-fixed
        """
        required_keys = schema.get("required", [])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Schema validation failed: missing required key '{key}'")

        plan = data.get("research_plan")
        if not isinstance(plan, list):
            raise ValueError("Schema validation failed: 'research_plan' must be a list")

        item_schema = schema.get("properties", {}).get("research_plan", {}).get("items", {})
        item_required = item_schema.get("required", ["step_id", "goal", "required_data", "chunk_strategy"])  # default
        auto_converted = False
        
        for idx, step in enumerate(plan):
            if not isinstance(step, dict):
                raise ValueError(f"Schema validation failed: step {idx} must be an object")
            for req in item_required:
                if req not in step:
                    raise ValueError(f"Schema validation failed: step {idx} missing '{req}'")
            if not isinstance(step.get("step_id"), int):
                raise ValueError(f"Schema validation failed: step {idx} 'step_id' must be integer")
            if not isinstance(step.get("goal"), str):
                raise ValueError(f"Schema validation failed: step {idx} 'goal' must be string")
            
            # Validate required_data - handle list/array case
            required_data = step.get("required_data")
            if not isinstance(required_data, str):
                # Log the actual value for debugging
                actual_type = type(required_data).__name__
                actual_value = str(required_data)[:200]  # Truncate for logging
                self.logger.error(f"Step {idx} 'required_data' is {actual_type}, not string. Value: {actual_value}")
                
                # If auto-convert is disabled or not a list, raise error immediately
                if not allow_auto_convert:
                    raise ValueError(f"Schema validation failed: step {idx} 'required_data' must be string, got {actual_type} (value: {actual_value[:100]})")
                
                # Try to convert list to string (join with comma or take first element)
                if isinstance(required_data, list):
                    if len(required_data) > 0:
                        # Take first element if it's a list of strings
                        if isinstance(required_data[0], str):
                            self.logger.warning(f"Converting list to string for step {idx}: taking first element '{required_data[0]}'")
                            step["required_data"] = required_data[0]
                            auto_converted = True
                        else:
                            # Join if elements are strings
                            step["required_data"] = ", ".join(str(item) for item in required_data)
                            self.logger.warning(f"Converting list to comma-separated string for step {idx}")
                            auto_converted = True
                    else:
                        raise ValueError(f"Schema validation failed: step {idx} 'required_data' is empty list, must be string")
                else:
                    raise ValueError(f"Schema validation failed: step {idx} 'required_data' must be string, got {actual_type} (value: {actual_value[:100]})")
            
            if not isinstance(step.get("chunk_strategy"), str):
                raise ValueError(f"Schema validation failed: step {idx} 'chunk_strategy' must be string")
        
        # Return True if auto-conversion happened (so caller knows to potentially retry)
        return auto_converted
    
    def _format_suggested_goals(self, suggested_goals: List[Dict[str, Any]]) -> str:
        """Format suggested goals from Phase 1 for prompt context."""
        if not suggested_goals:
            return "（无原始研究目标）"
        
        formatted = ""
        for i, goal in enumerate(suggested_goals, 1):
            goal_text = goal.get("goal_text", "")
            rationale = goal.get("rationale", "")
            uses = goal.get("uses", [])
            sources = goal.get("sources", [])
            
            formatted += f"{i}. {goal_text}\n"
            if rationale:
                formatted += f"   理由: {rationale}\n"
            if uses:
                formatted += f"   数据类型: {', '.join(uses)}\n"
            if sources:
                if sources and isinstance(sources[0], str):
                    sources_str = ', '.join(sources)
                else:
                    sources_str = ', '.join([str(s) for s in sources])
                formatted += f"   来源: {sources_str}\n"
            formatted += "\n"
        
        return formatted.strip()
    
    def _format_synthesized_goal(self, synthesized_goal: Dict[str, Any]) -> str:
        """Format synthesized goal from Phase 1.5 for prompt context."""
        if not synthesized_goal:
            return "（无综合研究主题）"
        
        comprehensive_topic = synthesized_goal.get("comprehensive_topic", "")
        component_questions = synthesized_goal.get("component_questions", [])
        unifying_theme = synthesized_goal.get("unifying_theme", "")
        research_scope = synthesized_goal.get("research_scope", "")
        
        formatted = f"**综合主题**: {comprehensive_topic}\n\n"
        
        if component_questions:
            formatted += "**组成问题**:\n"
            for i, question in enumerate(component_questions, 1):
                formatted += f"{i}. {question}\n"
            formatted += "\n"
        
        if unifying_theme:
            formatted += f"**统一主题**: {unifying_theme}\n\n"
        
        if research_scope:
            formatted += f"**研究范围**: {research_scope}\n"
        
        return formatted.strip()

