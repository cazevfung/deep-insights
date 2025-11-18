"""Context formatters for structured phase outputs.

This module provides helpers to format structured phase output objects
for use in prompt templates. This allows phases to receive full structured
objects while formatting only what they need for prompts.
"""

from typing import Dict, Any, Optional, Union, List, Tuple


def format_research_role_for_context(role_obj: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, str]:
    """
    Format research_role for prompt context.
    
    Handles both structured (dict) and legacy (string) formats for backward compatibility.
    
    Args:
        role_obj: Research role object (dict with 'role' and 'rationale') or legacy string
        
    Returns:
        Dict with 'research_role_display', 'research_role_rationale', and 'system_role_description' formatted for prompts
    """
    default_role = "资深数据分析专家"
    
    if not role_obj:
        return {
            "research_role_display": "",
            "research_role_rationale": "",
            "system_role_description": default_role
        }
    
    if isinstance(role_obj, dict):
        role_name = role_obj.get("role", "")
        rationale = role_obj.get("rationale", "")
        rationale_text = f"\n**角色选择理由:** {rationale}" if rationale else ""
        return {
            "research_role_display": role_name,
            "research_role_rationale": rationale_text,
            "system_role_description": role_name or default_role
        }
    else:
        # Backward compatibility: treat as string
        role_str = str(role_obj)
        return {
            "research_role_display": role_str,
            "research_role_rationale": "",
            "system_role_description": role_str or default_role
        }


def format_synthesized_goal_for_context(goal_obj: Dict[str, Any]) -> Dict[str, str]:
    """
    Format synthesized_goal for prompt context.
    
    Extracts and formats all fields from synthesized_goal object, including
    any new fields that may be added in the future.
    
    Args:
        goal_obj: Synthesized goal object from Phase 2 (preserves Phase 1 questions directly)
        
    Returns:
        Dict with formatted context fields for prompts
    """
    if not goal_obj:
        return {
            "synthesized_topic": "",
            "component_questions_list": "",
            "component_questions_count": "0",
            "unifying_theme": "",
            "research_scope": ""
        }
    
    # Extract core fields
    topic = goal_obj.get("comprehensive_topic", "")
    questions = goal_obj.get("component_questions", [])
    theme = goal_obj.get("unifying_theme", "")
    scope = goal_obj.get("research_scope", "")
    
    # Format component questions
    questions_text = ""
    if questions:
        questions_text = "\n".join([
            f"{i+1}. {q}" for i, q in enumerate(questions)
        ])
    
    # Build base context
    context = {
        "synthesized_topic": topic,
        "component_questions_list": questions_text,
        "component_questions_count": str(len(questions)),
        "unifying_theme": theme or "",
        "research_scope": scope or ""
    }
    
    # Add any additional fields automatically (future-proof)
    for key, value in goal_obj.items():
        if key not in context and key not in ["comprehensive_topic", "component_questions"]:
            # Format additional fields with prefix
            field_name = f"synthesized_{key}"
            if isinstance(value, list):
                context[field_name] = "\n".join([f"- {item}" for item in value])
            elif isinstance(value, dict):
                context[field_name] = "\n".join([
                    f"- {k}: {v}" for k, v in value.items()
                ])
            else:
                context[field_name] = str(value) if value else ""
    
    return context


def format_suggested_goals_for_context(goals: List[Dict[str, Any]]) -> str:
    """
    Format suggested goals list for prompt context.
    
    Args:
        goals: List of goal objects from Phase 1
        
    Returns:
        Formatted string with numbered list of goals
    """
    if not goals:
        return "（无研究目标）"
    
    formatted = ""
    for i, goal in enumerate(goals, 1):
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
            sources_str = ', '.join(sources) if isinstance(sources[0], str) else ', '.join([str(s) for s in sources])
            formatted += f"   来源: {sources_str}\n"
        formatted += "\n"
    
    return formatted.strip()


def format_research_plan_for_context(plan: List[Dict[str, Any]]) -> str:
    """
    Format research plan for prompt context.
    
    Args:
        plan: List of plan steps from Phase 2
        
    Returns:
        Formatted string with numbered list of plan steps
    """
    if not plan:
        return "（无研究计划）"
    
    formatted = ""
    for step in sorted(plan, key=lambda x: x.get("step_id", 0)):
        step_id = step.get("step_id", 0)
        goal = step.get("goal", "")
        required_data = step.get("required_data", "")
        chunk_strategy = step.get("chunk_strategy", "")
        notes = step.get("notes", "")
        
        formatted += f"步骤 {step_id}: {goal}\n"
        formatted += f"  所需数据: {required_data}\n"
        if chunk_strategy:
            formatted += f"  分块策略: {chunk_strategy}\n"
        if notes:
            formatted += f"  说明: {notes}\n"
        formatted += "\n"
    
    return formatted.strip()


