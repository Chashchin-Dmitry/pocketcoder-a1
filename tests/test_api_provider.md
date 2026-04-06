# `test_api_provider.py`

Tests for PR: base URL and model environment-variable support for the `claude-api` provider.

This module mirrors the structure of `sandbox/test-verify/tests/test_calculator.py`:

- Unit tests run always and do not require real API credentials.
- The integration test requires real credentials passed through `--env-file`.

## Integration Test Usage

### 1. Anthropic API

Run:

```bash
pytest tests/test_api_provider.py -v -s --env-file ./anthropic.env
```

Example `anthropic.env`:

```bash
export ANTHROPIC_BASE_URL=""
export ANTHROPIC_AUTH_TOKEN=""
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_DEFAULT_OPUS_MODEL="claude-haiku-4-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="claude-haiku-4-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku-4-5"
export CLAUDE_CODE_SUBAGENT_MODEL="claude-haiku-4-5"
```

### 2. OpenRouter / Anthropic-compatible gateway

Run:

```bash
pytest tests/test_api_provider.py -v -s --env-file ./openrouter.env
```

Example `openrouter.env`:

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="sk-or-..."
export ANTHROPIC_API_KEY="" # Important: Must be explicitly empty
export ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic/claude-haiku-4.5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-haiku-4.5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="anthropic/claude-haiku-4.5"
export CLAUDE_CODE_SUBAGENT_MODEL="anthropic/claude-haiku-4.5"
```

### 3. z.ai API

Run:

```bash
pytest tests/test_api_provider.py -v -s --env-file ./zai.env
```

Example `zai.env`:

```bash
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="..."
export ANTHROPIC_API_KEY="" # Important: Must be explicitly empty
export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.7"
export CLAUDE_CODE_SUBAGENT_MODEL="glm-4.7"
```
