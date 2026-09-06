import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import List, Set
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.document_parsers import parse_html_text
from app.guardrails import validate_url_for_crawl
from app.hash_utils import hash_text
from app.indexing import index_text_source

logger = logging.getLogger(__name__)


@dataclass
class WebPage:
    """Scraped page content."""

    url: str
    title: str
    text: str
    content_hash: str


def _robots_allowed(url: str) -> bool:
    """Check robots.txt when configured."""
    if not settings.respect_robots_txt:
        return True

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)

    try:
        parser.read()
        return parser.can_fetch(settings.crawl_user_agent, url)
    except Exception:
        return False


def _download(url: str) -> str:
    """Download a page with size and timeout limits."""
    headers = {"User-Agent": settings.crawl_user_agent}
    with requests.get(url, headers=headers, stream=True, timeout=settings.web_request_timeout_seconds) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type}")

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=65536, decode_unicode=True):
            if not chunk:
                continue
            total += len(chunk.encode("utf-8", errors="ignore"))
            if total > settings.max_page_bytes:
                raise ValueError("Page exceeds maximum allowed size.")
            chunks.append(chunk)
        return "".join(chunks)


def _extract_links(html: str, base_url: str, seed_host: str) -> List[str]:
    """Extract safe, same-domain links from a page."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        absolute = urljoin(base_url, href)
        absolute, _fragment = urldefrag(absolute)
        verdict = validate_url_for_crawl(absolute, seed_host=seed_host)
        if verdict.allowed:
            links.append(absolute)

    return links


def scrape_page(url: str, seed_host: str | None = None) -> WebPage:
    """Fetch and extract readable text from one URL."""
    seed_host = seed_host or urlparse(url).hostname or ""
    verdict = validate_url_for_crawl(url, seed_host=seed_host)
    if not verdict.allowed:
        raise ValueError(verdict.reason)

    if not _robots_allowed(url):
        raise ValueError("robots.txt disallows crawling this URL.")

    html = _download(url)
    parsed = parse_html_text(html, fallback_title=url)
    return WebPage(
        url=url,
        title=parsed.title,
        text=parsed.text,
        content_hash=hash_text(html),
    )


def crawl(seed_urls: List[str], max_pages: int | None = None, max_depth: int | None = None) -> dict:
    """Breadth-first crawl from approved seed URLs."""
    if not settings.enable_web_crawl:
        raise ValueError("Web crawling is disabled in configuration.")

    page_limit = min(max_pages or settings.max_crawl_pages, settings.max_crawl_pages)
    depth_limit = min(max_depth if max_depth is not None else settings.max_crawl_depth, settings.max_crawl_depth)

    queue = deque()
    visited: Set[str] = set()
    blocked: list[str] = []
    errors: list[dict[str, str]] = []
    pages: list[WebPage] = []

    for seed in seed_urls:
        seed_text = str(seed)
        seed_host = urlparse(seed_text).hostname or ""
        verdict = validate_url_for_crawl(seed_text, seed_host=seed_host)
        if verdict.allowed:
            queue.append((seed_text, 0, seed_host))
        else:
            blocked.append(f"{seed_text}: {verdict.reason}")

    while queue and len(pages) < page_limit:
        url, depth, seed_host = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            verdict = validate_url_for_crawl(url, seed_host=seed_host)
            if not verdict.allowed:
                blocked.append(f"{url}: {verdict.reason}")
                continue

            if not _robots_allowed(url):
                blocked.append(f"{url}: blocked by robots.txt")
                continue

            html = _download(url)
            parsed = parse_html_text(html, fallback_title=url)
            page = WebPage(url=url, title=parsed.title, text=parsed.text, content_hash=hash_text(html))

            if page.text.strip():
                pages.append(page)

            if depth < depth_limit:
                for link in _extract_links(html, url, seed_host):
                    if link not in visited:
                        queue.append((link, depth + 1, seed_host))

            time.sleep(settings.crawl_delay_seconds)

        except Exception as exc:
            logger.warning("Failed to crawl %s: %s", url, exc)
            errors.append({"url": url, "error": str(exc)})

    return {"pages": pages, "blocked": blocked, "errors": errors}


def index_web_pages(pages: List[WebPage]) -> int:
    """Index scraped pages as low-authority web evidence."""
    indexed = 0
    for page in pages:
        result = index_text_source(
            title=page.title,
            source_type="web",
            source_uri=page.url,
            text=page.text,
            authority=20,
            content_hash=page.content_hash,
            metadata={
                "classification": "External/Public or Internal Web",
                "source_status": "untrusted_web",
            },
        )
        if result["status"] == "indexed":
            indexed += 1
    return indexed
