"""Loader utility for shared test links with batch and link ids."""
import os
import json
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


VALID_TYPES = {"youtube", "bilibili", "reddit", "article"}
DEFAULT_PATH = Path(__file__).parent / "data" / "test_links.json"


class TestLinksLoader:
    def __init__(self, file_path: Optional[str] = None):
        env_override = os.environ.get("TEST_LINKS_FILE")
        path = Path(env_override or file_path or DEFAULT_PATH)
        self._path = path
        self._data = self._load_and_validate(path)

        # Build typed index and url-dedup per type
        self.batch_id: str = self._data["batchId"]
        self.links: List[Dict[str, Any]] = self._data["links"]
        self._links_by_type: Dict[str, List[Dict[str, Any]]] = {}
        seen_by_type: Dict[str, set] = {t: set() for t in VALID_TYPES}
        for item in self.links:
            t = item["type"]
            if t not in self._links_by_type:
                self._links_by_type[t] = []
            url = item["url"].strip()
            if url not in seen_by_type[t]:
                self._links_by_type[t].append(item)
                seen_by_type[t].add(url)

    def _load_and_validate(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Test links file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Root must be an object with batchId and links")

        batch_id = data.get("batchId")
        links = data.get("links")
        if not batch_id or not isinstance(batch_id, str):
            raise ValueError("batchId is required and must be a string")
        if not isinstance(links, list):
            raise ValueError("links must be an array")

        # Validate links
        ids_seen = set()
        for idx, item in enumerate(links):
            if not isinstance(item, dict):
                raise ValueError(f"links[{idx}] must be an object")
            lid = item.get("id")
            ltype = item.get("type")
            url = item.get("url")
            if not lid or not isinstance(lid, str):
                raise ValueError(f"links[{idx}] missing id (string)")
            if lid in ids_seen:
                raise ValueError(f"Duplicate link id detected: {lid}")
            ids_seen.add(lid)
            if ltype not in VALID_TYPES:
                raise ValueError(f"links[{idx}] invalid type: {ltype}; valid: {sorted(VALID_TYPES)}")
            if not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"links[{idx}] invalid url: {url}")

        return data

    def get_batch_id(self) -> str:
        return self.batch_id

    def get_links(self, link_type: str) -> List[Dict[str, Any]]:
        if link_type not in VALID_TYPES:
            raise ValueError(f"Unknown link type: {link_type}")
        return list(self._links_by_type.get(link_type, []))

    def iter_links(self, types: Optional[List[str]] = None):
        wanted = set(types) if types else VALID_TYPES
        for t in wanted:
            for item in self._links_by_type.get(t, []):
                yield t, item


