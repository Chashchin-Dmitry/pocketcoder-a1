"""
Checkpoint Manager — сохранение состояния между сессиями
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class CheckpointManager:
    """Управление checkpoint'ами для автономной работы"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.a1_dir = self.project_dir / ".a1"
        self.checkpoint_file = self.a1_dir / "checkpoint.json"
        self.checkpoints_dir = self.a1_dir / "checkpoints"

        # Создаём структуру если не существует
        self.a1_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Загрузить текущий checkpoint"""
        if not self.checkpoint_file.exists():
            return self._create_initial()

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._create_initial()

    def save(self, checkpoint: Dict[str, Any]) -> None:
        """Сохранить checkpoint"""
        checkpoint["updated_at"] = datetime.now().isoformat()

        # Сохраняем текущий
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

        # Архивируем копию
        session = checkpoint.get("session", 0)
        archive_file = self.checkpoints_dir / f"session_{session:03d}.json"
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

    def _create_initial(self) -> Dict[str, Any]:
        """Создать начальный checkpoint"""
        return {
            "status": "STARTING",
            "session": 0,
            "current_task": None,
            "context_percent": 0,
            "files_modified": [],
            "decisions": [],
            "next_steps": [],
            "last_action": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def start_session(self) -> Dict[str, Any]:
        """Начать новую сессию"""
        checkpoint = self.load()
        checkpoint["session"] += 1
        checkpoint["status"] = "WORKING"
        checkpoint["session_started_at"] = datetime.now().isoformat()
        self.save(checkpoint)
        return checkpoint

    def end_session(
        self,
        current_task: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        last_action: Optional[str] = None,
        context_percent: int = 0,
    ) -> None:
        """Завершить сессию с сохранением состояния"""
        checkpoint = self.load()

        if current_task:
            checkpoint["current_task"] = current_task
        if files_modified:
            # Добавляем к существующим, убираем дубли
            existing = set(checkpoint.get("files_modified", []))
            existing.update(files_modified)
            checkpoint["files_modified"] = list(existing)
        if decisions:
            checkpoint["decisions"].extend(decisions)
            checkpoint["decisions"] = checkpoint["decisions"][-20:]
        if next_steps:
            checkpoint["next_steps"] = next_steps
        if last_action:
            checkpoint["last_action"] = last_action

        checkpoint["context_percent"] = context_percent
        checkpoint["session_ended_at"] = datetime.now().isoformat()

        self.save(checkpoint)

    def mark_completed(self) -> None:
        """Отметить всю работу как завершённую"""
        checkpoint = self.load()
        checkpoint["status"] = "COMPLETED"
        checkpoint["completed_at"] = datetime.now().isoformat()
        self.save(checkpoint)

    def is_completed(self) -> bool:
        """Проверить завершена ли работа"""
        checkpoint = self.load()
        return checkpoint.get("status") == "COMPLETED"

    def get_session_number(self) -> int:
        """Получить номер текущей сессии"""
        checkpoint = self.load()
        return checkpoint.get("session", 0)

    def get_summary(self) -> str:
        """Получить текстовое резюме для промпта"""
        cp = self.load()

        lines = [
            f"## Checkpoint (Session #{cp['session']})",
            f"Status: {cp['status']}",
            f"Current task: {cp.get('current_task', 'None')}",
            f"Last action: {cp.get('last_action', 'None')}",
        ]

        if cp.get("files_modified"):
            lines.append(f"Files modified: {', '.join(cp['files_modified'][-10:])}")

        if cp.get("decisions"):
            lines.append("Recent decisions:")
            for d in cp["decisions"][-5:]:
                lines.append(f"  - {d}")

        if cp.get("next_steps"):
            lines.append("Next steps:")
            for s in cp["next_steps"]:
                lines.append(f"  - {s}")

        # Session history — what was done in previous sessions
        # Include as many recent sessions as fit in ~8000 chars
        history = cp.get("session_history", [])
        if history:
            lines.append("")
            lines.append("## Previous Sessions (DO NOT repeat this work):")
            history_lines = []
            total_chars = 0
            for h in reversed(history):
                sn = h.get("session", "?")
                edits = h.get("edits", [])
                result = h.get("result", "")
                tools = h.get("tools", 0)
                dur = h.get("duration", 0)
                entry = [f"  Session #{sn} ({dur}s, {tools} tools):"]
                if edits:
                    entry.append(f"    Files edited: {', '.join(edits[:10])}")
                if result:
                    entry.append(f"    Result: {result[:200]}")
                entry_text = "\n".join(entry)
                if total_chars + len(entry_text) > 8000:
                    break
                history_lines.insert(0, entry_text)
                total_chars += len(entry_text)
            for hl in history_lines:
                lines.append(hl)

        return "\n".join(lines)
