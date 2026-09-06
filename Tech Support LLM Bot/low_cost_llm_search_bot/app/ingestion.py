import logging
from pathlib import Path

from app import sqlite_store
from app.config import settings
from app.document_parsers import parse_file
from app.hash_utils import hash_file
from app.indexing import index_text_source

logger = logging.getLogger(__name__)


def _is_inside_directory(path: Path, parent: Path) -> bool:
    """Prevent path traversal outside the configured documents directory."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ingest_documents(reset_file_sources: bool = False) -> dict:
    """Index supported files from the configured documents directory."""
    sqlite_store.init_db()

    if reset_file_sources:
        sqlite_store.delete_by_source_type("file")

    files_seen = 0
    files_indexed = 0
    files_skipped = 0
    chunks_indexed = 0
    errors: list[dict[str, str]] = []

    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    allowed_extensions = {ext.lower() for ext in settings.supported_file_extensions}

    for path in settings.documents_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_extensions:
            continue

        files_seen += 1

        if not _is_inside_directory(path, settings.documents_dir):
            files_skipped += 1
            errors.append({"file": str(path), "error": "Path is outside documents directory."})
            continue

        try:
            parsed = parse_file(path)
            source_uri = f"file:///{path.resolve().as_posix()}"
            content_hash = hash_file(path)
            result = index_text_source(
                title=parsed.title,
                source_type="file",
                source_uri=source_uri,
                text=parsed.text,
                authority=100,
                metadata={
                    "file_name": path.name,
                    "file_extension": path.suffix.lower(),
                    "parser": parsed.metadata.get("parser"),
                    "document_owner": "Cybersecurity",
                    "classification": "Internal",
                    "source_status": "approved",
                },
                file_path=str(path.resolve()),
                content_hash=content_hash,
            )

            if result["status"] == "indexed":
                files_indexed += 1
                chunks_indexed += result["chunks_indexed"]
            else:
                files_skipped += 1

        except Exception as exc:
            logger.exception("Failed to ingest file: %s", path)
            files_skipped += 1
            errors.append({"file": str(path), "error": str(exc)})

    return {
        "files_seen": files_seen,
        "files_indexed": files_indexed,
        "files_skipped": files_skipped,
        "chunks_indexed": chunks_indexed,
        "errors": errors,
    }
