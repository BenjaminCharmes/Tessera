import asyncio
import shlex
from typing import Any
import time
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.lancement import essais_de_commande
from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 120

# pytest sort 5 quand il n'a collecté aucun test. Ce n'est pas un test rouge :
# lu comme tel, un projet neuf renvoyait le codeur corriger des tests qui
# n'existent pas (ticket-122).
_PYTEST_NO_TESTS_COLLECTED = 5


class TestCommandNotFound(Exception):
    # Not a pytest test class despite the "Test" prefix — see TestResult.
    __test__ = False


@dataclass
class TestResult:
    # Tells pytest not to try collecting this as a test class just because
    # its name starts with "Test" (it is a result dataclass, and pytest
    # warns on every run otherwise).
    __test__ = False

    passed: bool
    total: int
    failed: int
    output_summary: str
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0
    #: La commande a-t-elle seulement démarré ? Faux quand l'exécutable est
    #: introuvable — ce qui n'est pas la même chose que des tests rouges, et
    #: ne demande pas la même chose au codeur. Deux tours de revue ont été
    #: dépensés à corriger du code qui n'était pas en cause (ticket-157).
    demarree: bool = True


class TestRunnerService:
    def __init__(self, cwd: str | None = None, timeout: int | None = None) -> None:
        """``cwd`` and ``timeout`` come from the project's pipeline config.

        Les tests d'ide-core vivent dans `../../backend`, et la suite dure plus
        que le délai par défaut : sans ces deux réglages, le testeur ne pouvait
        être activé sur aucun projet dont les tests ne sont pas à sa racine
        (ticket-241).
        """
        self._cwd = cwd
        self._timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT

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

    async def _lancer(self, args: list[str], dossier: Path) -> Any:
        """Launch the command, trying its Windows form when needed.

        La règle de résolution est dans `services/lancement.py`, partagée avec
        `ProcessRegistry` : deux copies de cette logique ont divergé une fois,
        et c'est ce qui a rendu `blocked` un ticket dont le code était juste
        (ticket-157).
        """
        derniere: FileNotFoundError | None = None
        for tentative in essais_de_commande(args):
            try:
                return await asyncio.create_subprocess_exec(
                    *tentative,
                    cwd=dossier,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as exc:
                derniere = exc
        raise derniere if derniere else FileNotFoundError(args[0] if args else "")

    async def run_tests(
        self,
        project_path: Path,
        test_command: str | None = None,
        timeout: int | None = None,
    ) -> TestResult:
        # Résolu, et pas seulement absolu : `projects/` ne contient que des
        # liens symboliques vers les vrais dépôts. Lancé sur le chemin du
        # lien, Vite résout une racine réelle qu'il ne retrouve plus, et les
        # tests échouaient sous le pipeline en passant à la main, au même
        # instant et au même endroit. ADR-017 pose déjà l'invariant pour le
        # provider ; il vaut partout où l'on lance un processus (ticket-158).
        project_path = project_path.resolve()
        cmd = self.detect_test_command(project_path, override=test_command)
        args = shlex.split(cmd)
        if timeout is None:
            timeout = self._timeout

        # Même frontière que les services d'ADR-042 : un `cwd` qui sort du
        # projet ne lance rien, et le résultat le dit plutôt que de lever.
        try:
            dossier = resoudre_le_cwd(project_path, self._cwd) if self._cwd else project_path
        except CommandeInvalide as exc:
            return TestResult(
                passed=False,
                demarree=False,
                total=0,
                failed=0,
                output_summary=f"La commande de test n'a pas démarré : {exc}",
                errors=[str(exc)],
            )

        start = time.monotonic()
        try:
            proc = await self._lancer(args, dossier)
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            # `kill()` sans `wait()` laisse un zombie et un transport que
            # asyncio ferme en se plaignant (ticket-122).
            try:
                proc.kill()
                await proc.wait()
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
        except FileNotFoundError as exc:
            # Pas un test rouge : la commande n'a pas démarré. Le dire
            # explicitement évite au codeur de corriger du code qui n'est pas
            # en cause (ticket-157).
            duration_ms = int((time.monotonic() - start) * 1000)
            _logger.warning(
                "test_runner_commande_introuvable",
                extra={"cmd": cmd, "error": str(exc)},
            )
            return TestResult(
                passed=False,
                demarree=False,
                total=0,
                failed=0,
                output_summary=(
                    f"La commande de test n'a pas démarré : « {cmd} » — "
                    "exécutable introuvable. Ce n'est pas un test en échec."
                ),
                errors=[str(exc)],
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
    if returncode == _PYTEST_NO_TESTS_COLLECTED and "no tests ran" in output.lower():
        _logger.warning("test_runner_no_tests_collected")
        return TestResult(
            passed=True,
            total=0,
            failed=0,
            output_summary="Aucun test collecté (exit 5) — rien à exécuter.",
            duration_ms=duration_ms,
        )
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
