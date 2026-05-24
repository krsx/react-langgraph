import os
import stat
import subprocess
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENTRYPOINT = BACKEND_DIR / "entrypoint.sh"


def _make_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_entrypoint(tmp_path: Path, prepare_cache) -> tuple[subprocess.CompletedProcess[str], str]:
    home_dir = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    cache_dir = home_dir / ".workspace-mcp"
    log_path = tmp_path / "invocations.log"

    home_dir.mkdir()
    bin_dir.mkdir()
    prepare_cache(cache_dir)

    _make_executable(
        bin_dir / "workspace-mcp",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "workspace-mcp:$*" >> "{log_path}"
exit 0
""",
    )
    _make_executable(
        bin_dir / "app-cmd",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "app-cmd:$*" >> "{log_path}"
exit 0
""",
    )

    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    result = subprocess.run(
        [str(ENTRYPOINT), "app-cmd"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    log = log_path.read_text() if log_path.exists() else ""
    return result, log


def test_entrypoint_runs_auth_when_cache_is_missing(tmp_path: Path):
    def prepare_cache(cache_dir: Path) -> None:
        # Cache directory is intentionally absent.
        assert not cache_dir.exists()

    result, log = _run_entrypoint(tmp_path, prepare_cache)

    assert result.returncode == 0
    assert "workspace-mcp:auth" in log
    assert "app-cmd:" in log


def test_entrypoint_runs_auth_when_cache_contains_only_unrelated_file(tmp_path: Path):
    def prepare_cache(cache_dir: Path) -> None:
        cache_dir.mkdir()
        (cache_dir / "README.txt").write_text("placeholder")

    result, log = _run_entrypoint(tmp_path, prepare_cache)

    assert result.returncode == 0
    assert "workspace-mcp:auth" in log
    assert "app-cmd:" in log


def test_entrypoint_skips_auth_when_cache_contains_non_empty_token_artifact(tmp_path: Path):
    def prepare_cache(cache_dir: Path) -> None:
        cache_dir.mkdir()
        (cache_dir / "oauth_tokens.enc").write_text("encrypted-token-bytes")

    result, log = _run_entrypoint(tmp_path, prepare_cache)

    assert result.returncode == 0
    assert "workspace-mcp:auth" not in log
    assert "app-cmd:" in log
