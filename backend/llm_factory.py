import os

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from config import get_config


def create_llm(provider: str | None = None, model: str | None = None) -> ChatOpenAI | ChatOllama:
    cfg = get_config()
    resolved_provider = provider or "openrouter"

    if resolved_provider == "openrouter":
        return ChatOpenAI(
            base_url=cfg.LLM_PROVIDER_URL,
            model=cfg.DEFAULT_MODEL,
            api_key=cfg.OPENROUTER_API_KEY,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "4096")),
        )
    elif resolved_provider == "ollama":
        return ChatOllama(
            base_url=cfg.OLLAMA_BASE_URL,
            model=cfg.OLLAMA_DEFAULT_MODEL,
        )
    else:
        raise ValueError(f"Unknown provider: {resolved_provider!r}. Choose 'openrouter' or 'ollama'.")
