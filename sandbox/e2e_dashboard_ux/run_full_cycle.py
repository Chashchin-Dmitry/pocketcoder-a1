#!/usr/bin/env python3
"""
E2E Full Cycle: Real project (epotos-templates)

Step 0: Verify clean state
Step 1: Initial screenshots
Step 2: Create 3 tasks via web form (Playwright)
Step 3: Verify tasks in backend (API + file)
Step 4: Start agent (POST /start)
Step 5: Live monitor: every 15s — screenshots, API, files, logs
Step 6: Wait for completion or timeout (5 min)
Step 7: Final verification (5 levels)
Step 8: Summary + all screenshots

From: absolutely nothing
To: tasks completed, verified, documented
"""

import json
import time
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# ============================
# CONFIG
# ============================
PORT = 7331
BASE = f"http://localhost:{PORT}"
PROJECT_DIR = Path("/home/telebot/projects/pocketcoder-a1/sandbox/epotos-templates")
SS_DIR = Path(__file__).parent / "screenshots_full_cycle"
SS_DIR.mkdir(exist_ok=True)

POLL_INTERVAL = 15
MAX_CYCLES = 20  # 20 * 15s = 5 min max

ss_count = 0
checks_passed = 0
checks_failed = 0


def ss(page, name):
    global ss_count
    ss_count += 1
    path = SS_DIR / f"{ss_count:02d}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [SS #{ss_count:02d}] {name}")
    return path


def check(condition, msg):
    global checks_passed, checks_failed
    if condition:
        checks_passed += 1
        print(f"  [OK] {msg}")
    else:
        checks_failed += 1
        print(f"  [FAIL] {msg}")


def api(endpoint):
    return requests.get(f"{BASE}{endpoint}", timeout=5).json()


# Tasks to create via web form
TASKS_TO_CREATE = [
    {
        "title": "Add health check endpoint",
        "description": "Create /api/health endpoint that returns {status: 'ok', timestamp: Date.now()}. File: src/app/api/health/route.ts"
    },
    {
        "title": "Add version info to health endpoint",
        "description": "Read version from package.json and return it in the /api/health response. Add a 'version' field."
    },
    {
        "title": "Create API documentation file",
        "description": "Create docs/API.md listing all API endpoints with methods, paths, and response examples. Include /api/health."
    },
]

# ============================
# STEP 0: Health check
# ============================
print("=" * 60)
print("STEP 0: Dashboard health check")
print("=" * 60)

try:
    resp = requests.get(f"{BASE}/api/status", timeout=5)
    status = resp.json()
    check(resp.status_code == 200, f"Dashboard alive on :{PORT}")
    check(status["checkpoint"]["status"] == "IDLE", "Checkpoint: IDLE (clean)")
    check(len(status["tasks"]) == 0, f"Tasks: {len(status['tasks'])} (clean)")
    check(not status["running"], "Agent: not running")
    print(f"  Project: epotos-templates")
except Exception as e:
    print(f"  [FATAL] Dashboard not running: {e}")
    sys.exit(1)


