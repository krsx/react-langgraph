from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


def test_dockerfile_entrypoint_module_exists():
    # main:app is declared in the Dockerfile CMD; the entrypoint uses exec "$@"
    # to forward it. Verify the ASGI module exists on disk.
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text()

    assert "main:app" in dockerfile
    assert (BACKEND_DIR / "main.py").exists()


def test_required_dependencies_are_declared():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # Python 3.10 backport

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
    assert "./backend/db:/docker-entrypoint-initdb.d:ro" in compose
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


# ── workspace-mcp infrastructure ─────────────────────────────────────────────

def test_dockerfile_copies_and_invokes_entrypoint_script():
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text()

    assert "COPY entrypoint.sh" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "entrypoint.sh" in dockerfile
    assert (BACKEND_DIR / "entrypoint.sh").exists()


def test_dockerfile_installs_workspace_tools():
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text()

    assert "workspace-mcp" in dockerfile
    assert "workspace-cli" in dockerfile


def test_docker_compose_backend_has_workspace_mcp_env_vars():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    assert "WORKSPACE_MCP_COMMAND" in compose
    assert "WORKSPACE_MCP_ARGS" in compose
    assert "WORKSPACE_MCP_URL" not in compose


def test_env_example_documents_workspace_mcp_vars():
    env_example = (REPO_ROOT / ".env.example").read_text()

    assert "WORKSPACE_MCP_COMMAND" in env_example
    assert "WORKSPACE_MCP_ARGS" in env_example
    assert "WORKSPACE_MCP_URL" not in env_example


