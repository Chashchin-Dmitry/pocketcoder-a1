"""
a1/config.py — Configuration management for PocketCoder-A1.

Loads/saves .a1/config.json with priority resolution:
  CLI args > env vars > config.json > defaults
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULTS = {
    "provider": "claude-max",
    "model": None,
    "api_key": None,
    "ollama_host": "http://localhost:11434",
    "ollama_model": "qwen3:30b-a3b",
    "max_sessions": 100,
    "max_turns": 25,
    "session_delay": 5,
    "context_threshold": 0.70,
}

# Env var → config key mapping
ENV_MAP = {
    "ANTHROPIC_API_KEY": "api_key",
    "OLLAMA_HOST": "ollama_host",
    "OLLAMA_MODEL": "ollama_model",
}


class Config:
    """Configuration manager — load/save/resolve .a1/config.json."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.path = self.project_dir / ".a1" / "config.json"
        self._data: dict = {}
        self.load()

    def load(self) -> dict:
        """Load from disk. Returns stored values (not merged with defaults)."""
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}
        return self._data

    def save(self) -> None:
        """Save current data to .a1/config.json."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with fallback: config → DEFAULTS → default."""
        if key in self._data and self._data[key] is not None:
            return self._data[key]
        if key in DEFAULTS and DEFAULTS[key] is not None:
            return DEFAULTS[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """Set a value and save to disk."""
        self._data[key] = value
        self.save()

    def get_all(self) -> dict:
        """Get full config merged with defaults."""
        result = dict(DEFAULTS)
        result.update({k: v for k, v in self._data.items() if v is not None})
        return result

    def reset(self) -> None:
        """Reset to defaults."""
        self._data = {}
        self.save()

    def resolve(self, cli_args: Optional[dict] = None) -> dict:
        """Merge all sources: CLI > env > config > defaults.

        Returns dict with keys matching SessionLoop.__init__ params:
          provider, model, api_key, ollama_host, ollama_model,
          max_sessions, max_turns, session_delay
        """
        # 1. Start with defaults
        result = dict(DEFAULTS)

        # 2. Overlay config.json values
        for k, v in self._data.items():
            if v is not None:
                result[k] = v

        # 3. Overlay env vars
        for env_var, config_key in ENV_MAP.items():
            val = os.environ.get(env_var)
            if val:
                result[config_key] = val

        # 4. Overlay CLI args (skip None values — means "not provided")
        if cli_args:
            for k, v in cli_args.items():
                if v is not None:
                    result[k] = v

        # Remove context_threshold from result (it's not a SessionLoop param)
        # Store it separately so loop.py can access if needed
        result.pop("context_threshold", None)

        return result

    def mask_api_key(self, key: Optional[str] = None) -> Optional[str]:
        """Mask API key for display: sk-ant-api03-...xxxx."""
        k = key or self.get("api_key")
        if not k or len(k) < 8:
            return k
        return k[:10] + "..." + k[-4:]

    def __repr__(self) -> str:
        return f"Config({self.path}, keys={list(self._data.keys())})"
