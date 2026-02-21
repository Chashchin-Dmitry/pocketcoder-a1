# CLAUDE.md — PocketCoder-A1

## AFTER /clear — READ THIS FIRST!

```
1. Read CLAUDE.md (this file) — project overview
2. Read CURRENT_STAGE.md — cause-effect chains, bug status
3. Read .a1/checkpoint.json — current state
4. Read .a1/tasks.json — task list
5. Read TODO.md — detailed phases
6. Continue work from checkpoint
```

---

## WHAT IS THIS

**PocketCoder-A1** — autonomous coding agent that:
- Works without human intervention
- Saves state between sessions (checkpoint)
- Auto-restarts when context fills up
- Validates its work (tests, lint)
- **Has autonomous vision-based QA tester** (screenshot → AI → action)

---

## PROJECT STRUCTURE

```
pocketcoder-a1/
├── a1/                      # Main code
│   ├── __init__.py          # Version
│   ├── checkpoint.py        # State between sessions
│   ├── tasks.py             # Task management
│   ├── validator.py         # Validation (tests, lint)
│   ├── loop.py              # Session loop (Claude CLI/API/Ollama)
│   ├── dashboard.py         # Web UI (full dashboard)
│   ├── cli.py               # CLI commands
│   └── tester/              # Vision-based QA agent
│       ├── __init__.py
│       ├── runner.py        # Main loop: screenshot → analyze → action
│       ├── browser.py       # Playwright headless wrapper
│       ├── analyzer.py      # Claude Vision analysis
│       ├── scenarios.py     # 7 predefined test scenarios
│       └── report.py        # HTML/JSON reports with screenshots
│
├── .a1/                     # Data (created on init)
│   ├── checkpoint.json      # Current state
│   ├── tasks.json           # Task list
│   ├── sessions/            # Session logs
│   ├── checkpoints/         # Checkpoint archive
│   └── test-reports/        # Vision tester reports + screenshots
│
├── .mcp.json                # Playwright MCP config
├── .venv/                   # Python virtual environment
├── BACKLOG.md               # Full scope
├── TODO.md                  # Detailed phases
├── CURRENT_STAGE.md         # Current state with cause-effect chains
├── CLAUDE.md                # This file
└── pyproject.toml           # pip install
```

---

## CLI COMMANDS

```bash
pca init <dir>           # Initialize project
pca task add "..."       # Add task
pca think "..."          # Add raw thought
pca tasks                # Show all tasks
pca start                # Start autonomous work
pca status               # Current status
pca validate             # Run validation
pca ui                   # Web dashboard
pca log                  # Session history
pca test                 # Run vision-based QA tests (all 7 scenarios)
pca test -s 1            # Run specific scenario
pca test --web-only      # Web tests only
pca test --no-vision     # Without AI vision analysis
```

---

## VISION TESTER

Autonomous QA agent that tests the dashboard visually:

```
Screenshot → Claude Vision analyzes → Decides action → Executes → Screenshot → ...
```

### 7 Test Scenarios:
1. Dashboard loads — page renders, all cards visible
2. Add task via web — form submit, task appears
3. Add thought — thought form works
4. Navigation — all 6 pages load correctly
5. Theme toggle — dark/light switch
6. Start/Stop agent — controls work
7. API endpoint — /api/status returns valid JSON

### How to run:
```bash
source .venv/bin/activate
pca ui --no-browser &     # Start dashboard
pca test --no-vision      # Run all tests
# Reports: .a1/test-reports/latest.html
```

---

## AUTONOMOUS WORK PROTOCOL

```
1. SESSION START
   └── Read checkpoint.json
   └── Read tasks.json
   └── Identify current task

2. WORK
   └── Take pending/in_progress task
   └── Execute subtasks
   └── Validate after each change

3. VALIDATION
   └── python -m py_compile (syntax)
   └── pytest (tests)
   └── ruff check (lint)
   └── If FAIL → fix
   └── If OK → commit

4. CONTEXT MONITORING
   └── Check /tokens every 10-15 min
   └── At 70%+ → save checkpoint → exit

5. CHECKPOINT FORMAT
   └── What was done
   └── Which files changed
   └── What decisions were made
   └── What to do next
```

---

## POST-SESSION VERIFICATION

After each session, loop.py automatically verifies the agent's work:

```
Agent says "COMPLETED"
  └── _verify_session() runs
      ├── BLOCKING (must pass): syntax, tests, files_modified exist, success_criteria
      ├── WARNING (log only): lint, build, git status
      └── Anti-infinite-loop: baseline comparison, max 3 retries, force_accept
```

**Key methods (a1/loop.py)**:
- `_capture_baseline()` — snapshot validation state before first session
- `_is_new_issue()` — only NEW failures count (pre-existing issues skipped)
- `_verify_session()` — runs all checks, returns `{passed, blocking_issues, warnings, retry_count}`
- `_get_verification_prompt()` — injects failure details into next session prompt

**Validation methods (a1/validator.py)**:
- `run_all()` — syntax + tests + lint + build + git (optional)
- `has_git()` / `_check_git()` — git detection, works without git
- `check_files_exist(paths)` — verify files on disk
- `check_criteria(criteria)` — heuristic: "tests pass" → pytest, "file X exists" → os.path.exists

