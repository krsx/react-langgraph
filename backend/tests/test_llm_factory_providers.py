"""Tests for multi-provider LLM factory (issue #11)."""
import pytest
import sys
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in ("llm_factory", "config"):
        sys.modules.pop(mod, None)


BASE_ENV = {
    "DEFAULT_MODEL": "google/gemini-2.5-flash",
    "OPENROUTER_API_KEY": "test-key",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_DEFAULT_MODEL": "qwen3:4b",
    "MYSQL_HOST": "localhost",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "root",
    "MYSQL_PASSWORD": "secret",
    "MYSQL_DATABASE": "csagent",
}


# ── Cycle 1: Ollama provider returns ChatOllama ───────────────────────────────

def test_create_llm_ollama_returns_chat_ollama(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm(provider="ollama")

    assert isinstance(llm, ChatOllama)


# ── Cycle 2: OpenRouter provider returns ChatOpenAI ───────────────────────────

def test_create_llm_openrouter_returns_chat_openai(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm(provider="openrouter")

    assert isinstance(llm, ChatOpenAI)


def test_create_llm_openrouter_uses_openrouter_base_url(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm(provider="openrouter")

    assert "openrouter.ai" in llm.openai_api_base


# ── Cycle 3: Default (no provider) falls back to openrouter ──────────────────

def test_create_llm_no_provider_defaults_to_openrouter(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm()

    assert isinstance(llm, ChatOpenAI)


# ── Cycle 4: Model override is respected ─────────────────────────────────────

def test_create_llm_ollama_uses_specified_model(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm(provider="ollama", model="llama3.2")

    assert llm.model == "llama3.2"


def test_create_llm_openrouter_uses_specified_model(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm(provider="openrouter", model="anthropic/claude-3-haiku")

    assert llm.model_name == "anthropic/claude-3-haiku"


def test_create_llm_ollama_uses_default_model_when_none(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "mistral")

    from llm_factory import create_llm
    llm = create_llm(provider="ollama")

    assert llm.model == "mistral"


# ── Cycle 5: Unknown provider raises ValueError ───────────────────────────────

def test_create_llm_unknown_provider_raises_value_error(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm

    with pytest.raises(ValueError, match="Unknown provider"):
        create_llm(provider="anthropic")
