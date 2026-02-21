# CURRENT STAGE — PocketCoder-A1

**Last updated**: 2026-02-21 18:00
**Status**: Phase 1 DONE + E2E VERIFIED, Dashboard Upgrade (6 features) DONE, E2E #2 PENDING

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

## WHAT'S NEXT

### Phase 2: Autonomy Improvements (from original roadmap)
- [ ] 2.1 Context monitoring (token usage tracking)
- [ ] 2.2 Git integration (auto-branch, status check)
- [ ] 2.3 Checkpoint improvement (diffs, crash recovery)

### E2E Test #2: Full User Journey
- [ ] Test all 6 new features through web interface
- [ ] Screenshots at every step
- [ ] Verify live logs, drag-drop, transform, queue message
