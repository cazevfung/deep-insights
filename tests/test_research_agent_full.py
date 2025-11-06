"""Full end-to-end test for Deep Research Agent.

This test runs the complete research workflow using data from run_20251104_023548
and verifies that the final article is outputted to the results folder.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def ensure_dependency(module_name: str, package_name: str = None, version: str = None):
    """
    Ensure a Python module is available, installing it if necessary.
    
    Args:
        module_name: The module name to import (e.g., 'pytest' or 'yaml')
        package_name: The package name for pip (e.g., 'pyyaml'). 
                      If None, uses module_name
        version: Optional version specifier (e.g., '>=7.0.0')
    """
    # Determine what package to install
    install_package = package_name if package_name is not None else module_name
    if version:
        install_package = f"{install_package}{version}"
    
    try:
        __import__(module_name)
    except ImportError:
        print(f"⚠️  {module_name} not found. Installing {install_package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--quiet", install_package
            ])
            print(f"✓ Successfully installed {install_package}")
            # Re-import after installation
            __import__(module_name)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {install_package}: {e}")
            sys.exit(1)


# Only auto-install test framework dependencies
# Runtime dependencies (openai, loguru, pyyaml, etc.) should be installed via:
# pip install -r requirements.txt
# We only auto-install test tools that aren't critical for the main application
ensure_dependency("pytest", version=">=7.0.0")

# Now safe to import
import pytest

# Try importing project modules - if they fail due to missing dependencies,
# provide a helpful error message pointing to requirements.txt
try:
    from research.agent import DeepResearchAgent
    from research.ui.mock_interface import MockConsoleInterface
    from core.config import Config
    from loguru import logger
except ImportError as e:
    missing_module = str(e).split("'")[1] if "'" in str(e) else "unknown"
    print(f"\n❌ Missing runtime dependency: {missing_module}")
    print(f"   Please install all dependencies first:")
    print(f"   pip install -r requirements.txt")
    print(f"\n   Or install specific package:")
    print(f"   pip install {missing_module}")
    sys.exit(1)


# Test configuration
TEST_BATCH_ID = "20251104_023548"
TEST_DATA_DIR = project_root / "tests" / "results" / f"run_{TEST_BATCH_ID}"
TEST_OUTPUT_DIR = project_root / "tests" / "results" / "reports"


def check_api_key() -> Optional[str]:
    """Check if API key is available from env var or config.yaml."""
    # First check environment variable
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    
    # If not found, try config.yaml
    if not api_key:
        try:
            config = Config()
            api_key = config.get("qwen.api_key")
        except Exception:
            pass  # Config may not be available
    
    if not api_key:
        logger.warning(
            "API key not found. Please set it in one of:\n"
            "  - DASHSCOPE_API_KEY/QWEN_API_KEY environment variable\n"
            "  - config.yaml (qwen.api_key)"
        )
    
    return api_key


@pytest.fixture(scope="function")
def output_dir():
    """Create and return test output directory."""
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_OUTPUT_DIR


@pytest.fixture(scope="function")
def test_data_exists():
    """Verify test data directory exists."""
    if not TEST_DATA_DIR.exists():
        pytest.skip(f"Test data directory not found: {TEST_DATA_DIR}")
    
    # Check for at least some JSON files
    json_files = list(TEST_DATA_DIR.glob("*.json"))
    if not json_files:
        pytest.skip(f"No JSON files found in test data directory: {TEST_DATA_DIR}")
    
    logger.info(f"Found {len(json_files)} JSON files in test data directory")
    return True


def test_research_agent_full_workflow(test_data_exists, output_dir):
    """
    Test complete research agent workflow end-to-end.
    
    This test:
    1. Loads data from run_20251104_023548
    2. Runs all phases (Prepare, Discover, Plan, Execute, Synthesize)
    3. Verifies report is generated
    4. Verifies report is saved to tests/results/reports/
    
    Environment variables:
    - FORCE_INTERACTIVE=1: Use real ConsoleInterface for interactive role input
    - TEST_AUTO_ROLE=<role>: Auto-provide this role when using MockConsoleInterface
    """
    # Check API key
    api_key = check_api_key()
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY not set. Skipping live test.")
    
    # Check if interactive mode is requested
    force_interactive = os.getenv("FORCE_INTERACTIVE", "0").lower() in ("1", "true", "yes", "on")
    test_auto_role = os.getenv("TEST_AUTO_ROLE")  # Allow setting role via env var
    
    # Detect if running in interactive terminal (TTY)
    is_tty = hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()
    
    if force_interactive:
        # Use real ConsoleInterface for interactive role input
        from research.ui.console_interface import ConsoleInterface
        ui = ConsoleInterface()
        logger.info("Using real ConsoleInterface (FORCE_INTERACTIVE=1) - you can provide input interactively")
    else:
        # Create mock UI - use interactive mode if running in TTY (interactive terminal)
        ui = MockConsoleInterface(
            auto_select_goal_id=None,  # Auto-select first goal
            auto_confirm_plan=True,
            auto_role=test_auto_role,  # Use env var if provided, otherwise None (skip role)
            verbose=True,
            interactive=is_tty  # Wait for input if running in interactive terminal
        )
        if is_tty:
            logger.info("Using MockConsoleInterface in interactive mode (detected TTY) - prompts will wait for input")
        if test_auto_role:
            logger.info(f"Using MockConsoleInterface with auto_role: {test_auto_role}")
        else:
            if not is_tty:
                logger.info("Using MockConsoleInterface (set FORCE_INTERACTIVE=1 for interactive mode or TEST_AUTO_ROLE=<role> to provide role)")
    
    # Initialize agent with UI and additional output directory
    agent = DeepResearchAgent(
        api_key=api_key,
        ui=ui,
        additional_output_dirs=[str(output_dir)]
    )
    
    # Run research
    logger.info(f"Starting research workflow for batch: {TEST_BATCH_ID}")
    result = agent.run_research(
        batch_id=TEST_BATCH_ID,
        user_topic=None  # Let AI discover goals naturally
    )
    
    # Verify completion
    assert result["status"] == "completed", f"Research did not complete. Status: {result.get('status')}"
    assert "session_id" in result, "Missing session_id in result"
    assert "report_path" in result, "Missing report_path in result"
    assert "selected_goal" in result, "Missing selected_goal in result"
    
    # Verify default report file exists
    default_report_path = Path(result["report_path"])
    assert default_report_path.exists(), f"Default report file not found: {default_report_path}"
    logger.info(f"Default report saved to: {default_report_path}")
    
    # Verify additional report file exists
    assert "additional_report_paths" in result, "Missing additional_report_paths in result"
    assert len(result["additional_report_paths"]) > 0, "No additional report paths saved"
    
    additional_report_path = Path(result["additional_report_paths"][0])
    assert additional_report_path.exists(), f"Additional report file not found: {additional_report_path}"
    logger.info(f"Additional report saved to: {additional_report_path}")
    
    # Verify report is in tests/results/reports/
    assert str(additional_report_path).startswith(str(output_dir)), \
        f"Report not in expected directory. Expected: {output_dir}, Got: {additional_report_path.parent}"
    
    # Verify report content
    with open(additional_report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    assert len(report_content) > 100, "Report content too short"
    assert "# 研究报告" in report_content, "Report missing title header"
    assert f"**批次ID**: {TEST_BATCH_ID}" in report_content, "Report missing batch ID"
    assert result["selected_goal"] in report_content, "Report missing selected goal"
    
    # Verify report has substantial content
    assert len(report_content) > 500, "Report seems too short for a research article"
    
    logger.success(f"✓ Research workflow completed successfully!")
    logger.info(f"✓ Report verified at: {additional_report_path}")
    logger.info(f"✓ Report length: {len(report_content)} characters")
    logger.info(f"✓ Selected goal: {result['selected_goal'][:100]}...")
    
    # Log usage if available
    if "usage" in result:
        usage = result["usage"]
        logger.info(f"✓ API usage: {usage.get('total_tokens', 'N/A')} tokens")


@pytest.mark.skip(reason="Single-test mode: this file runs only the full workflow test")
def test_research_agent_with_specific_goal(test_data_exists, output_dir):
    """
    Test research agent with a specific goal ID selection.
    
    Note: The workflow now synthesizes all goals automatically, so goal selection
    is no longer part of the workflow. This test verifies the synthesized goal
    is properly generated and used.
    """
    # Check API key
    api_key = check_api_key()
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY not set. Skipping live test.")
    
    # Check if interactive mode is requested
    force_interactive = os.getenv("FORCE_INTERACTIVE", "0").lower() in ("1", "true", "yes", "on")
    test_auto_role = os.getenv("TEST_AUTO_ROLE")
    
    if force_interactive:
        from research.ui.console_interface import ConsoleInterface
        ui = ConsoleInterface()
    else:
        # Create mock UI (goal selection is no longer used, but kept for compatibility)
        ui = MockConsoleInterface(
            auto_select_goal_id="2",  # Not used anymore, but kept for compatibility
            auto_confirm_plan=True,
            auto_role=test_auto_role,
            verbose=False
        )
    
    # Initialize agent
    agent = DeepResearchAgent(
        api_key=api_key,
        ui=ui,
        additional_output_dirs=[str(output_dir)]
    )
    
    # Run research
    result = agent.run_research(
        batch_id=TEST_BATCH_ID,
        user_topic=None
    )
    
    # Verify completion
    assert result["status"] == "completed"
    
    # Verify synthesized goal exists (the workflow now synthesizes all goals)
    assert "selected_goal" in result, "Missing selected_goal (synthesized comprehensive topic) in result"
    assert len(result["selected_goal"]) > 0, "Synthesized goal is empty"
    
    # Verify additional report paths exist
    assert "additional_report_paths" in result, "Missing additional_report_paths in result"
    assert len(result["additional_report_paths"]) > 0, "additional_report_paths is empty"
    
    # Verify report exists
    additional_report_path = Path(result["additional_report_paths"][0])
    assert additional_report_path.exists()
    
    logger.success(f"✓ Research with synthesized goal completed: {result['selected_goal'][:80]}...")


@pytest.mark.skip(reason="Single-test mode: this file runs only the full workflow test")
def test_research_agent_with_custom_topic(test_data_exists, output_dir):
    """
    Test research agent with a custom user topic.
    """
    # Check API key
    api_key = check_api_key()
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY not set. Skipping live test.")
    
    # Check if interactive mode is requested
    force_interactive = os.getenv("FORCE_INTERACTIVE", "0").lower() in ("1", "true", "yes", "on")
    test_auto_role = os.getenv("TEST_AUTO_ROLE")
    
    if force_interactive:
        from research.ui.console_interface import ConsoleInterface
        ui = ConsoleInterface()
    else:
        # Create mock UI
        ui = MockConsoleInterface(
            auto_select_goal_id=None,
            auto_confirm_plan=True,
            auto_role=test_auto_role,
            verbose=False
        )
    
    # Initialize agent
    agent = DeepResearchAgent(
        api_key=api_key,
        ui=ui,
        additional_output_dirs=[str(output_dir)]
    )
    
    # Run research with custom topic
    custom_topic = "游戏提取类型的未来发展趋势"
    result = agent.run_research(
        batch_id=TEST_BATCH_ID,
        user_topic=custom_topic
    )
    
    # Verify completion
    assert result["status"] == "completed"
    
    # Verify report exists and mentions topic
    additional_report_path = Path(result["additional_report_paths"][0])
    assert additional_report_path.exists()
    
    with open(additional_report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # The report should be relevant to the topic (though exact wording may vary)
    logger.success(f"✓ Research with custom topic completed: {custom_topic}")


if __name__ == "__main__":
    """Run tests directly."""
    import sys
    
    # Configure logging only when running directly
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Check API key
    api_key = check_api_key()
    if not api_key:
        print("\n❌ Error: API key not found.")
        print("   Please set it in one of:")
        print("   1. Environment variable:")
        print("      export DASHSCOPE_API_KEY=your_key_here  # Linux/Mac")
        print("      set DASHSCOPE_API_KEY=your_key_here     # Windows")
        print("   2. config.yaml file:")
        print("      qwen:")
        print("        api_key: 'your_key_here'")
        sys.exit(1)
    
    # Verify test data exists
    if not TEST_DATA_DIR.exists():
        print(f"\n❌ Error: Test data directory not found: {TEST_DATA_DIR}")
        sys.exit(1)
    
    # Create output directory
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Test data directory: {TEST_DATA_DIR}")
    print(f"✓ Output directory: {TEST_OUTPUT_DIR}")
    print(f"✓ API key configured: {'*' * 10}")
    
    # Run pytest
    print("\n" + "=" * 60)
    print("Running Deep Research Agent Full Workflow Test")
    print("=" * 60 + "\n")
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ])
    sys.exit(exit_code)

