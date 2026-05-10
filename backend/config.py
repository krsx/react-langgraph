import os
from dataclasses import dataclass


@dataclass
class Config:
    LLM_PROVIDER_URL: str
    DEFAULT_MODEL: str
    OPENROUTER_API_KEY: str
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str


def get_config() -> Config:
    missing = [
        var for var in (
            "LLM_PROVIDER_URL", "DEFAULT_MODEL", "OPENROUTER_API_KEY",
            "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE",
        )
        if not os.environ.get(var)
    ]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        LLM_PROVIDER_URL=os.environ["LLM_PROVIDER_URL"],
        DEFAULT_MODEL=os.environ["DEFAULT_MODEL"],
        OPENROUTER_API_KEY=os.environ["OPENROUTER_API_KEY"],
        MYSQL_HOST=os.environ["MYSQL_HOST"],
        MYSQL_PORT=int(os.environ["MYSQL_PORT"]),
        MYSQL_USER=os.environ["MYSQL_USER"],
        MYSQL_PASSWORD=os.environ["MYSQL_PASSWORD"],
        MYSQL_DATABASE=os.environ["MYSQL_DATABASE"],
    )
