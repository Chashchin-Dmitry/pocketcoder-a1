"""
Session Loop — основной цикл автономной работы
"""

import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .checkpoint import CheckpointManager
from .tasks import TaskManager
from .validator import Validator


class SessionLoop:
    """Основной цикл автономной работы"""

    def __init__(
        self,
        project_dir: Path,
        provider: str = "claude-max",
        max_sessions: int = 100,
        session_delay: int = 5,
    ):
        self.project_dir = Path(project_dir)
        self.provider = provider
        self.max_sessions = max_sessions
        self.session_delay = session_delay

        self.checkpoint = CheckpointManager(project_dir)
        self.tasks = TaskManager(project_dir)
        self.validator = Validator(project_dir)

        self._running = False
        self._current_process: Optional[subprocess.Popen] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Настроить обработку Ctrl+C"""
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Обработать прерывание"""
        print("\n\n[!]  Interrupt received. Saving checkpoint...")
        self._running = False
        if self._current_process:
            self._current_process.terminate()

    def stop(self):
        """Остановить loop извне (из dashboard)"""
        self._running = False
        if self._current_process:
            self._current_process.terminate()

    def build_prompt(self, is_first: bool = False) -> str:
        """Build prompt for session (English prompts, respond in user's language)"""
        checkpoint_summary = self.checkpoint.get_summary()
        tasks_summary = self.tasks.get_summary()

        if is_first:
            prompt = f"""
AUTONOMOUS MODE ACTIVATED — Session #1

## LANGUAGE RULE
- All system prompts are in English
- Respond in the language of user's request
- Code comments in English

## PROJECT
Working directory: {self.project_dir}

{tasks_summary}

## PROTOCOL
1. Read CLAUDE.md for project context
2. Read TODO.md for detailed phases
3. Pick first pending task from tasks list
4. Work step by step
5. After each change — validate (syntax, tests, lint)
6. If validation OK → git commit → mark task done → next task
7. If validation FAIL → fix the issue

## CONTEXT MANAGEMENT
- Check /tokens every 10-15 minutes
- When context > 70%:
  1. Update .a1/checkpoint.json with current state
  2. Include: completed work, modified files, decisions made, next steps
  3. Type: exit

## VALIDATION COMMANDS
- Syntax: python -m py_compile <file>
- Tests: pytest -v
- Lint: ruff check .

## SUCCESS CRITERIA
Each task has success_criteria field — verify it before marking done.

## START
Begin with first pending task. Work autonomously.
"""
        else:
            prompt = f"""
AUTONOMOUS MODE — Continuing Session #{self.checkpoint.get_session_number()}

## LANGUAGE RULE
Respond in the language of user's request. Code comments in English.

{checkpoint_summary}

{tasks_summary}

## PROTOCOL
1. Continue from checkpoint (see above)
2. Complete current task or pick next pending
3. Validate after each change
4. Verify success_criteria before marking done
5. If context > 70% → save checkpoint → exit

## CONTEXT CHECK
Run /tokens to check usage. Save checkpoint before reaching limit.

Continue working.
"""
        return prompt.strip()

    def run_session(self, prompt: str) -> int:
        """Запустить одну сессию Claude"""
        if self.provider == "claude-max":
            return self._run_claude_max(prompt)
        elif self.provider == "claude-api":
            return self._run_claude_api(prompt)
        elif self.provider.startswith("ollama"):
            return self._run_ollama(prompt)
        else:
            print(f"[ERROR] Unknown provider: {self.provider}")
            return 1

    def _run_claude_max(self, prompt: str) -> int:
        """Запустить Claude Code CLI (Max subscription)"""
        session_num = self.checkpoint.get_session_number()
        log_dir = self.project_dir / ".a1" / "sessions"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"session_{session_num:03d}.log"

        try:
            self._current_process = subprocess.Popen(
                ["claude", "--print", "-p", prompt],
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output_lines = []
            with open(log_file, "w") as f:
                for line in self._current_process.stdout:
                    print(line, end="")
                    f.write(line)
                    output_lines.append(line)

            self._current_process.wait()
            returncode = self._current_process.returncode
            self._current_process = None
            return returncode

        except FileNotFoundError:
            print("[ERROR] Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
            return 1
        except KeyboardInterrupt:
            if self._current_process:
                self._current_process.terminate()
                self._current_process = None
            return 130

    def _run_claude_api(self, prompt: str) -> int:
        """Запустить через Claude API (требует ключ)"""
        # TODO: Implement API-based session
        print("[ERROR] Claude API provider not implemented yet")
        return 1

    def _run_ollama(self, prompt: str) -> int:
        """Запустить через Ollama (локально)"""
        # TODO: Implement Ollama session
        print("[ERROR] Ollama provider not implemented yet")
        return 1

    def start(self) -> None:
        """Запустить автономный цикл"""
        self._running = True
        session_count = 0

        print("=" * 60)
        print("::: AUTONOMOUS GNOME ACTIVATED")
        print("=" * 60)
        print(f"Project: {self.project_dir}")
        print(f"Provider: {self.provider}")
        print(f"Max sessions: {self.max_sessions}")
        print("=" * 60)
        print()

        while self._running and session_count < self.max_sessions:
            session_count += 1
            is_first = session_count == 1 and self.checkpoint.get_session_number() == 0

            # Начинаем сессию
            cp = self.checkpoint.start_session()

            print("-" * 60)
            print(f">> SESSION #{cp['session']} started at {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 60)

            # Собираем промпт
            prompt = self.build_prompt(is_first=is_first)

            # Запускаем сессию
            start_time = time.time()
            exit_code = self.run_session(prompt)
            duration = int(time.time() - start_time)

            print()
            print(f"-- Session #{cp['session']} ended (duration: {duration}s, exit: {exit_code})")

            # Проверяем статус
            if self.checkpoint.is_completed():
                print()
                print("=" * 60)
                print("[OK] ALL TASKS COMPLETED!")
                print("=" * 60)
                done, total = self.tasks.get_progress()
                print(f"Tasks: {done}/{total}")
                print(f"Sessions: {session_count}")
                break

            # Проверяем прерывание
            if exit_code == 130:  # Ctrl+C
                print()
                response = input("Continue? (y/n): ").strip().lower()
                if response != "y":
                    print("Stopping autonomous gnome.")
                    break
                self._running = True

            # Пауза перед следующей сессией
            if self._running:
                print()
                print(f"[..] Next session in {self.session_delay} seconds... (Ctrl+C to pause)")
                time.sleep(self.session_delay)

        print()
        print("=" * 60)
        print("::: AUTONOMOUS GNOME STOPPED")
        print("=" * 60)
        done, total = self.tasks.get_progress()
        print(f"Progress: {done}/{total} tasks completed")
        print(f"Sessions: {session_count}")
        print(f"Checkpoint saved in: {self.checkpoint.checkpoint_file}")
