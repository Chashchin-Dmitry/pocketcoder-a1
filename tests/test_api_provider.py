"""
Tests for PR: base_url and model env var support for claude-api provider.

Mirrors the structure of sandbox/test-verify/tests/test_calculator.py:
- Unit tests run always (no API keys needed)
- Integration test requires real API keys via --env-file:

    pytest tests/test_api_provider.py -v -s --env-file ./openrouter.env

openrouter.env file format for OpenRouter/Anthropic API (example):
  export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
  export ANTHROPIC_AUTH_TOKEN="sk-or-..."
  export ANTHROPIC_API_KEY="" # Important: Must be explicitly empty
  export ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic/claude-haiku-4.5"
  export ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-haiku-4.5"
  export ANTHROPIC_DEFAULT_HAIKU_MODEL="anthropic/claude-haiku-4.5"
  export CLAUDE_CODE_SUBAGENT_MODEL="anthropic/claude-haiku-4.5"

    pytest tests/test_api_provider.py -v -s --env-file ./zai.env

zai.env file format for z.ai API (example):
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="..."
export ANTHROPIC_API_KEY="" # Important: Must be explicitly empty
export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.7"
export CLAUDE_CODE_SUBAGENT_MODEL="glm-4.7"
"""

import subprocess
import sys
from pathlib import Path

import pytest

from a1.config import Config, ENV_MAP
from a1.loop import SessionLoop


def _parse_env_file(path: str) -> dict:
    """Parse a .env file into a plain dict. Handles KEY=value, # comments, export KEY=value."""
    result = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"').strip("'")
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
