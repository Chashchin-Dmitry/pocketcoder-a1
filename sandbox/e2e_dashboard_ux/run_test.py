#!/usr/bin/env python3
"""
E2E Test: Dashboard UX/UI Upgrade
Tests: 6 cards, colored icons, task detail view, token metrics, responsive, API

From Step 0 (clean state) to Step N (full verification)
Uses: Playwright (real browser) + API (backend) + Files (disk)
"""

import json
import os
import subprocess
import sys
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
SS_DIR = Path(__file__).parent / "screenshots"
SS_DIR.mkdir(exist_ok=True)

ss_count = 0
checks_passed = 0
checks_failed = 0


def ss(page, name):
    """Take a numbered screenshot"""
    global ss_count
    ss_count += 1
    path = SS_DIR / f"{ss_count:02d}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [SS #{ss_count:02d}] {name}")
    return path


def check(condition, msg):
    """Assert with counter"""
    global checks_passed, checks_failed
    if condition:
        checks_passed += 1
        print(f"  [OK] {msg}")
    else:
        checks_failed += 1
        print(f"  [FAIL] {msg}")


def api(endpoint):
    """GET API endpoint"""
    return requests.get(f"{BASE}{endpoint}").json()


# ============================
# STEP 0: Verify dashboard is running
# ============================
print("=" * 60)
print("STEP 0: Verify dashboard")
print("=" * 60)

try:
    resp = requests.get(f"{BASE}/api/status", timeout=5)
    check(resp.status_code == 200, f"Dashboard responds on :{PORT}")
    status = resp.json()
    check("checkpoint" in status, "API returns checkpoint")
    check("tasks" in status, "API returns tasks")
    check("metrics" in status, "API returns metrics (NEW)")
    check("progress" in status, "API returns progress")
    print(f"  Tasks: {len(status['tasks'])}, Running: {status['running']}")
except Exception as e:
    print(f"  [FATAL] Dashboard not running: {e}")
    print(f"  Start it: pca ui --no-browser")
    sys.exit(1)


