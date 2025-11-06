"""Context formatters for structured phase outputs.

This module provides helpers to format structured phase output objects
for use in prompt templates. This allows phases to receive full structured
objects while formatting only what they need for prompts.
"""

from typing import Dict, Any, Optional, Union, List


def format_research_role_for_context(role_obj: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, str]:
    """
    Format research_role for prompt context.
    
    Handles both structured (dict) and legacy (string) formats for backward compatibility.
    
    Args:
        role_obj: Research role object (dict with 'role' and 'rationale') or legacy string
        
    Returns:
        Dict with 'research_role_display' and 'research_role_rationale' formatted for prompts
    """
    if not role_obj:
        return {
            "research_role_display": "",
            "research_role_rationale": ""
        }
    
    if isinstance(role_obj, dict):
        role_name = role_obj.get("role", "")
        rationale = role_obj.get("rationale", "")
        rationale_text = f"\n**角色选择理由:** {rationale}" if rationale else ""
        return {
            "research_role_display": role_name,
            "research_role_rationale": rationale_text
        }
    else:
        # Backward compatibility: treat as string
        return {
            "research_role_display": str(role_obj),
            "research_role_rationale": ""
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

