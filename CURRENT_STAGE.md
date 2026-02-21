# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-02-21 21:30
**Status**: Phase 1 DONE, Dashboard (6 features) DONE, Stream-JSON DONE, Post-Session Verification DONE

---

## STATE MAP (cause → effect chains)

```
[Phase 1: Core MVP] ──DONE──> [E2E Test #1] ──PASSED──> [Dashboard Upgrade] ──DONE
       │                           │                          │
       │                           │                          ├── 1. Task forms (title+desc) ── DONE
       │                           │                          │     cause: forms only had title
       │                           │                          │     effect: textarea for description in both forms
       │                           │                          │
       │                           │                          ├── 2. Priorities + drag-drop ── DONE
       │                           │                          │     cause: tasks had no order
       │                           │                          │     effect: priority field, auto-assign, badges,
       │                           │                          │     HTML5 DnD, POST /api/reorder
       │                           │                          │     chain: tasks.py priority → dashboard badges →
       │                           │                          │            DnD JS → reorder API → tasks.json update
       │                           │                          │
       │                           │                          ├── 3. Auto-execution by priority ── DONE
       │                           │                          │     cause: agent didn't know about priorities
       │                           │                          │     effect: prompt says "LOWEST priority first"
       │                           │                          │     chain: loop.py prompt → get_next_task(sort) → agent
       │                           │                          │
       │                           │                          ├── 4. Real-time agent logs ── DONE
       │                           │                          │     cause: no visibility into agent work
       │                           │                          │     effect: live log panel + raw log + AJAX polling
       │                           │                          │     chain: loop._log_callback → _on_agent_line →
       │                           │                          │            AGENT_LOG_BUFFER → /api/log → JS fetch
       │                           │                          │            every 2s → DOM update (no reload)
       │                           │                          │     icons: read=book, edit=pencil, write=file+,
       │                           │                          │            bash=terminal, thinking=chat, text=paragraph
       │                           │                          │
       │                           │                          ├── 5. Queue message to agent ── DONE
       │                           │                          │     cause: no way to communicate with running agent
       │                           │                          │     effect: form visible when Running, saves to
       │                           │                          │            .a1/queue.json, loop reads on next session
       │                           │                          │     chain: dashboard form → POST /queue-message →
       │                           │                          │            queue.json → loop._read_queue_messages →
       │                           │                          │            prompt injection → agent reads
       │                           │                          │
       │                           │                          └── 6. Transform (text→tasks via LLM) ── DONE
       │                           │                                cause: manual task creation tedious
       │                           │                                effect: /transform page, AI breaks text into
       │                           │                                       tasks, preview with checkboxes, confirm
       │                           │                                chain: textarea → POST /transform →
       │                           │                                       claude -p "break into tasks" →
       │                           │                                       JSON parse → preview render →
       │                           │                                       POST /transform-confirm → tasks.json
       │                           │
       │                           └── [E2E Test #2] ── PENDING
       │                                 Full user journey with all 6 features
       │
       ├── checkpoint.py ── DONE (all bugs fixed)
       ├── tasks.py ── UPDATED (priority field, reorder, sort)
       ├── validator.py ── DONE
       ├── loop.py ── UPDATED (_log_callback, _read_queue_messages, priority prompt)
       ├── cli.py ── DONE
       ├── dashboard.py ── MAJOR UPDATE (7 new endpoints, live logs, DnD, transform page)
       └── tester/ ── DONE (7/7 scenarios)
```

---

## BUGS FIXED (12 total)

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
| 9 | loop.py | stream-json needs --verbose | Added `--verbose` flag | FIXED |
| 10 | loop.py | Parser wrong event format | tool_use in assistant content[] | FIXED |
| 11 | loop.py | f-string nested quotes | Extracted to variable | FIXED |
| 12 | validator.py | check_criteria case-sensitive | Re-match on original criteria (not lowered) | FIXED |

---

## DASHBOARD UPGRADE — 6 FEATURES (2026-02-21)

### Feature 1: Task Forms with Description
- **Before**: Only title field in Quick Add and Tasks page
- **After**: `<textarea name="description">` added to both forms
- **Backend**: `TaskManager.add_task(title, description=desc)` already supported

