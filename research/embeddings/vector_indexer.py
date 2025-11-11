"""Vector indexer for Phase 0 embedding pipeline."""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger

from core.config import Config
from research.embeddings.embedding_client import EmbeddingClient, EmbeddingConfig
from research.vector_store.sqlite_vector_store import SQLiteVectorStore, VectorRecord


def _default_config() -> Dict[str, int]:
    return {
        "chunk_default_tokens": 750,
        "chunk_min_tokens": 400,
        "chunk_overlap_tokens": 150,
        "document_chunk_tokens": 1200,
    }


@dataclass
class IndexerSettings:
    embedding_version: int = 1
    chunk_default_tokens: int = 750
    chunk_min_tokens: int = 400
    chunk_overlap_tokens: int = 150
    document_chunk_tokens: int = 1200
    enable_indexing: bool = True
    max_preview_chars: int = 320
    max_text_chars: int = 12000
    embedding_batch_size: int = 16


@dataclass
class ChunkCandidate:
    link_id: str
    chunk_id: str
    chunk_index: int
    chunk_type: str  # transcript|comments|document
    scale: str  # coarse|fine
    text: str
    metadata: Dict[str, Any]
    text_preview: str = ""
    embedding: Optional[List[float]] = None


class VectorIndexer:
    """Prepare chunked embeddings and persist them into the vector store."""

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        vector_store: Optional[SQLiteVectorStore] = None,
    ) -> None:
        self.config = config or Config()
        self.settings = self._load_settings()

        embedding_cfg = self._load_embedding_config()
        self.embedding_client = embedding_client or EmbeddingClient(embedding_cfg)

        self.vector_store = vector_store or SQLiteVectorStore(
            db_path=self._resolve_store_path(),
            embedding_dimension=embedding_cfg.dimension,
        )

    # ------------------------------------------------------------------
    def _load_settings(self) -> IndexerSettings:
        research_cfg = self.config.get("research", {}) or {}
        embeddings_cfg = research_cfg.get("embeddings", {}) or {}

        defaults = _default_config()

        return IndexerSettings(
            embedding_version=int(embeddings_cfg.get("version", 1)),
            chunk_default_tokens=int(embeddings_cfg.get("chunk", {}).get("default_tokens", defaults["chunk_default_tokens"])),
            chunk_min_tokens=int(embeddings_cfg.get("chunk", {}).get("min_tokens", defaults["chunk_min_tokens"])),
            chunk_overlap_tokens=int(embeddings_cfg.get("chunk", {}).get("overlap_tokens", defaults["chunk_overlap_tokens"])),
            document_chunk_tokens=int(embeddings_cfg.get("chunk", {}).get("document_tokens", defaults["document_chunk_tokens"])),
            enable_indexing=bool(embeddings_cfg.get("enable", True)),
            max_preview_chars=int(embeddings_cfg.get("max_preview_chars", 320)),
            max_text_chars=int(embeddings_cfg.get("max_text_chars", 12000)),
            embedding_batch_size=int(embeddings_cfg.get("batch_size", 16)),
        )

    def _load_embedding_config(self) -> EmbeddingConfig:
        research_cfg = self.config.get("research", {}) or {}
        embeddings_cfg = research_cfg.get("embeddings", {}) or {}

        return EmbeddingConfig(
            provider=embeddings_cfg.get("provider", "hash"),
            model=embeddings_cfg.get("model", "text-embedding-v1"),
            dimension=int(embeddings_cfg.get("dimension", 768)),
            batch_size=int(embeddings_cfg.get("batch_size", 16)),
            timeout=int(embeddings_cfg.get("timeout", 45)),
            base_url=embeddings_cfg.get("base_url"),
        )

    def _resolve_store_path(self) -> Path:
        base_dir = self.config.get("research.embeddings.store.path", "data/vector_store")
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / "embeddings.sqlite"

    # ------------------------------------------------------------------
    def index_batch(self, batch_id: str, batch_data: Dict[str, Dict[str, Any]]) -> None:
        if not self.settings.enable_indexing:
            logger.info("[PHASE0-INDEX] Embedding indexing disabled via config; skipping batch %s", batch_id)
            return

        t0 = time.time()
        logger.info("[PHASE0-INDEX] Starting embedding index for batch %s (%s items)", batch_id, len(batch_data))

        # Determine which items need re-indexing by comparing checksums
        content_checksums = {
            link_id: self._compute_checksum(data)
            for link_id, data in batch_data.items()
        }

        status_map = self.vector_store.fetch_content_status(list(batch_data.keys()))

        to_index: Dict[str, List[ChunkCandidate]] = {}
        for link_id, data in batch_data.items():
            checksum = content_checksums.get(link_id)
            status = status_map.get(link_id)

            if status and status.checksum == checksum and status.embedding_version == self.settings.embedding_version:
                logger.debug("[PHASE0-INDEX] Skipping %s (checksum unchanged, version %s)", link_id, status.embedding_version)
                continue

            candidates = self._build_candidates(link_id, data, batch_id=batch_id)
            if not candidates:
                logger.debug("[PHASE0-INDEX] No chunk candidates generated for %s", link_id)
                continue

            to_index[link_id] = candidates

        if not to_index:
            logger.info("[PHASE0-INDEX] All content already indexed; nothing to do for batch %s", batch_id)
            return

        # Embed candidates in batches
        all_candidates = [c for cand_list in to_index.values() for c in cand_list]
        self._embed_candidates(all_candidates)

        # Persist per content item
        for link_id, candidates in to_index.items():
            checksum = content_checksums[link_id]
            records = [
                VectorRecord(
                    chunk_id=c.chunk_id,
                    link_id=c.link_id,
                    chunk_index=c.chunk_index,
                    chunk_type=c.chunk_type,
                    scale=c.scale,
                    embedding=c.embedding or [],
                    text_preview=c.text_preview,
                    metadata=c.metadata,
                )
                for c in candidates
            ]

            self.vector_store.replace_content_embeddings(
                link_id=link_id,
                records=records,
                checksum=checksum,
                embedding_version=self.settings.embedding_version,
            )

        elapsed = time.time() - t0
        logger.info(
            "[PHASE0-INDEX] Finished embedding index for batch %s in %.2fs (indexed %s items)",
            batch_id,
            elapsed,
            len(to_index),
        )

    # ------------------------------------------------------------------
    def _embed_candidates(self, candidates: List[ChunkCandidate]) -> None:
        batch_size = max(1, min(self.settings.embedding_batch_size, self.embedding_client.batch_size))
        texts: List[str] = []
        bucket: List[ChunkCandidate] = []

        for candidate in candidates:
            texts.append(candidate.text)
            bucket.append(candidate)

            if len(texts) >= batch_size:
                embeddings = self.embedding_client.embed_texts(texts)
                for cand, emb in zip(bucket, embeddings):
                    cand.embedding = emb
                texts.clear()
                bucket.clear()

        if texts:
            embeddings = self.embedding_client.embed_texts(texts)
            for cand, emb in zip(bucket, embeddings):
                cand.embedding = emb

    # ------------------------------------------------------------------
    def _build_candidates(self, link_id: str, data: Dict[str, Any], *, batch_id: str) -> List[ChunkCandidate]:
        candidates: List[ChunkCandidate] = []
        metadata_base = {
            "link_id": link_id,
            "source": data.get("source"),
            "language": ((data.get("metadata") or {}).get("language") if isinstance(data.get("metadata"), dict) else None),
            "batch_id": batch_id,
        }

        transcript = data.get("transcript") or ""
        comments = data.get("comments") or []
        summary = data.get("summary") or {}

        # Document-level summary chunk (coarse)
        document_text = self._build_document_text(transcript, summary)
        if document_text:
            chunk_id = f"{link_id}::doc"
            candidates.append(
                ChunkCandidate(
                    link_id=link_id,
                    chunk_id=chunk_id,
                    chunk_index=-1,
                    chunk_type="document",
                    scale="coarse",
                    text=document_text,
                    text_preview=document_text[: self.settings.max_preview_chars],
                    metadata={**metadata_base, "chunk_scope": "document"},
                )
            )

        # Transcript chunks (fine)
        if transcript:
            tokens = transcript.split()
            chunk_size = max(self.settings.chunk_min_tokens, self.settings.chunk_default_tokens)
            overlap = min(self.settings.chunk_overlap_tokens, max(1, int(chunk_size * 0.25)))
            stride = max(1, chunk_size - overlap)

            for idx, start in enumerate(range(0, len(tokens), stride)):
                end = min(len(tokens), start + chunk_size)
                chunk_tokens = tokens[start:end]
                if len(chunk_tokens) < self.settings.chunk_min_tokens and idx != 0 and candidates:
                    # merge with previous chunk text to avoid tiny tail
                    previous = candidates[-1]
                    previous_span = list(previous.metadata.get("token_span", [0, start]))
                    previous_text = f"{previous.text} {' '.join(chunk_tokens)}"
                    previous.text = self._clip_text(previous_text)
                    previous.text_preview = previous.text[: self.settings.max_preview_chars]
                    previous.metadata["token_span"] = [previous_span[0], end]
                    break

                chunk_text = " ".join(chunk_tokens)
                chunk_id = f"{link_id}::transcript::{idx}"
                metadata = {
                    **metadata_base,
                    "chunk_scope": "transcript",
                    "token_span": [start, end],
                    "marker_types": list(self._collect_marker_types(summary.get("transcript_summary", {}))),
                }

                candidates.append(
                    ChunkCandidate(
                        link_id=link_id,
                        chunk_id=chunk_id,
                        chunk_index=idx,
                        chunk_type="transcript",
                        scale="fine",
                        text=self._clip_text(chunk_text),
                        text_preview=chunk_text[: self.settings.max_preview_chars],
                        metadata=metadata,
                    )
                )

                if end >= len(tokens):
                    break

        # Comments chunk (optional, treat as coarse)
        if comments:
            comments_text = self._build_comments_text(comments)
            if comments_text:
                chunk_id = f"{link_id}::comments"
                candidates.append(
                    ChunkCandidate(
                        link_id=link_id,
                        chunk_id=chunk_id,
                        chunk_index=-1,
                        chunk_type="comments",
                        scale="coarse",
                        text=self._clip_text(comments_text),
                        text_preview=comments_text[: self.settings.max_preview_chars],
                        metadata={
                            **metadata_base,
                            "chunk_scope": "comments",
                            "marker_types": list(self._collect_marker_types(summary.get("comments_summary", {}))),
                        },
                    )
                )

        return candidates

    # ------------------------------------------------------------------
    @staticmethod
    def _collect_marker_types(summary_section: Dict[str, Any]) -> Iterable[str]:
        if not summary_section:
            return []
        types = []
        for key, value in summary_section.items():
            if isinstance(value, list) and value:
                types.append(key)
        return types

    def _clip_text(self, text: str) -> str:
        if len(text) <= self.settings.max_text_chars:
            return text
        return text[: self.settings.max_text_chars] + "\n[...截断以符合长度限制...]"

    def _build_document_text(self, transcript: str, summary: Dict[str, Any]) -> str:
        parts: List[str] = []
        summary_section = summary.get("transcript_summary") or {}

        if summary_section:
            for key in ("key_facts", "key_opinions", "key_datapoints"):
                values = summary_section.get(key)
                if isinstance(values, list) and values:
                    parts.extend(str(v) for v in values[:10])

        if transcript and len(transcript.split()) < self.settings.document_chunk_tokens:
            parts.append(transcript)
        elif transcript:
            tokens = transcript.split()
            head = tokens[: self.settings.document_chunk_tokens]
            tail = tokens[-self.settings.document_chunk_tokens :]
            parts.append(" ".join(head + ["..."] + tail))

        document_text = "\n".join(parts).strip()
        return self._clip_text(document_text)

    @staticmethod
    def _build_comments_text(comments: Iterable) -> str:
        lines: List[str] = []
        for idx, comment in enumerate(comments):
            if isinstance(comment, dict):
                content = comment.get("content") or comment.get("text") or ""
                likes = comment.get("likes", 0)
                replies = comment.get("replies", 0)
                lines.append(f"[{idx}] (likes:{likes}, replies:{replies}) {content}")
            else:
                lines.append(f"[{idx}] {comment}")
        return "\n".join(lines)

    def _compute_checksum(self, data: Dict[str, any]) -> str:
        payload = {
            "transcript": data.get("transcript") or "",
            "comments": data.get("comments") or [],
            "summary": data.get("summary") or {},
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

