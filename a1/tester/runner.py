"""
Vision Tester Runner — REAL browser interaction
Opens Chromium, clicks, types, takes screenshots at every step.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .browser import Browser
from .report import TestReport, ScenarioResult, StepResult


class VisionTester:
    """Full E2E tester — real Playwright browser interaction"""

    def __init__(
        self,
        project_dir: Path,
        base_url: str = "http://localhost:7331",
    ):
        self.project_dir = Path(project_dir)
        self.base_url = base_url
        self.browser = Browser()
        self.report = TestReport()
        self.report_dir = self.project_dir / ".a1" / "test-reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self) -> TestReport:
        """Run full E2E user path"""
        print(f"\n{'=' * 60}")
        print(f"  A1 VISION TESTER — Full E2E")
        print(f"  Base URL: {self.base_url}")
        print(f"  Playwright: real Chromium browser")
        print(f"{'=' * 60}\n")

        try:
            self.browser.launch()

            self._test_1_dashboard_loads()
            self._test_2_add_task()
            self._test_3_add_thought()
            self._test_4_navigate_all_pages()
            self._test_5_theme_toggle()
            self._test_6_start_stop_agent()
            self._test_7_api_endpoint()

        except Exception as e:
            print(f"  [FATAL] {e}")
        finally:
            self.browser.close()

        self.report.finalize()
        self._save_reports()
        self._print_summary()
        return self.report

    def run_one(self, scenario_id: int) -> TestReport:
        """Run one scenario"""
        tests = {
            1: self._test_1_dashboard_loads,
            2: self._test_2_add_task,
            3: self._test_3_add_thought,
            4: self._test_4_navigate_all_pages,
            5: self._test_5_theme_toggle,
            6: self._test_6_start_stop_agent,
            7: self._test_7_api_endpoint,
        }
        fn = tests.get(scenario_id)
        if not fn:
            print(f"[ERROR] Scenario #{scenario_id} not found (1-7)")
            return self.report

        try:
            self.browser.launch()
            fn()
        except Exception as e:
            print(f"  [FATAL] {e}")
        finally:
            self.browser.close()

        self.report.finalize()
        self._save_reports()
        self._print_summary()
        return self.report

    # ─── SCENARIO 1: Dashboard loads ─────────────────────────

    def _test_1_dashboard_loads(self):
        result = ScenarioResult(1, "Dashboard loads", "pass")
        start = time.time()
        print("  [1] Dashboard loads")

        try:
            self.browser.navigate(self.base_url)
            self._snap(result, "01_dashboard")

            # Check key elements
            for selector, name in [
                (".card", "Stats cards"),
                (".task-list", "Task list"),
                (".form-section", "Quick Add form"),
                (".sidebar", "Sidebar navigation"),
                (".status", "Status badge"),
            ]:
                visible = self.browser.is_visible(selector)
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", f"{name} visible",
                    "pass" if visible else "fail",
                    details=f"Selector: {selector} → {'found' if visible else 'NOT FOUND'}",
                ))
                if not visible:
                    result.status = "fail"
                    result.error = f"{name} not found"

            # Check page text contains expected content
            text = self.browser.get_all_text()
            for keyword in ["Dashboard", "Tasks", "Session", "Context"]:
                found = keyword in text
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", f"Text '{keyword}' present",
                    "pass" if found else "fail",
                ))

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 2: Add task via web ────────────────────────

    def _test_2_add_task(self):
        result = ScenarioResult(2, "Add task via web", "pass")
        start = time.time()
        print("  [2] Add task via web")

        try:
            self.browser.navigate(self.base_url)
            self._snap(result, "02_before_add")

            # Fill task form and submit
            task_name = f"E2E test task {int(time.time())}"
            self.browser.fill('input[name="task"]', task_name)
            self._snap(result, "02_form_filled")

            self.browser.click('.form-section button[type="submit"]')
            self.browser.page.wait_for_load_state("networkidle")
            self._snap(result, "02_after_submit")

            # Navigate to tasks page to verify
            self.browser.navigate(f"{self.base_url}/tasks")
            self._snap(result, "02_tasks_page")

            # Check task appears
            text = self.browser.get_all_text()
            if task_name in text:
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", "Task appeared in list",
                    "pass", details=f"Found: {task_name}",
                ))
            else:
                result.status = "fail"
                result.error = f"Task '{task_name}' not found in page"
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", "Task appeared in list",
                    "fail", details=f"NOT found: {task_name}",
                ))

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 3: Add thought ─────────────────────────────

    def _test_3_add_thought(self):
        result = ScenarioResult(3, "Add thought", "pass")
        start = time.time()
        print("  [3] Add thought")

        try:
            self.browser.navigate(f"{self.base_url}/tasks")
            self._snap(result, "03_before_thought")

            thought_text = f"E2E thought {int(time.time())}"
            self.browser.fill('input[name="thought"]', thought_text)
            self.browser.click('form[action="/add-thought"] button[type="submit"]')
            self.browser.page.wait_for_load_state("networkidle")
            self._snap(result, "03_after_thought")

            text = self.browser.get_all_text()
            if thought_text in text:
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", "Thought appeared",
                    "pass", details=f"Found: {thought_text}",
                ))
            else:
                result.status = "fail"
                result.error = "Thought not found"

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 4: Navigate all pages ──────────────────────

    def _test_4_navigate_all_pages(self):
        result = ScenarioResult(4, "Navigate all pages", "pass")
        start = time.time()
        print("  [4] Navigate all pages")

        pages = [
            ("/", "Dashboard"),
            ("/tasks", "Tasks"),
            ("/sessions", "Sessions"),
            ("/log", "Activity Log"),
            ("/commits", "Commits"),
            ("/settings", "Settings"),
        ]

        try:
            for path, name in pages:
                url = f"{self.base_url}{path}"
                self.browser.navigate(url)
                self._snap(result, f"04_page_{name.lower().replace(' ', '_')}")

                # Check page renders (has main content)
                has_main = self.browser.is_visible(".main")
                has_sidebar = self.browser.is_visible(".sidebar")

                status = "pass" if (has_main and has_sidebar) else "fail"
                result.steps.append(StepResult(
                    len(result.steps) + 1, "navigate", f"{name} page loads",
                    status, details=f"main={has_main}, sidebar={has_sidebar}",
                ))

                if status == "fail":
                    result.status = "fail"
                    result.error = f"{name} page failed to render"

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 5: Theme toggle ────────────────────────────

    def _test_5_theme_toggle(self):
        result = ScenarioResult(5, "Theme toggle", "pass")
        start = time.time()
        print("  [5] Theme toggle")

        try:
            self.browser.navigate(self.base_url)
            self._snap(result, "05_theme_light")

            # Get current theme
            theme_before = self.browser.evaluate(
                'document.documentElement.getAttribute("data-theme")'
            )

            # Click theme toggle
            self.browser.click(".theme-toggle")
            time.sleep(0.3)
            self._snap(result, "05_theme_toggled")

            theme_after = self.browser.evaluate(
                'document.documentElement.getAttribute("data-theme")'
            )

            if theme_before != theme_after:
                result.steps.append(StepResult(
                    len(result.steps) + 1, "check", "Theme changed",
                    "pass", details=f"{theme_before} → {theme_after}",
                ))
            else:
                result.status = "fail"
                result.error = f"Theme didn't change: {theme_before}"

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 6: Start/Stop agent ────────────────────────

    def _test_6_start_stop_agent(self):
        result = ScenarioResult(6, "Start/Stop agent controls", "pass")
        start = time.time()
        print("  [6] Start/Stop agent")

        try:
            self.browser.navigate(self.base_url)
            self._snap(result, "06_initial_state")

            # Check Start button exists
            has_start = self.browser.is_visible('form[action="/start"] button')
            result.steps.append(StepResult(
                len(result.steps) + 1, "check", "Start button visible",
                "pass" if has_start else "fail",
            ))

            # Check status badge shows Stopped
            text = self.browser.get_all_text()
            has_stopped = "Stopped" in text
            result.steps.append(StepResult(
                len(result.steps) + 1, "check", "Status shows Stopped",
                "pass" if has_stopped else "fail",
            ))

            if not has_start or not has_stopped:
                result.status = "fail"

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── SCENARIO 7: API endpoint ────────────────────────────

    def _test_7_api_endpoint(self):
        result = ScenarioResult(7, "API endpoint /api/status", "pass")
        start = time.time()
        print("  [7] API endpoint")

        try:
            # Use playwright to fetch API
            response = self.browser.page.request.get(f"{self.base_url}/api/status")
            body = response.text()

            result.steps.append(StepResult(
                len(result.steps) + 1, "api_call", "GET /api/status",
                "pass" if response.ok else "fail",
                details=f"HTTP {response.status}, {len(body)} bytes",
            ))

            # Parse JSON
            try:
                data = json.loads(body)
                for field in ["checkpoint", "tasks", "running"]:
                    has_field = field in data
                    result.steps.append(StepResult(
                        len(result.steps) + 1, "check", f"Field '{field}' present",
                        "pass" if has_field else "fail",
                    ))
                    if not has_field:
                        result.status = "fail"
            except json.JSONDecodeError:
                result.status = "fail"
                result.error = "Response is not valid JSON"

        except Exception as e:
            result.status = "error"
            result.error = str(e)

        result.duration_ms = int((time.time() - start) * 1000)
        self._finish_scenario(result)

    # ─── Helpers ─────────────────────────────────────────────

    def _snap(self, result: ScenarioResult, name: str):
        """Take screenshot and add to result"""
        path = self.report_dir / f"{name}.png"
        self.browser.screenshot(path)
        result.steps.append(StepResult(
            len(result.steps) + 1, "screenshot", f"Screenshot: {name}",
            "pass", screenshot=str(path),
        ))

    def _finish_scenario(self, result: ScenarioResult):
        """Print result and add to report"""
        icon = {"pass": "[OK]", "fail": "[FAIL]", "error": "[ERR]"}.get(result.status, "[?]")
        print(f"      {icon} {result.duration_ms}ms")
        if result.error:
            print(f"      {result.error}")
        print()
        self.report.add_result(result)

    def _save_reports(self):
        """Save JSON and HTML reports"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"report_{ts}.json"
        html_path = self.report_dir / f"report_{ts}.html"

        self.report.save_json(json_path)
        self.report.save_html(html_path)
        self.report.save_json(self.report_dir / "latest.json")
        self.report.save_html(self.report_dir / "latest.html")

        print(f"  Reports:")
        print(f"    HTML: {html_path}")
        print(f"    JSON: {json_path}")

    def _print_summary(self):
        """Print summary"""
        r = self.report
        print(f"\n{'=' * 60}")
        print(f"  RESULTS: {r.passed}/{r.total} passed", end="")
        if r.failed:
            print(f", {r.failed} failed", end="")
        if r.errors:
            print(f", {r.errors} errors", end="")
        print(f"\n  Screenshots: {self.browser.screenshot_count}")
        print(f"{'=' * 60}\n")
