import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import sqlite_store
from app.config import settings
from app.ingestion import ingest_documents
from app.logging_config import configure_logging
from app.models import (
    CrawlRequest,
    CrawlResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from app.ollama_client import health_check, unload_model
from app.rag import answer_question
from app.security import require_api_key
from app.web_scraper import crawl, index_web_pages

configure_logging()
logger = logging.getLogger(__name__)
sqlite_store.init_db()

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(
    title=settings.assistant_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def ui() -> FileResponse:
    """Serve the simple internal web interface."""
    return FileResponse(INDEX_HTML)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return basic application health."""
    return HealthResponse(
        status="ok",
        assistant_name=settings.assistant_name,
        department=settings.department,
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
    )


@app.get("/api/ollama", dependencies=[Depends(require_api_key)])
def ollama_status() -> dict:
    """Return local Ollama model status for administrators."""
    return health_check()


@app.post("/api/query", response_model=QueryResponse, dependencies=[Depends(require_api_key)])
def query(request: QueryRequest) -> dict:
    """Answer a user question with local RAG."""
    logger.info("Query received mode=%s live_web=%s", request.mode, request.use_live_web)
    return answer_question(request)


@app.post("/api/admin/ingest", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
def ingest(request: IngestRequest) -> dict:
    """Index approved files from the documents directory."""
    return ingest_documents(reset_file_sources=request.reset_file_sources)


@app.get("/api/admin/sources", dependencies=[Depends(require_api_key)])
def sources() -> list[dict]:
    """List indexed sources for troubleshooting."""
    return sqlite_store.list_documents()


@app.post("/api/admin/web/crawl", response_model=CrawlResponse, dependencies=[Depends(require_api_key)])
def crawl_endpoint(request: CrawlRequest) -> dict:
    """Crawl approved web URLs and optionally index them."""
    result = crawl(
        seed_urls=[str(url) for url in request.seed_urls],
        max_pages=request.max_pages,
        max_depth=request.max_depth,
    )
    pages_indexed = index_web_pages(result["pages"]) if request.index_results else 0
    return {
        "pages_fetched": len(result["pages"]),
        "pages_indexed": pages_indexed,
        "blocked": result["blocked"],
        "errors": result["errors"],
    }


@app.post("/api/admin/unload", dependencies=[Depends(require_api_key)])
def unload() -> dict:
    """Unload configured Ollama models to reduce idle memory use."""
    unload_model(settings.chat_model)
    unload_model(settings.embedding_model)
    return {"status": "unload_requested"}
