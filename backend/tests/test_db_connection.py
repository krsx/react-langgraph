import pytest
import sys
import os


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    sys.modules.pop("db.connection", None)
    sys.modules.pop("config", None)


pytestmark = pytest.mark.integration

ENV = {
    "LLM_PROVIDER_URL": "https://openrouter.ai/api/v1",
    "DEFAULT_MODEL": "google/gemini-2.5-flash",
    "OPENROUTER_API_KEY": "test-key",
    "MYSQL_HOST": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "MYSQL_PORT": os.environ.get("MYSQL_PORT", "3306"),
    "MYSQL_USER": os.environ.get("MYSQL_USER", "root"),
    "MYSQL_PASSWORD": os.environ.get("MYSQL_PASSWORD", "root"),
    "MYSQL_DATABASE": os.environ.get("MYSQL_DATABASE", "csagent"),
}


@pytest.mark.integration
def test_get_connection_returns_live_connection(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)

    from db.connection import get_connection
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result == (1,)
    finally:
        conn.close()


@pytest.mark.integration
def test_get_connection_pool_reuses_connections(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)

    from db.connection import get_connection
    conn1 = get_connection()
    conn1.close()
    conn2 = get_connection()

    try:
        cursor = conn2.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
    finally:
        conn2.close()
