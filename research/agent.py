"""Main Deep Research Agent orchestrator."""

from typing import Dict, Any, Optional
import os
from loguru import logger

from research.client import QwenStreamingClient
from research.session import ResearchSession
from research.progress_tracker import ProgressTracker
from research.phases.phase0_prepare import Phase0Prepare
from research.phases.phase0_5_role_generation import Phase0_5RoleGeneration
from research.phases.phase1_discover import Phase1Discover
from research.phases.phase2_synthesize import Phase2Synthesize
from research.phases.phase3_execute import Phase3Execute
from research.phases.phase4_synthesize import Phase4Synthesize
from research.ui.console_interface import ConsoleInterface
from pathlib import Path


class DeepResearchAgent:
    """Main orchestrator for deep research workflow."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: Optional[str] = None,
        ui = None,
        additional_output_dirs: Optional[list] = None
    ):
        """
        Initialize research agent.
        
        Args:
            api_key: Qwen API key (defaults to env var or config.yaml)
            base_url: API base URL
            model: Model name (defaults to config.yaml qwen.model or "qwen3-max")
            ui: Optional UI interface (defaults to ConsoleInterface)
            additional_output_dirs: Optional list of additional directories to save reports to
        """
        self.client = QwenStreamingClient(api_key=api_key, base_url=base_url, model=model)
        self.ui = ui if ui is not None else ConsoleInterface()
        self.additional_output_dirs = additional_output_dirs or []
        
        logger.info("Initialized DeepResearchAgent")
    
    def _convert_questions_to_steps(
        self,
        phase1_goals: list,
        data_summary: Dict[str, Any]
    ) -> list:
        """
        Convert Phase 1 questions directly to research steps for Phase 3.
        
        Args:
            phase1_goals: List of goal objects from Phase 1
            data_summary: Summary of available data
            
        Returns:
            List of research plan steps
        """
        steps = []
        for i, goal in enumerate(phase1_goals, 1):
            goal_text = goal.get("goal_text", "")
            
            # Determine required_data based on goal uses
            uses = goal.get("uses", [])
            if isinstance(uses, list):
                if "transcript_with_comments" in uses or "comments" in uses:
                    required_data = "transcript_with_comments"
                elif "transcript" in uses:
                    required_data = "transcript"
                else:
                    required_data = "transcript_with_comments"  # Default
            else:
                required_data = "transcript_with_comments"  # Default
            
            # Determine chunk strategy based on data size
            total_words = data_summary.get("total_words", 0)
            if total_words > 50000:  # Large dataset
                chunk_strategy = "sequential"
            else:
                chunk_strategy = "all"
            
            step = {
                "step_id": i,
                "goal": goal_text,  # Use Phase 1 question directly
                "required_data": required_data,
                "chunk_strategy": chunk_strategy,
                "notes": f"直接回答研究问题：{goal_text}"
            }
            steps.append(step)
        
        return steps
    
    def run_research(
        self,
        batch_id: str,
        user_topic: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete research workflow.
        
        Args:
            batch_id: Batch ID to analyze
            user_topic: Optional user-specified research topic
            session_id: Optional session ID (for resuming)
            
        Returns:
            Final results dictionary
        """
        # Initialize session
        if session_id:
            try:
                session = ResearchSession.load(session_id)
                logger.info(f"Resumed session: {session_id}")
            except FileNotFoundError:
                logger.warning(f"Session not found: {session_id}, creating new")
                session = ResearchSession(session_id=session_id)
        else:
            session = ResearchSession()
        
        logger.info(f"Starting research for batch: {batch_id}, session: {session.session_id}")
        
        try:
            # Phase 0: Prepare
            self.ui.display_header("Phase 0: 数据准备")
            phase0 = Phase0Prepare(self.client, session)
            phase0_result = phase0.execute(batch_id)
            
            # Aggregate abstracts
            abstracts = phase0_result.get("abstracts", {})
            combined_abstract = "\n\n---\n\n".join([
                f"**来源: {link_id}**\n{abstract}"
                for link_id, abstract in abstracts.items()
            ])
            
            # Cap combined abstract length to prevent API issues (e.g., data_inspection_failed)
            MAX_ABSTRACT_LENGTH = 80000  # ~80k chars to stay safe with API limits
            if len(combined_abstract) > MAX_ABSTRACT_LENGTH:
                logger.warning(
                    f"Combined abstract too large ({len(combined_abstract)} chars), "
                    f"truncating to {MAX_ABSTRACT_LENGTH} chars"
                )
                combined_abstract = combined_abstract[:MAX_ABSTRACT_LENGTH] + "\n\n[注意: 摘要已截断]"
            
            # Calculate data summary
            batch_data = phase0_result.get("data", {})
            # Make batch data available to retrieval handler and later phases
            try:
                # Attach to session for retrieval handler access
                session.batch_data = batch_data  # type: ignore[attr-defined]
            except Exception:
                # Fallback: set via metadata if direct attr not available
                session.set_metadata("_has_batch_data", True)
            sources = list(set([data.get("source", "unknown") for data in batch_data.values()]))
            total_words = sum([data.get("metadata", {}).get("word_count", 0) for data in batch_data.values()])
            total_comments = sum([
                len(data.get("comments") or [])  # Handle None values safely
                for data in batch_data.values()
            ])
            
            # Get quality assessment (enhancement #4)
            quality_assessment = phase0_result.get("quality_assessment", {})
            quality_flags = quality_assessment.get("quality_flags", [])
            
            # Display quality warnings if any
            if quality_flags:
                warnings = [f["message"] for f in quality_flags if f["severity"] in ["warning", "error"]]
                if warnings:
                    self.ui.display_message(
                        f"数据质量警告: {'; '.join(warnings[:2])}", 
                        "warning"
                    )
            
            # Calculate transcript size distribution for Phase 2 planning
            transcript_sizes = []
            for link_id, data in batch_data.items():
                transcript = data.get("transcript", "")
                if transcript:
                    word_count = len(transcript.split())
                    transcript_sizes.append(word_count)
            
            transcript_size_analysis = {}
            if transcript_sizes:
                transcript_size_analysis = {
                    "max_transcript_words": max(transcript_sizes),
                    "avg_transcript_words": int(sum(transcript_sizes) / len(transcript_sizes)),
                    "large_transcript_count": sum(1 for s in transcript_sizes if s > 5000),
                    "total_transcripts": len(transcript_sizes)
                }
            
            data_summary = {
                "sources": sources,
                "total_words": total_words,
                "total_comments": total_comments,
                "num_items": len(batch_data),
                "quality_assessment": quality_assessment,  # Enhancement #4
                "transcript_size_analysis": transcript_size_analysis  # New: for planning guidance
            }
            
            # Phase 0.5: Automatically generate research role
            self.ui.display_header("Phase 0.5: 生成研究角色")
            phase0_5 = Phase0_5RoleGeneration(self.client, session, ui=self.ui)
            role_result = phase0_5.execute(combined_abstract, user_topic)
            research_role = role_result.get("research_role", None)
            if research_role:
                # Handle both structured (dict) and legacy (string) formats
                role_display = research_role.get("role", "") if isinstance(research_role, dict) else str(research_role)
                self.ui.display_message(f"生成的研究角色: {role_display}", "info")
            else:
                self.ui.display_message("未生成研究角色，将使用通用分析视角", "warning")
            
            # Phase 1: Discover (with role + amendment loop before synthesis)
            self.ui.display_header("Phase 1: 生成研究目标")
            phase1 = Phase1Discover(self.client, session, ui=self.ui)

            # Initial goals
            phase1_result = phase1.execute(
                combined_abstract,
                user_topic,
                research_role=research_role,
                amendment_feedback=None,
                batch_data=batch_data,  # Pass batch_data for marker overview
            )
            goals = phase1_result.get("suggested_goals", [])
            self.ui.display_goals(goals)

            # Amendment step (single prompt: amend or leave blank to approve)
            # Always prompt - UI interfaces will handle appropriately (ConsoleInterface prompts, MockInterface auto-responds)
            amend = self.ui.prompt_user("你想如何修改这些目标？(自由输入，留空表示批准并继续)")
            if amend:
                # User wants to amend - regenerate goals once
                amended_result = phase1.execute(
                    combined_abstract,
                    user_topic,
                    research_role=research_role,
                    amendment_feedback=amend,
                    batch_data=batch_data,  # Pass batch_data for marker overview
                )
                goals = amended_result.get("suggested_goals", [])
                self.ui.display_goals(goals)
                proceed = self.ui.prompt_user("是否采用这些修订后的目标并继续？(y/n)", ["y", "n"])
                if proceed == "y":
                    # Use amended goals
                    phase1_result = amended_result
                else:
                    # User rejected revised goals - use original goals
                    logger.info("用户拒绝了修订后的目标，使用原始目标继续")
                    goals = phase1_result.get("suggested_goals", [])
            # If amend was blank, proceed with original goals (already in phase1_result)

            # Phase 2: Synthesize goals AFTER user amendment/approval
            # Pass full phase1_output object - preserves Phase 1 questions directly
            # Also pass user input and topic to ensure Phase 2 considers user context
            self.ui.display_header("Phase 2: 综合研究主题")
            phase2 = Phase2Synthesize(self.client, session, ui=self.ui)
            phase2_result = phase2.execute(
                phase1_result, 
                combined_abstract,
                user_input=amend if amend else None,  # Pass user amendment feedback
                user_topic=user_topic  # Pass original user topic
            )

            # Extract from full output for display
            synthesized = phase2_result.get("synthesized_goal", {})
            comprehensive_topic = synthesized.get("comprehensive_topic", "")
            component_questions = synthesized.get("component_questions", [])
            unifying_theme = synthesized.get("unifying_theme", "")

            # Validate comprehensive_topic was generated
            if not comprehensive_topic or not comprehensive_topic.strip():
                raise ValueError("Phase 2 failed to generate a comprehensive topic")

            self.ui.display_message("综合研究主题已生成", "success")
            self.ui.display_synthesized_goal(synthesized)
            
            # Convert Phase 1 questions directly to research steps (skip old Phase 2)
            phase1_goals = phase1_result.get("suggested_goals", [])
            plan = self._convert_questions_to_steps(phase1_goals, data_summary)
            
            logger.info(f"Converted {len(phase1_goals)} questions directly to {len(plan)} research steps")
            self.ui.display_plan(plan)
            
            # Confirm plan execution
            confirm = self.ui.prompt_user("是否继续执行计划? (y/n)", ["y", "n"])
            if confirm != "y":
                logger.info("User cancelled plan execution")
                return {"status": "cancelled"}
            
            # Update progress tracker with actual steps
            progress_tracker = ProgressTracker(total_steps=len(plan))
            progress_tracker.add_callback(self.ui.display_progress)
            # Register step completion callback to send step results to frontend
            if hasattr(self.ui, 'display_step_complete'):
                progress_tracker.add_step_complete_callback(self.ui.display_step_complete)
            
            # Phase 3: Execute
            self.ui.display_header("Phase 3: 执行研究计划")
            phase3 = Phase3Execute(self.client, session, progress_tracker)
            
            phase3_result = phase3.execute(plan, batch_data)
            
            self.ui.display_message("研究计划执行完成", "success")
            
            # Phase 4: Synthesize - Pass full phase2_output object
            # Note: Phase 4 doesn't use progress_tracker to avoid repeated 100% messages
            # Phase change notification is handled by display_header() independently
            self.ui.display_header("Phase 4: 生成最终报告")
            phase4 = Phase4Synthesize(self.client, session, progress_tracker=None)
            
            # Set stream callback for report generation
            self.ui.clear_stream_buffer()
            phase4_result = phase4.execute(phase1_5_output=phase2_result, phase3_output=phase3_result)
            
            report = phase4_result.get("report", "")
            
            # Save report
            from datetime import datetime
            
            # Default reports directory (project_root/data/research/reports)
            reports_dir = Path(__file__).parent.parent / "data" / "research" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = reports_dir / f"report_{session.session_id}.md"
            
            # Prepare report content
            report_content = (
                f"# 研究报告\n\n"
                f"**研究目标**: {comprehensive_topic}\n\n"
                f"**生成时间**: {datetime.now().isoformat()}\n\n"
                f"**批次ID**: {batch_id}\n\n"
                f"---\n\n"
                f"{report}"
            )
            
            # Save to default location
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Save to additional output directories
            additional_paths = []
            for output_dir in self.additional_output_dirs:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                additional_file = output_path / f"report_{batch_id}_{session.session_id}.md"
                with open(additional_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                additional_paths.append(str(additional_file))
                logger.info(f"Report also saved to: {additional_file}")
            
            self.ui.display_report(report, str(report_file))
            
            # Explicit completion logging
            logger.info("")
            logger.success("=" * 60)
            logger.success("  RESEARCH SESSION FINISHED - SUCCESSFULLY COMPLETED")
            logger.success("=" * 60)
            logger.success(f"  Session ID: {session.session_id}")
            logger.success(f"  Batch ID: {batch_id}")
            logger.success(f"  Report saved to: {report_file}")
            if additional_paths:
                logger.success(f"  Additional report: {additional_paths[0]}")
            usage_info = self.client.get_usage_info()
            logger.success(f"  Total tokens used: {usage_info.get('total_tokens', 0)}")
            logger.success("=" * 60)
            logger.success("  RESEARCH COMPLETE - NO FURTHER ACTION REQUIRED")
            logger.success("=" * 60)
            logger.info("")
            
            # Save final session state with completion marker
            from datetime import datetime
            session.set_metadata("status", "completed")
            session.set_metadata("completed_at", datetime.now().isoformat())
            session.set_metadata("finished", True)  # Explicit finished flag
            session.save()
            
            return {
                "status": "completed",
                "session_id": session.session_id,
                "batch_id": batch_id,
                "report_path": str(report_file),
                "additional_report_paths": additional_paths,
                "selected_goal": comprehensive_topic,
                "usage": usage_info
            }
            
        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            self.ui.display_message(f"错误: {str(e)}", "error")
            raise

