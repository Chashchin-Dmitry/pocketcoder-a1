"""
Validator — "зрение" агента, проверка результатов
"""

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ValidationResult(Enum):
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class ValidationReport:
    result: ValidationResult
    message: str
    details: Optional[str] = None
    command: Optional[str] = None


class Validator:
    """Зрение агента — проверка что всё ок"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    def has_git(self) -> bool:
        """Check if project has git initialized"""
        return (self.project_dir / ".git").exists()

    def run_all(self) -> Dict[str, ValidationReport]:
        """Запустить все проверки"""
        results = {}

        results["syntax"] = self._check_syntax()
        results["tests"] = self._run_tests()
        results["lint"] = self._run_lint()
        results["build"] = self._check_build()

        # Git checks (optional — works without git)
        git_report = self._check_git()
        if git_report:
            results["git"] = git_report

        return results

    def _run_command(
        self, cmd: List[str], timeout: int = 60
    ) -> Tuple[int, str, str]:
        """Запустить команду и вернуть результат"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"

    def _check_syntax(self) -> ValidationReport:
        """Проверить синтаксис Python файлов"""
        py_files = list(self.project_dir.rglob("*.py"))

        if not py_files:
            return ValidationReport(
                result=ValidationResult.SKIP,
                message="No Python files found",
            )

        errors = []
        for f in py_files:
            code, stdout, stderr = self._run_command(
                ["python", "-m", "py_compile", str(f)]
            )
            if code != 0:
                errors.append(f"{f.name}: {stderr}")

        if errors:
            return ValidationReport(
                result=ValidationResult.FAIL,
                message=f"Syntax errors in {len(errors)} files",
                details="\n".join(errors[:5]),
                command="python -m py_compile",
            )

        return ValidationReport(
            result=ValidationResult.OK,
            message=f"Syntax OK ({len(py_files)} files)",
        )

    def _run_tests(self) -> ValidationReport:
        """Запустить тесты"""
        # Пробуем pytest
        code, stdout, stderr = self._run_command(
            ["python", "-m", "pytest", "-v", "--tb=short"], timeout=120
        )

        if code == -2:  # pytest не установлен
            # Пробуем unittest
            code, stdout, stderr = self._run_command(
                ["python", "-m", "unittest", "discover", "-v"]
            )

            if code == -2:
                return ValidationReport(
                    result=ValidationResult.SKIP,
                    message="No test framework found",
                )

        if code == 0:
            return ValidationReport(
                result=ValidationResult.OK,
                message="All tests passed",
                details=stdout[-500:] if stdout else None,
                command="pytest",
            )
        elif code == 5:  # pytest: no tests found
            return ValidationReport(
                result=ValidationResult.SKIP,
                message="No tests found",
                command="pytest",
            )
        else:
            return ValidationReport(
                result=ValidationResult.FAIL,
                message="Tests failed",
                details=(stderr or stdout)[-500:],
                command="pytest",
            )

    def _run_lint(self) -> ValidationReport:
        """Запустить линтер"""
        # Пробуем ruff (быстрый)
        code, stdout, stderr = self._run_command(
            ["ruff", "check", ".", "--output-format=concise"]
        )

        if code == -2:  # ruff не установлен
            # Пробуем flake8
            code, stdout, stderr = self._run_command(["flake8", "."])

            if code == -2:
                return ValidationReport(
                    result=ValidationResult.SKIP,
                    message="No linter found (ruff/flake8)",
                )

        if code == 0:
            return ValidationReport(
                result=ValidationResult.OK,
                message="Lint passed",
                command="ruff check",
            )
        else:
            # Lint warnings/errors но не критично
            issues = stdout.count("\n") if stdout else 0
            return ValidationReport(
                result=ValidationResult.FAIL,
                message=f"Lint issues: {issues}",
                details=(stdout or stderr)[-500:],
                command="ruff check",
            )

    def _check_build(self) -> ValidationReport:
        """Проверить что проект собирается"""
        # Python package
        if (self.project_dir / "pyproject.toml").exists():
            code, stdout, stderr = self._run_command(
                ["python", "-m", "build", "--no-isolation"], timeout=120
            )

            if code == -2:
                return ValidationReport(
                    result=ValidationResult.SKIP,
                    message="build module not installed",
                )

            if code == 0:
                return ValidationReport(
                    result=ValidationResult.OK,
                    message="Build successful",
                    command="python -m build",
                )
            else:
                return ValidationReport(
                    result=ValidationResult.FAIL,
                    message="Build failed",
                    details=(stderr or stdout)[-500:],
                    command="python -m build",
                )

        # Node.js
        if (self.project_dir / "package.json").exists():
            code, stdout, stderr = self._run_command(["npm", "run", "build"])

            if code == 0:
                return ValidationReport(
                    result=ValidationResult.OK,
                    message="npm build successful",
                    command="npm run build",
                )
            elif "missing script: build" in stderr:
                return ValidationReport(
                    result=ValidationResult.SKIP,
                    message="No build script",
                )
            else:
                return ValidationReport(
                    result=ValidationResult.FAIL,
                    message="npm build failed",
                    details=(stderr or stdout)[-500:],
                    command="npm run build",
                )

        return ValidationReport(
            result=ValidationResult.SKIP,
            message="No build config found",
        )

    def _check_git(self) -> Optional[ValidationReport]:
        """Check git status if git is available. Returns None if no git."""
        if not self.has_git():
            return None

        # Check for changes
        code, stdout, stderr = self._run_command(["git", "diff", "--stat"])
        staged_code, staged_out, _ = self._run_command(["git", "diff", "--cached", "--stat"])
        has_changes = bool(stdout.strip()) or bool(staged_out.strip())

        # Check for untracked files
        code, stdout, stderr = self._run_command(["git", "status", "--porcelain"])
        lines = [l for l in stdout.strip().split("\n") if l.strip()]
        untracked = [l for l in lines if l.startswith("??")]

        msg = f"Changes: {'yes' if has_changes else 'none'}, untracked: {len(untracked)}"
        return ValidationReport(
            result=ValidationResult.OK,
            message=msg,
            command="git status",
        )

    def check_files_exist(self, file_paths: List[str]) -> ValidationReport:
        """Check that specified files actually exist on disk"""
        if not file_paths:
            return ValidationReport(
                result=ValidationResult.SKIP,
                message="No files to check",
            )

        missing = []
        for fp in file_paths:
            full = self.project_dir / fp
            if not full.exists():
                missing.append(fp)

        if missing:
            return ValidationReport(
                result=ValidationResult.FAIL,
                message=f"{len(missing)} files missing: {', '.join(missing[:5])}",
            )

        return ValidationReport(
            result=ValidationResult.OK,
            message=f"All {len(file_paths)} files exist",
        )

    def check_criteria(self, criteria: str) -> ValidationReport:
        """Check success_criteria using heuristics.

        Recognizes patterns:
        - "tests pass" / "pytest" → run pytest
        - "file X exists" → check file
        - "lint clean" / "no lint" → run linter
        - anything else → SKIP (can't verify programmatically)
        """
        cl = criteria.lower()

        # Tests pass?
        if ("test" in cl and "pass" in cl) or "pytest" in cl:
            report = self._run_tests()
            return ValidationReport(
                result=report.result,
                message=f"Criteria '{criteria}': {report.message}",
                details=report.details,
                command=report.command,
            )

        # Lint clean?
        if "lint" in cl and ("clean" in cl or "pass" in cl or "no " in cl):
            report = self._run_lint()
            return ValidationReport(
                result=report.result,
                message=f"Criteria '{criteria}': {report.message}",
                details=report.details,
                command=report.command,
            )

        # File exists? (pattern: "file X exists" or "X.ext exists")
        # Use ORIGINAL criteria for filename (not lowercased) to preserve case
        import re
        file_match = re.search(r"['\"]?(\S+\.\w{1,5})['\"]?\s+exist", cl)
        if not file_match:
            file_match = re.search(r"exist\w*\s+['\"]?(\S+\.\w{1,5})['\"]?", cl)
        if file_match:
            # Re-match on original criteria to get correct case
            orig_match = re.search(r"['\"]?(\S+\.\w{1,5})['\"]?\s+exist", criteria, re.IGNORECASE)
            if not orig_match:
                orig_match = re.search(r"exist\w*\s+['\"]?(\S+\.\w{1,5})['\"]?", criteria, re.IGNORECASE)
            fname = orig_match.group(1) if orig_match else file_match.group(1)
            exists = (self.project_dir / fname).exists()
            return ValidationReport(
                result=ValidationResult.OK if exists else ValidationResult.FAIL,
                message=f"Criteria '{criteria}': file {'found' if exists else 'NOT found'}",
            )

        # Can't verify programmatically
        return ValidationReport(
            result=ValidationResult.SKIP,
            message=f"Criteria '{criteria}': can't verify automatically",
        )

    def get_summary(self) -> str:
        """Получить текстовое резюме для промпта"""
        results = self.run_all()

        lines = ["## Validation Results"]

        icons = {
            ValidationResult.OK: "[OK]",
            ValidationResult.FAIL: "[FAIL]",
            ValidationResult.SKIP: "[SKIP]",
            ValidationResult.ERROR: "[ERR]",
        }

        all_ok = True
        for name, report in results.items():
            icon = icons.get(report.result, "?")
            lines.append(f"{icon} {name}: {report.message}")
            if report.result == ValidationResult.FAIL:
                all_ok = False
                if report.details:
                    for line in report.details.split("\n")[:3]:
                        lines.append(f"    {line}")

        if all_ok:
            lines.insert(1, "**All checks passed!**\n")
        else:
            lines.insert(1, "**Some checks failed!**\n")

        return "\n".join(lines)
