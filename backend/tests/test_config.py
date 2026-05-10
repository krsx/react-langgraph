import pytest
import sys
import os


@pytest.fixture(autouse=True)
def clean_config_import():
    yield
    sys.modules.pop("config", None)


REQUIRED_VARS = {
    "LLM_PROVIDER_URL": "https://openrouter.ai/api/v1",
    "DEFAULT_MODEL": "google/gemini-2.5-flash",
    "OPENROUTER_API_KEY": "test-key",
    "MYSQL_HOST": "localhost",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "root",
    "MYSQL_PASSWORD": "secret",
    "MYSQL_DATABASE": "csagent",
}


def test_config_loads_all_env_vars(monkeypatch):
    for k, v in REQUIRED_VARS.items():
        monkeypatch.setenv(k, v)

    from config import get_config
    cfg = get_config()

    assert cfg.LLM_PROVIDER_URL == "https://openrouter.ai/api/v1"
    assert cfg.DEFAULT_MODEL == "google/gemini-2.5-flash"
    assert cfg.OPENROUTER_API_KEY == "test-key"
    assert cfg.MYSQL_HOST == "localhost"
    assert cfg.MYSQL_PORT == 3306
    assert cfg.MYSQL_USER == "root"
    assert cfg.MYSQL_PASSWORD == "secret"
    assert cfg.MYSQL_DATABASE == "csagent"


@pytest.mark.parametrize("missing_var", list(REQUIRED_VARS.keys()))
def test_config_raises_on_missing_required_var(monkeypatch, missing_var):
    for k, v in REQUIRED_VARS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(missing_var)

    from config import get_config
    with pytest.raises(EnvironmentError, match=missing_var):
        get_config()
