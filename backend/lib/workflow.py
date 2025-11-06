"""
Workflow functions - thin wrappers around test_full_workflow_integration.

These functions use the proven, working code from tests/ folder.
They are simple re-exports that can be used directly by backend services.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Re-export working test functions directly
# Backend services will use asyncio.to_thread() to call these sync functions
# and provide progress callbacks that queue messages for async processing
from tests.test_full_workflow_integration import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent,
)

__all__ = [
    'run_all_scrapers',
    'verify_scraper_results',
    'run_research_agent',
]

