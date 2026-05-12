"""Tests for planner runtime provider switching (issue #11)."""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage


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


def _make_state(messages=None):
    return {
        "messages": messages or [HumanMessage(content="hello")],
        "customer_id": 1,
        "memory_context": [],
    }


# ── Cycle 1: Planner passes provider from configurable to create_llm ─────────

def test_planner_uses_ollama_when_configured(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(content="hi")

    with patch("graph.planner.create_llm", return_value=mock_llm) as mock_factory:
        from graph.planner import planner

        config = {"configurable": {"thread_id": "t1", "customer_id": 1, "provider": "ollama", "model": "llama3"}}
        planner(_make_state(), config)

        mock_factory.assert_called_once_with(provider="ollama", model="llama3")


def test_planner_uses_openrouter_when_configured(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(content="hi")

    with patch("graph.planner.create_llm", return_value=mock_llm) as mock_factory:
        from graph.planner import planner

        config = {"configurable": {"thread_id": "t1", "customer_id": 1, "provider": "openrouter", "model": None}}
        planner(_make_state(), config)

        mock_factory.assert_called_once_with(provider="openrouter", model=None)


def test_planner_defaults_to_no_provider_when_not_in_config(monkeypatch):
    for k, v in BASE_ENV.items():
        monkeypatch.setenv(k, v)

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(content="hi")

    with patch("graph.planner.create_llm", return_value=mock_llm) as mock_factory:
        from graph.planner import planner

        config = {"configurable": {"thread_id": "t1", "customer_id": 1}}
        planner(_make_state(), config)

        mock_factory.assert_called_once_with(provider=None, model=None)
