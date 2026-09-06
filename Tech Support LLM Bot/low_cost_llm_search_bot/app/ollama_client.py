import logging
from typing import Iterable, List

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Raised when the local Ollama service returns an error."""


def _post_json(path: str, payload: dict, timeout: int) -> dict:
    """POST JSON to Ollama and return JSON response."""
    url = f"{settings.ollama_base_url.rstrip('/')}{path}"
    response = requests.post(url, json=payload, timeout=timeout)
    if response.status_code >= 400:
        raise OllamaError(f"Ollama error {response.status_code}: {response.text[:500]}")
    return response.json()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Create embeddings with Ollama's local embedding model."""
    if not texts:
        return []

    payload = {
        "model": settings.embedding_model,
        "input": texts,
        "keep_alive": settings.embedding_keep_alive,
    }

    try:
        data = _post_json("/api/embed", payload, timeout=180)
        embeddings = data.get("embeddings")
        if embeddings:
            return embeddings
    except OllamaError as exc:
        logger.warning("Batch embed endpoint failed, trying legacy endpoint: %s", exc)

    # Fallback for older Ollama versions that expose /api/embeddings.
    output = []
    for text in texts:
        legacy_payload = {
            "model": settings.embedding_model,
            "prompt": text,
            "keep_alive": settings.embedding_keep_alive,
        }
        data = _post_json("/api/embeddings", legacy_payload, timeout=180)
        embedding = data.get("embedding")
        if not embedding:
            raise OllamaError(f"No embedding returned: {data}")
        output.append(embedding)
    return output


def chat(system_prompt: str, user_prompt: str) -> str:
    """Generate a grounded answer with the local chat model."""
    payload = {
        "model": settings.chat_model,
        "stream": False,
        "keep_alive": settings.chat_keep_alive,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "num_ctx": settings.num_ctx,
            "num_predict": settings.num_predict,
            "temperature": settings.temperature,
        },
    }
    data = _post_json("/api/chat", payload, timeout=600)
    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise OllamaError(f"No chat content returned: {data}")
    return content


def unload_model(model_name: str) -> None:
    """Ask Ollama to unload a model by using keep_alive=0."""
    payload = {
        "model": model_name,
        "prompt": "",
        "stream": False,
        "keep_alive": 0,
    }
    _post_json("/api/generate", payload, timeout=60)


def health_check() -> dict:
    """Return the local Ollama model list."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
