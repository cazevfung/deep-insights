"""Profile Phase 3 vector indexing + execution for selected steps."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

from loguru import logger

from core.config import Config
from research.client import QwenStreamingClient
from research.session import ResearchSession
from research.data_loader import ResearchDataLoader
from research.embeddings.vector_indexer import VectorIndexer
from research.phases.phase3_execute import Phase3Execute
from research.retrieval.vector_retrieval_service import VectorRetrievalService


@contextmanager
def timed(label: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[TIMING] {label}: {elapsed:.3f}s")


def build_plan_steps(metadata: Dict[str, object], limit: int = 2) -> List[Dict[str, object]]:
    goals = metadata.get("phase1_confirmed_goals") or []
    steps: List[Dict[str, object]] = []

    for idx, goal in enumerate(goals[:limit], start=1):
        goal_text = goal.get("goal_text", f"临时步骤 {idx}")
        uses = goal.get("uses") or []

        if "transcript_with_comments" in uses:
            required_data = "transcript_with_comments"
        elif "metadata" in uses:
            required_data = "metadata"
        else:
            required_data = "transcript"

        step = {
            "step_id": idx,
            "goal": goal_text,
            "required_data": required_data,
            "chunk_strategy": "sequential" if required_data.startswith("transcript") else "all",
            "chunk_size": 4000,
        }

        steps.append(step)

    if not steps:
        raise ValueError("No phase1_confirmed_goals found in session metadata; cannot build plan.")

    return steps


def main(session_id: str, batch_id: str) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"profile_phase3_{session_id}.log"
    logger.remove()
    logger.add(log_file, level="INFO", mode="w")
    logger.add(lambda msg: print(msg, end=""), level="INFO")

    logger.info("=== Profiling Phase 3 (session=%s, batch=%s) ===", session_id, batch_id)

    session = ResearchSession.load(session_id)
    loader = ResearchDataLoader()

    with timed("load_batch"):
        batch_data = loader.load_batch(batch_id)

    indexer = VectorIndexer()
    with timed("vector_indexing"):
        indexer.index_batch(batch_id, batch_data)

    plan_steps = build_plan_steps(session.metadata, limit=2)
    logger.info("Plan steps derived from session: %s", json.dumps(plan_steps, ensure_ascii=False, indent=2))

    config = Config()
    client = QwenStreamingClient(api_key=config.get("qwen.api_key"))

    phase3 = Phase3Execute(client=client, session=session)
    phase3.vector_service = VectorRetrievalService()

    with timed("phase3_steps_1_2"):
        result = phase3.execute(plan_steps, batch_data)

    logger.info("Phase 3 result snippet: %s", json.dumps(result, ensure_ascii=False, indent=2))
    telemetry = result.get("telemetry", {})
    if telemetry:
        logger.info("Phase 3 telemetry summary: %s", json.dumps(telemetry, ensure_ascii=False, indent=2))
    logger.info("=== Profiling complete; log written to %s ===", log_file)


if __name__ == "__main__":
    main(session_id="20251107_202526", batch_id="20251107_121603")

