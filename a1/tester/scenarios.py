"""
Test Scenarios — predefined QA scenarios for A1 dashboard
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ScenarioType(Enum):
    WEB = "web"
    CLI = "cli"
    INTEGRATION = "integration"


@dataclass
class TestStep:
    action: str  # navigate, screenshot, check, click, type, wait, api_call, cli
    target: str  # URL, selector, CLI command
    value: str = ""  # text to type, expected value
    description: str = ""


@dataclass
class Scenario:
    id: int
    name: str
    description: str
    type: ScenarioType
    steps: List[TestStep] = field(default_factory=list)
    expected: str = ""
    tags: List[str] = field(default_factory=list)


def get_all_scenarios(base_url: str = "http://localhost:7331") -> List[Scenario]:
    """Return all 7 test scenarios"""
    return [
        # 1. Dashboard loads
        Scenario(
            id=1,
            name="Dashboard loads",
            description="Open main dashboard and verify it renders correctly",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/", description="Open dashboard"),
                TestStep("screenshot", "dashboard_main", description="Capture main page"),
                TestStep("check", "page_loads", "Dashboard", "Verify page title visible"),
                TestStep("check", "element_present", "Tasks card", "Check tasks card exists"),
                TestStep("check", "element_present", "Session card", "Check session card"),
                TestStep("check", "element_present", "Context card", "Check context card"),
            ],
            expected="Dashboard renders with all 4 stat cards, task list, and add form",
            tags=["web", "smoke"],
        ),

        # 2. Add task via web
        Scenario(
            id=2,
            name="Add task via web",
            description="Submit a task through the dashboard form and verify it appears",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/", description="Open dashboard"),
                TestStep("screenshot", "before_add_task", description="Before state"),
                TestStep("api_call", f"{base_url}/add-task",
                         "task=Test+task+from+vision+tester",
                         "POST task via form"),
                TestStep("navigate", f"{base_url}/tasks", description="Open tasks page"),
                TestStep("screenshot", "after_add_task", description="After state"),
                TestStep("check", "element_present",
                         "Test task from vision tester",
                         "Verify new task appears in list"),
            ],
            expected="Task appears in task list after submission",
            tags=["web", "crud"],
        ),

        # 3. Add thought
        Scenario(
            id=3,
            name="Add thought",
            description="Add a raw thought via form and verify it appears",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/tasks", description="Open tasks page"),
                TestStep("screenshot", "before_thought", description="Before state"),
                TestStep("api_call", f"{base_url}/add-thought",
                         "thought=Vision+tester+thought",
                         "POST thought via form"),
                TestStep("navigate", f"{base_url}/tasks", description="Refresh tasks"),
                TestStep("screenshot", "after_thought", description="After state"),
                TestStep("check", "element_present",
                         "Vision tester thought",
                         "Verify thought appears"),
            ],
            expected="Thought appears in raw thoughts section",
            tags=["web", "crud"],
        ),

        # 4. Navigation — all pages
        Scenario(
            id=4,
            name="Navigation",
            description="Visit all 6 pages and verify each loads",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/", description="Dashboard"),
                TestStep("screenshot", "nav_dashboard", description="Dashboard page"),
                TestStep("check", "page_loads", "Dashboard", "Dashboard loads"),

                TestStep("navigate", f"{base_url}/tasks", description="Tasks"),
                TestStep("screenshot", "nav_tasks", description="Tasks page"),
                TestStep("check", "page_loads", "Tasks", "Tasks page loads"),

                TestStep("navigate", f"{base_url}/sessions", description="Sessions"),
                TestStep("screenshot", "nav_sessions", description="Sessions page"),
                TestStep("check", "page_loads", "Sessions", "Sessions page loads"),

                TestStep("navigate", f"{base_url}/log", description="Activity Log"),
                TestStep("screenshot", "nav_log", description="Log page"),
                TestStep("check", "page_loads", "Activity Log", "Log page loads"),

                TestStep("navigate", f"{base_url}/commits", description="Commits"),
                TestStep("screenshot", "nav_commits", description="Commits page"),
                TestStep("check", "page_loads", "Commits", "Commits page loads"),

                TestStep("navigate", f"{base_url}/settings", description="Settings"),
                TestStep("screenshot", "nav_settings", description="Settings page"),
                TestStep("check", "page_loads", "Settings", "Settings page loads"),
            ],
            expected="All 6 pages render without errors",
            tags=["web", "navigation", "smoke"],
        ),

        # 5. Theme toggle
        Scenario(
            id=5,
            name="Theme toggle",
            description="Switch between light and dark theme",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/", description="Open dashboard"),
                TestStep("screenshot", "theme_light", description="Light theme"),
                TestStep("navigate", f"{base_url}/settings", description="Open settings"),
                TestStep("screenshot", "theme_settings", description="Settings page"),
                # Theme toggle is client-side JS, visual check only
                TestStep("check", "element_present",
                         "Toggle Dark/Light button",
                         "Theme toggle button exists"),
            ],
            expected="Theme toggle button is present and functional",
            tags=["web", "ui"],
        ),

        # 6. Start/Stop agent
        Scenario(
            id=6,
            name="Start/Stop agent",
            description="Test agent start and stop controls via dashboard",
            type=ScenarioType.WEB,
            steps=[
                TestStep("navigate", f"{base_url}/", description="Open dashboard"),
                TestStep("screenshot", "agent_initial", description="Initial state"),
                TestStep("check", "element_present",
                         "Start Agent button",
                         "Start button visible"),
                TestStep("check", "element_present",
                         "Stopped status badge",
                         "Status shows Stopped"),
            ],
            expected="Start/Stop controls are visible and status badge reflects state",
            tags=["web", "agent"],
        ),

        # 7. API endpoint
        Scenario(
            id=7,
            name="API endpoint",
            description="Test /api/status returns valid JSON",
            type=ScenarioType.INTEGRATION,
            steps=[
                TestStep("api_call", f"{base_url}/api/status", "", "GET status API"),
                TestStep("check", "api_response", "json",
                         "Response is valid JSON"),
                TestStep("check", "api_field", "checkpoint",
                         "Has checkpoint field"),
                TestStep("check", "api_field", "tasks",
                         "Has tasks field"),
                TestStep("check", "api_field", "running",
                         "Has running field"),
            ],
            expected="/api/status returns JSON with checkpoint, tasks, progress, running fields",
            tags=["api", "integration"],
        ),
    ]


def get_scenario_by_id(scenario_id: int, base_url: str = "http://localhost:7331") -> Optional[Scenario]:
    """Get a specific scenario by ID"""
    for s in get_all_scenarios(base_url):
        if s.id == scenario_id:
            return s
    return None
