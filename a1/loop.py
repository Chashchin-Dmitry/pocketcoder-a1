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
        self._log_callback = None  # Callback for live log streaming
        self._last_verification = None  # Last verification result
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Настроить обработку Ctrl+C (only works in main thread)"""
        import threading
        if threading.current_thread() is threading.main_thread():
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

    def _classify_tool(self, tool_name: str, tool_input: dict):
        """Classify a tool_use block into (display_text, event_type)"""
        type_map = {"Read": "read", "Edit": "edit", "Write": "write",
                    "Bash": "bash", "Glob": "read", "Grep": "read"}
        ev_type = type_map.get(tool_name, "bash")
        if tool_name in ("Read", "Glob", "Grep"):
            target = tool_input.get("file_path") or tool_input.get("pattern") or ""
            return f"[{tool_name}] {target}", ev_type
        elif tool_name in ("Edit", "Write"):
            target = tool_input.get("file_path", "")
            return f"[{tool_name}] {target}", ev_type
        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")[:80]
            return f"[Bash] {cmd}", ev_type
        return f"[{tool_name}]", ev_type

    def _parse_stream_event(self, line: str):
        """Parse a stream-json NDJSON line into (display_text, event_type)

        With -p --verbose --output-format stream-json, Claude CLI outputs:
        - {"type":"system","subtype":"init",...}
        - {"type":"assistant","message":{"content":[{"type":"text",...}]}}
        - {"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read",...}]}}
        - {"type":"assistant","message":{"content":[{"type":"thinking",...}]}}
        - {"type":"user","message":{"content":[{"type":"tool_result",...}]}} (skip)
        - {"type":"result","result":"..."}
        - {"type":"rate_limit_event",...} (skip)
        """
        import json as _json
        stripped = line.strip()
        if not stripped:
            return None, None
        try:
            event = _json.loads(stripped)
        except (_json.JSONDecodeError, ValueError):
            return stripped, "text"

        etype = event.get("type", "")

        # Skip non-useful events
        if etype in ("system", "user", "rate_limit_event"):
            return None, None

        # Result message
        if etype == "result":
            result_text = str(event.get("result", ""))[:200]
            if result_text.strip():
                return f"[Result] {result_text}", "text"
            return None, None

        # Assistant message — contains text, tool_use, or thinking blocks
        if etype == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])
            for block in content:
                btype = block.get("type", "")

                # Tool use — Read, Edit, Write, Bash, etc.
                if btype == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    return self._classify_tool(tool_name, tool_input)

                # Text output
                if btype == "text":
                    text = block.get("text", "")[:150]
                    if text.strip():
                        return text.strip(), "text"

                # Thinking (extended thinking)
                if btype == "thinking":
                    thinking = block.get("thinking", "")[:100]
                    if thinking.strip():
                        return thinking.strip(), "thinking"

            return None, None

        return None, None

    # Checks that BLOCK completion (must fix)
    BLOCKING_CHECKS = {"syntax", "tests"}
    # Checks that WARN but don't block (nice to fix)
    WARNING_CHECKS = {"lint", "build", "git"}
    # Max retries before giving up
    MAX_VERIFY_RETRIES = 3

    def _capture_baseline(self):
        """Capture validation state BEFORE first session.

        Baseline = pre-existing issues that aren't agent's fault.
        Only NEW issues (not in baseline) count as failures.
        """
        print("  [BASELINE] Capturing initial validation state...")
        self._baseline = {}
        val_results = self.validator.run_all()
        for name, report in val_results.items():
            self._baseline[name] = {
                "result": report.result.value,
                "message": report.message,
            }
        baseline_str = ", ".join(f"{k}={v['result']}" for k, v in self._baseline.items())
        print(f"  [BASELINE] Captured: {baseline_str}")

    def _is_new_issue(self, check_name: str, report) -> bool:
        """Check if this failure is NEW (not in baseline)."""
        if not hasattr(self, "_baseline") or not self._baseline:
            return True  # No baseline = everything is new
        baseline = self._baseline.get(check_name, {})
        # If baseline already had this check failing, it's pre-existing
        if baseline.get("result") == "fail":
            return False
        return True

    def _verify_session(self) -> dict:
        """Post-session verification — don't trust agent, verify.

        Three tiers:
        - BLOCKING (syntax, tests): must pass → retry if fail
        - WARNING (lint, build, git): log but don't block
        - INFO (files_exist, criteria): check and report

        Anti-infinite-loop: max 3 retries, baseline comparison.

        Returns: {"passed": bool, "blocking_issues": [], "warnings": [],
                  "retry_count": int, "summary": str}
        """
        blocking_issues = []
        warnings = []

        # 1. Run validator
        print("  [VERIFY] Running validation checks...")
        val_results = self.validator.run_all()

        for name, report in val_results.items():
            if report.result.value != "fail":
                continue
            # Skip pre-existing issues (baseline)
            if not self._is_new_issue(name, report):
                warnings.append(f"{name}: {report.message} (pre-existing, skipped)")
                continue

            if name in self.BLOCKING_CHECKS:
                blocking_issues.append(f"{name}: {report.message}")
                if report.details:
                    blocking_issues.append(f"  {report.details[:200]}")
            else:
                warnings.append(f"{name}: {report.message}")

        # 2. Check files_modified exist (BLOCKING)
        checkpoint = self.checkpoint.load()
        files_modified = checkpoint.get("files_modified", [])
        if files_modified:
            files_report = self.validator.check_files_exist(files_modified)
            if files_report.result.value == "fail":
                blocking_issues.append(f"files: {files_report.message}")

        # 3. Success criteria (BLOCKING)
        done_tasks = self.tasks.get_tasks(status="done")
        for task in done_tasks:
            if task.success_criteria:
                criteria_report = self.validator.check_criteria(task.success_criteria)
                if criteria_report.result.value == "fail":
                    blocking_issues.append(f"{task.id} criteria: {criteria_report.message}")

        # 4. All tasks done? (BLOCKING if checkpoint says COMPLETED)
        if checkpoint.get("status") == "COMPLETED":
            done, total = self.tasks.get_progress()
            if done < total:
                blocking_issues.append(f"tasks: Only {done}/{total} done but checkpoint says COMPLETED")

        # 5. Retry counter
        last_ver = checkpoint.get("last_verification", {})
        prev_retry = last_ver.get("retry_count", 0) if not last_ver.get("passed", True) else 0
        retry_count = prev_retry + 1 if blocking_issues else 0

        # 6. Anti-infinite-loop: max retries exceeded?
        force_accept = False
        if blocking_issues and retry_count >= self.MAX_VERIFY_RETRIES:
            force_accept = True
            warnings.append(
                f"MAX RETRIES ({self.MAX_VERIFY_RETRIES}) reached — accepting with issues"
            )

        passed = len(blocking_issues) == 0 or force_accept

        # Build summary
        summary_lines = []
        if passed and not force_accept:
            summary_lines.append("[VERIFY] All checks PASSED")
            for name, report in val_results.items():
                icon = "OK" if report.result.value == "ok" else "SKIP"
                summary_lines.append(f"  [{icon}] {name}: {report.message}")
        elif force_accept:
            summary_lines.append(f"[VERIFY] FORCE ACCEPTED after {retry_count} retries")
            for issue in blocking_issues:
                summary_lines.append(f"  [!] {issue}")
        else:
            summary_lines.append(f"[VERIFY] FAILED (attempt {retry_count}/{self.MAX_VERIFY_RETRIES})")
            for issue in blocking_issues:
                summary_lines.append(f"  [BLOCK] {issue}")

        if warnings:
            summary_lines.append("  Warnings:")
            for w in warnings[:5]:
                summary_lines.append(f"    [WARN] {w}")

        summary = "\n".join(summary_lines)
        print(summary)

        # Log callback for dashboard
        if self._log_callback:
            try:
                log_msg = f"[Verification] {'PASSED' if passed else f'FAILED ({retry_count}/{self.MAX_VERIFY_RETRIES}): ' + '; '.join(blocking_issues[:2])}"
                self._log_callback(log_msg, "text" if passed else "bash")
            except Exception:
                pass

        return {
            "passed": passed,
            "force_accepted": force_accept,
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "retry_count": retry_count,
            "summary": summary,
        }

    def _read_queue_messages(self) -> str:
        """Read unread messages from queue.json and mark them as read"""
        import json
        queue_file = self.project_dir / ".a1" / "queue.json"
        if not queue_file.exists():
            return ""
        try:
            data = json.loads(queue_file.read_text())
        except (json.JSONDecodeError, IOError):
            return ""
        unread = [m for m in data.get("messages", []) if not m.get("read")]
        if not unread:
            return ""
        # Mark as read
        for m in data["messages"]:
            if not m.get("read"):
                m["read"] = True
        queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        lines = ["## USER MESSAGES (from queue)"]
        for m in unread:
            lines.append(f"- [{m.get('added_at', '?')}] {m['text']}")
        lines.append("Please address these messages as part of your work.\n")
        return "\n".join(lines)

    def _get_verification_prompt(self) -> str:
        """Build verification failure info for prompt"""
        if not self._last_verification or self._last_verification.get("passed", True):
            return ""
        blocking = self._last_verification.get("blocking_issues", [])
        warnings = self._last_verification.get("warnings", [])
        retry = self._last_verification.get("retry_count", 0)
        if not blocking and not warnings:
            return ""
        lines = [
            f"## VERIFICATION FAILED (attempt {retry}/{self.MAX_VERIFY_RETRIES})",
            "The system ran automated checks after your last session.",
            "",
        ]
        if blocking:
            lines.append("BLOCKING ISSUES (must fix):")
            for issue in blocking[:10]:
                lines.append(f"- {issue}")
            lines.append("")
        if warnings:
            lines.append("Warnings (non-blocking):")
            for w in warnings[:5]:
                lines.append(f"- {w}")
            lines.append("")
        lines.append("FIX THE BLOCKING ISSUES before marking any task as done.")
        if retry >= self.MAX_VERIFY_RETRIES - 1:
            lines.append(f"WARNING: This is attempt {retry + 1} of {self.MAX_VERIFY_RETRIES}. If issues persist, the system will force-accept.")
        lines.append("")
        return "\n".join(lines)

    def build_prompt(self, is_first: bool = False) -> str:
        """Build prompt for session (English prompts, respond in user's language)"""
        checkpoint_summary = self.checkpoint.get_summary()
        tasks_summary = self.tasks.get_summary()
        queue_messages = self._read_queue_messages()
        verification_prompt = self._get_verification_prompt()

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

## HOW TO UPDATE TASK STATUS
When you complete a task, edit .a1/tasks.json:
- Change "status": "pending" → "in_progress" when starting
- Change "status": "in_progress" → "done" when finished
- Add "completed_at": "<ISO datetime>" when done

## HOW TO UPDATE CHECKPOINT
When done or before stopping, edit .a1/checkpoint.json:
- Set "current_task" to the task ID you worked on
- Set "files_modified" to list of files you changed
- Set "decisions" to list of key decisions made
- Set "last_action" to description of last thing done
- Set "status" to "COMPLETED" if ALL tasks are done

## VALIDATION COMMANDS
- Syntax: python -m py_compile <file>
- Tests: pytest -v
- Lint: ruff check .

## SUCCESS CRITERIA
Each task has success_criteria field — verify it before marking done.

## TASK PRIORITY
Tasks are ordered by priority (lower number = higher priority).
Always work on the pending task with the LOWEST priority number first.

## IMPORTANT
- You have max 25 tool-use turns. Work efficiently.
- Focus on ONE task at a time.
- Validate your changes before marking done.

## START
Begin with the highest-priority pending task. Work autonomously.

{verification_prompt}{queue_messages}"""
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

## HOW TO UPDATE TASK STATUS
Edit .a1/tasks.json — change "status" field: "pending" → "in_progress" → "done"
Add "completed_at" ISO datetime when marking done.

## HOW TO UPDATE CHECKPOINT
Edit .a1/checkpoint.json — set current_task, files_modified, decisions, last_action.

## IMPORTANT
- You have max 25 tool-use turns. Work efficiently.
- Focus on ONE task at a time.

{verification_prompt}{queue_messages}Continue working.
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
            # Clean env: remove CLAUDECODE to allow nested sessions
            import os
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)

            self._current_process = subprocess.Popen(
                ["claude", "-p", prompt,
                 "--dangerously-skip-permissions",
                 "--no-session-persistence",
                 "--max-turns", "25",
                 "--verbose",
                 "--output-format", "stream-json"],
                cwd=self.project_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            output_lines = []
            with open(log_file, "w") as f:
                while True:
                    line = self._current_process.stdout.readline()
                    if not line and self._current_process.poll() is not None:
                        break
                    if not line:
                        continue
                    f.write(line)
                    f.flush()
                    output_lines.append(line)

                    # Parse stream-json NDJSON events
                    display_text, event_type = self._parse_stream_event(line)
                    if display_text:
                        print(display_text)
                        if self._log_callback:
                            try:
                                self._log_callback(display_text, event_type)
                            except Exception:
                                pass

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

        # Capture baseline BEFORE first session (pre-existing issues)
        self._capture_baseline()

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

            # POST-SESSION VERIFICATION — don't trust agent, verify
            verification = self._verify_session()
            self._last_verification = verification

            # Проверяем статус (only trust COMPLETED if verification passed)
            if self.checkpoint.is_completed():
                if verification["passed"]:
                    label = "FORCE ACCEPTED" if verification.get("force_accepted") else "VERIFIED"
                    print()
                    print("=" * 60)
                    print(f"[OK] ALL TASKS COMPLETED + {label}!")
                    print("=" * 60)
                    done, total = self.tasks.get_progress()
                    print(f"Tasks: {done}/{total}")
                    print(f"Sessions: {session_count}")
                    if verification.get("force_accepted"):
                        print(f"  (accepted with issues after {verification['retry_count']} retries)")
                    break
                else:
                    # Agent says COMPLETED but verification failed — retry
                    retry = verification["retry_count"]
                    print()
                    print(f"[!] Agent marked COMPLETED but verification FAILED (attempt {retry}/{self.MAX_VERIFY_RETRIES})")
                    print("    Resetting to WORKING — will retry in next session")
                    cp_data = self.checkpoint.load()
                    cp_data["status"] = "WORKING"
                    cp_data["last_verification"] = {
                        "passed": False,
                        "blocking_issues": verification["blocking_issues"],
                        "warnings": verification["warnings"],
                        "retry_count": retry,
                        "session": cp_data.get("session", 0),
                    }
                    self.checkpoint.save(cp_data)

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
