"""CLI entry point for deep research agent."""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.agent import DeepResearchAgent
from core.config import Config
from loguru import logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Deep Research Agent - Analyze scraped content using Qwen3-max")
    parser.add_argument(
        "batch_id",
        help="Batch ID to analyze (e.g., 251029_150500)"
    )
    parser.add_argument(
        "--topic",
        "-t",
        help="Optional research topic"
    )
    parser.add_argument(
        "--session",
        "-s",
        help="Optional session ID to resume"
    )
    parser.add_argument(
        "--api-key",
        "-k",
        help="Qwen API key (or set DASHSCOPE_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url",
        help="API base URL (default: Beijing region)",
        default="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    parser.add_argument(
        "--model",
        "-m",
        help="Model name (overrides config.yaml)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Read model from config.yaml if not provided via CLI
    model = args.model
    if model is None:
        try:
            config = Config()
            model = config.get("qwen.model", "qwen3-max")
            logger.info(f"Using model from config.yaml: {model}")
        except Exception:
            model = "qwen3-max"  # Fallback default
            logger.info(f"Using default model: {model}")
    
    # Initialize agent
    try:
        agent = DeepResearchAgent(
            api_key=args.api_key,
            base_url=args.base_url,
            model=model
        )
        
        # Run research
        result = agent.run_research(
            batch_id=args.batch_id,
            user_topic=args.topic,
            session_id=args.session
        )
        
        if result.get("status") == "completed":
            logger.success(f"Research completed successfully!")
            logger.info(f"Report saved to: {result.get('report_path')}")
            logger.info(f"Session ID: {result.get('session_id')}")
            logger.info("")
            logger.info("=" * 60)
            logger.success("PROCESS FINISHED - EXITING NOW")
            logger.info("=" * 60)
            sys.exit(0)  # Explicitly exit on successful completion
        else:
            logger.warning(f"Research status: {result.get('status')}")
            logger.error("Research did not complete successfully - exiting with error")
            sys.exit(1)  # Exit with error code if status is not completed
    
    except KeyboardInterrupt:
        logger.warning("Research interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Research failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

