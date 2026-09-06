# Low-Cost Local LLM Search Bot

This project is a starter implementation for a low-cost, local-first cybersecurity RAG assistant running on Windows Server 2025 Standard.

It uses:

- Python FastAPI for the backend
- Ollama for local chat and embedding models
- SQLite as a cheap local vector store
- Local document ingestion for `.txt`, `.md`, `.csv`, `.html`, `.pdf`, and `.docx`
- Optional controlled web crawling and scraping
- Guardrails for source isolation, crawl restrictions, secret detection, rate limiting, and grounded answers

## Quick start on Windows

1. Copy this folder to `C:\RAGAssistant`.
2. Copy `.env.example` to `.env` and set `API_KEY`.
3. Run `scripts\create_folders.ps1`.
4. Install Ollama and pull your models:
   ```powershell
   ollama pull llama3.1
   ollama pull nomic-embed-text
   ```
5. Run `scripts\install_requirements.ps1`.
6. Put approved cybersecurity documents in `C:\RAGAssistant\data\documents`.
7. Start the backend with `scripts\run_backend.ps1`.
8. Open `http://127.0.0.1:8088` on the server.
9. Call `/api/admin/ingest` to index documents.
10. Place IIS with HTTPS in front of this app for internal users.

## Important defaults

- Web crawling is disabled until `ENABLE_WEB_CRAWL=true`.
- SearXNG search is disabled until `ENABLE_SEARXNG_SEARCH=true`.
- Cross-domain crawling is disabled unless an allowlist is configured.
- Private network crawling is blocked by default to reduce SSRF risk.
- Files that appear to contain secrets are skipped by default.
- The vector store is SQLite, which is cheap and simple but not optimized for large-scale search.
