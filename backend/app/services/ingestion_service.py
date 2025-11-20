"""
Rich source ingestion service for URLs, file uploads, and manual text.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile
from loguru import logger

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional at import time
    pd = None

from utils.link_formatter import build_items, current_batch_id, iso_timestamp


MAX_FILE_COUNT = 10
MAX_TOTAL_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024  # 25 MB

TEXT_EXTENSIONS = {'.txt', '.md', '.markdown'}
WORD_EXTENSIONS = {'.doc', '.docx'}
PPT_EXTENSIONS = {'.ppt', '.pptx'}
EXCEL_EXTENSIONS = {'.xls', '.xlsx'}
PDF_EXTENSIONS = {'.pdf'}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | WORD_EXTENSIONS | PPT_EXTENSIONS | EXCEL_EXTENSIONS | PDF_EXTENSIONS


@dataclass
class IngestionItem:
    """Represents a normalized ingestion source mapped to a link entry."""

    url: str
    source_kind: str  # url | upload | text
    display_name: str
    metadata: Dict[str, Any]


class IngestionService:
    """Service to normalize mixed sources into scraper-compatible artifacts."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.links_file = self.project_root / "tests" / "data" / "test_links.json"
        self.upload_root = self.project_root / "backend" / "uploads"
        self.storage_root = self.project_root / "data" / "research"
        self.upload_root.mkdir(parents=True, exist_ok=True)

    async def ingest_sources(
        self,
        urls: List[str],
        text_entries: List[Dict[str, str]],
        files: List[UploadFile],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """Normalize sources, update batch artifacts, and return batch metadata."""
        if not (urls or text_entries or files):
            raise ValueError("At least one link, upload, or text entry is required")

        logger.info(
            "Ingesting sources: %s urls, %s text entries, %s files",
            len(urls),
            len(text_entries),
            len(files),
        )

        if len(files) > MAX_FILE_COUNT:
            raise ValueError(f"Too many files uploaded (max {MAX_FILE_COUNT})")

        total_bytes = 0
        for upload in files:
            size = await self._get_upload_size(upload)
            if size > MAX_SINGLE_FILE_BYTES:
                raise ValueError(f"{upload.filename} exceeds the {MAX_SINGLE_FILE_BYTES // (1024 * 1024)} MB limit")
            total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError(f"Total upload size exceeds {MAX_TOTAL_BYTES // (1024 * 1024)} MB limit")

        batch_id = current_batch_id()
        target_session_id = session_id or batch_id

        batch_storage = self._ensure_batch_storage(target_session_id, batch_id)
        manifest_items: List[Dict[str, Any]] = []
        normalized_inputs: List[IngestionItem] = []

        # 1. URLs (unchanged)
        for raw_url in urls:
            url = raw_url.strip()
            if not url:
                continue
            normalized_inputs.append(
                IngestionItem(
                    url=url,
                    source_kind="url",
                    display_name=url,
                    metadata={"original_url": url},
                )
            )
            manifest_items.append(
                {
                    "source_kind": "url",
                    "display_name": url,
                    "original_url": url,
                }
            )

        # 2. Text entries
        for idx, entry in enumerate(text_entries, start=1):
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            label = entry.get("label") or f"Text #{idx}"
            text_path = self._write_text_entry(content, label, batch_storage)
            normalized_inputs.append(
                IngestionItem(
                    url=text_path.as_uri(),
                    source_kind="text",
                    display_name=label,
                    metadata={
                        "label": label,
                        "character_count": len(content),
                        "file_path": str(text_path),
                    },
                )
            )
            manifest_items.append(
                {
                    "source_kind": "text",
                    "display_name": label,
                    "character_count": len(content),
                    "text_file": str(text_path),
                }
            )

        # 3. File uploads
        for upload in files:
            normalized = await self._convert_upload(upload, batch_storage)
            normalized_inputs.append(normalized["item"])
            manifest_items.append(normalized["manifest"])

        if not normalized_inputs:
            raise ValueError("No valid sources were provided after filtering")

        # Build link entries compatible with scrapers
        ordered_urls = [entry.url for entry in normalized_inputs]
        link_items = build_items(ordered_urls)

        # Map manifest metadata with generated link IDs
        for item, manifest in zip(link_items, manifest_items):
            manifest["link_id"] = item["id"]
            manifest["link_type"] = item["type"]
            manifest["url"] = item["url"]

        payload = {
            "batchId": batch_id,
            "createdAt": iso_timestamp(),
            "links": link_items,
        }
        self._write_links_file(payload)
        self._write_manifest(batch_storage, target_session_id, batch_id, manifest_items)

        logger.info(
            "Prepared batch %s: %s items (%s urls, %s uploads, %s texts)",
            batch_id,
            len(link_items),
            len(urls),
            len(files),
            len(text_entries),
        )

        return {
            "batch_id": batch_id,
            "items": [
                {
                    "url": item["url"],
                    "source": item["type"],
                    "link_id": item["id"],
                }
                for item in link_items
            ],
            "total": len(link_items),
            "session_id": target_session_id,
            "manifest": manifest_items,
        }

    async def _convert_upload(self, upload: UploadFile, batch_storage: Path) -> Dict[str, Any]:
        """Convert uploaded file into normalized artifact and manifest."""
        filename = upload.filename or f"upload-{uuid.uuid4().hex}"
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {filename}")

        raw_dir = batch_storage / "uploads"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{uuid.uuid4().hex}{suffix}"

        # Persist raw bytes
        contents = await upload.read()
        raw_path.write_bytes(contents)
        logger.info("Saved upload %s to %s (%s bytes)", filename, raw_path, len(contents))

        text_content = self._extract_text_from_file(raw_path, suffix)
        if not text_content.strip():
            raise ValueError(f"No textual content could be extracted from {filename}")

        text_file = batch_storage / "prepared" / f"{raw_path.stem}.txt"
        text_file.parent.mkdir(parents=True, exist_ok=True)
        text_file.write_text(text_content, encoding="utf-8")

        item = IngestionItem(
            url=text_file.as_uri(),
            source_kind="upload",
            display_name=filename,
            metadata={
                "original_name": filename,
                "file_extension": suffix,
                "raw_path": str(raw_path),
                "text_path": str(text_file),
            },
        )

        manifest = {
            "source_kind": "upload",
            "display_name": filename,
            "raw_path": str(raw_path),
            "text_file": str(text_file),
            "file_extension": suffix,
        }

        if suffix in EXCEL_EXTENSIONS and pd is not None:
            manifest["structured_preview"] = self._extract_excel_preview(raw_path)

        return {"item": item, "manifest": manifest}

    def _extract_text_from_file(self, path: Path, suffix: str) -> str:
        """Route to the appropriate converter."""
        if suffix in TEXT_EXTENSIONS:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix in PDF_EXTENSIONS:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        if suffix in WORD_EXTENSIONS:
            from docx import Document

            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        if suffix in PPT_EXTENSIONS:
            from pptx import Presentation

            prs = Presentation(str(path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        texts.append(shape.text)
            return "\n".join(texts)
        if suffix in EXCEL_EXTENSIONS:
            if pd is None:
                raise RuntimeError("pandas is required for Excel ingestion")
            data = self._extract_excel_preview(path)
            return json.dumps(data, ensure_ascii=False, indent=2)
        raise ValueError(f"Unsupported file extension: {suffix}")

    def _extract_excel_preview(self, path: Path) -> Dict[str, Any]:
        """Convert Excel sheets into JSON-ready structure."""
        if pd is None:
            raise RuntimeError("pandas is required for Excel ingestion")
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
        preview = {}
        for sheet_name, df in sheets.items():
            sanitized = df.dropna(how="all")
            sanitized = sanitized.dropna(axis=1, how="all")
            sanitized = sanitized.fillna("")
            preview[str(sheet_name)] = {
                "columns": [str(col) for col in sanitized.columns],
                "records": sanitized.astype(str).to_dict(orient="records"),
            }
        return preview

    def _write_text_entry(self, content: str, label: str, batch_storage: Path) -> Path:
        """Persist inline text as a file for scraping."""
        safe_label = "".join(ch for ch in label if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")
        if not safe_label:
            safe_label = uuid.uuid4().hex[:8]
        text_dir = batch_storage / "text"
        text_dir.mkdir(parents=True, exist_ok=True)
        path = text_dir / f"{safe_label}.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_links_file(self, payload: Dict[str, Any]) -> None:
        """Persist formatted links for downstream scrapers."""
        self.links_file.parent.mkdir(parents=True, exist_ok=True)
        self.links_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote %s links to %s", len(payload.get("links", [])), self.links_file)

    def _write_manifest(
        self,
        batch_storage: Path,
        session_id: str,
        batch_id: str,
        manifest_items: List[Dict[str, Any]],
    ) -> None:
        """Persist manifest alongside research artifacts."""
        manifest = {
            "session_id": session_id,
            "batch_id": batch_id,
            "created_at": iso_timestamp(),
            "items": manifest_items,
        }
        manifest_path = batch_storage / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Manifest written to %s", manifest_path)

    def _ensure_batch_storage(self, session_id: str, batch_id: str) -> Path:
        """Ensure storage directory exists for session/batch artifacts."""
        base = self.storage_root / session_id / batch_id
        base.mkdir(parents=True, exist_ok=True)
        return base

    async def _get_upload_size(self, upload: UploadFile) -> int:
        """Determine upload size without losing the stream."""
        current = await upload.read()
        size = len(current)
        if hasattr(upload, "seek"):
            await upload.seek(0)
        else:  # pragma: no cover - fallback
            upload.file.seek(0)
        return size

