# E2E Testing with Playwright + Claude Code: Step-by-Step Guide

> How we built autonomous E2E testing for a web dashboard with screenshots, parallel backend monitoring, and AI-powered validation.

---

## What This Guide Covers

This is a practical guide for testing web applications using:
- **Playwright** (Python) for browser automation and screenshots
- **Claude Code** as the AI agent doing the actual work
- **Parallel monitoring** — frontend (screenshots) + backend (API/files) at the same time
- **Post-session verification** — never trust the agent, always verify

We'll walk through the complete flow from step 0 (empty project) to step N (verified results with screenshots).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Setup](#2-project-setup)
3. [Start the Dashboard](#3-start-the-dashboard)
4. [Screenshot Initial State](#4-screenshot-initial-state)
5. [Add Tasks via Web Forms](#5-add-tasks-via-web-forms)
6. [Start the Agent](#6-start-the-agent)
7. [Monitor: Frontend + Backend in Parallel](#7-monitor-frontend--backend-in-parallel)
8. [Verify Results](#8-verify-results)
9. [Post-Session Verification System](#9-post-session-verification-system)
10. [Full Test Script](#10-full-test-script)
11. [Lessons Learned](#11-lessons-learned)

---

## 1. Prerequisites

```bash
# Python 3.10+
python3 --version

# Playwright
pip install playwright
playwright install chromium

# pytest (for running tests)
pip install pytest

# Claude Code CLI (for the agent)
# Already installed if you're reading this in Claude Code

# PocketCoder-A1
cd pocketcoder-a1
pip install -e .
```

### Key tools:

| Tool | What it does | When to use |
|------|-------------|-------------|
| `playwright` | Headless browser — navigate, fill forms, click, screenshot | Frontend testing |
| `requests` / `curl` | HTTP calls to API endpoints | Backend monitoring |
| File reads (`tasks.json`, `checkpoint.json`) | Direct state inspection | Verification |
| `pytest` | Run test suites | Validation |

---

## 2. Project Setup

### Step 0: Create a clean test project

```bash
# Create project directory
mkdir sandbox/test-project && cd sandbox/test-project

# Create a simple Python file to work with
cat > calculator.py << 'EOF'
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
EOF

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "calculator"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
EOF

# Initialize git
git init && git add -A && git commit -m "initial"

# Initialize PocketCoder-A1
pca init .
```

After `pca init`:
```
.a1/
├── checkpoint.json   # {"status": "IDLE", "session": 0, ...}
├── tasks.json        # {"tasks": [], "next_id": 1}
├── sessions/         # Session logs (empty)
└── checkpoints/      # Checkpoint archive (empty)
```

### Step 1: Create screenshots directory

```bash
mkdir -p screenshots
```

---

## 3. Start the Dashboard

```bash
# Start dashboard in background
pca ui --no-browser &

# Or programmatically:
python3 -c "
import sys; sys.path.insert(0, '/path/to/pocketcoder-a1')
from a1.dashboard import run_dashboard
run_dashboard('/path/to/test-project', port=7331)
" &

# Verify it's running
curl -s http://localhost:7331/api/status | python3 -m json.tool
```

Expected response:
```json
{
    "running": false,
    "status": "IDLE",
    "session": 0,
    "progress": [0, 0],
    "current_task": null
}
```

---

## 4. Screenshot Initial State

This is where Playwright comes in. We take screenshots of every page BEFORE any work is done.

```python
from playwright.sync_api import sync_playwright

base = "http://localhost:7331"
ss = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Screenshot all 7 pages
    pages = {
        "dashboard": "/",
        "tasks": "/tasks",
        "sessions": "/sessions",
        "log": "/log",
        "settings": "/settings",
        "commits": "/commits",
        "transform": "/transform",
    }

    for name, path in pages.items():
        page.goto(f"{base}{path}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{ss}/01_{name}_initial.png")
        print(f"[screenshot] {name}: {path}")

    browser.close()
```

**Result**: 7 screenshots showing empty dashboard, empty task list, etc.

---

## 5. Add Tasks via Web Forms

This is the key step — we use Playwright to fill forms just like a real user.

```python
from playwright.sync_api import sync_playwright

base = "http://localhost:7331"
ss = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # --- Task 1 ---
    page.goto(f"{base}/tasks")
    page.wait_for_load_state("networkidle")

    # Fill the form
    page.locator('input[name="task"]').fill("Write pytest tests for calculator.py")
    page.locator('textarea[name="description"]').fill(
        "Create tests/test_calculator.py with tests for add, subtract, "
        "multiply, divide. Include edge cases: division by zero, negative "
        "numbers, floats."
    )

    # Screenshot BEFORE clicking submit
    page.screenshot(path=f"{ss}/02_filling_task1.png")

    # Submit
    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")

    # Screenshot AFTER submit
    page.screenshot(path=f"{ss}/03_task1_added.png")

    # --- Task 2 ---
    page.goto(f"{base}/tasks")  # reload to get clean form
    page.wait_for_load_state("networkidle")

    page.locator('input[name="task"]').fill("Create README.md with usage examples")
    page.locator('textarea[name="description"]').fill(
        "Write README.md explaining what calculator.py does, "
        "with code examples for each function."
    )
    page.screenshot(path=f"{ss}/04_filling_task2.png")

    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{ss}/05_task2_added.png")

    # --- Verify on dashboard ---
    page.goto(base)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{ss}/06_dashboard_2tasks.png")

    browser.close()
```

**Parallel backend check** (run alongside or immediately after):
```python
import json

# Verify tasks were created in the data file
with open(".a1/tasks.json") as f:
    data = json.load(f)
    tasks = data["tasks"]

print(f"Tasks created: {len(tasks)}")
for t in tasks:
    print(f"  [{t['status']}] #{t['priority']} {t['title']}")

# Verify via API too
import requests
status = requests.get(f"{base}/api/status").json()
print(f"API progress: {status['progress']}")  # [0, 2]
```

---

## 6. Start the Agent

Two ways to start:

### Option A: Via Playwright (click the button)
```python
page.goto(base)
page.locator('button:has-text("Start Agent")').click()
page.screenshot(path=f"{ss}/07_agent_started.png")
```

### Option B: Via API
```python
import requests
requests.post(f"{base}/start")
```

**What happens under the hood:**
```
POST /start
  → dashboard.py starts SessionLoop in a thread
    → loop.py builds prompt from tasks.json + checkpoint.json
      → subprocess: claude -p <prompt> --dangerously-skip-permissions
                    --no-session-persistence --max-turns 25
                    --verbose --output-format stream-json
        → Claude agent reads files, writes code, runs tests
        → NDJSON events stream back line by line
          → loop._parse_stream_event() classifies each event
            → dashboard._on_agent_line() adds to AGENT_LOG_BUFFER
              → /api/log serves entries to frontend
                → JS updateLog() polls every 2s → DOM update
```

---

## 7. Monitor: Frontend + Backend in Parallel

This is the most important part. While the agent works, we monitor BOTH frontend and backend simultaneously.

### Frontend monitoring (Playwright screenshots):
```python
import time

for i in range(20):  # 5 minutes max (20 * 15s)
    time.sleep(15)

    page.goto(base)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{ss}/{8+i:02d}_monitor_{i*15}s.png")

    # Check if agent finished
    status = requests.get(f"{base}/api/status").json()
    print(f"[{i*15}s] running={status['running']}, progress={status['progress']}")

    if not status["running"]:
        print("Agent finished!")
        break
```

### Backend monitoring (API + files):
```python
import requests, json

log_since = 0

# Poll status and logs
status = requests.get(f"{base}/api/status").json()
print(f"Status: {status['status']}, running={status['running']}")
print(f"Progress: {status['progress']}")
print(f"Current task: {status.get('current_task')}")

# Get new log entries
log_data = requests.get(f"{base}/api/log?since={log_since}").json()
for entry in log_data.get("entries", []):
    icon = entry.get("type", "text")
    text = entry.get("text", "")[:80]
    print(f"  [{icon}] {text}")
log_since = log_data.get("total", log_since)

# Direct file inspection
with open(".a1/checkpoint.json") as f:
    cp = json.load(f)
    print(f"Checkpoint: session={cp['session']}, status={cp['status']}")
    print(f"Files modified: {cp.get('files_modified', [])}")
    print(f"Decisions: {cp.get('decisions', [])[-3:]}")
```

### Combined parallel monitoring pattern:

```python
import time, json, requests
from playwright.sync_api import sync_playwright

base = "http://localhost:7331"
ss = "screenshots"
log_since = 0

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Start agent
    requests.post(f"{base}/start")
    page.goto(base)
    page.screenshot(path=f"{ss}/10_agent_started.png")

    # Monitor loop
    for i in range(20):
        time.sleep(15)

        # ----- FRONTEND: Screenshot -----
        page.goto(base)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{ss}/{11+i:02d}_monitor.png")

        # ----- BACKEND: API status -----
        status = requests.get(f"{base}/api/status").json()
        progress = status["progress"]  # [done, total]
        running = status["running"]

        # ----- BACKEND: Log entries -----
        log = requests.get(f"{base}/api/log?since={log_since}").json()
        new_entries = log.get("entries", [])
        log_since = log.get("total", log_since)

        # ----- BACKEND: Direct file read -----
        with open(".a1/checkpoint.json") as f:
            cp = json.load(f)

        # Print combined status
        print(f"[{(i+1)*15}s] running={running} "
              f"progress={progress[0]}/{progress[1]} "
              f"logs={log_since} "
              f"checkpoint={cp['status']}")

        for e in new_entries:
            print(f"  [{e.get('type','?')}] {e.get('text','')[:60]}")

        if not running:
            break

    browser.close()
```

**Key insight**: We don't just look at the frontend. We verify the backend state (files, API, data) independently. The agent can't fool us if we check both.

---

## 8. Verify Results

After the agent stops, thorough verification:

### Frontend verification (screenshots of all pages):
```python
final_pages = [
    ("dashboard", "/"),
    ("tasks", "/tasks"),
    ("sessions", "/sessions"),
    ("log", "/log"),
    ("commits", "/commits"),
]

for name, path in final_pages:
    page.goto(f"{base}{path}")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{ss}/99_{name}_final.png")
```

### Backend verification:
```python
import json

# 1. All tasks done?
with open(".a1/tasks.json") as f:
    tasks = json.load(f)["tasks"]
all_done = all(t["status"] == "done" for t in tasks)
print(f"Tasks: {sum(1 for t in tasks if t['status']=='done')}/{len(tasks)} done")

# 2. Checkpoint says COMPLETED?
with open(".a1/checkpoint.json") as f:
    cp = json.load(f)
print(f"Checkpoint: {cp['status']}")
print(f"Files modified: {cp.get('files_modified', [])}")

# 3. Files actually exist?
from pathlib import Path
for fp in cp.get("files_modified", []):
    exists = Path(fp).exists()
    print(f"  {'[OK]' if exists else '[MISSING]'} {fp}")

# 4. Tests pass?
import subprocess
result = subprocess.run(
    ["python3", "-m", "pytest", "-v", "--tb=short"],
    capture_output=True, text=True
)
print(f"Tests: {'PASS' if result.returncode == 0 else 'FAIL'}")
print(result.stdout[-300:])

# 5. Log analysis
status = requests.get(f"{base}/api/status").json()
log = requests.get(f"{base}/api/log?since=0").json()
entries = log.get("entries", [])
types = {}
for e in entries:
    t = e.get("type", "text")
    types[t] = types.get(t, 0) + 1
print(f"Log entries: {len(entries)}")
print(f"Icon types: {types}")
```

---

## 9. Post-Session Verification System

The most important principle: **never trust the agent's self-report**.

### The Problem

```
Agent writes "status: done" in tasks.json
Agent writes "COMPLETED" in checkpoint.json
  └── But did it actually do the work?
  └── Did the tests pass?
  └── Do the files exist?
  └── Are the success criteria met?
```

### The Solution: Three-Tier Verification

```
After agent session completes:
  │
  ├── TIER 1: BLOCKING (must pass)
  │   ├── syntax: python -m py_compile → all .py files compile?
  │   ├── tests: pytest → all tests pass?
  │   ├── files: checkpoint.files_modified → files exist on disk?
  │   └── criteria: task.success_criteria → met?
  │
  ├── TIER 2: WARNING (log but don't block)
  │   ├── lint: ruff check → clean?
  │   ├── build: python -m build → succeeds?
  │   └── git: diff/status → changes committed?
  │
  └── TIER 3: Anti-infinite-loop
      ├── Baseline: capture state BEFORE agent runs
      ├── Only NEW failures count (pre-existing skip)
      ├── Max 3 retry attempts
      └── Force accept after 3 failures
```

### How it works in code:

```python
# In loop.py, after agent session completes:

# 1. Capture baseline BEFORE first session
baseline = validator.run_all()  # {syntax: OK, tests: FAIL, lint: OK, ...}

# 2. After session, verify
results = validator.run_all()

# 3. Compare with baseline — only new issues block
blocking_issues = []
for check_name in ["syntax", "tests"]:
    report = results[check_name]
    if report.result == "fail":
        # Was this already failing before agent ran?
        if baseline[check_name].result != "fail":
            blocking_issues.append(f"{check_name}: {report.message}")

# 4. If blocking issues found
if blocking_issues:
    if retry_count < 3:
        # Reset status, inject issues into next prompt
        checkpoint.status = "WORKING"
        next_prompt += f"VERIFICATION FAILED: {blocking_issues}. Fix it."
        retry_count += 1
    else:
        # Force accept — can't loop forever
        print("FORCE ACCEPTED after 3 retries")
        # Log issues for human review
```

### Success Criteria

Tasks can have a `success_criteria` field:

```json
{
    "id": "task_001",
    "title": "Write tests",
    "success_criteria": "tests pass, README.md exists"
}
```

The validator parses these heuristically:
- `"tests pass"` → run pytest, check exit code 0
- `"file X exists"` → check file on disk
- `"lint clean"` → run ruff, check exit code 0
- Anything else → can't verify automatically, trust agent

---

## 10. Full Test Script

Here's the complete E2E test flow we used:

```python
#!/usr/bin/env python3
"""
Full E2E test: Web Forms → Agent → Verification
Step 0 to Step N with parallel frontend + backend monitoring
"""

import json, time, subprocess, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- Config ---
PROJECT_DIR = Path("sandbox/test-verify")
BASE_URL = "http://localhost:7331"
SS_DIR = PROJECT_DIR / "screenshots"
SS_DIR.mkdir(exist_ok=True)

ss_count = 0

def screenshot(page, name):
    global ss_count
    ss_count += 1
    path = SS_DIR / f"{ss_count:02d}_{name}.png"
    page.screenshot(path=str(path))
    print(f"  [screenshot #{ss_count}] {name}")
    return path


# === STEP 0: Prepare ===
print("=== STEP 0: Prepare ===")

# Kill old dashboard
subprocess.run("lsof -ti:7331 | xargs kill 2>/dev/null", shell=True)
time.sleep(1)

# Reset checkpoint
cp_file = PROJECT_DIR / ".a1" / "checkpoint.json"
if cp_file.exists():
    cp = json.loads(cp_file.read_text())
    cp["status"] = "IDLE"
    cp["session"] = 0
    cp_file.write_text(json.dumps(cp, indent=2))

# Start dashboard
dash_proc = subprocess.Popen(
    ["python3", "-c", f"""
import sys; sys.path.insert(0, '.')
from a1.dashboard import run_dashboard
run_dashboard('{PROJECT_DIR}', port=7331)
"""],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
time.sleep(3)

# Verify
resp = requests.get(f"{BASE_URL}/api/status")
assert resp.status_code == 200
print(f"Dashboard running: {resp.json()}")


# === STEP 1-N: Playwright test ===
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # --- STEP 1: Initial screenshots ---
    print("\n=== STEP 1: Initial State ===")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "dashboard_empty")

    page.goto(f"{BASE_URL}/tasks")
    page.wait_for_load_state("networkidle")
    screenshot(page, "tasks_empty")

    # --- STEP 2: Add tasks via web ---
    print("\n=== STEP 2: Add Tasks ===")

    # Task 1
    page.locator('input[name="task"]').fill("Write pytest tests for calculator.py")
    page.locator('textarea[name="description"]').fill(
        "Create tests/test_calculator.py with tests for add, subtract, multiply, divide."
    )
    screenshot(page, "filling_task1")
    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")
    screenshot(page, "task1_added")

    # Task 2
    page.goto(f"{BASE_URL}/tasks")
    page.wait_for_load_state("networkidle")
    page.locator('input[name="task"]').fill("Create README.md with usage examples")
    page.locator('textarea[name="description"]').fill(
        "Write README.md explaining calculator.py with code examples."
    )
    screenshot(page, "filling_task2")
    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")
    screenshot(page, "task2_added")

    # Dashboard with tasks
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "dashboard_2tasks")

    # --- STEP 3: Start agent ---
    print("\n=== STEP 3: Start Agent ===")
    requests.post(f"{BASE_URL}/start")
    time.sleep(2)
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "agent_running")

    # --- STEP 4: Monitor (parallel frontend + backend) ---
    print("\n=== STEP 4: Monitor ===")
    log_since = 0
    for i in range(20):
        time.sleep(15)

        # Frontend
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        screenshot(page, f"monitor_{(i+1)*15}s")

        # Backend: API
        status = requests.get(f"{BASE_URL}/api/status").json()
        log = requests.get(f"{BASE_URL}/api/log?since={log_since}").json()
        log_since = log.get("total", log_since)

        # Backend: Files
        cp = json.loads(cp_file.read_text())

        print(f"  [{(i+1)*15}s] running={status['running']} "
              f"progress={status['progress']} "
              f"logs={log_since} checkpoint={cp['status']}")

        if not status["running"]:
            break

    # --- STEP 5: Final screenshots ---
    print("\n=== STEP 5: Final State ===")
    for name, path in [("dashboard", "/"), ("tasks", "/tasks"),
                       ("sessions", "/sessions"), ("log", "/log"),
                       ("commits", "/commits")]:
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")
        screenshot(page, f"final_{name}")

    browser.close()


# === STEP 6: Backend verification ===
print("\n=== STEP 6: Verify ===")

# Tasks
tasks = json.loads((PROJECT_DIR / ".a1/tasks.json").read_text())["tasks"]
done = sum(1 for t in tasks if t["status"] == "done")
print(f"Tasks: {done}/{len(tasks)} done")

# Checkpoint
cp = json.loads(cp_file.read_text())
print(f"Checkpoint: {cp['status']}")
print(f"Files: {cp.get('files_modified', [])}")

# Files exist?
for fp in cp.get("files_modified", []):
    exists = (PROJECT_DIR / fp).exists()
    print(f"  {'[OK]' if exists else '[MISSING]'} {fp}")

# Tests
result = subprocess.run(
    ["python3", "-m", "pytest", "-v", "--tb=short"],
    cwd=str(PROJECT_DIR), capture_output=True, text=True
)
passed = result.stdout.count(" PASSED")
print(f"Tests: {passed} passed, exit code {result.returncode}")

print(f"\nTotal screenshots: {ss_count}")
print("DONE!")

# Cleanup
dash_proc.terminate()
```

---

## 11. Lessons Learned

### 1. Don't trust the agent — verify everything

The agent writes its own status. It can say "done" without actually doing the work. Always independently verify:
- Files exist on disk
- Tests actually pass
- Code compiles
- Success criteria are met

### 2. Screenshot BEFORE and AFTER every action

Screenshots are your proof. Take them:
- Before filling a form (shows empty state)
- After filling but before submit (shows what you entered)
- After submit (shows result)
- During agent work (shows progress)
- Final state (shows completion)

### 3. Monitor frontend AND backend in parallel

The dashboard might show "Completed" but:
- Tasks might not all be "done" in tasks.json
- Files might not exist on disk
- Tests might be failing

Check both layers. The truth is in the backend files.

### 4. Use baseline comparison for verification

Pre-existing problems (lint warnings from before the agent ran) shouldn't fail verification. Capture the state BEFORE the agent starts, and only flag NEW issues.

### 5. Protect against infinite loops

If the agent can't fix tests after 3 attempts, force-accept and move on. Don't loop forever. Log the issues for human review.

### 6. Case sensitivity matters

Bug we found: `check_criteria("README.md exists")` was lowered to `"readme.md exists"` which doesn't match on Linux (case-sensitive filesystem). Always preserve original case for filenames.

### 7. Stream-JSON for real-time logs

Without `--verbose --output-format stream-json`, Claude CLI buffers everything and outputs only after completion. With it, you get NDJSON events in real-time — each tool call, each text response, as it happens.

### 8. Interactive > Batch for E2E tests

Running a batch Python script is fine for CI. But for development and documentation, interactive step-by-step testing with Playwright gives you:
- Better screenshots at exact moments
- Ability to inspect state between steps
- More natural testing flow
- Better documentation for articles

---

## Project Structure

```
docs/tutorial/
├── README.md              ← This file
├── screenshots/           ← Example screenshots from real test
│   ├── 01_dashboard_empty.png
│   ├── 02_tasks_empty.png
│   ├── 03_filling_task1.png
│   ├── ...
│   └── 16_final_commits.png
└── examples/
    └── e2e_test.py        ← Full test script (copy of section 10)
```
