from dataclasses import dataclass


@dataclass
class TextChunk:
    """A chunk of source text prepared for embedding."""

    index: int
    text: str


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 250) -> list[TextChunk]:
    """Split text into overlapping chunks using paragraph boundaries when possible."""
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, chunk_size, overlap))
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    return [TextChunk(index=i, text=chunk) for i, chunk in enumerate(_add_overlap(chunks, overlap))]


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split very long paragraphs by character count."""
    output = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        output.append(text[start:end].strip())
        next_start = end - overlap
        start = next_start if next_start > start else end
    return [item for item in output if item]


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Prefix each chunk with a small tail from the previous chunk."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    output = [chunks[0]]
    for i in range(1, len(chunks)):
        previous_tail = chunks[i - 1][-overlap:]
        output.append(f"{previous_tail}\n\n{chunks[i]}")
    return output
