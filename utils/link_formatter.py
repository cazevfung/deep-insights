"""Utility to convert URLs into test_links.json-style entries.

Usage examples:

  # Single item (default)
  python utils/link_formatter.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

  # Multiple items -> prints an array of items
  python utils/link_formatter.py https://www.youtube.com/watch?v=... https://www.bilibili.com/video/...

  # Read from stdin (one URL per line)
  type urls.txt | python utils/link_formatter.py

  # Full batch payload (ready to overwrite tests/data/test_links.json)
  python utils/link_formatter.py --batch --batch-id 251029_150500 \
      https://www.bilibili.com/video/BV... https://www.youtube.com/watch?v=...

  # Detect duplicates in provided URLs (warn) and optionally drop them
  python utils/link_formatter.py --dedupe https://a ... https://a ...

  # Check against existing test_links.json for already-present URLs
  python utils/link_formatter.py --check-existing tests/data/test_links.json https://a ...

Outputs JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


TYPE_RULES: List[Tuple[str, str, str]] = [
    ("bilibili", "bilibili", "bili"),
    ("youtube", "youtube", "yt"),
    ("youtu.be", "youtube", "yt"),
    ("reddit", "reddit", "rd"),
]


def clean_url(url: str) -> str:
    """Remove tracking/extra query parameters from URLs.
    
    - Bilibili: removes spm_id_from parameter
    - YouTube: removes pp parameter
    
    Args:
        url: URL to clean
        
    Returns:
        Cleaned URL with tracking parameters removed, or original URL if unchanged
    """
    try:
        parsed = urlparse(url)
        netloc_lower = parsed.netloc.lower()
        
        # Parse query parameters
        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        modified = False
        
        # Remove Bilibili tracking parameters
        if 'bilibili.com' in netloc_lower:
            if 'spm_id_from' in query_dict:
                del query_dict['spm_id_from']
                modified = True
        
        # Remove YouTube tracking parameters
        if 'youtube.com' in netloc_lower or 'youtu.be' in netloc_lower:
            if 'pp' in query_dict:
                del query_dict['pp']
                modified = True
        
        # Reconstruct URL only if modified
        if not modified:
            return url
        
        # Reconstruct query string
        new_query = urlencode(query_dict, doseq=True)
        
        # Reconstruct URL
        new_parsed = parsed._replace(query=new_query)
        return urlunparse(new_parsed)
    except Exception:
        # If parsing fails, return original URL
        return url


def infer_type_and_prefix(url: str) -> Tuple[str, str]:
    """Infer link type and id prefix from URL host.

    Returns (type, prefix). Unknown domains default to ("article", "art").
    """
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""

    for needle, link_type, prefix in TYPE_RULES:
        if needle in host:
            return link_type, prefix
    return "article", "art"


def build_item(url: str, index_for_type: int) -> Dict[str, str]:
    """Create a single link item dict matching tests/data/test_links.json format.

    id pattern: {prefix}_req{n}, where n is 1-based per type within this run.
    """
    cleaned_url = clean_url(url.strip())
    link_type, prefix = infer_type_and_prefix(cleaned_url)
    item_id = f"{prefix}_req{index_for_type}"
    return {"id": item_id, "type": link_type, "url": cleaned_url}


def build_items(urls: List[str]) -> List[Dict[str, str]]:
    counts_by_type_prefix: Dict[str, int] = {}
    items: List[Dict[str, str]] = []
    for raw in urls:
        url = raw.strip()
        if not url:
            continue
        _, prefix = infer_type_and_prefix(url)
        counts_by_type_prefix[prefix] = counts_by_type_prefix.get(prefix, 0) + 1
        idx = counts_by_type_prefix[prefix]
        items.append(build_item(url, idx))
    return items


def current_batch_id() -> str:
    # Example: 20251030_130123
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert URL(s) into tests/data/test_links.json-style entries",
    )
    parser.add_argument("urls", nargs="*", help="URL(s) to convert")
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Drop duplicate URLs from input before formatting",
    )
    parser.add_argument(
        "--check-existing",
        nargs="?",
        const="tests/data/test_links.json",
        help="Optional path to an existing JSON file to check for already-present URLs (default: tests/data/test_links.json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Output a full batch object with batchId, createdAt, and links",
    )
    parser.add_argument(
        "--batch-id",
        help="Batch ID to use when --batch is set (default: current UTC timestamp)",
    )
    return parser.parse_args(argv)


def read_urls_from_stdin() -> List[str]:
    if sys.stdin is None or sys.stdin.closed:
        return []
    if sys.stdin.isatty():
        return []
    return [line.rstrip("\n") for line in sys.stdin]


def main(argv: List[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    # Collect URLs from args or stdin
    urls = list(args.urls)
    if not urls:
        urls = read_urls_from_stdin()

    # Identify duplicates in provided URLs
    if urls:
        seen: set[str] = set()
        dupes: List[str] = []
        for u in urls:
            key = u.strip()
            if key in seen:
                dupes.append(u)
            else:
                seen.add(key)
        if dupes:
            print(f"Warning: duplicate URL(s) in input will create duplicates unless --dedupe is used:\n  - " + "\n  - ".join(dupes), file=sys.stderr)
        if args.dedupe and dupes:
            # Preserve first occurrence order
            deduped: List[str] = []
            seen.clear()
            for u in urls:
                key = u.strip()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(u)
            urls = deduped

    # Check against existing file for already-present URLs
    if args.check_existing:
        try:
            from pathlib import Path
            p = Path(args.check_existing)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                existing_urls = set()
                if isinstance(data, dict) and isinstance(data.get("links"), list):
                    for item in data["links"]:
                        if isinstance(item, dict) and isinstance(item.get("url"), str):
                            existing_urls.add(item["url"].strip())
                overlap = [u for u in urls if u.strip() in existing_urls]
                if overlap:
                    print(
                        "Warning: provided URL(s) already exist in " + str(p) + ":\n  - " + "\n  - ".join(overlap),
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"Warning: failed to check existing file: {e}", file=sys.stderr)

    if not urls:
        print("[]" if not args.batch else json.dumps({"batchId": "", "createdAt": iso_timestamp(), "links": []}, ensure_ascii=False, indent=2))
        return 0

    items = build_items(urls)

    if args.batch:
        batch_id = args.batch_id or current_batch_id()
        payload = {
            "batchId": batch_id,
            "createdAt": iso_timestamp(),
            "links": items,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        # Print a single item or an array if multiple were given
        out = items[0] if len(items) == 1 else items
        print(json.dumps(out, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


