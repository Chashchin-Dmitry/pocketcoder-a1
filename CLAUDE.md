# CLAUDE.md — PocketCoder-A1

## AFTER /clear — READ THIS FIRST!

```
1. Read CLAUDE.md (this file) — project overview + module map
2. Read CURRENT_STAGE.md — cause-effect chains, architecture, full manual
3. Read .a1/checkpoint.json — current state
4. Read .a1/tasks.json — task list
5. Read TODO.md — phases roadmap
6. Continue work from checkpoint
```

---

## WHAT IS THIS

**PocketCoder-A1** — autonomous coding agent (4882 lines Python, 13 modules):
- Works without human intervention (Claude CLI subprocess)
- Real-time dashboard with 6 metric cards, live logs, token tracking
- Saves state between sessions (checkpoint + task priorities)
- Post-session verification ("don't trust, verify" — 3-tier gate)
- Anti-infinite-loop protection (baseline + max 3 retries)
- Vision-based QA tester (screenshot → AI → action)

---

## MODULE MAP (13 modules, 4882 lines)

```
a1/                          # 3795 lines — Main code
├── __init__.py       (6)    # Version 0.1.0
├── loop.py           (744)  # Brain: subprocess → stream-json → verify → metrics
├── dashboard.py      (2038) # Web UI: 7 pages, 17 API, 6 cards, live logs
├── validator.py      (361)  # Eyes: syntax, tests, lint, build, git, criteria
├── cli.py            (289)  # CLI: pca init/task/start/status/ui/test/...
├── tasks.py          (211)  # Tasks: CRUD, priority, reorder, criteria
├── checkpoint.py     (146)  # State: session, status, metrics, decisions
└── tester/           (1087) # Vision QA agent
    ├── runner.py     (419)  # Main loop: scenario → steps → screenshot → analyze
    ├── scenarios.py  (203)  # 7 test scenarios
    ├── report.py     (193)  # HTML/JSON reports
    ├── analyzer.py   (142)  # Claude Vision API
    └── browser.py    (124)  # Playwright wrapper
```

### Module dependencies

```
cli.py ──────────┐
                  ├──→ loop.py ──→ checkpoint.py
dashboard.py ────┤               → tasks.py
                  │               → validator.py
                  └──→ tasks.py
                  └──→ checkpoint.py
```

---

## DATA DIRECTORY — .a1/

```
.a1/                           ← Created by `pca init`
├── checkpoint.json            ← Session state (status, metrics, decisions)
├── tasks.json                 ← Task list (id, title, priority, criteria)
├── queue.json                 ← Message queue for agent (created on send)
├── sessions/
│   └── session_NNN.log        ← Raw agent output per session
├── checkpoints/
│   └── session_NNN.json       ← Checkpoint snapshots
└── test-reports/
    └── latest.html            ← Vision QA reports
```

### Data formats

**checkpoint.json**:
```json
{
  "status": "IDLE|WORKING|COMPLETED",
  "session": 2,
  "current_task": "task_003",
  "files_modified": ["src/health.ts"],
  "decisions": ["Combined tasks 1+2"],
  "session_metrics": {
    "tokens_in": 12400, "tokens_out": 3200,
    "cache_read": 8000, "cache_creation": 1500,
    "tools_used": 58, "session_duration": 166
  }
}
```

**tasks.json**:
```json
{
  "tasks": [{
    "id": "task_001",
    "title": "Add health endpoint",
    "description": "Create /api/health...",
    "status": "pending|in_progress|done|blocked",
    "priority": 1,
    "success_criteria": "pytest passes",
    "phase": "2.1"
  }],
  "next_id": 2
}
```

---

## CONFIG — .claude/

```
.claude/
└── settings.local.json    ← MCP server config
```

```json
{
  "enabledMcpjsonServers": ["playwright"],
  "enableAllProjectMcpServers": true
}
```

