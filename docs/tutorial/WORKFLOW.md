# Testing Workflow Cheatsheet

Quick reference: what to do, in what order.

---

## Sequence (from 0 to N)

```
STEP 0: PREPARE
├── Kill old processes: lsof -ti:7331 | xargs kill
├── Reset .a1/checkpoint.json → IDLE
├── Reset .a1/tasks.json → empty
├── Start dashboard: pca ui --no-browser
└── Verify: curl localhost:7331/api/status

STEP 1: SCREENSHOT INITIAL STATE
├── Playwright: open dashboard, tasks page
├── screenshot() each page
└── Save as 01_dashboard_empty.png, 02_tasks_empty.png

STEP 2: ADD TASKS VIA WEB FORMS (Playwright)
├── page.goto("/tasks")
├── page.locator('input[name="task"]').fill("...")
├── page.locator('textarea[name="description"]').fill("...")
├── screenshot() — form filled
├── page.locator('button:has-text("Add")').click()
├── screenshot() — task added
├── REPEAT for each task
├── page.goto("/") — dashboard overview
└── screenshot() — shows N tasks, 0/N done

STEP 3: START AGENT
├── requests.post("/start") OR click "Start Agent" button
├── time.sleep(2) — let agent initialize
├── page.goto("/") — refresh dashboard
├── screenshot() — shows "Running" badge
└── Verify: /api/status → running=true

STEP 4: MONITOR (loop every 15s)
│
├── FRONTEND (Playwright):
│   ├── page.goto("/")
│   ├── screenshot() — progress bar, log entries
│   └── Visual check: Running badge, task progress
│
├── BACKEND — API:
│   ├── GET /api/status → running, progress [done, total]
│   ├── GET /api/log?since=N → new log entries with types
│   └── Print: elapsed, progress, log count
│
├── BACKEND — Files:
│   ├── Read .a1/checkpoint.json → status, session, files_modified
│   ├── Read .a1/tasks.json → task statuses
│   └── Check agent-created files exist
│
└── EXIT when: running=false OR timeout (5 min)

STEP 5: SCREENSHOT FINAL STATE
├── Dashboard — progress bar, completion badge
├── Tasks — all green checkmarks
├── Sessions — session log entry
├── Activity Log — timeline of events
└── Commits — git commits made by agent

STEP 6: BACKEND VERIFICATION
├── tasks.json: all status="done"?
├── checkpoint.json: status="COMPLETED"?
├── files_modified: each file exists on disk?
├── pytest -v: all tests pass?
├── ruff check: lint clean?
├── Log analysis: entry count, icon types
└── success_criteria: met? (if defined)

STEP 7: DOCUMENT
├── Update CURRENT_STAGE.md with results
├── Count: screenshots, tests, tasks, time
├── Note: bugs found, lessons learned
└── git commit + push
```

---

## Tools Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Take screenshot | Playwright | `page.screenshot(path="...")` |
| Fill form | Playwright | `page.locator('input').fill("...")` |
| Click button | Playwright | `page.locator('button:has-text("...")').click()` |
| Check API | requests | `requests.get("http://localhost:7331/api/status").json()` |
| Read data file | Python | `json.loads(Path(".a1/tasks.json").read_text())` |
| Run tests | subprocess | `subprocess.run(["python3", "-m", "pytest", "-v"])` |
| Run lint | subprocess | `subprocess.run(["ruff", "check", "."])` |

---

## API Endpoints for Testing

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/status` | GET | `{running, status, session, progress: [done, total], current_task}` |
| `/api/log?since=N` | GET | `{entries: [{type, text, time}], total}` |
| `/start` | POST | Start agent |
| `/stop` | POST | Stop agent |
| `/add-task` | POST | Add task (form: `task=...&description=...`) |
| `/queue-message` | POST | Send message to agent (form: `message=...`) |

---

## Log Entry Types (icon types)

| Type | Icon | Meaning |
|------|------|---------|
| `read` | book | Agent reading a file |
| `edit` | pencil | Agent editing a file |
| `write` | file+ | Agent creating a file |
| `bash` | terminal | Agent running a command |
| `thinking` | chat | Agent reasoning |
| `text` | paragraph | Agent text output |

---

## Verification Tiers

```
BLOCKING (must pass to accept "COMPLETED"):
  ✓ syntax — all .py files compile
  ✓ tests — pytest passes
  ✓ files — files_modified actually exist
  ✓ criteria — success_criteria met

WARNING (log but don't block):
  ⚠ lint — ruff check
  ⚠ build — python -m build
  ⚠ git — uncommitted changes

ANTI-LOOP:
  ↻ baseline — pre-existing issues don't count
  ↻ max 3 retries — then force accept
```