# ============================
# STEP 1: Initial state screenshots
# ============================
print()
print("=" * 60)
print("STEP 1: Initial state — all pages")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Dashboard — main page with 6 cards
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "dashboard_initial")

    # Check 6 cards present
    cards = page.locator(".card").count()
    check(cards == 6, f"Dashboard has 6 cards (got {cards})")

    # Check card titles via .card-title selectors
    titles = page.locator(".card-title").all_text_contents()
    titles_joined = " ".join(titles)
    check("Tasks" in titles_joined, "Card: Tasks present")
    check("Session" in titles_joined, "Card: Session present")
    check("Tokens" in titles_joined, "Card: Tokens present (NEW)")
    check("Cost" in titles_joined, "Card: Cost present (NEW)")
    check("Duration" in titles_joined, "Card: Duration present (NEW)")
    check("Files" in titles_joined, "Card: Files present")

    # Check status badge
    badge = page.locator("#status-badge")
    check(badge.count() > 0, "Status badge visible")

    # Check log panel exists (terminal style)
    log_panel = page.locator(".log-panel")
    check(log_panel.count() > 0, "Log panel visible")

    # Terminal-style elements
    terminal_dots = page.locator(".terminal-dots")
    check(terminal_dots.count() > 0, "Terminal dots (red/yellow/green)")
    terminal_title = page.locator(".terminal-title")
    check(terminal_title.count() > 0, "Terminal title bar")
    title_text = terminal_title.text_content() if terminal_title.count() > 0 else ""
    check("agent@pocketcoder" in title_text, f"Terminal title: {title_text}")

    # Check queue message section
    queue = page.locator("#queue-msg-section")
    check(queue.count() > 0, "Queue message section exists")

    # ============================
    # STEP 2: Tasks page — detail view
    # ============================
    print()
    print("=" * 60)
    print("STEP 2: Tasks page — detail view")
    print("=" * 60)

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")
    ss(page, "tasks_initial")

    # Check tasks listed
    task_items = page.locator(".task-clickable").count()
    check(task_items > 0, f"Tasks page has {task_items} clickable tasks")

    # Check chevron icon (expand indicator)
    chevrons = page.locator(".bi-chevron-down").count()
    check(chevrons > 0, f"Tasks have expand indicators ({chevrons} chevrons)")

    # Click first task to expand detail
    if task_items > 0:
        first_task = page.locator(".task-clickable").first
        first_task.click()
        time.sleep(0.5)
        ss(page, "task_detail_expanded")

        # Check detail view opened
        open_details = page.locator(".task-detail.open").count()
        check(open_details > 0, "Task detail expanded on click")

        # Check stage steps visible
        stages = page.locator(".task-detail.open .stage-step").count()
        check(stages == 3, f"Stage steps visible ({stages} steps)")

        # Check metadata
        detail_text = page.locator(".task-detail.open").first.inner_text()
        check("Status" in detail_text, "Detail shows Status")
        check("Phase" in detail_text, "Detail shows Phase")
        check("Created" in detail_text, "Detail shows Created date")

    # ============================
    # STEP 3: Add task via web form
    # ============================
    print()
    print("=" * 60)
    print("STEP 3: Add task via web form")
    print("=" * 60)

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")

    # Fill form
    page.locator('input[name="task"]').fill("E2E Test Task - Dashboard UX")
    page.locator('textarea[name="description"]').fill(
        "Test task added by Playwright E2E to verify form + backend"
    )
    ss(page, "form_filled")

    # Submit
    page.locator('button:has-text("Add Task")').click()
    page.wait_for_load_state("networkidle")
    ss(page, "form_submitted")

    # Backend verification
    tasks_data = json.loads(
        (PROJECT_DIR / ".a1" / "tasks.json").read_text()
    )
    task_titles = [t["title"] for t in tasks_data["tasks"]]
    check(
        "E2E Test Task - Dashboard UX" in task_titles,
        "Task saved to .a1/tasks.json"
    )

    # API verification
    api_status = api("/api/status")
    api_tasks = [t["title"] for t in api_status["tasks"]]
    check(
        "E2E Test Task - Dashboard UX" in api_tasks,
        "Task visible via API"
    )

    # ============================
    # STEP 4: Navigate all pages
    # ============================
    print()
    print("=" * 60)
    print("STEP 4: Navigate all pages")
    print("=" * 60)

    pages_to_test = [
        ("/", "dashboard"),
        ("/tasks", "tasks"),
        ("/sessions", "sessions"),
        ("/log", "log"),
        ("/commits", "commits"),
        ("/settings", "settings"),
        ("/transform", "transform"),
    ]

    for path, name in pages_to_test:
        page.goto(f"{BASE}{path}")
        page.wait_for_load_state("networkidle")
        ss(page, f"page_{name}")

        # Basic checks
        title = page.title()
        check(
            "PocketCoder" in title,
            f"Page /{name} loads (title: {title[:30]})"
        )

        # Check sidebar nav is present
        sidebar = page.locator(".sidebar").count()
        check(sidebar > 0, f"Page /{name} has sidebar")

    # ============================
    # STEP 5: Theme toggle (dark mode)
    # ============================
    print()
    print("=" * 60)
    print("STEP 5: Theme toggle")
    print("=" * 60)

    page.goto(BASE)
    page.wait_for_load_state("networkidle")

    # Get current theme
    theme_before = page.evaluate(
        "document.documentElement.getAttribute('data-theme')"
    )
    print(f"  Theme before: {theme_before}")

    # Click theme toggle
    page.locator(".theme-toggle").first.click()
    time.sleep(0.3)

    theme_after = page.evaluate(
        "document.documentElement.getAttribute('data-theme')"
    )
    print(f"  Theme after: {theme_after}")
    check(theme_before != theme_after, "Theme toggled successfully")

    ss(page, "dark_mode")

    # Toggle back
    page.locator(".theme-toggle").first.click()
    time.sleep(0.3)

    # ============================
    # STEP 6: API endpoints test
    # ============================
    print()
    print("=" * 60)
    print("STEP 6: API endpoints")
    print("=" * 60)

    # /api/status
    status = api("/api/status")
    check("metrics" in status, "/api/status has 'metrics' field")
    check("running" in status, "/api/status has 'running' field")
    check(isinstance(status["progress"], list), "/api/status progress is list")

    # Check metrics structure
    metrics = status.get("metrics", {})
    print(f"  Metrics: {json.dumps(metrics)[:100]}")

    # /api/log
    log = api("/api/log?since=0")
    check("entries" in log, "/api/log has 'entries' field")
    check("total" in log, "/api/log has 'total' field")
    print(f"  Log entries: {log['total']}")

    # ============================
    # STEP 7: Colored icons verification (JS)
    # ============================
    print()
    print("=" * 60)
    print("STEP 7: Colored icons + JS functions")
    print("=" * 60)

    page.goto(BASE)
    page.wait_for_load_state("networkidle")

    # Check JS functions exist
    has_fmt_tokens = page.evaluate("typeof fmtTokens === 'function'")
    check(has_fmt_tokens, "JS: fmtTokens() function exists")

    has_fmt_duration = page.evaluate("typeof fmtDuration === 'function'")
    check(has_fmt_duration, "JS: fmtDuration() function exists")

    has_estimate_cost = page.evaluate("typeof estimateCost === 'function'")
    check(has_estimate_cost, "JS: estimateCost() function exists")

    has_tick_timer = page.evaluate("typeof tickTimer === 'function'")
    check(has_tick_timer, "JS: tickTimer() function exists")

    has_toggle_detail = page.evaluate("typeof toggleTaskDetail === 'function'")
    check(has_toggle_detail, "JS: toggleTaskDetail() function exists")

    # Test fmtTokens
    fmt_result = page.evaluate("fmtTokens(12400)")
    check(fmt_result == "12.4K", f"fmtTokens(12400) = '{fmt_result}' (expect 12.4K)")

    fmt_result2 = page.evaluate("fmtTokens(1500000)")
    check(fmt_result2 == "1.5M", f"fmtTokens(1500000) = '{fmt_result2}' (expect 1.5M)")

    # Test fmtDuration
    dur_result = page.evaluate("fmtDuration(125)")
    check(dur_result == "2m 5s", f"fmtDuration(125) = '{dur_result}' (expect 2m 5s)")

    # Test estimateCost
    cost = page.evaluate("estimateCost(100000, 5000, 80000)")
    check(cost > 0, f"estimateCost returns positive: {cost:.4f}")

    # Check terminal-style log labels in JS source
    html = page.content()
    check("'READ'" in html or "READ" in html, "Label: READ in page")
    check("'EDIT'" in html or "EDIT" in html, "Label: EDIT in page")
    check("'BASH'" in html or "BASH" in html, "Label: BASH in page")
    check("'THINK'" in html or "THINK" in html, "Label: THINK in page")
    check("'METRIC'" in html or "METRIC" in html, "Label: METRIC in page")
    check("'CHECK'" in html or "CHECK" in html, "Label: CHECK (verify) in page")
    check("'OUT'" in html or "OUT" in html, "Label: OUT (text) in page")

    # Check terminal-style colors (Catppuccin palette)
    check("#89b4fa" in html, "Color: blue for read")
    check("#fab387" in html, "Color: peach for edit")
    check("#cba6f7" in html, "Color: mauve for bash")
    check("#f9e2af" in html, "Color: yellow for thinking")
    check("#89dceb" in html, "Color: sky for metric")

    # ============================
    # STEP 8: Responsive (hamburger)
    # ============================
    print()
    print("=" * 60)
    print("STEP 8: Responsive layout")
    print("=" * 60)

    # Check hamburger button exists in HTML
    check("hamburger" in html, "Hamburger button in HTML")

    # CSS responsive classes
    check("sidebar.open" in html or ".sidebar.open" in html,
          "CSS: sidebar.open class defined")

    # Test at mobile viewport
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "mobile_view")

    # Back to desktop
    page.set_viewport_size({"width": 1400, "height": 900})

    # ============================
    # STEP 9: Backend file verification
    # ============================
    print()
    print("=" * 60)
    print("STEP 9: Backend files")
    print("=" * 60)

    # tasks.json
    tasks_path = PROJECT_DIR / ".a1" / "tasks.json"
    check(tasks_path.exists(), ".a1/tasks.json exists")

    tasks = json.loads(tasks_path.read_text())
    check(len(tasks["tasks"]) > 0, f"tasks.json has {len(tasks['tasks'])} tasks")

    # checkpoint via API (in-memory, not on disk)
    cp_api = api("/api/status")
    check("checkpoint" in cp_api, "Checkpoint accessible via API")

    # Source files compile
    for pyfile in ["a1/loop.py", "a1/dashboard.py", "a1/tasks.py",
                   "a1/checkpoint.py", "a1/validator.py"]:
        fpath = PROJECT_DIR / pyfile
        check(fpath.exists(), f"{pyfile} exists")

    # Syntax check
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(PROJECT_DIR / "a1/dashboard.py")],
        capture_output=True, text=True
    )
    check(result.returncode == 0, "dashboard.py compiles OK")

    result2 = subprocess.run(
        [sys.executable, "-m", "py_compile", str(PROJECT_DIR / "a1/loop.py")],
        capture_output=True, text=True
    )
    check(result2.returncode == 0, "loop.py compiles OK")

    # ============================
    # STEP 10: Final screenshots
    # ============================
    print()
    print("=" * 60)
    print("STEP 10: Final screenshots")
    print("=" * 60)

    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    ss(page, "final_dashboard")

    page.goto(f"{BASE}/tasks")
    page.wait_for_load_state("networkidle")
    # Expand all task details
    clickables = page.locator(".task-clickable")
    for i in range(min(3, clickables.count())):
        clickables.nth(i).click()
        time.sleep(0.2)
    ss(page, "final_tasks_expanded")

    browser.close()


# ============================
# SUMMARY
# ============================
print()
print("=" * 60)
print("E2E TEST SUMMARY")
print("=" * 60)
total = checks_passed + checks_failed
print(f"  Screenshots: {ss_count}")
print(f"  Checks: {checks_passed}/{total} passed")
if checks_failed > 0:
    print(f"  FAILED: {checks_failed} checks")
print(f"  Result: {'PASS' if checks_failed == 0 else 'FAIL'}")
print("=" * 60)
