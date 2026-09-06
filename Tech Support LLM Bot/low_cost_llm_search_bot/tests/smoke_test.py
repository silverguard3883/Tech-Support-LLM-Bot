import requests


def test_health() -> None:
    """Simple local smoke test for the FastAPI service."""
    response = requests.get("http://127.0.0.1:8088/api/health", timeout=10)
    response.raise_for_status()
    assert response.json()["status"] == "ok"
