"""Vector retrieval utilities for Phase 3 semantic search."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from loguru import logger

from core.config import Config
from research.embeddings.embedding_client import EmbeddingClient, EmbeddingConfig
from research.vector_store.sqlite_vector_store import SQLiteVectorStore, VectorSearchResult


@dataclass
class RetrievalFilters:
    link_ids: Optional[List[str]] = None
    chunk_types: Optional[List[str]] = None


class VectorRetrievalService:
    """High-level API for vector similarity queries with caching."""

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        embedding_client: Optional[EmbeddingClient] = None,
        vector_store: Optional[SQLiteVectorStore] = None,
    ) -> None:
        self.config = config or Config()
        embeddings_cfg = self.config.get("research.embeddings", {}) or {}
        self.enabled = bool(embeddings_cfg.get("enable", True))
        self.top_k_default = int(embeddings_cfg.get("search", {}).get("top_k", 30))
        self.max_context_chars = int(embeddings_cfg.get("search", {}).get("max_context_chars", 4000))

        embedding_cfg = EmbeddingConfig(
            provider=embeddings_cfg.get("provider", "hash"),
            model=embeddings_cfg.get("model", "text-embedding-v1"),
            dimension=int(embeddings_cfg.get("dimension", 768)),
            batch_size=int(embeddings_cfg.get("batch_size", 16)),
            timeout=int(embeddings_cfg.get("timeout", 45)),
            base_url=embeddings_cfg.get("base_url"),
        )

        self.embedding_client = embedding_client or EmbeddingClient(embedding_cfg)
        self.vector_store = vector_store or SQLiteVectorStore(
            db_path=self._resolve_store_path(),
            embedding_dimension=embedding_cfg.dimension,
        )

        self._cache: Dict[str, List[VectorSearchResult]] = {}

        logger.info(
            "[PHASE3-VECTOR] Vector retrieval service initialized (enabled=%s)",
            self.enabled,
        )

    def _resolve_store_path(self):
        from pathlib import Path

        base_dir = self.config.get("research.embeddings.store.path", "data/vector_store")
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / "embeddings.sqlite"

    # ------------------------------------------------------------------
    def search(
        self,
        query_text: str,
        *,
        filters: Optional[RetrievalFilters] = None,
        top_k: Optional[int] = None,
    ) -> List[VectorSearchResult]:
        if not self.enabled:
            logger.debug("[PHASE3-VECTOR] Vector retrieval disabled; returning empty result")
            return []

        query_text = (query_text or "").strip()
        if not query_text:
            return []

        cache_key = self._cache_key(query_text, filters, top_k)
        if cache_key in self._cache:
            logger.debug("[PHASE3-VECTOR] Cache hit for query '%s'", query_text[:50])
            return self._cache[cache_key]

        embedding = self.embedding_client.embed_texts([query_text])
        if not embedding:
            return []

        filter_dict = {}
        if filters:
            if filters.link_ids:
                filter_dict["link_ids"] = filters.link_ids
            if filters.chunk_types:
                filter_dict["chunk_types"] = filters.chunk_types

        results = self.vector_store.search(
            query_vector=embedding[0],
            top_k=top_k or self.top_k_default,
            filters=filter_dict,
        )

        self._cache[cache_key] = results
        logger.info(
            "[PHASE3-VECTOR] Semantic search '%s' → %s candidates",
            query_text[:60],
            len(results),
        )
        return results

    # ------------------------------------------------------------------
    def format_results(self, results: Iterable[VectorSearchResult]) -> str:
        if not results:
            return "(No semantic matches found)"

        parts: List[str] = []
        total_chars = 0

        for idx, result in enumerate(results, 1):
            header = f"[Vector Match #{idx}] link_id={result.link_id} score={result.score:.3f} chunk_id={result.chunk_id}"
            metadata_lines = []
            metadata = result.metadata or {}
            for key in sorted(metadata.keys()):
                value = metadata[key]
                if isinstance(value, (list, tuple)):
                    display = ", ".join(str(v) for v in value[:10])
                else:
                    display = str(value)
                metadata_lines.append(f"  - {key}: {display}")

            body = result.text_preview or "(no preview available)"
            block = "\n".join([header, *metadata_lines, "---", body])

            if total_chars + len(block) > self.max_context_chars:
                break

            parts.append(block)
            total_chars += len(block)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    @staticmethod
    def _cache_key(query_text: str, filters: Optional[RetrievalFilters], top_k: Optional[int]) -> str:
        payload = {
            "q": query_text,
            "link_ids": filters.link_ids if filters else None,
            "chunk_types": filters.chunk_types if filters else None,
            "top_k": top_k,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

