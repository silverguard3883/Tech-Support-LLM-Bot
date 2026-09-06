import logging
from typing import Any, Dict, List, Optional

from app.chunker import chunk_text
from app.guardrails import contains_secret, has_prompt_injection, redact_secrets
from app.hash_utils import hash_text
from app.ollama_client import embed_texts
from app import sqlite_store
from app.config import settings

logger = logging.getLogger(__name__)


EMBED_BATCH_SIZE = 16


def index_text_source(
    title: str,
    source_type: str,
    source_uri: str,
    text: str,
    authority: int,
    metadata: Optional[Dict[str, Any]] = None,
    file_path: str | None = None,
    content_hash: str | None = None,
    status: str = "approved",
) -> dict:
    """Chunk, embed, and store one text source."""
    metadata = metadata or {}
    content_hash = content_hash or hash_text(text)

    existing = sqlite_store.get_document_by_source_uri(source_uri)
    if existing and existing["content_hash"] == content_hash:
        return {"status": "skipped", "reason": "unchanged", "chunks_indexed": 0}

    if settings.skip_files_with_secrets and contains_secret(text):
        return {"status": "skipped", "reason": "possible_secret", "chunks_indexed": 0}

    safe_text = redact_secrets(text)
    prompt_injection_flag = has_prompt_injection(safe_text)
    chunks = chunk_text(safe_text)

    if not chunks:
        return {"status": "skipped", "reason": "empty_text", "chunks_indexed": 0}

    doc_id = hash_text(source_uri)
    if existing:
        sqlite_store.delete_document(existing["doc_id"])

    doc_metadata = {
        "department": settings.department,
        "prompt_injection_flag": prompt_injection_flag,
        **metadata,
    }

    sqlite_store.upsert_document(
        doc_id=doc_id,
        title=title[:500],
        source_type=source_type,
        source_uri=source_uri,
        file_path=file_path,
        content_hash=content_hash,
        authority=authority,
        status=status,
        metadata=doc_metadata,
    )

    total_inserted = 0
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start:start + EMBED_BATCH_SIZE]
        texts = [chunk.text for chunk in batch]
        embeddings = embed_texts(texts)

        records: List[Dict[str, Any]] = []
        for chunk, embedding in zip(batch, embeddings):
            chunk_id = hash_text(f"{doc_id}:{chunk.index}:{content_hash}")
            records.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_chars": len(chunk.text),
                    },
                }
            )

        total_inserted += sqlite_store.insert_chunks(records)

    logger.info("Indexed source title=%s chunks=%s", title, total_inserted)
    return {"status": "indexed", "chunks_indexed": total_inserted}
