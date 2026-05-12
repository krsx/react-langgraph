import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OLLAMA_BASE_URL_DEFAULT = "http://ollama:11434"
OLLAMA_DEFAULT_MODEL_DEFAULT = "qwen3.5:9b"


@dataclass
class Config:
    LLM_PROVIDER_URL: str
    DEFAULT_MODEL: str
    OPENROUTER_API_KEY: str
    OLLAMA_BASE_URL: str
    OLLAMA_DEFAULT_MODEL: str
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str


def get_config() -> Config:
    load_dotenv()

    missing = [
        var for var in (
            "DEFAULT_MODEL", "OPENROUTER_API_KEY",
            "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE",
        )
        if not os.environ.get(var)
    ]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        LLM_PROVIDER_URL=os.environ.get("LLM_PROVIDER_URL", OPENROUTER_BASE_URL),
        DEFAULT_MODEL=os.environ["DEFAULT_MODEL"],
        OPENROUTER_API_KEY=os.environ["OPENROUTER_API_KEY"],
        OLLAMA_BASE_URL=os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL_DEFAULT),
        OLLAMA_DEFAULT_MODEL=os.environ.get("OLLAMA_DEFAULT_MODEL", OLLAMA_DEFAULT_MODEL_DEFAULT),
        MYSQL_HOST=os.environ["MYSQL_HOST"],
        MYSQL_PORT=int(os.environ["MYSQL_PORT"]),
        MYSQL_USER=os.environ["MYSQL_USER"],
        MYSQL_PASSWORD=os.environ["MYSQL_PASSWORD"],
        MYSQL_DATABASE=os.environ["MYSQL_DATABASE"],
    )
