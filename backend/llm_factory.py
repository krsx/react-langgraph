from langchain_openai import ChatOpenAI
from config import get_config


def create_llm() -> ChatOpenAI:
    cfg = get_config()
    return ChatOpenAI(
        base_url=cfg.LLM_PROVIDER_URL,
        model=cfg.DEFAULT_MODEL,
        api_key=cfg.OPENROUTER_API_KEY,
    )
