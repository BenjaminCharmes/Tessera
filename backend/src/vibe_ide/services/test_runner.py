import asyncio
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 120


class TestCommandNotFound(Exception):
    pass


@dataclass
class TestResult:
    passed: bool
    total: int
    failed: int
    output_summary: str
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


class TestRunnerService:
    def detect_test_command(
        self,
        project_path: Path,
        override: str | None = None,
    ) -> str:
        if override:
            return override
        if (project_path / "pyproject.toml").exists():
            return "uv run pytest"
        if (project_path / "package.json").exists():
            return "npm test"
        if (project_path / "Cargo.toml").exists():
            return "cargo test"
        raise TestCommandNotFound(
            f"Impossible de détecter la commande de test dans {project_path}"
        )

    async def run_tests(
        self,
        project_path: Path,
        test_command: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> TestResult:
        cmd = self.detect_test_command(project_path, override=test_command)
        args = shlex.split(cmd)

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            duration_ms = int((time.monotonic() - start) * 1000)
            _logger.warning("test_runner_timeout", extra={"cmd": cmd, "timeout": timeout})
            return TestResult(
                passed=False,
                total=0,
                failed=0,
                output_summary=f"Timeout après {timeout}s — {cmd}",
                errors=[f"Timeout après {timeout}s"],
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            _logger.warning("test_runner_exec_failed", extra={"error": str(exc)})
            return TestResult(
                passed=False,
                total=0,
                failed=0,
                output_summary=f"Erreur d'exécution : {exc}",
                errors=[str(exc)],
                duration_ms=duration_ms,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        combined = (stdout + "\n" + stderr).strip()

        return _parse_output(proc.returncode or 0, combined, duration_ms)


def _parse_output(returncode: int, output: str, duration_ms: int) -> TestResult:
    passed = returncode == 0
    total, failed = _extract_counts(output)
    summary = _extract_summary_line(output) or (
        f"{'OK' if passed else 'FAILED'} (exit {returncode})"
    )
    errors = _extract_errors(output) if not passed else []
    return TestResult(
        passed=passed,
        total=total,
        failed=failed,
        output_summary=summary,
        errors=errors,
        duration_ms=duration_ms,
    )


def _extract_counts(output: str) -> tuple[int, int]:
    import re

    # pytest: "5 passed", "2 failed, 3 passed"
    m = re.search(r"(\d+) passed", output)
    passed_count = int(m.group(1)) if m else 0
    m_fail = re.search(r"(\d+) failed", output)
    failed_count = int(m_fail.group(1)) if m_fail else 0

    # jest/vitest: "Tests: 5 passed, 7 total"
    m_total = re.search(r"(\d+) total", output)
    total = int(m_total.group(1)) if m_total else (passed_count + failed_count)

    return total, failed_count


def _extract_summary_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line and any(
            kw in line.lower()
            for kw in ("passed", "failed", "error", "ok", "test")
        ):
            return line[:200]
    return ""


def _extract_errors(output: str, max_errors: int = 5) -> list[str]:
    errors: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if any(kw in stripped.upper() for kw in ("FAILED", "ERROR", "ASSERT")):
            errors.append(stripped[:300])
        if len(errors) >= max_errors:
            break
    return errors
