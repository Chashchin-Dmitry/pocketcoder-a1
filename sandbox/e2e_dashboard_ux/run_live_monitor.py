#!/usr/bin/env python3
"""
E2E Live Monitor: Start agent → Watch sync → Stop

1. Start agent via POST /start
2. Monitor every 10s: screenshots + API + files
3. Watch tokens, logs, progress sync in real-time
4. Stop after N cycles or when agent finishes
"""

import json
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# ============================
# CONFIG
# ============================
PORT = 7331
BASE = f"http://localhost:{PORT}"
PROJECT_DIR = Path("/home/telebot/projects/pocketcoder-a1")
SS_DIR = Path(__file__).parent / "screenshots_live"
SS_DIR.mkdir(exist_ok=True)

POLL_INTERVAL = 10  # seconds
MAX_CYCLES = 18     # 18 * 10s = 3 minutes max
ss_count = 0


def ss(page, name):
    global ss_count
    ss_count += 1
    path = SS_DIR / f"{ss_count:02d}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [SS #{ss_count:02d}] {name}")
    return path


def api(endpoint):
    return requests.get(f"{BASE}{endpoint}", timeout=5).json()


# ============================
# STEP 0: Health check
# ============================
print("=" * 60)
print("STEP 0: Health check")
print("=" * 60)

try:
    status = api("/api/status")
    print(f"  Dashboard: OK on :{PORT}")
    print(f"  Tasks: {len(status['tasks'])}")
    print(f"  Running: {status['running']}")
    print(f"  Metrics: {status.get('metrics', {})}")
except Exception as e:
    print(f"  [FATAL] Dashboard not running: {e}")
    print(f"  Start: nohup bash /tmp/start_dash.sh > /tmp/pca_ui.log 2>&1 &")
    exit(1)


# ============================
# STEP 1: Initial state
# ============================
print()
print("=" * 60)
print("STEP 1: Initial state (before agent start)")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "before_start")

    # Read card values
    tokens_val = page.locator("#tokens-count").text_content()
    cost_val = page.locator("#cost-value").text_content()
    duration_val = page.locator("#duration-value").text_content()
    task_val = page.locator("#task-count").text_content()
    print(f"  Tasks: {task_val}")
    print(f"  Tokens: {tokens_val}")
    print(f"  Cost: {cost_val}")
    print(f"  Duration: {duration_val}")

    # ============================
    # STEP 2: Start agent
    # ============================
    print()
    print("=" * 60)
    print("STEP 2: START AGENT (POST /start)")
    print("=" * 60)

    try:
        resp = requests.post(f"{BASE}/start", timeout=10)
        print(f"  Response: {resp.status_code}")
        time.sleep(2)
    except Exception as e:
        print(f"  [ERROR] Cannot start: {e}")

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "just_started")

    status = api("/api/status")
    print(f"  Running: {status['running']}")
    print(f"  Checkpoint: {status['checkpoint'].get('status', '?')}")

    # ============================
    # STEP 3: LIVE MONITOR
    # ============================
    print()
    print("=" * 60)
    print("STEP 3: LIVE MONITORING (every 10s)")
    print("=" * 60)

    log_since = 0
    prev_tokens = "0"
    prev_logs = 0

    for cycle in range(MAX_CYCLES):
        time.sleep(POLL_INTERVAL)
        elapsed = (cycle + 1) * POLL_INTERVAL

        # === FRONTEND: Screenshot ===
        page.goto(BASE)
        page.wait_for_load_state("networkidle")
        ss(page, f"monitor_{elapsed}s")

        # Read card values from DOM
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

        # === BACKEND: Log ===
        log = api(f"/api/log?since={log_since}")
        new_entries = log.get("entries", [])
        total_logs = log.get("total", 0)
        new_count = total_logs - prev_logs

        # === BACKEND: Files ===
        tasks_data = json.loads(
            (PROJECT_DIR / ".a1" / "tasks.json").read_text()
        )
        done_tasks = sum(
            1 for t in tasks_data["tasks"] if t["status"] == "done"
        )
        total_tasks = len(tasks_data["tasks"])

        # === PRINT STATUS LINE ===
        print(f"\n  [{elapsed:3d}s] running={running} cp={cp_status}")
        print(f"    FRONT: tasks={task_val} tokens={tokens_val} "
              f"cost={cost_val} dur={duration_val}")
        print(f"    BACK:  tasks={done_tasks}/{total_tasks} "
              f"logs={total_logs} (+{new_count} new) "
              f"metrics={json.dumps(metrics)[:80]}")

        # Show new log entries
        if new_entries:
            for entry in new_entries[-5:]:  # last 5
                etype = entry.get("type", "?")
                line = entry.get("line", "")[:70]
                print(f"    LOG [{etype:8s}] {line}")

        # Sync check
        tokens_changed = tokens_val != prev_tokens
        logs_changed = total_logs != prev_logs
        if tokens_changed or logs_changed:
            print(f"    >>> SYNC: tokens {'CHANGED' if tokens_changed else 'same'}, "
                  f"logs {'CHANGED' if logs_changed else 'same'}")

        prev_tokens = tokens_val
        prev_logs = total_logs
        log_since = total_logs

        # Stop condition
        if not running and cycle > 0:
            print(f"\n  Agent stopped after {elapsed}s")
            break

    # ============================
    # STEP 4: Final state
    # ============================
    print()
    print("=" * 60)
    print("STEP 4: Final state")
    print("=" * 60)

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "final_dashboard")

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")
    ss(page, "final_tasks")

    # Final values
    status = api("/api/status")
    metrics = status.get("metrics", {})
    print(f"  Running: {status['running']}")
    print(f"  Checkpoint: {status['checkpoint'].get('status', '?')}")
    print(f"  Metrics: {json.dumps(metrics)}")
    print(f"  Progress: {status['progress']}")

    browser.close()


# ============================
# SUMMARY
# ============================
print()
print("=" * 60)
print("LIVE MONITOR SUMMARY")
print("=" * 60)
print(f"  Screenshots: {ss_count}")
print(f"  Monitor cycles: {min(cycle + 1, MAX_CYCLES)}")
print(f"  Total time: ~{(min(cycle + 1, MAX_CYCLES)) * POLL_INTERVAL}s")
print("=" * 60)
