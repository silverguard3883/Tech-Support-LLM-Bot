from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from app.config import settings


class SearchMode(str, Enum):
    """Controls which source types are searched."""

    internal_only = "internal_only"
    web_only = "web_only"
    internal_plus_web = "internal_plus_web"


class QueryRequest(BaseModel):
    """User question payload."""

    question: str = Field(min_length=3, max_length=settings.max_question_chars)
    mode: SearchMode = SearchMode.internal_only
    use_live_web: bool = False
    seed_urls: List[HttpUrl] = Field(default_factory=list)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    """Sanitized source returned to the user."""

    label: str
    title: str
    source_type: str
    source_uri: str
    chunk_index: int
    similarity: float
    authority: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Answer plus the evidence used to produce it."""

    answer: str
    sources: List[Source]
    mode: SearchMode
    insufficient_evidence: bool = False


class IngestRequest(BaseModel):
    """Controls document ingestion."""

    reset_file_sources: bool = False


class IngestResponse(BaseModel):
    """Ingestion summary."""

    files_seen: int
    files_indexed: int
    files_skipped: int
    chunks_indexed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)


class CrawlRequest(BaseModel):
    """Web-crawl request for approved websites."""

    seed_urls: List[HttpUrl] = Field(min_length=1)
    max_pages: Optional[int] = Field(default=None, ge=1, le=50)
    max_depth: Optional[int] = Field(default=None, ge=0, le=3)
    index_results: bool = True


class CrawlResponse(BaseModel):
    """Web-crawl summary."""

    pages_fetched: int
    pages_indexed: int
    blocked: List[str] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    assistant_name: str
    department: str
    chat_model: str
    embedding_model: str
