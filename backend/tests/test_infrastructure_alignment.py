from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


def test_dockerfile_entrypoint_module_exists():
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text()

    assert "main:app" in dockerfile
    assert (BACKEND_DIR / "main.py").exists()


def test_required_dependencies_are_declared():
    import tomllib

    pyproject = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text())
    declared = pyproject["project"]["dependencies"]

    for dependency in (
        "langgraph",
        "langchain-openai",
        "fastapi",
        "uvicorn[standard]",
        "mysql-connector-python",
        "python-dotenv",
    ):
        assert any(dep.startswith(dependency) for dep in declared), (
            f"{dependency!r} not found in pyproject.toml dependencies"
        )


def test_docker_compose_declares_mysql_seeded_service():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    assert "mysql:" in compose
    assert '"3306:3306"' in compose
    assert "./backend/db/seed.sql:/docker-entrypoint-initdb.d/seed.sql" in compose
    assert "mysql_data:/var/lib/mysql" in compose
    assert "MYSQL_HOST: mysql" in compose


def test_seed_sql_covers_required_tables_and_fixtures():
    seed_sql = (BACKEND_DIR / "db" / "seed.sql").read_text()

    for table_name in (
        "customers",
        "orders",
        "complaints",
        "customer_memory",
        "sessions",
        "session_messages",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in seed_sql

    for order_id in ("12345", "1001", "5678", "2222", "7890"):
        assert f"({order_id}," in seed_sql or f"({order_id}, " in seed_sql

    assert "(1, 'Ahmad Rifqi'" in seed_sql
    assert "(2, 'Jane Doe'" in seed_sql
    assert "INSERT INTO complaints" in seed_sql
    assert "late delivery pattern" in seed_sql.lower()

    order_insert_block = seed_sql.split("INSERT INTO orders", maxsplit=1)[1]
    assert "(0000," not in order_insert_block


def test_mysql_refresh_seed_script_exists_and_reuses_compose_exec():
    script_path = REPO_ROOT / "scripts" / "mysql-refresh-seed.sh"

    assert script_path.exists()

    script_body = script_path.read_text()
    assert "set -euo pipefail" in script_body
    assert "docker compose exec" in script_body
    assert "backend/db/seed.sql" in script_body
    assert "DROP DATABASE IF EXISTS" in script_body
    assert "CREATE DATABASE" in script_body
