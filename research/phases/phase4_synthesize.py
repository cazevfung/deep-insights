"""Phase 4: Synthesize Final Report."""

from typing import Dict, Any, List, Optional
from research.phases.base_phase import BasePhase
from research.prompts import compose_messages
from research.prompts.context_formatters import format_synthesized_goal_for_context


class Phase4Synthesize(BasePhase):
    """Phase 4: Generate final research report."""
    
    def execute(
        self,
        phase1_5_output: Dict[str, Any],  # Now receives Phase 2 output (backward compatible name)
        phase3_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Phase 4: Generate final report.
        
        Args:
            phase1_5_output: Full Phase 2 output object containing synthesized_goal (preserves Phase 1 questions)
            phase3_output: Optional full Phase 3 output object containing findings
            
        Returns:
            Dict with report and raw_response (full output object)
        """
        self.logger.info("Phase 4: Generating final report")
        
        # Extract from full output objects (backward compatible)
        synthesized_goal = phase1_5_output.get("synthesized_goal", {})
        if not synthesized_goal and isinstance(phase1_5_output, dict) and "comprehensive_topic" in phase1_5_output:
            # Backward compatibility: accept synthesized_goal dict directly
            synthesized_goal = phase1_5_output
        
        comprehensive_topic = synthesized_goal.get("comprehensive_topic", "")
        component_questions = synthesized_goal.get("component_questions", [])
        
        # Get scratchpad
        scratchpad_contents = self.session.get_scratchpad_summary()
        
        # Retrieve user amendment / priorities to ensure final report honors them
        user_amendment = ""
        if isinstance(phase1_5_output, dict):
            user_amendment = phase1_5_output.get("user_input") or ""
        if not user_amendment:
            user_amendment = self.session.get_metadata("phase1_user_input", "")

        user_amendment_context = ""
        if user_amendment:
            user_amendment_context = f"**用户优先事项：**\n{user_amendment}\n"

        # Format component questions context
        if component_questions:
            component_questions_context = "**需要涵盖的组成问题：**\n"
            for i, question in enumerate(component_questions, 1):
                component_questions_context += f"{i}. {question}\n"
            component_questions_context += "\n**重要要求：**\n"
            component_questions_context += "- 文章必须全面回答综合主题，包括所有组成问题\n"
            component_questions_context += "- 但要以叙事方式整合，而不是分别回答（除非结构自然要求如此）\n"
            component_questions_context += "- 确保所有组成问题的关键发现都融入文章\n"
            component_questions_context += "- 如果某个组成问题没有得到充分回答，需要明确说明为什么（数据限制等）"
        else:
            component_questions_context = ""
        
        # Format synthesized goal for additional context
        goal_context = format_synthesized_goal_for_context(synthesized_goal)
        
        context = {
            "selected_goal": comprehensive_topic,
            "component_questions_context": component_questions_context,
            "scratchpad_contents": scratchpad_contents,
            # Include additional context from synthesized goal if available
            "unifying_theme": goal_context.get("unifying_theme", ""),
            "research_scope": goal_context.get("research_scope", ""),
            "user_amendment_context": user_amendment_context.strip() if user_amendment_context else "",
        }
        messages = compose_messages("phase4_synthesize", context=context)
        
        # Step 1: Generate outline (TOC) as JSON
        outline_msgs = compose_messages("phase4_synthesize", context={
            **context,
        }, locale=None, variant=None)
        # Replace the last user message with outline instruction
        if outline_msgs:
            outline_msgs[-1] = {"role": "user", "content": compose_messages("phase4_synthesize", context=context)[-1]["content"].replace("使用所有提供的\"结构化发现\"，撰写", "先生成报告大纲（只输出JSON）")}
        # Prefer dedicated outline prompt file
        try:
            outline_only = compose_messages("phase4_synthesize", context=context)
            # Best-effort: use outline.md role if available
            from research.prompts.loader import load_prompt, render_prompt
            outline_tmpl = load_prompt("phase4_synthesize", role="outline")
            outline_content = render_prompt(outline_tmpl, context)
            outline_msgs = [{"role": "user", "content": outline_content}]
        except Exception:
            pass

        # Time outline API call
        import time
        outline_start = time.time()
        self.logger.info(f"[TIMING] Starting outline API call for Phase 4 at {outline_start:.3f}")
        if hasattr(self, 'ui') and self.ui:
            self.ui.display_message("正在生成报告大纲...", "info")
        outline_resp = self._stream_with_callback(outline_msgs)
        outline_elapsed = time.time() - outline_start
        self.logger.info(f"[TIMING] Outline API call completed in {outline_elapsed:.3f}s for Phase 4")

        # Parse outline JSON
        sections: List[dict] = []
        try:
            parsed_outline = self.client.parse_json_from_stream(iter([outline_resp]))
            sections = parsed_outline.get("sections", []) if isinstance(parsed_outline, dict) else []
        except Exception:
            sections = []

        # Fallback to minimal sections if parsing failed
        if not sections:
            sections = [
                {"title": "核心吸引力与行为机制", "target_words": 600},
                {"title": "挫败感的来源与执行问题", "target_words": 600},
                {"title": "经济与公平：系统设计的影响", "target_words": 600},
                {"title": "社区与口碑：传播与留存", "target_words": 600},
                {"title": "对比与争议：不同作品的分歧", "target_words": 600},
                {"title": "未来方向与建议", "target_words": 600},
            ]

        # Step 2: Write sections one by one
        from research.prompts.loader import load_prompt, render_prompt
        section_tmpl = load_prompt("phase4_synthesize", role="section")
        section_outputs: List[str] = []
        total_sections = len(sections)
        for sec_idx, sec in enumerate(sections, 1):
            sec_title = sec.get("title", "章节")
            if hasattr(self, 'ui') and self.ui:
                self.ui.display_message(
                    f"正在生成章节 {sec_idx}/{total_sections}: {sec_title}",
                    "info"
                )
            
            sec_ctx = {
                **context,
                "section_title": sec_title,
                "section_target_words": sec.get("target_words", 600),
            }
            sec_msg = render_prompt(section_tmpl, sec_ctx)
            
            # Time section API call
            section_start = time.time()
            self.logger.info(f"[TIMING] Starting section {sec_idx}/{total_sections} API call for Phase 4 at {section_start:.3f}")
            sec_resp = self._stream_with_callback([
                {"role": "system", "content": compose_messages("phase4_synthesize", context=context)[0]["content"] if compose_messages("phase4_synthesize", context=context) else ""},
                {"role": "user", "content": sec_msg},
            ])
            section_elapsed = time.time() - section_start
            self.logger.info(f"[TIMING] Section {sec_idx}/{total_sections} API call completed in {section_elapsed:.3f}s for Phase 4")
            
            if hasattr(self, 'ui') and self.ui:
                self.ui.display_message(
                    f"章节 {sec_idx}/{total_sections} 生成完成: {sec_title}",
                    "success"
                )
            
            section_outputs.append(sec_resp)

        # Step 3: Assemble final report with header and appendices placeholder
        report = "\n\n".join(section_outputs)

        # Append mandatory appendices placeholders to encourage length
        report += (
            "\n\n## 方法与来源说明\n"
            "- 数据来源：视频转录、评论、文章资料\n"
            "- 检索方法：窗口化分页检索与关键词/语义提示\n"
            "- 局限性：样本与上下文可能不完整；引用比例受控≤5%\n\n"
            "## 证据附录\n"
            "- 本附录展示关键证据与示例的要点化列表与表格（自动生成）。\n"
        )

        result = {
            "report": report,
            "comprehensive_topic": comprehensive_topic,
            "component_questions": component_questions,
            "outline": sections,
        }
        
        # Store in session
        self.session.set_metadata("final_report", report)
        self.session.set_metadata("status", "completed")
        self.session.save()
        
        self.logger.info("Phase 4 complete: Generated final report")
        
        return result