### Feature 2: Task Priorities + Drag-and-Drop
- **tasks.py**: `priority: int = 0` field, auto-assign, `reorder_tasks()`, sort in `get_next_task/get_summary`
- **Migration**: `_load_data()` auto-assigns priority by position if missing
- **Dashboard**: `#N` badges, `draggable="true"`, HTML5 DnD events, `POST /api/reorder`

### Feature 3: Auto-execution by Priority
- **loop.py**: Prompt includes "LOWEST priority number first"
- **tasks.py**: `get_next_task()` sorts by priority ascending

### Feature 4: Real-time Agent Logs
- **Architecture**: `loop._log_callback` → `_on_agent_line()` → `AGENT_LOG_BUFFER[]` → `/api/log` → JS fetch
- **UI**: Compact Action Feed (icons + time + text) + collapsible Raw Log (monospace)
- **Polling**: `updateLog()` every 2s, `updateStatus()` every 3s (dashboard only, other pages still 5s reload)
- **Line classifier**: `_classify_line()` → read/edit/write/bash/thinking/text → Bootstrap Icon

### Feature 5: Queue Message to Agent
- **Flow**: Form (visible when Running) → `POST /queue-message` → `.a1/queue.json` → `loop._read_queue_messages()` → injected into prompt
- **Format**: `{"messages": [{"text": "...", "added_at": "...", "read": false}]}`

### Feature 6: Transform (Text → Tasks via LLM)
- **New page**: `/transform` in navigation (magic icon)
- **Flow**: textarea → `POST /transform` → `claude -p "break into tasks" --max-turns 1` → JSON parse → preview with checkboxes → `POST /transform-confirm` → tasks.json
- **Error handling**: timeout (60s), CLI not found, JSON parse failure

---

## E2E TEST #1 RESULTS (2026-02-21)

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

---

## FILE STATUS

| File | Status | Last Change |
|------|--------|-------------|
| `a1/__init__.py` | OK | — |
| `a1/checkpoint.py` | OK | decisions[-20:] fix |
| `a1/tasks.py` | UPDATED | priority, reorder, success_criteria in summary |
| `a1/validator.py` | MAJOR UPDATE | has_git, check_git, check_files_exist, check_criteria |
| `a1/loop.py` | MAJOR UPDATE | stream-json, verification, baseline, anti-loop |
| `a1/cli.py` | OK | pca test command |
| `a1/dashboard.py` | MAJOR UPDATE | 7 endpoints, live logs, DnD, transform, queue msg |
| `a1/tester/` | OK | 7/7 scenarios |

---

## DATA FILES

| File | Purpose | Format |
|------|---------|--------|
| `.a1/checkpoint.json` | Session state | `{session, status, current_task, files_modified, decisions}` |
| `.a1/tasks.json` | Task list | `{tasks: [{id, title, description, status, priority, ...}], next_id}` |
| `.a1/queue.json` | Message queue | `{messages: [{text, added_at, read}]}` |
| `.a1/sessions/` | Session logs | `session_NNN.log` |
| `.a1/checkpoints/` | Checkpoint archive | `session_NNN.json` |

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
| GET | `/transform` | Transform page (text → tasks) |
| GET | `/api/status` | JSON status (checkpoint + tasks + progress + running) |
| GET | `/api/log?since=N` | Agent log entries since index N |
| POST | `/add-task` | Add task (form: task=..., description=...) |
| POST | `/add-thought` | Add thought (form: thought=...) |
| POST | `/start` | Start agent |
| POST | `/stop` | Stop agent |
| POST | `/queue-message` | Queue message for agent (form: message=...) |
| POST | `/api/reorder` | Reorder tasks (JSON: {order: [task_ids]}) |
| POST | `/transform` | AI transform text (form: text=...) → JSON tasks |
| POST | `/transform-confirm` | Confirm tasks (JSON: {tasks: [...]}) |

---

## E2E TEST #2 RESULTS (2026-02-21, epotos-templates)

### Test Project: `sandbox/epotos-templates/`
- Real Next.js project (Epotos Templates — document generation)
- 3 tasks: DeepSeek provider, Ollama backward compat, OpenAI provider