**Constants**: `BLOCKING_CHECKS = {syntax, tests}`, `WARNING_CHECKS = {lint, build, git}`, `MAX_VERIFY_RETRIES = 3`

---

## BUGS FIXED (11, 2026-02-21)

1. **loop.py** — Claude CLI args: `["claude", prompt]` → `["claude", "-p", prompt]`
2. **loop.py** — Added output capture to session logs
3. **loop.py** — Nested sessions: unset `CLAUDECODE` env var
4. **loop.py** — Permissions: `--dangerously-skip-permissions` for autonomous mode
5. **dashboard.py** — Stop button now connected to `loop.stop()`
6. **dashboard.py** — XSS fixed with `html.escape()` on all user inputs
7. **checkpoint.py** — decisions[] limited to last 20 entries
8. **loop.py** — signal.signal() in non-main thread: added threading check
9. **loop.py** — `--output-format stream-json` requires `--verbose` with `-p`
10. **loop.py** — Parser: tool_use comes inside assistant content[], not content_block_start
11. **loop.py** — f-string nested quotes in `_capture_baseline()`: extracted to variable

---

## CLAUDE CLI REFERENCE (for subprocess calls)

### Correct way to call claude from Python (with stream-json):
```python
import os, subprocess

# MUST unset CLAUDECODE or nested sessions will be blocked
env = os.environ.copy()
env.pop("CLAUDECODE", None)

proc = subprocess.Popen(
    [
        "claude",
        "-p", prompt,                       # Non-interactive mode (REQUIRED)
        "--dangerously-skip-permissions",    # Auto-approve file writes
        "--no-session-persistence",          # Don't save session to disk
        "--max-turns", "25",                 # Limit agentic turns
        "--verbose",                         # REQUIRED for stream-json with -p
        "--output-format", "stream-json",    # Real-time NDJSON streaming
    ],
    cwd=str(project_dir),
    env=env,                                # Clean env without CLAUDECODE
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,                              # Line-buffered for real-time
)

# Read output line by line (NDJSON — one JSON object per line)
while True:
    line = proc.stdout.readline()
    if not line and proc.poll() is not None:
        break
    if line:
        event = json.loads(line)
        # event["type"] is: "system", "assistant", "user", "result", "rate_limit_event"
        # assistant content blocks: "text", "tool_use", "thinking"
        print(line, end="")
```

### Key flags:
| Flag | What it does |
|------|-------------|
| `-p "prompt"` | Non-interactive mode (print and exit) |
| `--dangerously-skip-permissions` | Auto-approve all tool calls |
| `--no-session-persistence` | Don't clutter session history |
| `--verbose` | Required for stream-json with -p |
| `--output-format stream-json` | Real-time NDJSON streaming (each event = 1 line) |
| `--output-format json` | Single JSON result (no streaming) |
| `--max-turns 25` | Limit agentic turns |
| `--allowedTools "Bash,Read,Edit"` | Only allow specific tools |

### Stream-JSON event format:
```
{"type":"system","subtype":"init",...}                          — skip
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{...}}]}} — tool call
{"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}  — text output
{"type":"assistant","message":{"content":[{"type":"thinking","thinking":"..."}]}} — thinking
{"type":"user","message":{"content":[{"type":"tool_result",...}]}}  — skip
{"type":"result","result":"..."}                                — final result
{"type":"rate_limit_event",...}                                  — skip
```

### Critical: CLAUDECODE env var
- Claude Code sets `CLAUDECODE=1` in its shell environment
- Nested `claude` calls fail with "cannot be launched inside another session"
- **Fix:** `env.pop("CLAUDECODE", None)` before subprocess

---

## PROVIDERS

| Provider | Command | Requires |
|----------|---------|----------|
| claude-max | `pca start` | Max subscription |
| claude-api | `pca start --provider claude-api` | API key |
| ollama | `pca start --provider ollama` | Local model |

---

## CURRENT STATUS

**Version:** 0.1.0 (MVP + Vision Tester)

**Done:**
- [x] Project structure
- [x] checkpoint.py (+ decisions limit fix)
- [x] tasks.py
- [x] validator.py
- [x] loop.py (+ Claude CLI fix + output capture)
- [x] cli.py (+ `pca test` command)
- [x] dashboard.py (+ XSS fix + stop fix)
- [x] Vision Tester (7/7 scenarios pass)
- [x] Playwright MCP integration
- [x] CURRENT_STAGE.md with cause-effect chains

**Done (2026-02-21 continued):**
- [x] Nested claude sessions fix (CLAUDECODE env var)
- [x] Auto-permissions (--dangerously-skip-permissions)
- [x] Full sandbox test on epotos-templates
- [x] A1 agent autonomously created 450-line provider.ts (DeepSeek + Ollama)
- [x] 20 dashboard screenshots documenting full web flow
- [x] Claude CLI reference docs in CLAUDE.md
- [x] Stream-JSON live logs (real-time NDJSON parsing, 6 icon types)
- [x] Post-session verification (3-tier: blocking/warning/anti-loop)
- [x] Git-optional validation (works with and without git)
- [x] Success criteria checking (heuristic parser in validator.py)
- [x] Anti-infinite-loop protection (baseline + max 3 retries + force_accept)

**In Progress:**
- [ ] E2E test of verification system (Task #14)
- See TODO.md and .a1/tasks.json
