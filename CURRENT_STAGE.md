# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-02-21 13:10
**Status**: Phase 1 DONE + E2E VERIFIED, Phase 2 IN PROGRESS

---

## STATE MAP (cause → effect chains)

```
[Phase 1: Core MVP] ──DONE──> [E2E Test] ──PASSED──> [Phase 2: Autonomy] ──IN PROGRESS
       │                           │                          │
       │                           │                          ├── 2.1 Context monitoring ── NOT STARTED
       │                           │                          │     UNBLOCKED: sessions work now
       │                           │                          │
       │                           │                          ├── 2.2 Git integration ── PARTIALLY DONE
       │                           │                          │     Agent does git commits autonomously
       │                           │                          │     TODO: auto-branch, status check
       │                           │                          │
       │                           │                          └── 2.3 Checkpoint improvement ── NOT STARTED
       │                           │
       │                           └── E2E Test Results:
       │                                 - 3/3 tasks completed autonomously
       │                                 - 4/4 pytest tests pass
       │                                 - 2 git commits made by agent
       │                                 - Dashboard shows real-time progress
       │                                 - 10 screenshots documenting flow
       │
       ├── checkpoint.py ── DONE (all bugs fixed)
       ├── tasks.py ── DONE
       ├── validator.py ── DONE
       ├── loop.py ── DONE (8 bugs fixed total)
       ├── cli.py ── DONE
       ├── dashboard.py ── DONE (all bugs fixed)
       └── tester/ ── DONE (7/7 scenarios)
```

---

## BUGS FIXED (8 total)

| # | File | Bug | Fix | Status |
|---|------|-----|-----|--------|
| 1 | loop.py | Claude CLI args wrong | `["claude", "-p", prompt]` | FIXED |
| 2 | loop.py | No output capture | `stdout=subprocess.PIPE` + log to file | FIXED |
| 3 | loop.py | Nested sessions crash | `env.pop("CLAUDECODE", None)` | FIXED |
| 4 | loop.py | No auto-permissions | `--dangerously-skip-permissions` | FIXED |
| 5 | loop.py | No max-turns limit | `--max-turns 25` | FIXED |
| 6 | loop.py | signal.signal() in thread | Check `threading.current_thread()` | FIXED |
| 7 | loop.py | Prompt missing file format | Added HOW TO UPDATE sections | FIXED |
| 8 | dashboard.py | XSS + stop button | `html.escape()` + `loop.stop()` | FIXED |

---

## E2E TEST RESULTS (2026-02-21)

### Test Project: `sandbox/test-e2e/`
- Simple Python project with `hello.py`
- 3 tasks added (1 via CLI, 2 via web dashboard)

### Flow:
```
1. pca init → .a1/ created
2. pca ui → Dashboard on :7331
3. POST /add-task → Task added via web form
4. POST /start → Agent started from web
5. Claude subprocess runs autonomously:
   - Read hello.py
   - Added goodbye() function
   - Created test_hello.py (4 tests)
   - Created README.md
   - Ran pytest (4/4 pass), ruff (clean)
   - 2 git commits
   - Updated tasks.json (all done)
   - Updated checkpoint.json (COMPLETED)
6. Dashboard shows real-time: Running → 1/3 → 3/3 → Completed
7. Agent stops automatically
```

### Screenshots (10):
| # | What | Shows |
|---|------|-------|
| 01 | Dashboard BEFORE | 0/3 tasks, Stopped |
| 02 | Tasks BEFORE | 1 pending task |
| 03 | Tasks after web add | 3 tasks visible |
| 04 | Dashboard RUNNING | Green "Running", Session #1 |
| 05 | Dashboard MID-WORK | 1/3 done, task_002 in progress |
| 06 | Tasks MID-WORK | Icons: done/in_progress/pending |
| 07 | Dashboard FINAL | 3/3 Completed (blue badge) |
| 08 | Tasks FINAL | All green checkmarks |
| 09 | Sessions | Session #1: COMPLETED, 3 files |
| 10 | Activity Log | Started → Stopped timeline |

### Agent Output (session_001.log):
- 4 pytest tests passed
- ruff clean
- 2 git commits: `bb8942f`, `4d744b8`
- Smart: recognized task_002 and task_003 as duplicates

### Files Created by Agent:
- `hello.py` — modified (added goodbye())
- `test_hello.py` — 4 tests
- `README.md` — project description

---

## WHAT'S NEXT (Phase 2)

### 2.1 Context Monitoring
- [ ] Parse Claude `--output-format json` for token usage
- [ ] Auto-checkpoint when approaching limit
- [ ] `/tokens` doesn't work in `-p` mode — need alternative

### 2.2 Git Integration (partially done)
- [x] Agent makes git commits autonomously
- [ ] Auto-create branch before work
- [ ] Check git status before commit
- [ ] Don't commit if tests fail

### 2.3 Checkpoint Improvement
- [ ] Save file diffs in checkpoint
- [ ] Crash recovery (Ctrl+C → checkpoint preserved)
- [ ] Multi-session continuation

---

## FILE STATUS

| File | Status | Last Change |
|------|--------|-------------|
| `a1/__init__.py` | OK | — |
| `a1/checkpoint.py` | OK | decisions[-20:] fix |
| `a1/tasks.py` | OK | — |
| `a1/validator.py` | OK | — |
| `a1/loop.py` | OK | 8 fixes: signal, max-turns, prompt format |
| `a1/cli.py` | OK | pca test command |
| `a1/dashboard.py` | OK | XSS + stop fixes |
| `a1/tester/` | OK | 7/7 scenarios |

---

## DASHBOARD API

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | `/` | Main dashboard page |
| GET | `/tasks` | Tasks page |
| GET | `/sessions` | Sessions page |
| GET | `/log` | Activity log |
| GET | `/settings` | Settings page |
| GET | `/commits` | Git commits page |
| GET | `/api/status` | JSON status (checkpoint + tasks + progress + running) |
| POST | `/add-task` | Add task (form: task=...) |
| POST | `/add-thought` | Add thought (form: thought=...) |
| POST | `/start` | Start agent |
| POST | `/stop` | Stop agent |