### Flow:
```
1. pca ui -d sandbox/epotos-templates → Dashboard on :7331
2. Screenshot all 7 pages (initial state)
3. POST /add-task → Added "Add OpenAI as third provider" via web form (title + desc)
4. POST /start → Agent started from web
5. Monitored: screenshots every 15s, /api/status polling, /api/log polling
6. POST /queue-message → Sent "Focus on task_001 first"
7. Agent completed 3/3 tasks (~150s):
   - Found real bug in provider.ts (function name mismatch)
   - Fixed callDeepSeekChat → callOpenAICompatibleChat (generic)
   - Created .env.example, updated .gitignore
8. Dashboard: Running → Completed, 3/3, 3 files modified
9. POST /stop
10. 36 screenshots documenting full journey
```

### What WORKS:
- [x] All 7 pages render correctly
- [x] Task forms with title + description
- [x] Priority badges (#1 #2 #3)
- [x] Start/Stop agent via web
- [x] Status badge: Stopped → Running → Completed (AJAX)
- [x] Queue message (form + queue.json created)
- [x] Transform page UI (textarea + AI Transform button)
- [x] Dark theme toggle
- [x] Commits page (fixed split bug)
- [x] Activity Log timeline

### What WAS BROKEN (now fixed):
- [x] **Live logs during agent work** — FIXED: `--verbose --output-format stream-json`
- [x] **Icon classification** — FIXED: parser reads tool_use from assistant content blocks
- [x] **Transform timeout** — FIXED: 120s → 300s

---

## BUG: LIVE LOGS NOT STREAMING (cause-effect chain)

```
ROOT CAUSE:
  claude -p (non-interactive mode)
    └── buffers ALL stdout internally
        └── releases output only when process exits
            └── our readline() loop gets nothing during execution
                └── _log_callback never fires while agent works
                    └── AGENT_LOG_BUFFER stays empty
                        └── /api/log returns 0 entries
                            └── JS updateLog() sees nothing
                                └── user sees empty "Agent Live Log"

ALSO:
  claude -p output = final summary text only
    └── no individual tool call lines (Read, Edit, Bash)
        └── _classify_line() sees "All 3 tasks completed..."
            └── classifies everything as "text" type
                └── all icons are bi-text-paragraph
                    └── no read/edit/bash/thinking icons
```

### FIX: `--output-format stream-json --verbose`

```
SOLUTION:
  claude -p --verbose --output-format stream-json
    └── outputs NDJSON events as they happen
        └── each event has type: "assistant", "tool_use", "tool_result", "text"
            └── we parse JSON per line in real-time
                ├── type="content_block_start" + tool_use → extract tool name
                │   └── classify: Read→"read", Edit→"edit", Bash→"bash", Write→"write"
                ├── type="content_block_delta" + text_delta → extract text content
                │   └── classify as "thinking"
                ├── type="assistant" → full message
                │   └── classify as "text"
                └── type="result" → final result text
                    └── classify as "text"

CRITICAL BUG FOUND DURING TEST:
  --output-format stream-json WITHOUT --verbose
    └── Error: "When using --print, --output-format=stream-json requires --verbose"
    └── agent loops outputting this error every 10s
    └── FIX: add --verbose flag

EFFECT:
  Real-time log entries with correct icons
    └── bi-book (Read), bi-pencil (Edit), bi-terminal (Bash), bi-file-earmark-plus (Write)
    └── entries appear every few seconds, not all at once
    └── user sees agent working in real-time
```

### Implementation Steps (all DONE):
1. [x] **loop.py**: Add `--output-format stream-json --verbose` to subprocess args
2. [x] **loop.py**: Add `_parse_stream_event()` method — NDJSON parser
3. [x] **loop.py**: Call `_log_callback(display_text, event_type)` with parsed type
4. [x] **dashboard.py**: Update `_on_agent_line(line, event_type=None)` — accept pre-classified type
5. [x] **loop.py**: readline() loop with bufsize=1 (not `for line in proc.stdout`)
6. [x] **Bug #9**: Added `--verbose` flag (required by stream-json with -p)

---

## TESTING METHODOLOGY

### Tools We Use:
| Tool | Purpose |
|------|---------|
| **Playwright** (Python) | Headless browser — navigate pages, fill forms, click buttons, take screenshots |
| **requests** (Python) | Direct API calls — POST /start, GET /api/status, GET /api/log |
| **curl** | Quick API health checks |
| **screenshots** | Visual proof at every step (saved to `screenshots/` dir) |

### Testing Pattern (how we test every feature):

```
STEP 1: PREPARE
  ├── Kill old processes (lsof -ti:7331 | xargs kill)
  ├── Reset checkpoint.json to IDLE
  ├── Start dashboard (python3 -c "run_dashboard(...)")
  └── Verify: curl /api/status → running=false

STEP 2: SCREENSHOT INITIAL STATE
  ├── Playwright: open each page
  ├── Screenshot: NN_page_initial.png
  └── Verify: page renders, no errors

STEP 3: USER ACTIONS (via Playwright)
  ├── Fill form fields (locator.fill())
  ├── Click buttons (locator.click())
  ├── Screenshot BEFORE and AFTER each action
  └── Verify: POST returns 200, data appears on page

STEP 4: AGENT EXECUTION
  ├── POST /start (or click Start Agent button)
  ├── Poll loop every 15s:
  │   ├── GET /api/status → check running, progress
  │   ├── GET /api/log?since=N → check log entries
  │   ├── Screenshot dashboard
  │   └── Print status to console
  ├── Wait for running=false or timeout
  └── Screenshot final state

STEP 5: VERIFY RESULTS
  ├── Screenshot all pages (Tasks, Sessions, Log, Commits)
  ├── Read .a1/tasks.json → all status="done"?
  ├── Read .a1/checkpoint.json → COMPLETED?
  ├── Read .a1/sessions/session_NNN.log → agent output
  ├── Read .a1/queue.json → messages read?
  └── Count screenshots, print summary

STEP 6: DOCUMENT
  ├── Update CURRENT_STAGE.md with results
  ├── Update MEMORY.md
  ├── Git commit + push
  └── List what works / what doesn't
```

### Example Test Script Structure:
```python
from playwright.sync_api import sync_playwright
import requests, time

base = "http://localhost:7331"
ss_dir = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # 1. Initial state
    page.goto(base)
    page.screenshot(path=f"{ss_dir}/01_initial.png")

    # 2. User action
    page.locator('input[name="task"]').fill("My task")
    page.locator('button:has-text("Add")').click()
    page.screenshot(path=f"{ss_dir}/02_after_add.png")

    # 3. Start agent
    page.locator('button:has-text("Start Agent")').click()

    # 4. Monitor
    for i in range(12):  # 3 minutes max
        time.sleep(15)
        status = requests.get(f"{base}/api/status").json()
        log = requests.get(f"{base}/api/log?since=0").json()
        print(f"{i*15}s: running={status['running']}, logs={log['total']}")
        page.goto(base)
        page.screenshot(path=f"{ss_dir}/{3+i:02d}_monitor.png")
        if not status['running']:
            break

    # 5. Final
    page.goto(f"{base}/tasks")
    page.screenshot(path=f"{ss_dir}/99_final_tasks.png")
    browser.close()
```

---

## BUGS FIXED (11 total)

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
| 9 | loop.py | stream-json needs --verbose | Added `--verbose` flag | FIXED |
| 10 | loop.py | Parser: wrong event format | tool_use in assistant content[], not content_block_start | FIXED |
| 11 | loop.py | f-string nested quotes | Extracted to variable before f-string | FIXED |

---

## CURRENT WORK — ШАГИ ЧТО МЫ ДЕЛАЕМ СЕЙЧАС

### Этап 1: Stream-JSON для живых логов — DONE

```
ШАГ 1: Проблема ── LIVE LOGS NOT STREAMING
  cause: claude -p буферит весь stdout, отдаёт только после завершения
  effect: лог-панель пустая пока агент работает

ШАГ 2: Решение ── --output-format stream-json
  cause: Claude CLI поддерживает NDJSON streaming
  effect: каждый tool_use/text/result приходит отдельной строкой JSON

ШАГ 3: Реализация (3 файла)
  a1/loop.py:
    ├── --verbose --output-format stream-json в subprocess args
    ├── _parse_stream_event() — парсит NDJSON
    ├── _classify_tool() — маппинг tool name → icon type
    ├── readline() loop с bufsize=1
    └── _log_callback(display_text, event_type)

  a1/dashboard.py:
    └── _on_agent_line(line, event_type=None) — pre-classified type
```

### Этап 2: Post-Session Verification — DONE

```
ШАГ 1: Анализ проблемы ── "агент врёт"
  cause: loop.py верит checkpoint.json blindly
  effect: агент может написать "COMPLETED" без реальной проверки
  validator.py существует но НИКОГДА не вызывается из loop

ШАГ 2: Решение ── три уровня проверки
  BLOCKING: syntax + tests + files_exist + success_criteria
  WARNING: lint + build + git (опционально)
  ANTI-LOOP: baseline + max 3 retries + force_accept

ШАГ 3: Реализация (3 файла)
  a1/loop.py:
    ├── _capture_baseline() — снимок ДО первой сессии
    ├── _is_new_issue() — сравнение с baseline
    ├── _verify_session() → dict с passed/blocking/warnings/retry
    ├── _get_verification_prompt() → текст для следующей сессии
    ├── start() — вставлена baseline + verify + retry логика
    └── Константы: BLOCKING_CHECKS, WARNING_CHECKS, MAX_VERIFY_RETRIES=3

  a1/validator.py:
    ├── has_git() — проверка наличия .git
    ├── _check_git() — diff + status (None если нет git)
    ├── check_files_exist(paths) — файлы на диске
    ├── check_criteria(criteria) — эвристика по success_criteria
    └── run_all() — добавлен опциональный git check

  a1/tasks.py:
    └── get_summary() — показывает SUCCESS CRITERIA для pending/in_progress

ШАГ 4: Анти-бесконечный-цикл
  cause: что если агент не может починить тесты?
  effect: без защиты loop будет крутиться вечно
  fix: MAX_VERIFY_RETRIES=3, baseline (пропуск старых проблем), force_accept
```

### Claude CLI subprocess — финальная команда:
```python
["claude", "-p", prompt,
 "--dangerously-skip-permissions",
 "--no-session-persistence",
 "--max-turns", "25",
 "--verbose",
 "--output-format", "stream-json"]
```

---

## POST-SESSION VERIFICATION SYSTEM (2026-02-21)

### Problem — "Не верим на слово"

```
BEFORE (weak — agent trusted blindly):
  Agent subprocess completes
    └── loop reads checkpoint.json
        └── status == "COMPLETED"? → trusts it → stops
            └── No check that anything was actually done
            └── No validator called
            └── success_criteria field existed but NEVER checked
            └── Agent could write "done" and lie

GAPS:
  ✗ Validator exists but never called from loop
  ✗ success_criteria in tasks.py — never verified
  ✗ files_modified in checkpoint — never checked if files exist
  ✗ Git diff — never used for verification
  ✗ No retry mechanism if verification fails
  ✗ No protection against infinite verification loops
```

### Solution — Three-tier verification gate

```
AFTER (robust — verify everything):
  Agent subprocess completes
    └── loop calls _verify_session()
        │
        ├── TIER 1: BLOCKING checks (must pass to accept "COMPLETED")
        │   ├── syntax: python -m py_compile on all .py files
        │   ├── tests: pytest -v
        │   ├── files_modified: do files from checkpoint.json actually exist on disk?
        │   ├── success_criteria: for each "done" task, verify criteria
        │   │   ├── "tests pass" → run pytest
        │   │   ├── "lint clean" → run ruff
        │   │   ├── "file X exists" → os.path.exists
        │   │   └── anything else → SKIP (can't verify programmatically)
        │   └── tasks: if checkpoint says COMPLETED, are ALL tasks really done?
        │
        ├── TIER 2: WARNING checks (log but don't block)
        │   ├── lint: ruff check
        │   ├── build: python -m build / npm run build
        │   └── git: diff --stat + status --porcelain (optional, works without git)
        │
        └── TIER 3: Anti-infinite-loop protection
            ├── Baseline: captured BEFORE first session (pre-existing issues don't count)
            ├── MAX_VERIFY_RETRIES = 3
            ├── retry_count tracked in checkpoint.last_verification
            └── After 3 failed retries → FORCE ACCEPT with warnings
                │
                ├── ALL PASS → trust "COMPLETED" → stop ✓
                │
                ├── BLOCKING FAIL (attempt < 3) → DON'T trust
                │   ├── checkpoint.status = "WORKING" (reset)
                │   ├── checkpoint.last_verification = {issues, retry_count}
                │   └── next session prompt includes:
                │       "VERIFICATION FAILED: [issues]. Fix before marking done."
                │       + retry count warning on last attempt
                │
                └── BLOCKING FAIL (attempt >= 3) → FORCE ACCEPT
                    └── Log warnings, stop loop, don't loop forever
```

### Files changed

| File | What changed | Why |
|------|-------------|-----|
| `a1/loop.py` | `_capture_baseline()`, `_is_new_issue()`, `_verify_session()`, `_get_verification_prompt()` | Core verification logic |
| `a1/loop.py` | `start()` — inserted baseline + verification + retry flow | Integration into main loop |
| `a1/loop.py` | Constants: `BLOCKING_CHECKS`, `WARNING_CHECKS`, `MAX_VERIFY_RETRIES` | Configuration |
| `a1/validator.py` | `has_git()`, `_check_git()`, `check_files_exist()`, `check_criteria()` | New validation methods |
| `a1/validator.py` | `run_all()` — added optional git check | Git detection (optional) |
| `a1/tasks.py` | `get_summary()` — shows `SUCCESS CRITERIA:` for non-done tasks | Agent sees criteria in prompt |

### Key design decisions

1. **Git is OPTIONAL**: `has_git()` checks `.git` dir. No git = skip silently. Git adds bonus checks.
2. **Baseline comparison**: Pre-existing lint issues don't block agent. Only NEW failures count.
3. **Force accept after 3 retries**: Prevents infinite loop. Logs all issues as warnings.
4. **BLOCKING vs WARNING**: Only syntax + tests block. Lint + build + git just warn.
5. **Verification in dashboard**: `_log_callback` sends verification status to live log panel.
6. **Prompt injection**: Failed verification details appear in next session's prompt so agent knows what to fix.

### Cause-effect chain: Agent lies about completion

```
Agent writes "COMPLETED" to checkpoint.json
  └── loop.py calls _verify_session()
      └── validator.run_all() finds: tests FAIL
          └── _is_new_issue("tests", report) → True (wasn't failing before)
              └── blocking_issues = ["tests: Tests failed"]
                  └── passed = False
                      └── checkpoint.status reset to "WORKING"
                          └── next session prompt includes:
                              "VERIFICATION FAILED (attempt 1/3)
                               BLOCKING ISSUES: tests: Tests failed
                               FIX THE BLOCKING ISSUES before marking done."
                              └── agent fixes tests → marks done again
                                  └── _verify_session() → tests PASS
                                      └── passed = True → loop stops ✓
```

### Cause-effect chain: Infinite loop prevention

```
Agent can't fix tests (3 attempts)
  └── attempt 1: _verify_session() → FAIL → retry_count=1 → reset to WORKING
      └── attempt 2: _verify_session() → FAIL → retry_count=2 → reset to WORKING
          └── attempt 3: _verify_session() → retry_count=3 >= MAX_VERIFY_RETRIES
              └── force_accept = True
                  └── passed = True (forced)
                      └── loop stops with warning:
                          "FORCE ACCEPTED after 3 retries"
                          └── issues logged for human review
```

### _verify_session() return format

```python
{
    "passed": bool,           # True if all blocking checks OK or force_accepted
    "force_accepted": bool,   # True if MAX_VERIFY_RETRIES reached
    "blocking_issues": [],    # List of strings: what failed (BLOCKING tier)
    "warnings": [],           # List of strings: what warned (WARNING tier)
    "retry_count": int,       # Current retry number (0 = first attempt)
    "summary": str,           # Human-readable summary for logs
}
```

### checkpoint.last_verification format

```json
{
    "passed": false,
    "blocking_issues": ["tests: Tests failed"],
    "warnings": ["lint: 3 issues"],
    "retry_count": 2,
    "session": 3
}
```

---

## WHAT'S NEXT

### Phase 2: Autonomy Improvements
- [x] 2.1 Post-session verification ("don't trust agent, verify")
- [x] 2.2 Git detection (optional — works with and without git)
- [ ] 2.3 Context monitoring (token usage from stream-json events)
- [ ] 2.4 Checkpoint improvement (diffs, crash recovery)
- [ ] 2.5 E2E test of verification system (Task #14)

---

## E2E TEST #3 RESULTS (2026-02-21, stream-json verification)

### Test Project: `sandbox/epotos-templates/`
- Same project, 1 task: "Create PROVIDERS.md"
- Purpose: verify stream-json produces real-time logs with correct icon types

### Results:
```
PASSED — 23 log entries, 6 icon types, 21 screenshots

Icon Distribution:
  text     : 7 entries  (bi-text-paragraph)
  read     : 5 entries  (bi-book)
  bash     : 5 entries  (bi-terminal)
  thinking : 3 entries  (bi-chat-dots)
  edit     : 2 entries  (bi-pencil)
  write    : 1 entries  (bi-file-earmark-plus)

Agent completed 1/1 task in 60 seconds, 1 session
```

### Bugs found and fixed during test:
1. Bug #9: `--output-format stream-json` requires `--verbose` with `-p`
2. Bug #10: Parser looked for `content_block_start` events, but actual format wraps tool_use in `assistant` messages

### Screenshots: `sandbox/epotos-templates/screenshots/e2e3/` (21 files)

---

## E2E TEST #4 RESULTS (2026-02-21, verification system + full web flow)

### Test Project: `sandbox/test-verify/`
- Fresh Python project: `calculator.py` (add/subtract/multiply/divide)
- Git initialized, 1 initial commit
- 2 tasks added via WEB FORMS (Playwright browser automation)

### Full automated flow:
```
STEP 0: Start dashboard on :7331
STEP 1: Screenshot all 7 pages (initial state) → 7 screenshots
STEP 2: Add tasks via web:
  - Playwright fills input[name="task"] + textarea[name="description"]
  - Click "Add" button → task created
  - Task 1: "Write pytest tests for calculator.py"
  - Task 2: "Create README.md with usage examples"
  - Screenshots after each add → 4 screenshots
STEP 3: Click "Start Agent" on dashboard → agent running
  - Screenshot → 1 screenshot
STEP 4: Monitor loop (12s interval):
  - GET /api/status → running, progress (done/total)
  - GET /api/log?since=N → new log entries with icon types
  - Read .a1/checkpoint.json → status, session, files_modified
  - Screenshot dashboard → 4 screenshots
  12s: running=true, 1/4, 5 logs (thinking, text, read)
  24s: running=true, 4/4, 12 logs (+read, read, read)
  36s: running=true, 4/4, 16 logs (+text, edit, read) → checkpoint: COMPLETED
  48s: running=false → agent stopped
STEP 5: Final screenshots all 7 pages → 7 screenshots
STEP 6: Backend verification
```

### Results:
```
PASSED — 4/4 tasks done, 23 tests, 2 git commits, 48 seconds

Agent output:
  - tests/test_calculator.py: 23 tests in 4 classes (TestAdd/Sub/Mul/Div)
  - tests/__init__.py: empty init
  - README.md: 60 lines with code examples
  - 2 git commits: "add pytest tests" + "add README"

Validator (manual check after test):
  [OK  ] syntax: 3 files
  [OK  ] tests: 23 passed
  [OK  ] lint: clean
  [FAIL] build: no build module (pre-existing → baseline skip)
  [OK  ] git: changes committed

Verification: PASSED CLEAN (no last_verification in checkpoint)
  → Agent did everything right, verification gate confirmed it

Icon distribution (20 log entries):
  read     : 9
  text     : 7
  bash     : 2
  thinking : 1
  edit     : 1

Screenshots: 23 total
```

### Bug found during test:
- Bug #12: `check_criteria("README.md exists")` → FAIL because `.lower()` turned "README.md" into "readme.md" (Linux case-sensitive). Fix: re-match on original criteria string.

### Screenshots: `sandbox/test-verify/screenshots/` (23 files)
| Range | What |
|-------|------|
| 01-07 | Initial state: all 7 pages |
| 08-09 | Task added via web form (title + description) |
| 10-11 | Tasks page + dashboard before start |
| 12 | Agent started (Running badge) |
| 13-16 | Monitoring: dashboard every 12s with progress |
| 17-23 | Final state: all 7 pages (4/4 completed) |