def test_env_example_workspace_mcp_args_is_bash_sourceable_and_has_no_serve_subcommand():
    """
    WORKSPACE_MCP_ARGS must be quoted in .env.example so that
    `set -a && source .env && set +a` does not execute flags as shell commands.
    'serve' is also not a valid workspace-mcp subcommand in the current version.
    """
    import re
    import subprocess

    env_example = (REPO_ROOT / ".env.example").read_text()
    match = re.search(r'^WORKSPACE_MCP_ARGS=(.+)$', env_example, re.MULTILINE)
    assert match, "WORKSPACE_MCP_ARGS not found in .env.example"

    raw_value = match.group(1).strip().strip('"').strip("'")
    first_token = raw_value.split()[0]
    assert first_token.startswith("--"), (
        f"WORKSPACE_MCP_ARGS must start with a flag (e.g. --single-user), "
        f"got: '{first_token}'. 'serve' is not a valid workspace-mcp subcommand."
    )

    # Verify it sources cleanly under set -a (no flags treated as commands)
    result = subprocess.run(
        ["bash", "-c", f'set -a; echo \'WORKSPACE_MCP_ARGS={match.group(1)}\' > /tmp/_args_test.env; source /tmp/_args_test.env; set +a; echo "OK:$WORKSPACE_MCP_ARGS"'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"source .env failed: {result.stderr}"
    assert "OK:" in result.stdout


def test_env_example_workspace_mcp_args_permissions_are_space_separated_service_level_pairs():
    """
    --permissions takes space-separated service:level pairs.
    Comma-separated values like 'gmail:send,calendar' are invalid and cause a
    runtime error: "Unknown level 'send,calendar' for service 'gmail'".
    """
    import re

    GMAIL_LEVELS = {"readonly", "organize", "drafts", "send", "full"}
    OTHER_LEVELS = {"readonly", "full"}

    env_example = (REPO_ROOT / ".env.example").read_text()
    match = re.search(r'^WORKSPACE_MCP_ARGS=(.+)$', env_example, re.MULTILINE)
    assert match, "WORKSPACE_MCP_ARGS not found in .env.example"

    raw_value = match.group(1).strip().strip('"').strip("'")
    tokens = raw_value.split()

    # Collect tokens that follow --permissions
    perms: list[str] = []
    capture = False
    for token in tokens:
        if token == "--permissions":
            capture = True
            continue
        if capture:
            if token.startswith("--"):
                break
            perms.append(token)

    assert perms, "No values found after --permissions in WORKSPACE_MCP_ARGS"

    for perm in perms:
        assert "," not in perm, (
            f"Permission '{perm}' contains a comma. Use space-separated pairs: "
            f"e.g. '--permissions gmail:send calendar:full', not 'gmail:send,calendar'."
        )
        assert ":" in perm, f"Permission '{perm}' must be in service:level format"
        service, level = perm.split(":", 1)
        valid = GMAIL_LEVELS if service == "gmail" else OTHER_LEVELS
        assert level in valid, (
            f"Invalid level '{level}' for service '{service}'. Valid: {sorted(valid)}"
        )


def test_entrypoint_script_is_executable_and_has_credential_check():
    import os
    script = BACKEND_DIR / "entrypoint.sh"

    assert script.exists()
    assert os.access(script, os.X_OK), "entrypoint.sh is not executable"
    body = script.read_text()
    assert body.startswith("#!/usr/bin/env bash")
    # 'workspace-mcp auth' was removed in the current version; the entrypoint
    # now checks for credentials and warns rather than running auth interactively.
    assert "workspace-mcp auth" not in body
    assert ".google_workspace_mcp" in body
    assert "WARNING" in body


def test_docker_compose_backend_mounts_token_cache_volume():
    import yaml

    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())

    backend_volumes = compose["services"]["backend"]["volumes"]
    assert any("workspace_mcp_tokens" in str(v) for v in backend_volumes)
    assert "workspace_mcp_tokens" in compose.get("volumes", {})


def test_entrypoint_execs_configured_command():
    # The entrypoint must use exec "$@" so the container's configured command
    # (from Docker Compose or CMD) is preserved rather than hardcoded.
    body = (BACKEND_DIR / "entrypoint.sh").read_text()
    assert 'exec "$@"' in body


def test_dockerfile_provides_default_uvicorn_cmd():
    # The image must supply a CMD so it works standalone; docker-compose command:
    # overrides this default via exec "$@" in the entrypoint.
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text()
    assert "CMD" in dockerfile
    assert "main:app" in dockerfile


def test_docker_compose_backend_passes_google_oauth_vars():
    # Google OAuth client credentials must reach the backend container so the
    # workspace-mcp subprocess inherits them for authentication.
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "GOOGLE_OAUTH_CLIENT_ID" in compose
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in compose
    assert "GOOGLE_CLIENT_ID" not in compose
    assert "GOOGLE_CLIENT_SECRET" not in compose


def test_workspace_mcp_args_default_includes_required_flags():
    # The default WORKSPACE_MCP_ARGS must configure the shared stdio subprocess:
    # single-user mode, core tool tier, combined Workspace Agent permissions.
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "single-user" in compose
    assert "tool-tier core" in compose
    assert "gmail:send" in compose
    assert "calendar" in compose


def test_env_example_documents_google_oauth_vars():
    env_example = (REPO_ROOT / ".env.example").read_text()
    assert "GOOGLE_OAUTH_CLIENT_ID" in env_example
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in env_example
    assert "GOOGLE_CLIENT_ID" not in env_example
    assert "GOOGLE_CLIENT_SECRET" not in env_example


def test_env_example_workspace_mcp_args_has_full_config():
    env_example = (REPO_ROOT / ".env.example").read_text()
    assert "single-user" in env_example
    assert "tool-tier core" in env_example
    assert "gmail:send" in env_example


def test_http_mode_scripts_are_deleted():
    assert not (REPO_ROOT / "scripts" / "start-workspace-mcp.sh").exists()
    assert not (REPO_ROOT / "scripts" / "test-workspace-mcp.sh").exists()


def test_env_example_documents_oauth_setup():
    env_example = (REPO_ROOT / ".env.example").read_text()
    assert "One-Time OAuth Setup" in env_example
    assert "~/.google_workspace_mcp/credentials" in env_example


def test_mcp_client_has_no_http_code_path():
    source = (BACKEND_DIR / "graph" / "mcp_client.py").read_text()
    assert "WORKSPACE_MCP_URL" not in source
    assert "streamable_http" not in source
