import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Header, HTTPException, Request, status

from app.config import settings


_request_times: Dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request, api_key: str | None) -> str:
    """Use API key or client IP as a lightweight rate-limit key."""
    if api_key:
        return f"key:{api_key[:8]}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def enforce_rate_limit(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Apply a small in-memory per-minute request limit."""
    now = time.time()
    key = _client_key(request, x_api_key)
    window = _request_times[key]

    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= settings.rate_limit_requests_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    window.append(now)


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Require API key when enabled, then rate-limit the caller."""
    if settings.enable_api_key_auth and x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    enforce_rate_limit(request, x_api_key)
