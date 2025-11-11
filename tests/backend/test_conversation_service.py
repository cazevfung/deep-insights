from pathlib import Path
from typing import Any, Dict, List
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / 'backend'
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from app.services.conversation_service import ConversationContextService, ConversationResult


class DummyLLMClient:
  def __init__(self, tokens: List[str], metadata: Dict[str, Any] | None = None):
    self._tokens = tokens
    self.last_call_metadata = metadata or {}
    self.usage = {"total_tokens": len("".join(tokens))}

  def stream_completion(self, *_args, **_kwargs):
    for token in self._tokens:
      yield token


@pytest.mark.asyncio
async def test_handle_user_message_immediate(monkeypatch):
  service = ConversationContextService()

  dummy_client = DummyLLMClient(["Hello, ", "world!"], {"provider": "test"})
  monkeypatch.setattr(service, "_ensure_llm_client", lambda: dummy_client)

  result: ConversationResult = await service.handle_user_message("batch-1", "Hi there")

  assert result.status == "ok"
  assert result.reply == "Hello, world!"
  assert result.assistant_message_id is not None

  user_payload = service.get_message_payload("batch-1", result.user_message_id)
  assert user_payload is not None
  assert user_payload["status"] == "completed"

  assistant_payload = service.get_message_payload("batch-1", result.assistant_message_id or "")
  assert assistant_payload is not None
  assert assistant_payload["content"] == "Hello, world!"


@pytest.mark.asyncio
async def test_handle_user_message_queue_and_resolve(monkeypatch):
  service = ConversationContextService()

  service.record_procedural_prompt("batch-queue", "prompt-1", "Please confirm", [])

  queued_result = await service.handle_user_message("batch-queue", "Follow-up question")
  assert queued_result.status == "queued"

  queued_payload = service.get_message_payload("batch-queue", queued_result.user_message_id)
  assert queued_payload is not None
  assert queued_payload["status"] == "queued"

  dummy_client = DummyLLMClient(["Acknowledged."], {"provider": "test"})
  monkeypatch.setattr(service, "_ensure_llm_client", lambda: dummy_client)

  resolved_results = await service.resolve_procedural_prompt("batch-queue", "prompt-1", "yes")
  assert len(resolved_results) == 1
  assert resolved_results[0].status == "ok"
  assert resolved_results[0].reply == "Acknowledged."

  updated_payload = service.get_message_payload("batch-queue", queued_result.user_message_id)
  assert updated_payload is not None
  assert updated_payload["status"] == "completed"

