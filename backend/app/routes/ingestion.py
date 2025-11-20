"""
Endpoints for ingesting mixed research sources (URLs, uploads, text).
"""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger

from app.routes.links import FormatLinksResponse
from app.services.ingestion_service import IngestionService
from research.session import ResearchSession

router = APIRouter(tags=["ingestion"])

_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Lazy-load ingestion service."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service


@router.post("/sources", response_model=FormatLinksResponse)
async def ingest_sources(
    links: Optional[str] = Form(None),
    text_entries: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Normalize user-provided sources into scraper-ready batch artifacts.

    Args:
        links: JSON array of URLs (stringified)
        text_entries: JSON array of {label, content}
        session_id: Existing research session identifier
        files: Uploaded binary files (PDF, Office, etc.)

    Returns:
        FormatLinksResponse compatible payload
    """
    session = _resolve_session(session_id)
    try:
        parsed_links = _parse_links_payload(links)
        parsed_text = _parse_text_entries(text_entries)
        upload_list = files or []

        service = get_ingestion_service()
        payload = await service.ingest_sources(parsed_links, parsed_text, upload_list, session.session_id)

        session.set_metadata("batch_id", payload["batch_id"])
        session.save()

        return FormatLinksResponse(
            batch_id=payload["batch_id"],
            items=payload["items"],
            total=payload["total"],
            session_id=session.session_id,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Ingestion validation failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - runtime protection
        logger.exception("Unexpected ingestion failure")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")


def _parse_links_payload(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("links must be an array")
        return [str(item).strip() for item in data if str(item).strip()]
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid links payload: {exc.msg}") from exc


def _parse_text_entries(raw: Optional[str]) -> List[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("text_entries must be an array")
        normalized = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            normalized.append(
                {
                    "label": str(entry.get("label") or "").strip(),
                    "content": str(entry.get("content") or ""),
                }
            )
        return normalized
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid text_entries payload: {exc.msg}") from exc


def _resolve_session(session_id: Optional[str]) -> ResearchSession:
    """Load or create a ResearchSession."""
    if session_id:
        try:
            return ResearchSession.load(session_id)
        except FileNotFoundError:
            logger.warning("Session %s not found. Creating new session.", session_id)
    return ResearchSession()

