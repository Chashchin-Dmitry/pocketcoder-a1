"""
Report — generate HTML/JSON test reports with screenshots
"""

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class StepResult:
    def __init__(self, step_num=0, action="", description="", status="",
                 screenshot="", details="", duration_ms=0):
        self.step_num = step_num
        self.action = action
        self.description = description
        self.status = status
        self.screenshot = screenshot
        self.details = details
        self.duration_ms = duration_ms

    def to_dict(self):
        return vars(self)


class ScenarioResult:
    def __init__(self, scenario_id=0, scenario_name="", status="",
                 steps=None, duration_ms=0, error=""):
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        self.status = status
        self.steps = steps or []
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self):
        d = vars(self).copy()
        d["steps"] = [s.to_dict() if hasattr(s, "to_dict") else s for s in self.steps]
        return d


class TestReport:
    """Generate test reports in JSON and HTML formats"""

    def __init__(self):
        self.results: List[ScenarioResult] = []
        self.started_at = datetime.now()
        self.finished_at = None

    def add_result(self, result: ScenarioResult):
        self.results.append(result)

    def finalize(self):
        self.finished_at = datetime.now()

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return len([r for r in self.results if r.status == "pass"])

    @property
    def failed(self) -> int:
        return len([r for r in self.results if r.status == "fail"])

    @property
    def errors(self) -> int:
        return len([r for r in self.results if r.status == "error"])

    def save_json(self, path: Path) -> Path:
        """Save JSON report"""
        data = {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
            },
            "scenarios": [r.to_dict() for r in self.results],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return path

    def save_html(self, path: Path) -> Path:
        """Save HTML report with embedded screenshots"""
        path.parent.mkdir(parents=True, exist_ok=True)

        scenarios_html = ""
        for r in self.results:
            status_color = {"pass": "#10b981", "fail": "#ef4444", "error": "#f59e0b"}.get(
                r.status, "#6c757d"
            )
            status_icon = {"pass": "check-circle", "fail": "x-circle", "error": "exclamation-triangle"}.get(
                r.status, "question-circle"
            )

            steps_html = ""
            for s in r.steps:
                s_dict = s.to_dict() if hasattr(s, "to_dict") else s
                s_color = {"pass": "#10b981", "fail": "#ef4444"}.get(
                    s_dict.get("status", ""), "#6c757d"
                )

                screenshot_html = ""
                ss_path = s_dict.get("screenshot", "")
                if ss_path and Path(ss_path).exists():
                    img_b64 = base64.b64encode(Path(ss_path).read_bytes()).decode()
                    screenshot_html = f'<img src="data:image/png;base64,{img_b64}" style="max-width:100%;border:1px solid #ddd;border-radius:8px;margin-top:8px">'

                steps_html += f'''
                <div style="padding:8px 16px;border-left:3px solid {s_color};margin:8px 0;background:#f8f9fa;border-radius:0 8px 8px 0">
                    <strong>{_esc(s_dict.get("description", ""))}</strong>
                    <span style="color:{s_color};font-weight:bold;float:right">{s_dict.get("status", "").upper()}</span>
                    {f'<div style="color:#666;font-size:13px;margin-top:4px">{_esc(s_dict.get("details", ""))}</div>' if s_dict.get("details") else ""}
                    {screenshot_html}
                </div>
                '''

            scenarios_html += f'''
            <div style="background:white;border:1px solid #dee2e6;border-radius:12px;padding:20px;margin-bottom:16px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="margin:0">#{r.scenario_id} {_esc(r.scenario_name)}</h3>
                    <span style="background:{status_color};color:white;padding:4px 12px;border-radius:12px;font-size:13px">{r.status.upper()}</span>
                </div>
                {f'<div style="color:#ef4444;margin-bottom:12px">{_esc(r.error)}</div>' if r.error else ""}
                {steps_html}
            </div>
            '''

        duration = ""
        if self.finished_at:
            dur = (self.finished_at - self.started_at).total_seconds()
            duration = f" in {dur:.1f}s"

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>A1 Vision Test Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; background: #f8f9fa; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
        .stat {{ background: white; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #dee2e6; }}
        .stat-value {{ font-size: 32px; font-weight: 600; }}
        .stat-label {{ font-size: 13px; color: #6c757d; margin-top: 4px; }}
    </style>
</head>
<body>
    <h1>A1 Vision Test Report</h1>
    <p style="color:#6c757d">{self.started_at.strftime("%Y-%m-%d %H:%M:%S")}{duration}</p>

    <div class="summary">
        <div class="stat">
            <div class="stat-value">{self.total}</div>
            <div class="stat-label">Total</div>
        </div>
        <div class="stat">
            <div class="stat-value" style="color:#10b981">{self.passed}</div>
            <div class="stat-label">Passed</div>
        </div>
        <div class="stat">
            <div class="stat-value" style="color:#ef4444">{self.failed}</div>
            <div class="stat-label">Failed</div>
        </div>
        <div class="stat">
            <div class="stat-value" style="color:#f59e0b">{self.errors}</div>
            <div class="stat-label">Errors</div>
        </div>
    </div>

    {scenarios_html}
</body>
</html>'''

        with open(path, "w") as f:
            f.write(html)

        return path


def _esc(text: str) -> str:
    """Escape HTML"""
    import html
    return html.escape(str(text)) if text else ""