Also `.mcp.json` in project root — Playwright MCP for browser automation:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-playwright"]
    }
  }
}
```

---

## CLI COMMANDS

```bash
pca init <dir>                   # Create .a1/ directory
pca task add "title"             # Add task
pca think "raw thought"          # Add thought (for transform)
pca tasks                        # Show all tasks with priorities
pca start                        # Start autonomous work (Claude Max)
pca start --task task_001        # Work on single task only
pca start --provider claude-api  # With Claude API
pca start --provider ollama      # With local model
pca status                       # Current checkpoint status
pca validate                     # Run all validation checks
pca ui                           # Launch web dashboard (:7331)
pca ui --no-browser              # Without opening browser
pca ui -d /path/to/project       # For specific project
pca log                          # Session history
pca test                         # Run all 7 vision QA tests
pca test -s 1                    # Run specific scenario
pca test --no-vision             # Without AI vision analysis
```

---

## DASHBOARD (7 pages, 17 API endpoints)

| Page | URL | What |
|------|-----|------|
| Dashboard | `/` | 6 cards, Start/Stop, live log |
| Tasks | `/tasks` | List + DnD + detail view |
| Sessions | `/sessions` | Session history |
| Log | `/log` | Activity timeline |
| Settings | `/settings` | Config (read-only) |
| Commits | `/commits` | Git history |
| Transform | `/transform` | Text → tasks via AI |

### 6 Metric Cards
| Card | Data | Source |
|------|------|--------|
| Tasks | `2/5 done` + progress bar | tasks.get_progress() |
| Session | `#3` + status badge | checkpoint.session |
| Tokens | `12.4K in / 3.2K out` | rate_limit_event metrics |
| Cost | `$0.08` per session | calculated from tokens |
| Duration | `48s` (live timer) | JS tickTimer() |
| Files | `3 modified` | checkpoint.files_modified |

### 8 Log Icon Types
| Type | Color | When |
|------|-------|------|
| read | blue | Claude reads file |
| edit | orange | Claude edits file |
| write | green | Claude creates file |
| bash | purple | Claude runs command |
| thinking | yellow | Claude thinks |
| text | gray | Text output |
| metric | indigo | Metrics update |
| verify | green | Verification result |

### Key API
| Method | Endpoint | What |
|--------|----------|------|
| GET | `/api/status` | Full status JSON (checkpoint + tasks + metrics) |
| GET | `/api/log?since=N` | Agent log entries from index N |
| POST | `/start` | Start agent |
| POST | `/stop` | Stop agent |
| POST | `/add-task` | Add task (form) |
| POST | `/queue-message` | Message to running agent |
| POST | `/api/reorder` | Reorder tasks (JSON) |
| POST | `/transform` | AI text→tasks |

---

## AUTONOMOUS WORK PROTOCOL

```
1. SESSION START
   └── _capture_baseline() → snapshot validation BEFORE work
   └── Read checkpoint.json + tasks.json
   └── build_prompt() → checkpoint + tasks + queue + verification errors

2. WORK (Claude subprocess)
   └── claude -p prompt --stream-json --verbose --dangerously-skip-permissions
   └── Real-time: _parse_stream_event() → log + metrics
   └── env.pop("CLAUDECODE") → prevent nested session crash

3. VERIFICATION (after each session)
   └── _verify_session()
       ├── BLOCKING: syntax, tests, files_exist, success_criteria
       ├── WARNING: lint, build, git
       └── ANTI-LOOP: baseline comparison, max 3 retries, force_accept
   └── PASS → accept COMPLETED → stop
   └── FAIL → reset to WORKING → inject errors into next prompt → retry

4. METRICS
   └── rate_limit_event → tokens_in/out/cache → session_metrics
   └── /api/status → dashboard cards (Tokens, Cost, Duration)
```

---

## VERIFICATION SYSTEM — "DON'T TRUST, VERIFY"

```
Agent says "COMPLETED"
  └── _verify_session()
      ├── TIER 1 BLOCKING (must pass):
      │   ├── syntax: py_compile all .py
      │   ├── tests: pytest
      │   ├── files_exist: checkpoint files on disk?
      │   └── success_criteria: heuristic check
      │
      ├── TIER 2 WARNING (log only):
      │   ├── lint: ruff
      │   ├── build: python -m build / npm run build
      │   └── git: diff + status (if .git exists)
      │
      └── TIER 3 ANTI-LOOP:
          ├── Baseline: pre-existing issues don't count
          ├── Max 5 retries → task BLOCKED + move to next
          ├── Single-task mode (--task): BLOCKED → stop
          └── Prompt injection: errors → next session prompt
```

---

## CLAUDE CLI SUBPROCESS (reference)

