import pytest
import sys
from langchain_openai import ChatOpenAI


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    sys.modules.pop("llm_factory", None)
    sys.modules.pop("config", None)


ENV = {
    "LLM_PROVIDER_URL": "https://openrouter.ai/api/v1",
    "DEFAULT_MODEL": "google/gemini-2.5-flash",
    "OPENROUTER_API_KEY": "test-key",
    "MYSQL_HOST": "localhost",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "root",
    "MYSQL_PASSWORD": "secret",
    "MYSQL_DATABASE": "csagent",
}


def test_create_llm_returns_chatopenai(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)

    from llm_factory import create_llm
    llm = create_llm()

    assert isinstance(llm, ChatOpenAI)


def test_create_llm_uses_provider_url(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("LLM_PROVIDER_URL", "http://192.168.1.10:11434/v1")

    from llm_factory import create_llm
    llm = create_llm()

    assert llm.openai_api_base == "http://192.168.1.10:11434/v1"


def test_create_llm_uses_default_model(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("DEFAULT_MODEL", "qwen2.5")

    from llm_factory import create_llm
    llm = create_llm()

    assert llm.model_name == "qwen2.5"
