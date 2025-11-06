"""
Backend library module - re-exports of working test functions.

This module provides direct access to proven, working functions from tests/ folder.
Backend services use these functions with asyncio.to_thread() for async compatibility.
"""

from backend.lib.workflow import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent,
)
from backend.lib.workflow_direct import (
    run_all_scrapers_direct,
)

__all__ = [
    'run_all_scrapers',
    'run_all_scrapers_direct',  # Direct execution with progress callbacks
    'verify_scraper_results',
    'run_research_agent',
]

