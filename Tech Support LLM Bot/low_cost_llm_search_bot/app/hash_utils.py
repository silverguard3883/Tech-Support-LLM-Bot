from hashlib import sha256
from pathlib import Path


def hash_text(text: str) -> str:
    """Return SHA-256 for text content."""
    return sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def hash_file(path: Path) -> str:
    """Return SHA-256 for a file without loading it all at once."""
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
