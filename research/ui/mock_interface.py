"""Mock console interface for testing."""

from typing import Dict, Any, Optional
from loguru import logger


class MockConsoleInterface:
    """Mock console interface for non-interactive testing."""
    
    def __init__(
        self,
        auto_select_goal_id: Optional[str] = None,
        auto_confirm_plan: bool = True,
        auto_role: Optional[str] = None,
        verbose: bool = False,
        interactive: bool = False
    ):
        """
        Initialize mock interface.
        
        Args:
            auto_select_goal_id: Goal ID to auto-select (default: first goal)
            auto_confirm_plan: Whether to auto-confirm plan execution
            auto_role: Role to auto-provide when prompted (default: empty string = skip)
            verbose: Whether to print messages
            interactive: If True, actually wait for user input (for testing interactive flows)
        """
        self.auto_select_goal_id = auto_select_goal_id
        self.auto_confirm_plan = auto_confirm_plan
        self.auto_role = auto_role
        self.verbose = verbose
        self.interactive = interactive
        self.current_stream_buffer = ""
        self.messages = []
        self.selected_goal_id = None
        self.plan_confirmed = False
    
    def display_message(self, message: str, level: str = "info"):
        """Display a message (logged if verbose)."""
        self.messages.append((level, message))
        if self.verbose:
            symbols = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}
            symbol = symbols.get(level, "•")
            logger.info(f"{symbol} {message}")
    
    def display_header(self, title: str):
        """Display a section header."""
        if self.verbose:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"  {title}")
            logger.info(f"{'=' * 60}\n")
        self.messages.append(("header", title))
    
    def display_progress(self, status: Dict[str, Any]):
        """Display progress information."""
        progress = status.get("progress_percentage", 0)
        current_step = status.get("current_step_id")
        if self.verbose and current_step:
            logger.debug(f"[进度: {progress:.1f}%] 步骤 {current_step}")
    
    def display_stream(self, token: str):
        """Display streaming token."""
        self.current_stream_buffer += token
        if self.verbose:
            print(token, end="", flush=True)
    
    def clear_stream_buffer(self):
        """Clear the streaming buffer."""
        self.current_stream_buffer = ""
    
    def get_stream_buffer(self) -> str:
        """Get current stream buffer contents."""
        return self.current_stream_buffer
    
    def prompt_user(self, prompt: str, choices: Optional[list] = None) -> str:
        """
        Mock user prompt - returns auto-selected value, or waits for input if interactive=True.
        
        Args:
            prompt: Prompt text
            choices: List of valid choices
            
        Returns:
            Auto-selected choice, or user input if interactive=True
        """
        if self.verbose:
            logger.info(f"Prompt: {prompt}")
            if choices:
                logger.info(f"Available choices: {choices}")
        
        # If interactive mode, actually wait for user input
        if self.interactive:
            import sys
            while True:
                user_input = input(f"\n{prompt}: ").strip()
                
                if not choices:
                    return user_input
                
                if user_input in choices:
                    return user_input
                
                print(f"无效输入。请选择: {', '.join(choices)}")
        
        # Handle role prompt
        if "角色" in prompt or "role" in prompt.lower() or "你希望AI以什么角色" in prompt:
            if self.auto_role is not None:
                role = self.auto_role
                if self.verbose:
                    logger.info(f"Auto-provided role: {role}")
                return role
            else:
                # Default: return empty string (skip role)
                if self.verbose:
                    logger.info("Auto-skipping role (empty string)")
                return ""
        
        # Handle goal selection
        if "研究目标ID" in prompt or "goal" in prompt.lower():
            if self.auto_select_goal_id:
                selected = self.auto_select_goal_id
                self.selected_goal_id = selected
                if self.verbose:
                    logger.info(f"Auto-selected goal ID: {selected}")
                return selected
            elif choices:
                # Default: select first available goal
                selected = choices[0]
                self.selected_goal_id = selected
                if self.verbose:
                    logger.info(f"Auto-selected first goal ID: {selected}")
                return selected
        
        # Handle plan confirmation
        if "继续执行计划" in prompt or ("plan" in prompt.lower() and "执行" in prompt):
            if self.auto_confirm_plan:
                self.plan_confirmed = True
                if self.verbose:
                    logger.info("Auto-confirmed plan execution")
                return "y"
            return "n"
        
        # Handle synthesis confirmation (after Phase 1.5)
        if "继续创建研究计划" in prompt or "创建研究计划" in prompt:
            if self.auto_confirm_plan:
                if self.verbose:
                    logger.info("Auto-confirmed synthesis (continue to planning)")
                return "y"
            return "n"
        
        # Default: return first choice or empty string
        if choices:
            return choices[0]
        return ""
    
    def display_goals(self, goals: list):
        """Display research goals (logged if verbose)."""
        if self.verbose:
            logger.info("\n" + "=" * 60)
            logger.info("  可用的研究目标：")
            logger.info("=" * 60)
            for goal in goals:
                goal_id = goal.get("id")
                goal_text = goal.get("goal_text", "")
                logger.info(f"\n  [{goal_id}] {goal_text}")
            logger.info("\n" + "=" * 60)
    
    def display_synthesized_goal(self, synthesized_goal: Dict[str, Any]):
        """Display the synthesized comprehensive topic (logged if verbose)."""
        comprehensive_topic = synthesized_goal.get("comprehensive_topic", "")
        component_questions = synthesized_goal.get("component_questions", [])
        unifying_theme = synthesized_goal.get("unifying_theme", "")
        
        if self.verbose:
            logger.info("\n" + "=" * 60)
            logger.info("  综合研究主题")
            logger.info("=" * 60)
            logger.info(f"\n{comprehensive_topic}")
            
            if unifying_theme:
                logger.info(f"\n统一主题: {unifying_theme}")
            
            if component_questions:
                logger.info("\n组成问题:")
                for i, question in enumerate(component_questions, 1):
                    logger.info(f"  {i}. {question}")
            logger.info("=" * 60)
        
        self.messages.append(("synthesized_goal", synthesized_goal))
    
    def display_plan(self, plan: list):
        """Display research plan (logged if verbose)."""
        if self.verbose:
            logger.info("\n研究计划：")
            logger.info("-" * 60)
            for step in plan:
                step_id = step.get("step_id")
                goal = step.get("goal", "")
                logger.info(f"\n步骤 {step_id}: {goal}")
    
    def display_report(self, report: str, save_path: Optional[str] = None):
        """Display final report (logged if verbose)."""
        if self.verbose:
            logger.info("\n" + "=" * 60)
            logger.info("  最终研究报告")
            logger.info("=" * 60)
            logger.info(f"\n报告已保存到: {save_path}")
        
        self.messages.append(("report", save_path or ""))




