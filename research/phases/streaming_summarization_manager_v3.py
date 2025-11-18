"""Scraping → Summarization Workflow Manager v3 (adapter on top of V2).

This module exposes a v3 workflow manager for the scraping → summarization
pipeline, integrated with the main workflow service.

Design notes:
 - For summarization, we build on the proven V2 manager + data-merger adapter.
 - For scraping, concurrency is still governed by the control-center
   (`run_all_scrapers_direct_v2`) with a worker pool (typically 8 workers).
 - This class exists as the single entrypoint the workflow service uses for
   "Phase 0" (streaming summarization), matching the v3 workflow diagram.

The actual orchestration between:
   scrapers → JSON files → merged scraped data → AI summaries (streamed)
is handled by:
   - `StreamingSummarizationAdapter` (merging + V2 manager)
   - `StreamingSummarizationManagerV2` (sequential summarization state machine)

v3 therefore focuses on providing a clear, named manager that the main
workflow can depend on, while reusing the stable V2 implementation underneath.
"""

from typing import Dict, Any, List
from loguru import logger

from research.phases.streaming_summarization_adapter import (
    StreamingSummarizationAdapter,
)


class StreamingSummarizationManagerV3(StreamingSummarizationAdapter):
    """
    v3 scraping → summarization workflow manager.

    This is the manager that `WorkflowService` uses for "Phase 0" in the
    end‑to‑end research pipeline on localhost.

    It currently extends the existing adapter (which wraps the V2 manager),
    so it:
      - Receives per-link scraped data (transcript/comments) as they finish
      - Merges multi-part sources (YouTube/Bilibili) via `DataMerger`
      - Feeds complete items into `StreamingSummarizationManagerV2`
      - Streams summarization progress/results back to the WebSocket UI

    The main difference is that this class gives us a dedicated, versioned
    entrypoint (`StreamingSummarizationManagerV3`) that corresponds to the
    v3 workflow design and can be evolved independently.
    """

    def __init__(self, client, config, ui, session, batch_id: str):
        logger.info(
            f"[StreamingSummarizationManagerV3] Initializing v3 workflow manager "
            f"for batch {batch_id}"
        )
        super().__init__(client=client, config=config, ui=ui, session=session, batch_id=batch_id)
        logger.info("[StreamingSummarizationManagerV3] Initialized successfully")



