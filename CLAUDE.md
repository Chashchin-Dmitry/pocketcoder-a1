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

## BUGS FIXED (2026-02-21)

1. **loop.py** — Claude CLI args: `["claude", prompt]` → `["claude", "-p", prompt]`
2. **loop.py** — Added output capture to session logs
3. **loop.py** — Nested sessions: unset `CLAUDECODE` env var
4. **loop.py** — Permissions: `--dangerously-skip-permissions` for autonomous mode
5. **dashboard.py** — Stop button now connected to `loop.stop()`
6. **dashboard.py** — XSS fixed with `html.escape()` on all user inputs
7. **checkpoint.py** — decisions[] limited to last 20 entries

---

## CLAUDE CLI REFERENCE (for subprocess calls)

### Correct way to call claude from Python:
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
    ],
    cwd=str(project_dir),
    env=env,                                # Clean env without CLAUDECODE
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

# Read output line by line
for line in proc.stdout:
    print(line, end="")
```

### Key flags:
| Flag | What it does |
|------|-------------|
| `-p "prompt"` | Non-interactive mode (print and exit) |
| `--dangerously-skip-permissions` | Auto-approve all tool calls |
| `--no-session-persistence` | Don't clutter session history |
| `--output-format json` | Structured JSON output |
| `--max-turns 5` | Limit agentic turns |
| `--allowedTools "Bash,Read,Edit"` | Only allow specific tools |

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

**In Progress:**
- See TODO.md and .a1/tasks.json
