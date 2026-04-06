"""Tests for claude-api provider env handling and integration behavior.

See tests/test_api_provider.md for usage notes and env-file examples.
"""

import os
import subprocess
import sys
import shlex
from pathlib import Path

import pytest

from a1.config import Config, ENV_MAP
from a1.loop import SessionLoop


def _parse_env_assignment(line: str) -> tuple[str, str] | None:
    """Parse one shell-style env assignment."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    tokens = shlex.split(stripped, comments=True, posix=True)
    if not tokens:
        return None
    if tokens[0] == "export":
        tokens = tokens[1:]
    if len(tokens) != 1 or "=" not in tokens[0]:
        return None

    key, value = tokens[0].split("=", 1)
    return key.strip(), value


def _parse_env_file(path: str) -> dict:
    """Parse a shell-style env file into a plain dict."""
    result = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_assignment(line)
        if parsed is None:
            continue
        key, value = parsed
        result[key] = value
    return result


def _setup_project(project_dir: Path) -> None:
    """Create a minimal .a1/ project with one trivial task."""
    from a1.checkpoint import CheckpointManager
    from a1.tasks import TaskManager

    (project_dir / ".a1" / "sessions").mkdir(parents=True, exist_ok=True)
    (project_dir / ".a1" / "checkpoints").mkdir(parents=True, exist_ok=True)
    CheckpointManager(project_dir).save(CheckpointManager(project_dir).load())
    TaskManager(project_dir).add_task(
        "Create hello.txt",
        description="Create a file named hello.txt containing exactly one line: Hello from PocketCoder.",
        success_criteria="hello.txt exists with content: Hello from PocketCoder.",
    )
    Config(project_dir).save()


# ---------------------------------------------------------------------------
# config.py changes
# ---------------------------------------------------------------------------

class TestConfigChanges:
    """Covers config.py: base_url in DEFAULTS, new ENV_MAP entries, VALID_PARAMS filter."""

    def test_base_url_default_is_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        result = Config(tmp_path).resolve()
        assert result.get("base_url") is None

    def test_base_url_in_env_map(self):
        assert "ANTHROPIC_BASE_URL" in ENV_MAP
        assert ENV_MAP["ANTHROPIC_BASE_URL"] == "base_url"

    def test_model_env_vars_in_env_map(self):
        assert "ANTHROPIC_DEFAULT_SONNET_MODEL" in ENV_MAP
        assert "ANTHROPIC_DEFAULT_HAIKU_MODEL" in ENV_MAP
        assert "ANTHROPIC_DEFAULT_OPUS_MODEL" in ENV_MAP

    def test_valid_params_filter_blocks_model_keys(self, tmp_path, monkeypatch):
        """model_haiku/sonnet/opus must not appear in resolve() — would cause TypeError in SessionLoop."""
        monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "any-value")
        monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "any-value")
        result = Config(tmp_path).resolve()
        assert "model_haiku" not in result
        assert "model_sonnet" not in result
        assert "model_opus" not in result


class TestEnvFileParsing:
    """Covers shell-style env-file parsing used by the integration test."""

    def test_export_empty_value_with_inline_comment(self):
        parsed = _parse_env_assignment(
            'export ANTHROPIC_AUTH_TOKEN="" # Important: Must be explicitly empty'
        )
        assert parsed == ("ANTHROPIC_AUTH_TOKEN", "")


# ---------------------------------------------------------------------------
# cli.py changes
# ---------------------------------------------------------------------------

class TestCliChanges:
    """Covers cli.py: --base-url argument registered in start subparser."""

    def test_base_url_arg_in_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "a1.cli", "start", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--base-url" in result.stdout


# ---------------------------------------------------------------------------
# loop.py changes
# ---------------------------------------------------------------------------

class TestLoopChanges:
    """Covers loop.py: base_url param in SessionLoop.__init__."""

    def test_base_url_default_none(self, tmp_path):
        loop = SessionLoop(project_dir=tmp_path)
        assert loop.base_url is None

    def test_normalize_optional_value(self):
        assert SessionLoop._normalize_optional_value(None) is None
        assert SessionLoop._normalize_optional_value("") is None
        assert SessionLoop._normalize_optional_value("   ") is None
        assert SessionLoop._normalize_optional_value(" value ") == "value"

    def test_clean_anthropic_env_restores_values(self, tmp_path, monkeypatch):
        loop = SessionLoop(project_dir=tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "   ")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "")
        monkeypatch.setenv("UNRELATED_ENV", "")

        with loop._clean_anthropic_env():
            assert "ANTHROPIC_API_KEY" not in os.environ
            assert "ANTHROPIC_AUTH_TOKEN" not in os.environ
            assert "ANTHROPIC_BASE_URL" not in os.environ
            assert os.environ["UNRELATED_ENV"] == ""

        assert os.environ["ANTHROPIC_API_KEY"] == ""
        assert os.environ["ANTHROPIC_AUTH_TOKEN"] == "   "
        assert os.environ["ANTHROPIC_BASE_URL"] == ""
        assert os.environ["UNRELATED_ENV"] == ""


# ---------------------------------------------------------------------------
# Integration — real API call, skipped without --env-file
# ---------------------------------------------------------------------------

class TestApiProviderIntegration:
    """Run a real claude-api session using keys from .env. Skipped without --env-file."""

    def test_session_runs_and_produces_log(self, local_tmp_path, env_file, monkeypatch):
        if not env_file:
            pytest.skip("--env-file not provided")

        env = _parse_env_file(env_file)
        for k, v in env.items():
            monkeypatch.setenv(k, v)

        _setup_project(local_tmp_path)

        resolved = Config(local_tmp_path).resolve(cli_args={"provider": "claude-api"})
        print(f"\n[config] base_url={resolved.get('base_url')!r}  model={resolved.get('model')!r}")

        resolved["max_sessions"] = 1
        resolved["max_turns"] = 20
        loop = SessionLoop(project_dir=local_tmp_path, **resolved)
        loop.start()

        # Assert: session log was created and is non-empty
        logs = sorted((local_tmp_path / ".a1" / "sessions").glob("*.log"))
        assert logs, "No session log created — agent did not run"
        log_content = logs[0].read_text(encoding="utf-8")
        assert log_content.strip(), "Session log is empty"
        print(f"\n[session log] {logs[0].name}  ({len(log_content)} bytes)")

        # Assert: task output file created with exact content
        hello = local_tmp_path / "hello.txt"
        assert hello.exists(), "hello.txt was not created by the agent"
        assert hello.read_text(encoding="utf-8").strip() == "Hello from PocketCoder.", \
            f"Wrong content in hello.txt: {hello.read_text(encoding='utf-8')!r}"

        # Assert: task marked done in tasks.json
        import json
        tasks_data = json.loads((local_tmp_path / ".a1" / "tasks.json").read_text(encoding="utf-8"))
        task = next((t for t in tasks_data["tasks"] if t["id"] == "task_001"), None)
        assert task is not None, "task_001 not found in tasks.json"
        assert task["status"] == "done", f"task_001 not completed: status={task['status']!r}"

        # Assert: checkpoint reached COMPLETED
        from a1.checkpoint import CheckpointManager
        cp = CheckpointManager(local_tmp_path).load()
        print(f"\n[checkpoint] session={cp['session']}  status={cp['status']}")
        assert cp.get("status") == "COMPLETED", f"Checkpoint not COMPLETED: {cp.get('status')!r}"
