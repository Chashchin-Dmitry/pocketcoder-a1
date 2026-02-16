"""
Task Manager — управление задачами
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: str = "pending"
    created_at: str = ""
    completed_at: Optional[str] = None
    raw_thought: Optional[str] = None  # Исходная мысль если была
    phase: Optional[str] = None  # Фаза из TODO.md
    success_criteria: Optional[str] = None  # Критерии успеха

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        # Filter only known fields
        known_fields = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class TaskManager:
    """Управление задачами для автономной работы"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.a1_dir = self.project_dir / ".a1"
        self.tasks_file = self.a1_dir / "tasks.json"

        self.a1_dir.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> Dict[str, Any]:
        """Загрузить данные"""
        if not self.tasks_file.exists():
            return {"raw_thoughts": [], "tasks": [], "next_id": 1}

        try:
            with open(self.tasks_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"raw_thoughts": [], "tasks": [], "next_id": 1}

    def _save_data(self, data: Dict[str, Any]) -> None:
        """Сохранить данные"""
        with open(self.tasks_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_raw_thought(self, thought: str) -> None:
        """Добавить сырую мысль (для последующей трансформации)"""
        data = self._load_data()
        data["raw_thoughts"].append(
            {"text": thought, "added_at": datetime.now().isoformat()}
        )
        self._save_data(data)

    def get_raw_thoughts(self) -> List[Dict[str, str]]:
        """Получить все сырые мысли"""
        data = self._load_data()
        return data.get("raw_thoughts", [])

    def clear_raw_thoughts(self) -> None:
        """Очистить сырые мысли (после трансформации)"""
        data = self._load_data()
        data["raw_thoughts"] = []
        self._save_data(data)

    def add_task(
        self, title: str, description: str = "", raw_thought: Optional[str] = None
    ) -> Task:
        """Добавить задачу"""
        data = self._load_data()

        task = Task(
            id=f"task_{data['next_id']:03d}",
            title=title,
            description=description,
            status="pending",
            created_at=datetime.now().isoformat(),
            raw_thought=raw_thought,
        )

        data["tasks"].append(task.to_dict())
        data["next_id"] += 1
        self._save_data(data)

        return task

    def get_tasks(self, status: Optional[str] = None) -> List[Task]:
        """Получить задачи (опционально по статусу)"""
        data = self._load_data()
        tasks = [Task.from_dict(t) for t in data.get("tasks", [])]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def get_next_task(self) -> Optional[Task]:
        """Получить следующую задачу для работы"""
        # Сначала ищем in_progress
        in_progress = self.get_tasks(status="in_progress")
        if in_progress:
            return in_progress[0]

        # Потом pending
        pending = self.get_tasks(status="pending")
        if pending:
            return pending[0]

        return None

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Обновить задачу"""
        data = self._load_data()

        for i, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                data["tasks"][i].update(kwargs)
                self._save_data(data)
                return Task.from_dict(data["tasks"][i])

        return None

    def start_task(self, task_id: str) -> Optional[Task]:
        """Начать работу над задачей"""
        return self.update_task(task_id, status="in_progress")

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Завершить задачу"""
        return self.update_task(
            task_id, status="done", completed_at=datetime.now().isoformat()
        )

    def get_progress(self) -> Tuple[int, int]:
        """Получить прогресс (done, total)"""
        tasks = self.get_tasks()
        done = len([t for t in tasks if t.status == "done"])
        return done, len(tasks)

    def get_summary(self) -> str:
        """Получить текстовое резюме для промпта"""
        done, total = self.get_progress()
        tasks = self.get_tasks()

        lines = [f"## Tasks ({done}/{total} completed)"]

        for t in tasks:
            status_mark = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "blocked": "[!]"}.get(
                t.status, "[?]"
            )
            lines.append(f"{status_mark} [{t.id}] {t.title}")
            if t.description:
                lines.append(f"    {t.description[:100]}")

        # Добавляем raw thoughts если есть
        thoughts = self.get_raw_thoughts()
        if thoughts:
            lines.append("\n## Raw Thoughts (need transform)")
            for th in thoughts:
                lines.append(f"  - {th['text']}")

        return "\n".join(lines)