def format_phase3_for_synthesis(
    phase3_output: Optional[Dict[str, Any]],
    research_plan: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    Format Phase 3 execution output into a synthesis-ready bundle.

    Returns:
        A tuple of (formatted_strings, structured_steps):
            formatted_strings: str fields ready for prompt injection
            structured_steps: step-level summaries for additional logic
    """
    formatted: Dict[str, str] = {
        "phase3_overall_summary": "",
        "phase3_step_overview": "",
        "phase3_key_claims": "",
        "phase3_counterpoints": "",
        "phase3_surprising_findings": "",
        "phase3_evidence_highlights": "",
        "phase3_open_questions": "",
        "phase3_storyline_candidates": "",
    }
    structured_steps: List[Dict[str, Any]] = []

    if not isinstance(phase3_output, dict):
        return formatted, structured_steps

    plan_lookup: Dict[int, Dict[str, Any]] = {}
    if isinstance(research_plan, list):
        for step in research_plan:
            if isinstance(step, dict):
                step_id = step.get("step_id")
                if isinstance(step_id, int):
                    plan_lookup[step_id] = step

    findings_entries = phase3_output.get("findings", [])
    if not isinstance(findings_entries, list):
        findings_entries = []

    overall_insights: List[str] = []
    step_overview_lines: List[str] = []
    key_claim_lines: List[str] = []
    counterpoint_lines: List[str] = []
    surprise_lines: List[str] = []
    evidence_lines: List[str] = []
    open_question_lines: List[str] = []
    storyline_lines: List[str] = []

    def _truncate(text: str, limit: int = 220) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    for entry in findings_entries:
        if not isinstance(entry, dict):
            continue
        step_id = entry.get("step_id")
        step_payload = entry.get("findings") or {}
        if not isinstance(step_payload, dict):
            continue

        structured = step_payload.get("findings") or {}
        if not isinstance(structured, dict):
            structured = {}

        insights = step_payload.get("insights") or ""
        summary = structured.get("summary") or insights or ""
        summary = _truncate(str(summary).strip(), 400)

        confidence = step_payload.get("confidence")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0

        sources: List[str] = []
        if isinstance(structured.get("sources"), list):
            sources = [str(s) for s in structured["sources"] if s]
        elif isinstance(step_payload.get("findings"), dict):
            potential_sources = step_payload["findings"].get("sources")
            if isinstance(potential_sources, list):
                sources = [str(s) for s in potential_sources if s]

        points_of_interest = structured.get("points_of_interest") or {}
        if not isinstance(points_of_interest, dict):
            points_of_interest = {}

        key_claims = points_of_interest.get("key_claims") or []
        controversial_topics = points_of_interest.get("controversial_topics") or []
        surprising_insights = points_of_interest.get("surprising_insights") or []
        specific_examples = points_of_interest.get("specific_examples") or []
        open_questions = points_of_interest.get("open_questions") or []

        goal_text = ""
        if isinstance(step_id, int) and step_id in plan_lookup:
            goal_text = str(plan_lookup[step_id].get("goal", "")).strip()

        top_claim_texts: List[str] = []
        for claim in key_claims:
            if not isinstance(claim, dict):
                continue
            claim_text = claim.get("claim")
            if not claim_text:
                continue
            supporting = claim.get("supporting_evidence") or ""
            detail = _truncate(str(supporting), 160)
            if detail:
                top_claim_texts.append(f"{claim_text}（支撑：{detail}）")
            else:
                top_claim_texts.append(str(claim_text))
            if len(top_claim_texts) >= 3:
                break

        evidence_for_step: List[str] = []
        for example in specific_examples[:4]:
            if not isinstance(example, dict):
                continue
            example_text = _truncate(str(example.get("example", "")), 160)
            context = _truncate(str(example.get("context", "")), 120)
            if example_text:
                formatted_example = f"例子：{example_text}"
                if context:
                    formatted_example += f"（上下文：{context}）"
                evidence_for_step.append(formatted_example)

        counterpoints_for_step: List[str] = []
        for topic in controversial_topics[:4]:
            if not isinstance(topic, dict):
                continue
            topic_name = _truncate(str(topic.get("topic", "")), 160)
            opposing_views = topic.get("opposing_views") or []
            if isinstance(opposing_views, list) and opposing_views:
                view_snippets = "; ".join(_truncate(str(view), 100) for view in opposing_views[:3])
                counterpoints_for_step.append(f"{topic_name} —— {view_snippets}")
            elif topic_name:
                counterpoints_for_step.append(topic_name)

        surprises_for_step: List[str] = []
        if isinstance(surprising_insights, list):
            for surprise in surprising_insights[:4]:
                surprises_for_step.append(_truncate(str(surprise), 160))

        open_q_for_step: List[str] = []
        if isinstance(open_questions, list):
            for question in open_questions[:4]:
                open_q_for_step.append(_truncate(str(question), 160))

        structured_steps.append({
            "step_id": step_id,
            "goal": goal_text,
            "summary": summary,
            "insights": _truncate(str(insights), 400),
            "confidence": confidence_value,
            "sources": sources,
            "key_claims": top_claim_texts,
            "counterpoints": counterpoints_for_step,
            "surprises": surprises_for_step,
            "evidence": evidence_for_step,
            "open_questions": open_q_for_step,
        })

        label = f"步骤 {step_id}"
        if goal_text:
            label = f"步骤 {step_id} · {goal_text}"
        confidence_label = f"（信心 {round(confidence_value * 100):d}%）" if confidence_value else ""
        step_overview_lines.append(f"- {label}: {summary}{confidence_label}")

        if summary:
            overall_insights.append(f"{label}: {summary}")

        for claim_text in top_claim_texts[:5]:
            key_claim_lines.append(f"- {claim_text}")

        for cp in counterpoints_for_step:
            counterpoint_lines.append(f"- {cp}")

        for surprise in surprises_for_step:
            surprise_lines.append(f"- {surprise}")

        for evidence_item in evidence_for_step:
            evidence_lines.append(f"- {evidence_item}")

        for question in open_q_for_step:
            open_question_lines.append(f"- {question}")

        storyline_hook = summary or (top_claim_texts[0] if top_claim_texts else "")
        storyline_label = goal_text or label
        if storyline_hook:
            storyline_lines.append(f"- {storyline_label}: {storyline_hook}")

    def _join(lines: List[str], limit: int) -> str:
        if not lines:
            return ""
        return "\n".join(lines[:limit])

    formatted["phase3_overall_summary"] = _join(overall_insights, 6)
    formatted["phase3_step_overview"] = _join(step_overview_lines, 20)
    formatted["phase3_key_claims"] = _join(key_claim_lines, 12)
    formatted["phase3_counterpoints"] = _join(counterpoint_lines, 10)
    formatted["phase3_surprising_findings"] = _join(surprise_lines, 8)
    formatted["phase3_evidence_highlights"] = _join(evidence_lines, 12)
    formatted["phase3_open_questions"] = _join(open_question_lines, 10)
    formatted["phase3_storyline_candidates"] = _join(storyline_lines, 12)

    return formatted, structured_steps


def format_phase_output_for_prompt(
    phase_name: str,
    output: Dict[str, Any]
) -> Dict[str, str]:
    """
    Generic formatter that formats any phase output for prompt context.
    
    This is a convenience function that extracts common patterns and formats
    them appropriately for prompts.
    
    Args:
        phase_name: Name of the phase (e.g., "phase1", "phase1_5")
        output: Phase output dictionary
        
    Returns:
        Dict with formatted context fields
    """
    context = {}
    
    # Extract top-level keys and format them
    for key, value in output.items():
        if key == "raw_response":
            continue  # Skip raw responses
        
        if isinstance(value, dict):
            # Nested dict - format recursively
            for nested_key, nested_value in value.items():
                field_name = f"{phase_name}_{nested_key}"
                if isinstance(nested_value, list):
                    context[field_name] = "\n".join([f"- {item}" for item in nested_value])
                elif isinstance(nested_value, dict):
                    context[field_name] = "\n".join([
                        f"- {k}: {v}" for k, v in nested_value.items()
                    ])
                else:
                    context[field_name] = str(nested_value) if nested_value else ""
        elif isinstance(value, list):
            # List - format as numbered list
            context[f"{phase_name}_{key}"] = "\n".join([
                f"{i+1}. {item}" if isinstance(item, str) else f"{i+1}. {str(item)}"
                for i, item in enumerate(value)
            ])
        else:
            # Simple value
            context[f"{phase_name}_{key}"] = str(value) if value else ""
    
    return context



