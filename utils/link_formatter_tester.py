"""Interactive tester for link_formatter.

Flow:
  1) Starts an interactive prompt to paste URLs (one per line).
  2) Blank line to finish input.
  3) Builds items using utils/link_formatter.py logic.
  4) Writes a full batch JSON into tests/data/test_links.json.

Run:
  python utils/link_formatter_tester.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

try:
    # Prefer project-resolved import if running from elsewhere
    from core.config import find_project_root  # type: ignore
except Exception:  # Fallback if core/config.py path differs
    def find_project_root(start_path: Path | None = None) -> Path:  # type: ignore
        return Path(__file__).resolve().parent.parent


from utils.link_formatter import build_items, current_batch_id, iso_timestamp  # type: ignore


def prompt_urls() -> List[str]:
    print("Paste URLs (one per line). Press Enter on an empty line to finish:\n")
    urls: List[str] = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            break
        urls.append(line)
    return urls


def main() -> int:
    project_root = find_project_root(Path(__file__).resolve())
    target_file = project_root / "tests" / "data" / "test_links.json"

    urls = prompt_urls()
    if not urls:
        print("No URLs entered. Nothing to do.")
        return 0

    items = build_items(urls)

    # Try to reuse existing batchId if file exists, otherwise generate a new one
    batch_id = None
    if target_file.exists():
        try:
            existing = json.loads(target_file.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("batchId"), str) and existing.get("batchId"):
                batch_id = existing["batchId"]
        except Exception:
            batch_id = None
    if not batch_id:
        batch_id = current_batch_id()

    payload = {
        "batchId": batch_id,
        "createdAt": iso_timestamp(),
        "links": items,
    }

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nWrote {len(items)} item(s) to: {target_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


