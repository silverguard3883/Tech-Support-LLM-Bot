import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings


def connect() -> sqlite3.Connection:
    """Open the local SQLite vector store."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes if needed."""
    with connect() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_uri TEXT NOT NULL UNIQUE,
                file_path TEXT,
                content_hash TEXT NOT NULL,
                authority INTEGER NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            """
        )


def get_document_by_source_uri(source_uri: str) -> Optional[sqlite3.Row]:
    """Return a document row by its source URI."""
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE source_uri = ?",
            (source_uri,),
        ).fetchone()


def delete_document(doc_id: str) -> None:
    """Delete a document and its chunks."""
    with connect() as conn:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))


def delete_by_source_type(source_type: str) -> None:
    """Delete all documents for a source type."""
    with connect() as conn:
        rows = conn.execute("SELECT doc_id FROM documents WHERE source_type = ?", (source_type,)).fetchall()
        for row in rows:
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (row["doc_id"],))
        conn.execute("DELETE FROM documents WHERE source_type = ?", (source_type,))


def upsert_document(
    doc_id: str,
    title: str,
    source_type: str,
    source_uri: str,
    file_path: str | None,
    content_hash: str,
    authority: int,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    """Insert or replace a document metadata row."""
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents
            (doc_id, title, source_type, source_uri, file_path, content_hash, authority, status, metadata_json, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                doc_id,
                title,
                source_type,
                source_uri,
                file_path,
                content_hash,
                authority,
                status,
                json.dumps(metadata, ensure_ascii=False),
            ),
        )


def insert_chunks(chunks: List[Dict[str, Any]]) -> int:
    """Insert embedded chunks."""
    if not chunks:
        return 0

    with connect() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, chunk_index, text, embedding_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["chunk_id"],
                    item["doc_id"],
                    item["chunk_index"],
                    item["text"],
                    json.dumps(item["embedding"]),
                    json.dumps(item.get("metadata", {}), ensure_ascii=False),
                )
                for item in chunks
            ],
        )
    return len(chunks)


def list_documents(limit: int = 200) -> List[Dict[str, Any]]:
    """Return a sanitized document inventory."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT doc_id, title, source_type, source_uri, authority, status, indexed_at, metadata_json
            FROM documents
            ORDER BY indexed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    output = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        output.append(item)
    return output


def search_chunks(
    query_embedding: List[float],
    top_k: int,
    source_types: Optional[Iterable[str]] = None,
    min_similarity: float = 0.0,
) -> List[Dict[str, Any]]:
    """Brute-force cosine search over local SQLite embeddings."""
    source_filter = list(source_types or [])

    with connect() as conn:
        if source_filter:
            placeholders = ",".join("?" for _ in source_filter)
            rows = conn.execute(
                f"""
                SELECT c.*, d.title, d.source_type, d.source_uri, d.authority, d.status, d.metadata_json AS doc_metadata_json
                FROM chunks c
                JOIN documents d ON d.doc_id = c.doc_id
                WHERE d.source_type IN ({placeholders}) AND d.status = 'approved'
                """,
                tuple(source_filter),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.*, d.title, d.source_type, d.source_uri, d.authority, d.status, d.metadata_json AS doc_metadata_json
                FROM chunks c
                JOIN documents d ON d.doc_id = c.doc_id
                WHERE d.status = 'approved'
                """
            ).fetchall()

    scored = []
    for row in rows:
        embedding = json.loads(row["embedding_json"])
        similarity = cosine_similarity(query_embedding, embedding)
        if similarity < min_similarity:
            continue

        chunk_metadata = json.loads(row["metadata_json"] or "{}")
        doc_metadata = json.loads(row["doc_metadata_json"] or "{}")
        scored.append(
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "chunk_index": row["chunk_index"],
                "text": row["text"],
                "title": row["title"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "authority": row["authority"],
                "similarity": similarity,
                "metadata": {**doc_metadata, **chunk_metadata},
            }
        )

    scored.sort(key=lambda item: (item["similarity"], item["authority"]), reverse=True)
    return scored[:top_k]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    """Compute cosine similarity for two vectors."""
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
