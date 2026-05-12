"""Tests for GET /providers endpoint (issue #11)."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# ── Cycle 1: Endpoint exists and returns correct shape ────────────────────────

def test_providers_endpoint_returns_both_providers():
    with patch("routes.providers._check_openrouter") as mock_or, \
         patch("routes.providers._check_ollama") as mock_oll:
        mock_or.return_value = {"available": True, "models": ["google/gemini-2.5-flash"]}
        mock_oll.return_value = {"available": True, "models": ["llama3.2"]}

        from main import app
        client = TestClient(app)
        resp = client.get("/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert "openrouter" in data
    assert "ollama" in data


def test_providers_response_has_available_and_models_keys():
    with patch("routes.providers._check_openrouter") as mock_or, \
         patch("routes.providers._check_ollama") as mock_oll:
        mock_or.return_value = {"available": True, "models": ["model-a"]}
        mock_oll.return_value = {"available": False, "models": []}

        from main import app
        client = TestClient(app)
        resp = client.get("/providers")

    data = resp.json()
    for provider in ("openrouter", "ollama"):
        assert "available" in data[provider], f"{provider} missing 'available'"
        assert "models" in data[provider], f"{provider} missing 'models'"


# ── Cycle 2: Ollama unreachable → available: False, empty models ──────────────

def test_ollama_unavailable_returns_false_not_crash():
    with patch("routes.providers._check_openrouter") as mock_or, \
         patch("routes.providers._check_ollama") as mock_oll:
        mock_or.return_value = {"available": True, "models": ["google/gemini-2.5-flash"]}
        mock_oll.return_value = {"available": False, "models": []}

        from main import app
        client = TestClient(app)
        resp = client.get("/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ollama"]["available"] is False
    assert data["ollama"]["models"] == []


# ── Cycle 3: _check_ollama returns False when HTTP fails ─────────────────────

def test_check_ollama_returns_unavailable_on_connection_error():
    import httpx
    with patch("routes.providers.httpx.get", side_effect=httpx.ConnectError("refused")):
        from routes.providers import _check_ollama
        result = _check_ollama("http://localhost:11434")

    assert result["available"] is False
    assert result["models"] == []


def test_check_ollama_returns_models_on_success():
    import httpx

    mock_response = httpx.Response(
        200,
        json={"models": [{"name": "llama3.2"}, {"name": "qwen3:4b"}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    with patch("routes.providers.httpx.get", return_value=mock_response):
        from routes.providers import _check_ollama
        result = _check_ollama("http://localhost:11434")

    assert result["available"] is True
    assert "llama3.2" in result["models"]
    assert "qwen3:4b" in result["models"]


# ── Cycle 4: _check_openrouter returns False when key is missing/invalid ─────

def test_check_openrouter_returns_unavailable_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)

    import sys
    sys.modules.pop("config", None)

    from routes.providers import _check_openrouter
    result = _check_openrouter(api_key="")

    assert result["available"] is False


def test_check_openrouter_returns_available_with_valid_key():
    import httpx

    mock_response = httpx.Response(
        200,
        json={"data": [{"id": "google/gemini-2.5-flash"}, {"id": "openai/gpt-4o"}]},
        request=httpx.Request("GET", "https://openrouter.ai/api/v1/models"),
    )
    with patch("routes.providers.httpx.get", return_value=mock_response):
        from routes.providers import _check_openrouter
        result = _check_openrouter(api_key="sk-test")

    assert result["available"] is True
    assert "google/gemini-2.5-flash" in result["models"]
