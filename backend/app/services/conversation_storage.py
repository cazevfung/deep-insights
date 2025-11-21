"""
Shared helpers for persisting conversation history to disk.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONVERSATION_DIR = PROJECT_ROOT / "data" / "research" / "conversations"
CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)


def get_conversation_path(batch_id: str) -> Path:
    """Return the storage path for a batch conversation file."""
    safe_batch_id = batch_id.replace("/", "_")
    return CONVERSATION_DIR / f"{safe_batch_id}.json"


def load_conversation_state(batch_id: str) -> Optional[Dict[str, Any]]:
    """Load persisted conversation state for a batch."""
    path = get_conversation_path(batch_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to load conversation history for {batch_id}: {exc}")
        return None


def save_conversation_state(batch_id: str, payload: Dict[str, Any]) -> None:
    """Persist conversation state atomically."""
    path = get_conversation_path(batch_id)
    tmp_path = path.with_suffix(path.suffix + ".tmp") if path.suffix else path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to persist conversation history for {batch_id}: {exc}")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)



