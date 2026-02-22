#!/usr/bin/env python3
"""
Full E2E test: Web Forms -> Agent -> Verification
Step 0 to Step N with parallel frontend + backend monitoring

Usage:
    python3 e2e_test.py /path/to/test-project

Prerequisites:
    pip install playwright requests
    playwright install chromium
    pip install -e /path/to/pocketcoder-a1
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# --- Config ---
PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
BASE_URL = "http://localhost:7331"
SS_DIR = PROJECT_DIR / "screenshots"
SS_DIR.mkdir(exist_ok=True)
MONITOR_INTERVAL = 15  # seconds between checks
MONITOR_TIMEOUT = 300  # 5 minutes max

ss_count = 0


def screenshot(page, name):
    """Take a numbered screenshot."""
    global ss_count
    ss_count += 1
    path = SS_DIR / f"{ss_count:02d}_{name}.png"
    page.screenshot(path=str(path))
    print(f"  [screenshot #{ss_count}] {name}")
    return path


def check_api(endpoint, method="GET", **kwargs):
    """Call API and return JSON."""
    url = f"{BASE_URL}{endpoint}"
    if method == "GET":
        return requests.get(url, **kwargs).json()
    return requests.post(url, **kwargs).json()


def read_json(path):
    """Read a JSON file."""
    with open(path) as f:
        return json.load(f)


# ========================================
# STEP 0: Prepare
# ========================================
print("=" * 60)
print("STEP 0: Prepare")
print("=" * 60)

# Kill old dashboard
subprocess.run("lsof -ti:7331 | xargs kill 2>/dev/null", shell=True)
time.sleep(1)

# Reset checkpoint to IDLE
cp_file = PROJECT_DIR / ".a1" / "checkpoint.json"
if cp_file.exists():
    cp = json.loads(cp_file.read_text())
    cp["status"] = "IDLE"
    cp["session"] = 0
    cp["files_modified"] = []
    cp["decisions"] = []
    cp["next_steps"] = []
    cp_file.write_text(json.dumps(cp, indent=2))
    print(f"  Checkpoint reset to IDLE")

# Reset tasks (remove all tasks)
tasks_file = PROJECT_DIR / ".a1" / "tasks.json"
if tasks_file.exists():
    tasks_data = json.loads(tasks_file.read_text())
    tasks_data["tasks"] = []
    tasks_data["next_id"] = 1
    tasks_file.write_text(json.dumps(tasks_data, indent=2))
    print(f"  Tasks cleared")

# Start dashboard
print("  Starting dashboard...")
dash_proc = subprocess.Popen(
    [
        "python3",
        "-c",
        f"import sys; sys.path.insert(0, '.'); "
        f"from a1.dashboard import run_dashboard; "
        f"run_dashboard('{PROJECT_DIR}', port=7331)",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(3)

# Verify
resp = requests.get(f"{BASE_URL}/api/status")
assert resp.status_code == 200, f"Dashboard not running: {resp.status_code}"
status = resp.json()
print(f"  Dashboard running: status={status['status']}, progress={status['progress']}")


# ========================================
# STEP 1-N: Playwright E2E Test
# ========================================
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # ========================================
    # STEP 1: Initial State Screenshots
    # ========================================
    print("\n" + "=" * 60)
    print("STEP 1: Initial State")
    print("=" * 60)

    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "dashboard_empty")

    page.goto(f"{BASE_URL}/tasks")
    page.wait_for_load_state("networkidle")
    screenshot(page, "tasks_empty")

    # ========================================
    # STEP 2: Add Tasks via Web Forms
    # ========================================
    print("\n" + "=" * 60)
    print("STEP 2: Add Tasks via Web Forms")
    print("=" * 60)

    # Task 1
    page.locator('input[name="task"]').fill("Write pytest tests for calculator.py")
    page.locator('textarea[name="description"]').fill(
        "Create tests/test_calculator.py with tests for add, subtract, "
        "multiply, divide. Include edge cases: division by zero, "
        "negative numbers, floats."
    )
    screenshot(page, "filling_task1")

    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")
    screenshot(page, "task1_added")

    # Verify backend
    tasks = read_json(tasks_file)["tasks"]
    print(f"  Backend: {len(tasks)} task(s) in tasks.json")

    # Task 2
    page.goto(f"{BASE_URL}/tasks")
    page.wait_for_load_state("networkidle")

    page.locator('input[name="task"]').fill("Create README.md with usage examples")
    page.locator('textarea[name="description"]').fill(
        "Write README.md explaining calculator.py with code examples for each function."
    )
    screenshot(page, "filling_task2")

    page.locator('button:has-text("Add")').click()
    page.wait_for_load_state("networkidle")
    screenshot(page, "task2_added")

    # Verify backend
    tasks = read_json(tasks_file)["tasks"]
    print(f"  Backend: {len(tasks)} task(s) in tasks.json")
    for t in tasks:
        print(f"    [{t['status']}] #{t.get('priority', '?')} {t['title']}")

    # Dashboard overview
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "dashboard_with_tasks")

    # ========================================
    # STEP 3: Start Agent
    # ========================================
    print("\n" + "=" * 60)
    print("STEP 3: Start Agent")
    print("=" * 60)

    requests.post(f"{BASE_URL}/start")
    time.sleep(2)
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    screenshot(page, "agent_running")

    status = check_api("/api/status")
    print(f"  Agent started: running={status['running']}")

    # ========================================
    # STEP 4: Monitor (Frontend + Backend)
    # ========================================
    print("\n" + "=" * 60)
    print("STEP 4: Monitor Agent")
    print("=" * 60)

    log_since = 0
    iterations = MONITOR_TIMEOUT // MONITOR_INTERVAL

    for i in range(iterations):
        time.sleep(MONITOR_INTERVAL)

        # --- FRONTEND: Screenshot ---
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        screenshot(page, f"monitor_{(i+1)*MONITOR_INTERVAL}s")

        # --- BACKEND: API Status ---
        status = check_api("/api/status")
        progress = status["progress"]

        # --- BACKEND: Log Entries ---
        log = check_api(f"/api/log?since={log_since}")
        new_entries = log.get("entries", [])
        log_since = log.get("total", log_since)

        # --- BACKEND: Checkpoint ---
        cp = read_json(cp_file)

        # --- Print combined status ---
        elapsed = (i + 1) * MONITOR_INTERVAL
        done = progress[0] if isinstance(progress, list) else progress.get("done", 0)
        total = progress[1] if isinstance(progress, list) else progress.get("total", 0)
        print(
            f"  [{elapsed}s] running={status['running']} "
            f"progress={done}/{total} "
            f"logs={log_since} "
            f"checkpoint={cp['status']}"
        )

        # Log new entries
        for e in new_entries:
            icon = e.get("type", "text")
            text = e.get("text", "")[:70]
            print(f"    [{icon:8s}] {text}")

        if not status["running"]:
            print(f"\n  Agent finished after {elapsed}s")
            break

    # ========================================
    # STEP 5: Final State Screenshots
    # ========================================
    print("\n" + "=" * 60)
    print("STEP 5: Final State")
    print("=" * 60)

    for name, path in [
        ("dashboard", "/"),
        ("tasks", "/tasks"),
        ("sessions", "/sessions"),
        ("log", "/log"),
        ("commits", "/commits"),
    ]:
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_load_state("networkidle")
        screenshot(page, f"final_{name}")

    browser.close()


# ========================================
# STEP 6: Backend Verification
# ========================================
print("\n" + "=" * 60)
print("STEP 6: Backend Verification")
print("=" * 60)

# Tasks
tasks = read_json(tasks_file)["tasks"]
done_count = sum(1 for t in tasks if t["status"] == "done")
total_count = len(tasks)
print(f"  Tasks: {done_count}/{total_count} done")
for t in tasks:
    print(f"    [{t['status']:12s}] {t['title']}")

# Checkpoint
cp = read_json(cp_file)
print(f"  Checkpoint: {cp['status']}, session={cp['session']}")
print(f"  Files modified: {cp.get('files_modified', [])}")
print(f"  Decisions ({len(cp.get('decisions', []))}):")
for d in cp.get("decisions", [])[-5:]:
    print(f"    - {d}")

# Files exist?
print("  File verification:")
for fp in cp.get("files_modified", []):
    full_path = PROJECT_DIR / fp
    exists = full_path.exists()
    size = full_path.stat().st_size if exists else 0
    print(f"    {'[OK]' if exists else '[MISSING]':10s} {fp} ({size} bytes)")

# Tests pass?
print("  Running tests...")
result = subprocess.run(
    ["python3", "-m", "pytest", "-v", "--tb=short"],
    cwd=str(PROJECT_DIR),
    capture_output=True,
    text=True,
)
passed = result.stdout.count(" PASSED")
failed = result.stdout.count(" FAILED")
print(f"    pytest: {passed} passed, {failed} failed (exit code {result.returncode})")

# Lint
result = subprocess.run(
    ["ruff", "check", "."],
    cwd=str(PROJECT_DIR),
    capture_output=True,
    text=True,
)
print(f"    ruff: {'clean' if result.returncode == 0 else result.stdout.strip()}")

# Log analysis
log = requests.get(f"{BASE_URL}/api/log?since=0").json()
entries = log.get("entries", [])
types = {}
for e in entries:
    t = e.get("type", "text")
    types[t] = types.get(t, 0) + 1
print(f"  Log: {len(entries)} entries, types: {types}")


# ========================================
# Summary
# ========================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Tasks: {done_count}/{total_count} done")
print(f"  Tests: {passed} passed, {failed} failed")
print(f"  Screenshots: {ss_count}")
print(f"  Status: {'PASS' if done_count == total_count and failed == 0 else 'FAIL'}")


# Cleanup
dash_proc.terminate()
print("\nDashboard stopped. Done!")
