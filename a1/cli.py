#!/usr/bin/env python3
"""
PocketCoder-A1 CLI — Autonomous Coding Agent
"""

import argparse
import sys
from pathlib import Path

from . import __codename__, __version__
from .checkpoint import CheckpointManager
from .dashboard import run_dashboard
from .loop import SessionLoop
from .tasks import TaskManager
from .validator import Validator


def cmd_init(args):
    """Initialize A1 in project directory"""
    project_dir = Path(args.dir if hasattr(args, 'dir') else args.project).resolve()

    if not project_dir.exists():
        print(f"[ERROR] Directory not found: {project_dir}")
        return 1

    # Создаём структуру
    a1_dir = project_dir / ".a1"
    a1_dir.mkdir(exist_ok=True)
    (a1_dir / "sessions").mkdir(exist_ok=True)
    (a1_dir / "checkpoints").mkdir(exist_ok=True)

    # Инициализируем менеджеры
    CheckpointManager(project_dir)
    TaskManager(project_dir)

    print(f"[OK] A1 initialized in {project_dir}")
    print(f"   Created: {a1_dir}")
    print()
    print("Next steps:")
    print("  pca think 'your task idea'   # Add tasks")
    print("  pca tasks                     # View tasks")
    print("  pca start                     # Start autonomous work")

    return 0


def cmd_think(args):
    """Add a raw thought"""
    project_dir = Path(args.project).resolve()
    tasks = TaskManager(project_dir)

    thought = " ".join(args.thought)
    tasks.add_raw_thought(thought)

    print(f"[THOUGHT] Added: {thought}")
    print()
    print("Use 'pca transform' to convert thoughts to tasks")
    print("Or 'pca task add \"...\"' to add a specific task")

    return 0


def cmd_task_add(args):
    """Add a specific task"""
    project_dir = Path(args.project).resolve()
    tasks = TaskManager(project_dir)

    title = " ".join(args.title)
    task = tasks.add_task(title, description=args.description or "")

    print(f"[OK] Added task: [{task.id}] {task.title}")

    return 0


def cmd_tasks(args):
    """Show all tasks"""
    project_dir = Path(args.project).resolve()
    tasks = TaskManager(project_dir)

    print(tasks.get_summary())

    return 0


def cmd_start(args):
    """Start autonomous work"""
    project_dir = Path(args.project).resolve()

    # Проверяем что A1 инициализирован
    if not (project_dir / ".a1").exists():
        print(f"[ERROR] A1 not initialized. Run: pca init {project_dir}")
        return 1

    # Проверяем есть ли задачи
    tasks = TaskManager(project_dir)
    pending = tasks.get_tasks(status="pending")
    in_progress = tasks.get_tasks(status="in_progress")

    if not pending and not in_progress:
        print("[ERROR] No tasks to work on!")
        print("   Add tasks with: pca think 'idea' or pca task add 'task'")
        return 1

    # Запускаем loop
    loop = SessionLoop(
        project_dir=project_dir,
        provider=args.provider,
        max_sessions=args.max_sessions,
    )

    loop.start()

    return 0


def cmd_status(args):
    """Show current status"""
    project_dir = Path(args.project).resolve()

    checkpoint = CheckpointManager(project_dir)
    tasks = TaskManager(project_dir)
    validator = Validator(project_dir)

    print("=" * 50)
    print("AUTONOMOUS GNOME STATUS")
    print("=" * 50)
    print()
    print(checkpoint.get_summary())
    print()
    print(tasks.get_summary())

    if args.validate:
        print()
        print(validator.get_summary())

    return 0


def cmd_validate(args):
    """Run validation checks"""
    project_dir = Path(args.project).resolve()
    validator = Validator(project_dir)

    print(validator.get_summary())

    return 0


def cmd_dashboard(args):
    """Launch web dashboard"""
    project_dir = Path(args.project).resolve()
    run_dashboard(project_dir, port=args.port, open_browser=not args.no_browser)
    return 0


def cmd_log(args):
    """Show session log"""
    project_dir = Path(args.project).resolve()
    checkpoints_dir = project_dir / ".a1" / "checkpoints"

    if not checkpoints_dir.exists():
        print("No sessions yet.")
        return 0

    sessions = sorted(checkpoints_dir.glob("session_*.json"))

    if args.session:
        # Показать конкретную сессию
        session_file = checkpoints_dir / f"session_{args.session:03d}.json"
        if session_file.exists():
            print(session_file.read_text())
        else:
            print(f"Session {args.session} not found")
    else:
        # Показать список сессий
        print(f"Sessions: {len(sessions)}")
        for s in sessions[-10:]:  # Последние 10
            print(f"  - {s.name}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="pca",
        description=f"PocketCoder-A1 v{__version__} ({__codename__})",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-p", "--project", default=".", help="Project directory (default: current)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize A1 in project")
    p_init.add_argument("dir", nargs="?", default=".", help="Project directory")
    p_init.set_defaults(func=cmd_init)

    # think
    p_think = subparsers.add_parser("think", help="Add a raw thought")
    p_think.add_argument("thought", nargs="+", help="Your thought")
    p_think.set_defaults(func=cmd_think)

    # task add
    p_task = subparsers.add_parser("task", help="Task management")
    task_sub = p_task.add_subparsers(dest="task_cmd")

    p_task_add = task_sub.add_parser("add", help="Add a task")
    p_task_add.add_argument("title", nargs="+", help="Task title")
    p_task_add.add_argument("-d", "--description", help="Task description")
    p_task_add.set_defaults(func=cmd_task_add)

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Show all tasks")
    p_tasks.set_defaults(func=cmd_tasks)

    # start
    p_start = subparsers.add_parser("start", help="Start autonomous work")
    p_start.add_argument(
        "--provider",
        default="claude-max",
        choices=["claude-max", "claude-api", "ollama"],
        help="AI provider",
    )
    p_start.add_argument(
        "--max-sessions", type=int, default=100, help="Max sessions"
    )
    p_start.set_defaults(func=cmd_start)

    # status
    p_status = subparsers.add_parser("status", help="Show status")
    p_status.add_argument("-v", "--validate", action="store_true", help="Run validation")
    p_status.set_defaults(func=cmd_status)

    # validate
    p_validate = subparsers.add_parser("validate", help="Run validation checks")
    p_validate.set_defaults(func=cmd_validate)

    # log
    p_log = subparsers.add_parser("log", help="Show session log")
    p_log.add_argument("-s", "--session", type=int, help="Session number")
    p_log.set_defaults(func=cmd_log)

    # dashboard (web UI)
    p_dash = subparsers.add_parser("ui", help="Launch web dashboard")
    p_dash.add_argument("--port", type=int, default=None, help="Port (default: auto-find from 7331)")
    p_dash.add_argument("--no-browser", action="store_true", help="Don't open browser")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
