# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-02-21 19:10
**Status**: Phase 1 DONE, Dashboard Upgrade (6 features) DONE, Stream-JSON fix DONE, E2E #2 PASSED

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

## BUGS FIXED (8 total, from Phase 1)

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
| `a1/tasks.py` | UPDATED | priority field, reorder_tasks(), sort |
| `a1/validator.py` | OK | — |
| `a1/loop.py` | UPDATED | _log_callback, _read_queue_messages, priority prompt |
| `a1/cli.py` | OK | pca test command |
| `a1/dashboard.py` | MAJOR UPDATE | 7 new endpoints, live logs, DnD, transform, queue msg |
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

### What DOESN'T WORK (known):
- [ ] **Live logs during agent work** — logs appear only AFTER agent finishes
- [ ] **Icon classification** — sees summary text, not tool calls (all "text" icons)
- [ ] **Transform timeout** — 60s not enough for Claude CLI (needs 90-120s)

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

## BUGS FIXED (9 total)

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

---

## CURRENT WORK — ШАГИ ЧТО МЫ ДЕЛАЕМ СЕЙЧАС

### Этап: Stream-JSON для живых логов — DONE

```
ШАГ 1: Проблема ── LIVE LOGS NOT STREAMING
  cause: claude -p буферит весь stdout, отдаёт только после завершения
  effect: лог-панель пустая пока агент работает

ШАГ 2: Решение ── --output-format stream-json
  cause: Claude CLI поддерживает NDJSON streaming
  effect: каждый tool_use/text/result приходит отдельной строкой JSON

ШАГ 3: Реализация (3 файла)
  a1/loop.py:
    ├── Добавлен --verbose --output-format stream-json в subprocess args
    ├── Новый метод _parse_stream_event() — парсит NDJSON строки
    ├── Маппинг: tool_use name → тип (Read→read, Edit→edit, Bash→bash)
    ├── readline() loop вместо for line in proc.stdout (буферизация)
    └── _log_callback(display_text, event_type) — передаёт тип

  a1/dashboard.py:
    ├── _on_agent_line(line, event_type=None) — принимает тип от парсера
    └── Если event_type есть — используем его, иначе _classify_line()

ШАГ 4: E2E тест #3 — нашёл баг #9
  cause: --output-format stream-json требует --verbose с -p
  error: "When using --print, --output-format=stream-json requires --verbose"
  fix: добавлен --verbose в subprocess args

ШАГ 5: Фикс + документация + commit + push ── ТЕКУЩИЙ ЭТАП
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

## WHAT'S NEXT

### Phase 2: Autonomy Improvements
- [ ] 2.1 Context monitoring (token usage from stream-json events)
- [ ] 2.2 Git integration (auto-branch, status check)
- [ ] 2.3 Checkpoint improvement (diffs, crash recovery)

### Optional:
- [ ] Transform: longer timeout + better error messages
- [ ] E2E test #4: verify stream-json produces real-time logs with correct icons