```python
import os, subprocess, json

env = os.environ.copy()
env.pop("CLAUDECODE", None)  # CRITICAL: prevent nested session crash

proc = subprocess.Popen(
    ["claude", "-p", prompt,
     "--dangerously-skip-permissions",
     "--no-session-persistence",
     "--max-turns", "25",
     "--verbose",
     "--output-format", "stream-json"],
    cwd=str(project_dir),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

while True:
    line = proc.stdout.readline()
    if not line and proc.poll() is not None:
        break
    if line:
        event = json.loads(line)
        # event["type"]: "system", "assistant", "user", "result", "rate_limit_event"
```

### Stream-JSON events:
```
assistant + tool_use  → agent reads/edits/writes/runs command
assistant + text      → agent text output
assistant + thinking  → agent thinking
rate_limit_event      → token usage (input/output/cache)
result                → final answer
system, user          → skip
```

### Critical flags:
| Flag | Why |
|------|-----|
| `-p prompt` | Non-interactive mode |
| `--dangerously-skip-permissions` | Auto-approve tools |
| `--verbose` | Required for stream-json with -p |
| `--output-format stream-json` | Real-time NDJSON |
| `--max-turns 25` | Prevent infinite work |
| `--no-session-persistence` | Don't save to history |

### CLAUDECODE env var:
Claude Code sets `CLAUDECODE=1`. Nested `claude` calls crash with "cannot launch inside another session". **Fix**: `env.pop("CLAUDECODE", None)` before subprocess.

---

## BUGS FIXED (13)

| # | File | Bug → Fix |
|---|------|-----------|
| 1 | loop.py | CLI args `["claude", prompt]` → added `-p` flag |
| 2 | loop.py | No output capture → `stdout=subprocess.PIPE` |
| 3 | loop.py | Nested session crash → `env.pop("CLAUDECODE")` |
| 4 | loop.py | No auto-permissions → `--dangerously-skip-permissions` |
| 5 | loop.py | No max-turns → `--max-turns 25` |
| 6 | loop.py | signal in thread → `threading.current_thread()` check |
| 7 | loop.py | Agent didn't know file formats → HOW TO UPDATE in prompt |
| 8 | dashboard.py | XSS + stop broken → `html.escape()` + `loop.stop()` |
| 9 | loop.py | stream-json error → added `--verbose` |
| 10 | loop.py | Parser wrong event format → tool_use in assistant content[] |
| 11 | loop.py | f-string nested quotes → extracted to variable |
| 12 | validator.py | Case-sensitive criteria → re-match on original string |
| 13 | dashboard.py | `$` in JS Template → escaped as `$$` |

---

## E2E TESTS (6/6 PASSED)

| # | What | Tasks | Checks | Time |
|---|------|-------|--------|------|
| 1 | Basic cycle | 3/3 | 10 SS | 90s |
| 2 | Real project (epotos) | 3/3 | 36 SS | 150s |
| 3 | Stream-JSON verify | 1/1 | 23 logs | 60s |
| 4 | Verification system | 4/4 | 23 tests | 48s |
| 5 | Dashboard UX | — | 77/77 | — |
| 6 | Full cycle (web→agent→done) | 3/3 | 22/22 | 165s |

---

## PROVIDERS

| Provider | Command | Requires |
|----------|---------|----------|
| claude-max | `pca start` | Max subscription |
| claude-api | `pca start --provider claude-api` | API key |
| ollama | `pca start --provider ollama` | Local model |

---

## CURRENT STATUS

**Version**: 0.1.0
**Code**: 4882 lines, 13 Python modules
**Dashboard**: 7 pages, 17 API endpoints, 12 features

**Done:**
- [x] Core: checkpoint, tasks, validator, loop, CLI
- [x] Dashboard: 7 pages, 17 API, 6 cards, live logs, DnD, transform
- [x] Stream-JSON: NDJSON parsing, 8 icon types, real-time
- [x] Verification: 3-tier gate, anti-loop, baseline
- [x] Token metrics: rate_limit_event → cards
- [x] Vision QA: 7 scenarios, Playwright
- [x] E2E: 6 tests passed
- [x] 13 bugs fixed

**In Progress:**
- [ ] Context monitoring (auto-checkpoint at 70%)
- [ ] Git integration (auto-branch, atomic commits)

**Next:** See TODO.md and .a1/tasks.json
