"""
Sample run script to verify Phase 3 streaming sanitation.

Usage:
    python scripts/test_phase3_stream_sanitizer.py

This simulates the backend receiving incremental tokens that contain literal
newline/control characters inside JSON strings (the exact scenario that used
to break phase3 real-time parsing). The script feeds the tokens through the
new sanitizer + StreamingJSONParser and prints partial + final updates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.utils.json_sanitizer import sanitize_json_stream_text
from research.utils.streaming_json_parser import StreamingJSONParser

# Raw response with literal newlines inside the summary/article fields.
RAW_RESPONSE = """{
  "step_id": 1,
  "findings": {
    "summary": "70%固定框架+30%AI演化的混合模式是当前AI陪伴游戏的可行范式。
它允许核心玩法保持可控，同时把情感反馈交给AI，以维持成本与创新的平衡。",
    "article": "第一部分：技术约束\\n混合模式要求把AI限定在情景反应而不是规则制定。
第二部分：商业验证\\nTolen等应用显示，当AI能记住昨天的对话时，用户付费更稳定。",
    "points_of_interest": {
      "key_claims": [
        {
          "claim": "玩家更在意AI记忆力带来的真实陪伴感",
          "relevance": "high"
        }
      ]
    },
    "analysis_details": {
      "assumptions": ["玩家愿意付费以换取情感稳定性"]
    }
  },
  "insights": "AI陪伴要把创新预算花在记忆和情绪建模上",
  "confidence": 0.78
}"""


def chunk_stream(text: str, chunk_size: int = 60) -> Iterable[str]:
    """Yield small chunks to mimic SSE token streaming."""
    for idx in range(0, len(text), chunk_size):
        yield text[idx : idx + chunk_size]


def main() -> None:
    print("== Phase3 Streaming Sanitizer Demo ==")
    parser = StreamingJSONParser(
        on_update=lambda data, complete: print(
            f"[parser] {'COMPLETE' if complete else 'partial'}: "
            f"keys={list(data.keys())}"
        )
    )

    for token in chunk_stream(RAW_RESPONSE):
        sanitized = sanitize_json_stream_text(token)
        parser.feed(sanitized)
        print("---")
        print(f"original token:\n{token}")
        print("sanitized token:\n", sanitized)

    final_data = parser.get_current_data()
    print("\n== Final Parsed JSON ==")
    print(json.dumps(final_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

