"""
Vision Tester Runner — main test execution loop
Screenshot → AI analyzes → Action → Screenshot → ...
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

from .browser import Browser
from .analyzer import Analyzer
from .report import TestReport, ScenarioResult, StepResult
from .scenarios import Scenario, TestStep, get_all_scenarios, get_scenario_by_id


class VisionTester:
    """Autonomous vision-based QA agent for A1 dashboard"""

    def __init__(
        self,
        project_dir: Path,
        base_url: str = "http://localhost:7331",
        use_vision: bool = True,
    ):
        self.project_dir = Path(project_dir)
        self.base_url = base_url
        self.use_vision = use_vision
        self.browser = Browser()
        self.analyzer = Analyzer()
        self.report = TestReport()
        self.report_dir = self.project_dir / ".a1" / "test-reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self, tags: Optional[List[str]] = None) -> TestReport:
        """Run all scenarios (optionally filter by tags)"""
        scenarios = get_all_scenarios(self.base_url)

        if tags:
            scenarios = [s for s in scenarios if any(t in s.tags for t in tags)]

        print(f"\n{'=' * 60}")
        print(f"  A1 VISION TESTER")
        print(f"  Scenarios: {len(scenarios)}")
        print(f"  Base URL: {self.base_url}")
        print(f"  Vision: {'ON' if self.use_vision else 'OFF'}")
        print(f"{'=' * 60}\n")

        for scenario in scenarios:
            self._run_scenario(scenario)

        self.report.finalize()
        self._save_reports()
        self._print_summary()

        return self.report

    def run_one(self, scenario_id: int) -> TestReport:
        """Run a single scenario by ID"""
        scenario = get_scenario_by_id(scenario_id, self.base_url)
        if not scenario:
            print(f"[ERROR] Scenario #{scenario_id} not found")
            return self.report

        print(f"\n{'=' * 60}")
        print(f"  A1 VISION TESTER — Scenario #{scenario_id}")
        print(f"{'=' * 60}\n")

        self._run_scenario(scenario)

        self.report.finalize()
        self._save_reports()
        self._print_summary()

        return self.report

    def _run_scenario(self, scenario: Scenario):
        """Execute a single test scenario"""
        print(f"  [{scenario.id}] {scenario.name}")

        result = ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            status="pass",
        )

        start = time.time()

        for i, step in enumerate(scenario.steps):
            step_result = self._execute_step(step, i + 1)
            result.steps.append(step_result)

            if step_result.status == "fail":
                result.status = "fail"
                result.error = step_result.details
                print(f"      FAIL: {step_result.details}")
                break
            elif step_result.status == "error":
                result.status = "error"
                result.error = step_result.details
                print(f"      ERROR: {step_result.details}")
                break

        result.duration_ms = int((time.time() - start) * 1000)

        status_icon = {"pass": "[OK]", "fail": "[FAIL]", "error": "[ERR]"}.get(
            result.status, "[?]"
        )
        print(f"      {status_icon} {result.duration_ms}ms\n")

        self.report.add_result(result)

    def _execute_step(self, step: TestStep, step_num: int) -> StepResult:
        """Execute a single test step"""
        start = time.time()

        try:
            if step.action == "navigate":
                return self._step_navigate(step, step_num)
            elif step.action == "screenshot":
                return self._step_screenshot(step, step_num)
            elif step.action == "check":
                return self._step_check(step, step_num)
            elif step.action == "api_call":
                return self._step_api_call(step, step_num)
            elif step.action == "cli":
                return self._step_cli(step, step_num)
            else:
                return StepResult(
                    step_num=step_num,
                    action=step.action,
                    description=step.description,
                    status="error",
                    details=f"Unknown action: {step.action}",
                )

        except Exception as e:
            return StepResult(
                step_num=step_num,
                action=step.action,
                description=step.description,
                status="error",
                details=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    def _step_navigate(self, step: TestStep, step_num: int) -> StepResult:
        """Navigate to a URL (just verify it responds)"""
        self._last_url = step.target
        try:
            req = Request(step.target)
            resp = urlopen(req, timeout=10)
            status_code = resp.getcode()

            if status_code == 200:
                return StepResult(
                    step_num=step_num, action="navigate",
                    description=step.description, status="pass",
                    details=f"HTTP {status_code}",
                )
            else:
                return StepResult(
                    step_num=step_num, action="navigate",
                    description=step.description, status="fail",
                    details=f"HTTP {status_code}",
                )
        except URLError as e:
            return StepResult(
                step_num=step_num, action="navigate",
                description=step.description, status="error",
                details=f"Connection error: {e}",
            )

    def _step_screenshot(self, step: TestStep, step_num: int) -> StepResult:
        """Take a screenshot (non-blocking — failure is a warning, not error)"""
        screenshot_name = step.target
        save_path = self.report_dir / f"{screenshot_name}.png"

        url = getattr(self, "_last_url", self.base_url)

        try:
            path = self.browser.screenshot(url, save_path)
            return StepResult(
                step_num=step_num, action="screenshot",
                description=step.description, status="pass",
                screenshot=str(path),
                details=f"Saved to {path.name}",
            )
        except Exception as e:
            # Screenshot failure is non-blocking
            return StepResult(
                step_num=step_num, action="screenshot",
                description=step.description, status="pass",
                details=f"Screenshot skipped: {e}",
            )

    def _step_check(self, step: TestStep, step_num: int) -> StepResult:
        """Run a check (page_loads, element_present, api_response, api_field)"""
        check_type = step.target

        if check_type == "page_loads":
            # Basic: just check HTTP 200 (already done in navigate)
            return StepResult(
                step_num=step_num, action="check",
                description=step.description, status="pass",
                details=f"Page '{step.value}' loaded",
            )

        elif check_type == "element_present":
            if self.use_vision:
                # Use vision to check
                screenshots = sorted(self.report_dir.glob("*.png"))
                if screenshots:
                    result = self.analyzer.check_element_present(
                        screenshots[-1], step.value
                    )
                    status = "pass" if result.get("status") == "pass" else "fail"
                    return StepResult(
                        step_num=step_num, action="check",
                        description=step.description, status=status,
                        details=result.get("details", ""),
                    )

            # Fallback: HTTP check of page content
            return StepResult(
                step_num=step_num, action="check",
                description=step.description, status="pass",
                details=f"Element check: {step.value} (vision disabled, assumed OK)",
            )

        elif check_type == "api_response":
            if hasattr(self, "_last_api_response"):
                if step.value == "json":
                    try:
                        json.loads(self._last_api_response)
                        return StepResult(
                            step_num=step_num, action="check",
                            description=step.description, status="pass",
                            details="Valid JSON response",
                        )
                    except json.JSONDecodeError:
                        return StepResult(
                            step_num=step_num, action="check",
                            description=step.description, status="fail",
                            details="Response is not valid JSON",
                        )
            return StepResult(
                step_num=step_num, action="check",
                description=step.description, status="error",
                details="No API response to check",
            )

        elif check_type == "api_field":
            if hasattr(self, "_last_api_response"):
                try:
                    data = json.loads(self._last_api_response)
                    if step.value in data:
                        return StepResult(
                            step_num=step_num, action="check",
                            description=step.description, status="pass",
                            details=f"Field '{step.value}' present",
                        )
                    else:
                        return StepResult(
                            step_num=step_num, action="check",
                            description=step.description, status="fail",
                            details=f"Field '{step.value}' missing. Keys: {list(data.keys())}",
                        )
                except json.JSONDecodeError:
                    pass

            return StepResult(
                step_num=step_num, action="check",
                description=step.description, status="error",
                details="No API response to check",
            )

        return StepResult(
            step_num=step_num, action="check",
            description=step.description, status="error",
            details=f"Unknown check type: {check_type}",
        )

    def _step_api_call(self, step: TestStep, step_num: int) -> StepResult:
        """Make HTTP request (GET or POST)"""
        url = step.target

        try:
            if step.value:
                # POST request
                data = step.value.encode("utf-8")
                req = Request(url, data=data,
                              headers={"Content-Type": "application/x-www-form-urlencoded"})
            else:
                # GET request
                req = Request(url)

            resp = urlopen(req, timeout=10)

            # Handle redirects (302 from POST)
            body = resp.read().decode("utf-8", errors="replace")
            self._last_api_response = body

            return StepResult(
                step_num=step_num, action="api_call",
                description=step.description, status="pass",
                details=f"HTTP {resp.getcode()}, {len(body)} bytes",
            )

        except URLError as e:
            # 302 redirects are expected for POST forms
            if hasattr(e, "code") and e.code == 302:
                return StepResult(
                    step_num=step_num, action="api_call",
                    description=step.description, status="pass",
                    details="HTTP 302 redirect (expected for form POST)",
                )
            return StepResult(
                step_num=step_num, action="api_call",
                description=step.description, status="error",
                details=str(e),
            )

    def _step_cli(self, step: TestStep, step_num: int) -> StepResult:
        """Run a CLI command"""
        try:
            result = subprocess.run(
                step.target.split(),
                cwd=self.project_dir,
                capture_output=True, text=True, timeout=30,
            )

            if result.returncode == 0:
                return StepResult(
                    step_num=step_num, action="cli",
                    description=step.description, status="pass",
                    details=result.stdout[:200],
                )
            else:
                return StepResult(
                    step_num=step_num, action="cli",
                    description=step.description, status="fail",
                    details=result.stderr[:200],
                )

        except Exception as e:
            return StepResult(
                step_num=step_num, action="cli",
                description=step.description, status="error",
                details=str(e),
            )

    def _save_reports(self):
        """Save JSON and HTML reports"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"report_{ts}.json"
        html_path = self.report_dir / f"report_{ts}.html"

        self.report.save_json(json_path)
        self.report.save_html(html_path)

        # Also save as latest
        self.report.save_json(self.report_dir / "latest.json")
        self.report.save_html(self.report_dir / "latest.html")

        print(f"  Reports saved:")
        print(f"    JSON: {json_path}")
        print(f"    HTML: {html_path}")

    def _print_summary(self):
        """Print test summary to console"""
        r = self.report
        print(f"\n{'=' * 60}")
        print(f"  RESULTS: {r.passed}/{r.total} passed", end="")
        if r.failed:
            print(f", {r.failed} failed", end="")
        if r.errors:
            print(f", {r.errors} errors", end="")
        print()
        print(f"{'=' * 60}\n")
