from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    assistant_name: str = "Cybersecurity AI Assistant"
    department: str = "Cybersecurity"

    enable_api_key_auth: bool = True
    api_key: str = "change-me"

    base_dir: Path = Path("C:/RAGAssistant")
    documents_dir: Path = Path("C:/RAGAssistant/data/documents")
    db_path: Path = Path("C:/RAGAssistant/data/sqlite/rag_store.db")
    log_dir: Path = Path("C:/RAGAssistant/data/logs")
    quarantine_dir: Path = Path("C:/RAGAssistant/data/quarantine")

    host: str = "127.0.0.1"
    port: int = 8088

    ollama_base_url: str = "http://127.0.0.1:11434"
    chat_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    chat_keep_alive: str = "3m"
    embedding_keep_alive: str = "1m"

    top_k: int = 8
    min_similarity: float = 0.15
    max_context_chars: int = 16000
    max_question_chars: int = 4000
    num_ctx: int = 8192
    num_predict: int = 1200
    temperature: float = 0.1
    max_concurrent_inference: int = 1

    enable_web_crawl: bool = False
    enable_searxng_search: bool = False
    searxng_base_url: str = "http://127.0.0.1:8080"
    allowed_web_domains: str = ""
    blocked_web_domains: str = ""
    allow_private_network_crawl: bool = False
    respect_robots_txt: bool = True
    max_crawl_pages: int = 10
    max_crawl_depth: int = 1
    max_page_bytes: int = 2 * 1024 * 1024
    web_request_timeout_seconds: int = 15
    crawl_delay_seconds: float = 1.0
    crawl_user_agent: str = "CyberRAGBot/0.1 internal pilot"

    redact_secrets: bool = True
    skip_files_with_secrets: bool = True
    rate_limit_requests_per_minute: int = 30

    supported_file_extensions: List[str] = Field(
        default_factory=lambda: [".txt", ".md", ".csv", ".html", ".htm", ".pdf", ".docx"]
    )

    def allowed_domains(self) -> set[str]:
        """Return normalized allowed crawl domains from CSV config."""
        return {item.strip().lower() for item in self.allowed_web_domains.split(",") if item.strip()}

    def blocked_domains(self) -> set[str]:
        """Return normalized blocked crawl domains from CSV config."""
        return {item.strip().lower() for item in self.blocked_web_domains.split(",") if item.strip()}

    def ensure_directories(self) -> None:
        """Create required directories if they do not already exist."""
        for path in [self.documents_dir, self.db_path.parent, self.log_dir, self.quarantine_dir]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
