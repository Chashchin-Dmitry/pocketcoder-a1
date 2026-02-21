# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-02-21
**Status**: Phase 1 DONE, Phase 2 IN PROGRESS, Bugs Fixing

---

## STATE MAP (cause → effect chains)

```
[Phase 1: Core MVP] ──DONE──> [Phase 2: Autonomy] ──IN PROGRESS
       │                              │
       │                              ├── 2.1 Context monitoring ── NOT STARTED
       │                              │     WHY BLOCKED: loop.py bug (Claude CLI args)
       │                              │     CAUSE: subprocess.run(["claude", prompt]) crashes
       │                              │     EFFECT: sessions never start → no context to monitor
       │                              │
       │                              ├── 2.2 Git integration ── NOT STARTED
       │                              │     WHY BLOCKED: no working sessions yet
       │                              │     CAUSE: can't test git commits without running agent
       │                              │
       │                              └── 2.3 Checkpoint improvement ── NOT STARTED
       │                                    WHY BLOCKED: no sessions = no checkpoints to improve
       │
       ├── checkpoint.py ── DONE but BUG
       │     BUG: decisions[] grows infinite (no limit)
       │     EFFECT: prompt gets bloated → context waste
       │
       ├── tasks.py ── DONE, working
       │
       ├── validator.py ── DONE, working
       │
       ├── loop.py ── DONE but 2 CRITICAL BUGS
       │     BUG 1: Claude CLI args wrong → agent can't start
       │     BUG 2: output not captured → no logs, blind execution
       │     EFFECT: entire autonomous loop is broken
       │
       ├── cli.py ── DONE, working
       │
       └── dashboard.py ── DONE but 2 BUGS
              BUG 1: Stop button not connected to loop._running
              BUG 2: XSS — unescaped user input in HTML
              EFFECT: can't stop agent from web + security hole
```

---

## CRITICAL PATH (what blocks what)

```
BUG: loop.py Claude CLI args ──────────────────────┐
  │                                                  │
  └─> FIX needed BEFORE anything else               │
       │                                             │
       v                                             │
Sessions can start ─────────────────────────────────┤
  │                                                  │
  ├─> Context monitoring becomes possible            │
  ├─> Checkpoints actually get created               │
  ├─> Git integration can be tested                  │
  └─> Vision Tester has something to test ──────────┘
                                                     │
                                                     v
                                            AUTONOMOUS TESTING
                                            (Phase we're building now)
```

---

## BUGS TO FIX (priority order)

| # | File | Bug | Impact | Blocks |
|---|------|-----|--------|--------|
| 1 | `loop.py:134` | Claude CLI: prompt as arg, not `--print -p` | **Agent can't start** | Everything |
| 2 | `loop.py:131` | No `capture_output` — blind execution | No logs, no debugging | Context monitoring |
| 3 | `dashboard.py:1131` | Stop sets global flag, not `loop._running` | Can't stop agent from web | Web control |
| 4 | `dashboard.py:748+` | XSS — raw HTML injection via task titles | Security hole | Production use |
| 5 | `checkpoint.py:93` | `decisions[]` unlimited growth | Context bloat over time | Long sessions |

---

## WHAT'S BEING BUILT NOW

### Vision-Based Autonomous Tester (`a1/tester/`)

```
PURPOSE: Test A1 the way a human QA would — visually

FLOW:
  Screenshot ──> Claude Vision analyzes ──> Decides action
      ^                                         │
      │                                         v
      └──── Takes screenshot after ◄─── Executes action
                                        (click/type/navigate)

WHY THIS APPROACH:
  - A1 is a web dashboard → visual testing catches real UX bugs
  - Can detect layout breaks, missing elements, wrong states
  - Autonomous — runs on cron, reports results
  - Uses Claude Code CLI (Max subscription) for vision analysis

DEPENDS ON:
  - Playwright (headless Chromium) — INSTALLED
  - Claude Code CLI — INSTALLED
  - Bug fixes in loop.py/dashboard.py — IN PROGRESS
```

### 7 Test Scenarios

| # | Scenario | Tests | Depends on |
|---|----------|-------|------------|
| 1 | Dashboard loads | Page renders, cards visible | dashboard.py works |
| 2 | Add task via web | Form submit, task appears | tasks.py + dashboard |
| 3 | Add thought | Form submit, thought appears | tasks.py + dashboard |
| 4 | Navigation | All 6 pages load correctly | dashboard routing |
| 5 | Theme toggle | Dark/light switch works | JS + CSS |
| 6 | Start/Stop agent | Status changes correctly | Bug #3 fix |
| 7 | API endpoint | /api/status returns JSON | dashboard API |

---

## FILE STATUS

| File | Status | Issues |
|------|--------|--------|
| `a1/__init__.py` | OK | - |
| `a1/checkpoint.py` | BUG | decisions[] unlimited |
| `a1/tasks.py` | OK | - |
| `a1/validator.py` | OK | - |
| `a1/loop.py` | 2 BUGS | Claude CLI args + no output capture |
| `a1/cli.py` | OK | needs `pca test` command |
| `a1/dashboard.py` | 2 BUGS | stop disconnect + XSS |
| `a1/tester/` | NEW | being created now |
| `pyproject.toml` | OK | needs test deps |
| `.mcp.json` | NEW | Playwright MCP config |

---

## NEXT ACTIONS (in order)

1. [x] Clone repo to `/home/telebot/projects/pocketcoder-a1/`
2. [x] Create CURRENT_STAGE.md (this file)
3. [ ] Set up Playwright MCP (`.mcp.json`)
4. [ ] Fix 5 bugs (loop.py, dashboard.py, checkpoint.py)
5. [ ] Build `a1/tester/` module (6 files)
6. [ ] Add `pca test` CLI command
7. [ ] Update README.md, CLAUDE.md, TODO.md
8. [ ] Git commit all changes
9. [ ] Run `pca test` — verify 7/7 scenarios pass
