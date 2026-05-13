import httpx
from fastapi import APIRouter

from config import get_config

router = APIRouter()

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_TIMEOUT = 5.0

# Ollama models confirmed to support tool calling (required for agent function).
# Models without tool-call support will fail at the bind_tools() step in the planner.
# Verified: qwen3:4b, qwen3:8b, llama3.1:8b, llama3.2:3b, mistral-nemo, firefunction-v2
# Not supported: most base/instruct-only models (e.g. phi3, gemma2, tinyllama)


def _check_openrouter(api_key: str) -> dict:
    if not api_key:
        return {"available": False, "models": []}
    try:
        resp = httpx.get(
            _OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            return {"available": True, "models": models}
        return {"available": False, "models": []}
    except Exception:
        return {"available": False, "models": []}


def _check_ollama(base_url: str) -> dict:
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=_TIMEOUT)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return {"available": True, "models": models}
        return {"available": False, "models": []}
    except Exception:
        return {"available": False, "models": []}


def _restrict_to_default_model(provider_state: dict, default_model: str) -> dict:
    models = provider_state.get("models", [])
    available = bool(provider_state.get("available")) and default_model in models

    return {
        "available": available,
        "models": [default_model] if available else [],
        "default_model": default_model if available else None,
    }


@router.get("/providers")
def get_providers() -> dict:
    cfg = get_config()
    return {
        "openrouter": _restrict_to_default_model(
            _check_openrouter(cfg.OPENROUTER_API_KEY),
            cfg.DEFAULT_MODEL,
        ),
        "ollama": _restrict_to_default_model(
            _check_ollama(cfg.OLLAMA_BASE_URL),
            cfg.OLLAMA_DEFAULT_MODEL,
        ),
    }