# ============================
# STEP 1: Initial screenshots
# ============================
print()
print("=" * 60)
print("STEP 1: Initial state (empty project)")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "initial_dashboard")

    # Cards visible
    cards = page.locator(".card").count()
    check(cards == 6, f"6 metric cards visible (got {cards})")

    # Card values are zero
    task_val = page.locator("#task-count").text_content()
    check("0/0" in task_val, f"Tasks card shows 0/0 (got: {task_val})")

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")
    ss(page, "initial_tasks_empty")

    # ============================
    # STEP 2: Create tasks via web form
    # ============================
    print()
    print("=" * 60)
    print("STEP 2: Create 3 tasks via web form")
    print("=" * 60)

    for i, task in enumerate(TASKS_TO_CREATE):
        page.goto(f"{BASE}/tasks")
        page.wait_for_load_state("networkidle")

        page.locator('input[name="task"]').fill(task["title"])
        page.locator('textarea[name="description"]').fill(task["description"])

        if i == 0:
            ss(page, "form_first_task")

        page.locator('button:has-text("Add Task")').click()
        page.wait_for_load_state("networkidle")

        print(f"  Created task {i+1}: {task['title']}")

    ss(page, "tasks_all_created")

    # ============================
    # STEP 3: Verify tasks in backend
    # ============================
    print()
    print("=" * 60)
    print("STEP 3: Backend verification (tasks created)")
    print("=" * 60)

    # API check
    status = api("/api/status")
    api_tasks = status["tasks"]
    check(len(api_tasks) == 3, f"API: {len(api_tasks)} tasks (expect 3)")

    for i, task in enumerate(TASKS_TO_CREATE):
        found = any(t["title"] == task["title"] for t in api_tasks)
        check(found, f"API: '{task['title'][:40]}' found")

    # File check
    tasks_file = json.loads((PROJECT_DIR / ".a1" / "tasks.json").read_text())
    check(
        len(tasks_file["tasks"]) == 3,
        f"File: {len(tasks_file['tasks'])} tasks in .a1/tasks.json"
    )

    # Progress check
    progress = status["progress"]
    check(
        isinstance(progress, list) and progress[1] == 3,
        f"Progress: {progress} (expect [0, 3])"
    )

    # ============================
    # STEP 4: Start agent
    # ============================
    print()
    print("=" * 60)
    print("STEP 4: START AGENT")
    print("=" * 60)

    resp = requests.post(f"{BASE}/start", timeout=10)
    print(f"  POST /start → {resp.status_code}")
    time.sleep(3)

    status = api("/api/status")
    check(status["running"], "Agent is now running")
    print(f"  Checkpoint: {status['checkpoint']['status']}")

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "agent_just_started")

    # ============================
    # STEP 5-6: Live monitor until completion
    # ============================
    print()
    print("=" * 60)
    print("STEP 5: LIVE MONITORING (every 15s, max 5 min)")
    print("=" * 60)

    log_since = 0
    prev_tokens_in = 0
    prev_logs = 0
    cycle = 0

    for cycle in range(MAX_CYCLES):
        time.sleep(POLL_INTERVAL)
        elapsed = (cycle + 1) * POLL_INTERVAL

        # === FRONTEND ===
        page.goto(BASE)
        page.wait_for_load_state("networkidle")

        if cycle % 2 == 0:  # Screenshot every 30s
            ss(page, f"monitor_{elapsed}s")

        tokens_val = page.locator("#tokens-count").text_content()
        cost_val = page.locator("#cost-value").text_content()
        duration_val = page.locator("#duration-value").text_content()
        task_val = page.locator("#task-count").text_content()

        # === BACKEND: API ===
        status = api("/api/status")
        running = status["running"]
        metrics = status.get("metrics", {})
        progress = status["progress"]
        cp_status = status["checkpoint"].get("status", "?")
        tokens_in = metrics.get("tokens_in", 0)
        tokens_out = metrics.get("tokens_out", 0)
        tools_used = metrics.get("tools_used", 0)

        # === BACKEND: Log ===
        log = api(f"/api/log?since={log_since}")
        total_logs = log.get("total", 0)
        new_entries = log.get("entries", [])
        new_count = total_logs - prev_logs

        # === BACKEND: File ===
        tasks_data = json.loads(
            (PROJECT_DIR / ".a1" / "tasks.json").read_text()
        )
        done_count = sum(
            1 for t in tasks_data["tasks"] if t["status"] == "done"
        )
        total_count = len(tasks_data["tasks"])

        # === SYNC CHECK ===
        tokens_changed = tokens_in != prev_tokens_in
        logs_changed = total_logs != prev_logs

        # === PRINT STATUS ===
        done_emoji = "DONE" if done_count == total_count else "working"
        print(f"\n  [{elapsed:3d}s] running={running} cp={cp_status} [{done_emoji}]")
        print(f"    FRONT: tasks={task_val} tokens={tokens_val} "
              f"cost={cost_val} dur={duration_val}")
        print(f"    BACK:  tasks={done_count}/{total_count} "
              f"tokens={tokens_in:,}/{tokens_out:,} "
              f"tools={tools_used} logs={total_logs}")

        if tokens_changed or logs_changed:
            print(f"    SYNC: tokens={'CHANGED' if tokens_changed else 'same'} "
                  f"logs={'CHANGED(+' + str(new_count) + ')' if logs_changed else 'same'}")

        # Show latest log entries
        if new_entries:
            for e in new_entries[-3:]:
                etype = e.get("type", "?")
                line = e.get("line", "")[:70]
                print(f"    LOG [{etype:8s}] {line}")

        prev_tokens_in = tokens_in
        prev_logs = total_logs
        log_since = total_logs

        # === STOP CONDITIONS ===
        if not running and cycle > 0:
            print(f"\n  Agent finished after {elapsed}s!")
            break

        if done_count == total_count and total_count > 0:
            print(f"\n  All {total_count} tasks done! Waiting for agent to stop...")

    # ============================
    # STEP 7: Final verification
    # ============================
    print()
    print("=" * 60)
    print("STEP 7: Final verification (5 levels)")
    print("=" * 60)

    # LEVEL 1: Final screenshots
    print("  --- Level 1: Screenshots ---")
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "final_dashboard")

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")
    ss(page, "final_tasks")

    page.goto(f"{BASE}/log")
    page.wait_for_load_state("networkidle")
    ss(page, "final_log")

    # LEVEL 2: API
    print("  --- Level 2: API ---")
    status = api("/api/status")
    final_metrics = status.get("metrics", {})
    final_progress = status["progress"]
    check(not status["running"], "Agent stopped")

    done_api = sum(1 for t in status["tasks"] if t["status"] == "done")
    check(done_api > 0, f"API: {done_api}/{len(status['tasks'])} tasks done")

    # LEVEL 3: Files
    print("  --- Level 3: Files ---")
    tasks_final = json.loads(
        (PROJECT_DIR / ".a1" / "tasks.json").read_text()
    )
    done_file = sum(
        1 for t in tasks_final["tasks"] if t["status"] == "done"
    )
    check(
        done_file > 0,
        f"File: {done_file}/{len(tasks_final['tasks'])} tasks done"
    )

    # Check if new files were created
    cp_final = json.loads(
        (PROJECT_DIR / ".a1" / "checkpoint.json").read_text()
    )
    files_mod = cp_final.get("files_modified", [])
    for fp in files_mod:
        full_path = PROJECT_DIR / fp
        check(full_path.exists(), f"File exists: {fp}")

    # LEVEL 4: Sync check (frontend == backend)
    print("  --- Level 4: Front/Back sync ---")
    api_done = done_api
    file_done = done_file
    check(
        api_done == file_done,
        f"Sync: API({api_done}) == File({file_done})"
    )

    # LEVEL 5: Metrics
    print("  --- Level 5: Metrics ---")
    final_tokens_in = final_metrics.get("tokens_in", 0)
    final_tokens_out = final_metrics.get("tokens_out", 0)
    final_tools = final_metrics.get("tools_used", 0)
    final_duration = final_metrics.get("session_duration", 0)

    print(f"  Tokens: {final_tokens_in:,} in / {final_tokens_out:,} out")
    print(f"  Tools: {final_tools}")
    print(f"  Duration: {final_duration:.0f}s")
    check(final_tools > 0, f"Tools used: {final_tools}")

    log_final = api("/api/log?since=0")
    final_log_count = log_final.get("total", 0)
    print(f"  Log entries: {final_log_count}")
    check(final_log_count > 0, f"Log has {final_log_count} entries")

    # Count log types
    type_counts = {}
    for e in log_final.get("entries", []):
        t = e.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  Log types: {type_counts}")

    browser.close()


# ============================
# SUMMARY
# ============================
print()
print("=" * 60)
print("E2E FULL CYCLE SUMMARY")
print("=" * 60)
total = checks_passed + checks_failed
print(f"  Project: epotos-templates")
print(f"  Tasks created: {len(TASKS_TO_CREATE)}")
print(f"  Screenshots: {ss_count}")
print(f"  Checks: {checks_passed}/{total} passed")
print(f"  Monitor cycles: {cycle + 1}")
print(f"  Total time: ~{(cycle + 1) * POLL_INTERVAL}s")
if checks_failed > 0:
    print(f"  FAILED: {checks_failed} checks")
print(f"  Result: {'PASS' if checks_failed == 0 else 'PARTIAL'}")
print("=" * 60)
