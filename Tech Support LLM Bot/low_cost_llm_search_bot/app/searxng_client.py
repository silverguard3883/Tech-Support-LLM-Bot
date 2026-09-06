import logging
from typing import List

import requests

from app.config import settings
from app.guardrails import validate_url_for_crawl

logger = logging.getLogger(__name__)


def search(query: str, limit: int = 5) -> List[str]:
    """Search a self-hosted SearXNG instance and return safe result URLs."""
    if not settings.enable_searxng_search:
        return []

    url = f"{settings.searxng_base_url.rstrip('/')}/search"
    response = requests.get(
        url,
        params={"q": query, "format": "json"},
        timeout=settings.web_request_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()

    output: list[str] = []
    for result in data.get("results", []):
        candidate = result.get("url")
        if not candidate:
            continue
        verdict = validate_url_for_crawl(candidate)
        if verdict.allowed:
            output.append(candidate)
        else:
            logger.info("Blocked SearXNG result %s: %s", candidate, verdict.reason)
        if len(output) >= limit:
            break

    return output
