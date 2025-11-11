"""SQLite-backed vector store for research content embeddings."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from loguru import logger

try:  # Optional dependency for faster math
    import numpy as np
except Exception:  # pragma: no cover - fallback when numpy unavailable
    np = None  # type: ignore


@dataclass
class ContentStatus:
    link_id: str
    checksum: str
    embedding_version: int
    updated_at: float


@dataclass
class VectorRecord:
    chunk_id: str
    link_id: str
    chunk_index: int
    chunk_type: str
    scale: str
    embedding: Sequence[float]
    text_preview: str
    metadata: Dict[str, object]


@dataclass
class VectorSearchResult:
    chunk_id: str
    link_id: str
    score: float
    text_preview: str
    metadata: Dict[str, object]


class SQLiteVectorStore:
    """Persist embeddings in SQLite for deterministic, dependency-free ANN."""

    def __init__(self, *, db_path: Path, embedding_dimension: int) -> None:
        self.db_path = db_path
        self.embedding_dimension = embedding_dimension

        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.execute("PRAGMA synchronous=NORMAL;")
        self._create_tables()

    # ------------------------------------------------------------------
    def _create_tables(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS content_items (
                    link_id TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    embedding_version INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    link_id TEXT NOT NULL,
                    chunk_index INTEGER,
                    chunk_type TEXT,
                    scale TEXT,
                    vector BLOB NOT NULL,
                    vector_norm REAL NOT NULL,
                    text_preview TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY(link_id) REFERENCES content_items(link_id) ON DELETE CASCADE
                )
                """
            )

            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_link ON embeddings(link_id);"
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_type ON embeddings(chunk_type);"
            )

    # ------------------------------------------------------------------
    def close(self) -> None:
        self.connection.close()

    # ------------------------------------------------------------------
    def fetch_content_status(self, link_ids: Iterable[str]) -> Dict[str, ContentStatus]:
        link_ids = list(link_ids)
        if not link_ids:
            return {}

        placeholders = ",".join("?" for _ in link_ids)
        query = f"SELECT link_id, checksum, embedding_version, updated_at FROM content_items WHERE link_id IN ({placeholders})"

        cursor = self.connection.execute(query, link_ids)
        rows = cursor.fetchall()

        result: Dict[str, ContentStatus] = {}
        for row in rows:
            result[row[0]] = ContentStatus(
                link_id=row[0],
                checksum=row[1],
                embedding_version=int(row[2]),
                updated_at=float(row[3]),
            )
        return result

    # ------------------------------------------------------------------
    def replace_content_embeddings(
        self,
        *,
        link_id: str,
        records: List[VectorRecord],
        checksum: str,
        embedding_version: int,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO content_items(link_id, checksum, embedding_version, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(link_id) DO UPDATE SET
                    checksum=excluded.checksum,
                    embedding_version=excluded.embedding_version,
                    updated_at=excluded.updated_at
                """,
                (link_id, checksum, embedding_version, time.time()),
            )

            self.connection.execute("DELETE FROM embeddings WHERE link_id = ?", (link_id,))

            insert_stmt = (
                "INSERT INTO embeddings(chunk_id, link_id, chunk_index, chunk_type, scale, vector, vector_norm, text_preview, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )

            for record in records:
                vector_blob, vector_norm = self._serialize_vector(record.embedding)
                self.connection.execute(
                    insert_stmt,
                    (
                        record.chunk_id,
                        record.link_id,
                        record.chunk_index,
                        record.chunk_type,
                        record.scale,
                        vector_blob,
                        vector_norm,
                        record.text_preview,
                        json.dumps(record.metadata, ensure_ascii=False, sort_keys=True),
                    ),
                )

    # ------------------------------------------------------------------
    def search(
        self,
        *,
        query_vector: Sequence[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Iterable[str]]] = None,
    ) -> List[VectorSearchResult]:
        filters = filters or {}
        allowed_link_ids = set(filters.get("link_ids", [])) if filters.get("link_ids") else None
        allowed_chunk_types = set(filters.get("chunk_types", [])) if filters.get("chunk_types") else None

        cursor = self.connection.execute(
            "SELECT chunk_id, link_id, chunk_index, chunk_type, scale, vector, text_preview, metadata_json FROM embeddings"
        )

        results: List[VectorSearchResult] = []
        for row in cursor.fetchall():
            chunk_id, link_id, _, chunk_type, scale, vector_blob, text_preview, metadata_json = row

            if allowed_link_ids and link_id not in allowed_link_ids:
                continue
            if allowed_chunk_types and chunk_type not in allowed_chunk_types:
                continue

            metadata = json.loads(metadata_json or "{}")
            candidate_vector = self._deserialize_vector(vector_blob)

            score = self._cosine_similarity(query_vector, candidate_vector)
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    link_id=link_id,
                    score=score,
                    text_preview=text_preview or "",
                    metadata=metadata,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    def _serialize_vector(self, vector: Sequence[float]) -> Tuple[bytes, float]:
        if np is not None:  # pragma: no branch - depends on numpy availability
            arr = np.asarray(vector, dtype="float32")
            norm = float(np.linalg.norm(arr)) or 1.0
            normalized = arr / norm
            return normalized.tobytes(), 1.0

        # Fallback: JSON encode and compute norm manually
        norm = (sum(float(x) ** 2 for x in vector) or 1.0) ** 0.5
        normalized = [float(x) / norm for x in vector]
        return json.dumps(normalized).encode("utf-8"), 1.0

    def _deserialize_vector(self, payload: bytes) -> List[float]:
        if np is not None:  # pragma: no branch
            arr = np.frombuffer(payload, dtype="float32")
            return arr.astype(float).tolist()
        return [float(x) for x in json.loads(payload.decode("utf-8"))]

    def _cosine_similarity(
        self,
        query: Sequence[float],
        candidate: Sequence[float],
    ) -> float:
        if np is not None:  # pragma: no branch
            q = np.asarray(query, dtype=float)
            c = np.asarray(candidate, dtype=float)
            denom = max((np.linalg.norm(q) or 1.0) * (np.linalg.norm(c) or 1.0), 1e-9)
            return float(np.dot(q, c) / denom)

        # Pure Python fallback
        dot = sum(float(a) * float(b) for a, b in zip(query, candidate))
        query_norm = (sum(float(x) ** 2 for x in query) or 1.0) ** 0.5
        candidate_norm = (sum(float(x) ** 2 for x in candidate) or 1.0) ** 0.5
        denom = max(query_norm * candidate_norm, 1e-9)
        return dot / denom

