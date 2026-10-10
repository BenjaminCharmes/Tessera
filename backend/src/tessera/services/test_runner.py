import asyncio
import shlex
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
import time
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.commande_chainee import decouper
from tessera.services.lancement import essais_de_commande
from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 120

# Sémaphore partagé entre tous les TestRunnerService du processus.
# Créé paresseusement : il n'y a pas de boucle asyncio à l'import (ticket-348).
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore | None:
    """Return (or create) the process-wide test slot semaphore.

    Lazily created on first call so that no event loop is required at import
    time.  Returns ``None`` when the bound is disabled (limit ≤ 0).
    """
    global _semaphore
    from tessera.config import settings

    limit = settings.max_parallel_test_runs
    if limit <= 0:
        return None
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(limit)
    return _semaphore


def reset_semaphore_for_tests(limit: int | None = None) -> None:
    """Reset the shared semaphore.  For test isolation only."""
    global _semaphore
    _semaphore = asyncio.Semaphore(limit) if (limit is not None and limit > 0) else None


@asynccontextmanager
async def _acquis(
    en_attente_fn: Callable[[], Awaitable[None]] | None,
) -> AsyncGenerator[None, None]:
    """Hold the shared test slot for the duration of a ``run_tests`` call.

    Calls ``en_attente_fn`` once if the slot is not immediately available.
    A ``None`` semaphore (limit ≤ 0) lets every call through without waiting.
    The check of ``_value`` is safe in asyncio's single-threaded model : no
    other coroutine runs between the check and the ``async with`` unless we
    yield, and we only yield here when the slot is already taken.
    """
    sem = _get_semaphore()
    if sem is None:
        yield
        return
    if sem._value <= 0 and en_attente_fn is not None:
        await en_attente_fn()
    async with sem:
        yield

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
    #: Détail structuré des échecs : section « short test summary info » de
    #: pytest ou lignes FAIL/× de vitest, suivi du bloc FAILURES/ERRORS,
    #: tronqué à 8 000 caractères. Vide quand les tests passent (ticket-393).
    failure_details: str = ""
    duration_ms: int = 0
    #: La commande a-t-elle seulement démarré ? Faux quand l'exécutable est
    #: introuvable — ce qui n'est pas la même chose que des tests rouges, et
    #: ne demande pas la même chose au codeur. Deux tours de revue ont été
    #: dépensés à corriger du code qui n'était pas en cause (ticket-157).
    demarree: bool = True
    #: Le délai global a-t-il été dépassé avant la fin de la commande ?
    #: Distinct d'un test rouge : aucun test n'a été exécuté jusqu'au bout,
    #: donc rien ne dit que le code est en cause. Relancer sans repasser par
    #: le codeur est la bonne réponse (ticket-349).
    expiree: bool = False
    #: Chaque étape lancée et son code de sortie, dans l'ordre : ce que le
    #: validateur lit pour juger « typecheck, lint et build passent »
    #: (ticket-337).
    etapes: list["EtapeTest"] = field(default_factory=list)


@dataclass
class EtapeTest:
    """One step of the test command, as it was launched."""

    commande: str
    code: int


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
        en_attente: Callable[[], Awaitable[None]] | None = None,
    ) -> TestResult:
        # Résolu, et pas seulement absolu : `projects/` ne contient que des
        # liens symboliques vers les vrais dépôts. Lancé sur le chemin du
        # lien, Vite résout une racine réelle qu'il ne retrouve plus, et les
        # tests échouaient sous le pipeline en passant à la main, au même
        # instant et au même endroit. ADR-017 pose déjà l'invariant pour le
        # provider ; il vaut partout où l'on lance un processus (ticket-158).
        project_path = project_path.resolve()
        cmd = self.detect_test_command(project_path, override=test_command)
        if timeout is None:
            timeout = self._timeout
        try:
            etapes_args = decouper(cmd)
        except ValueError as exc:
            # `CommandeNonGeree`, ou des guillemets que `shlex` ne referme pas :
            # rien n'a été lancé, et ce n'est pas un test rouge (ticket-337).
            return TestResult(
                passed=False,
                demarree=False,
                total=0,
                failed=0,
                output_summary=f"La commande de test n'a pas démarré : {exc}",
                errors=[str(exc)],
            )

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

        # Le créneau est pris ici : l'attente ne compte pas dans le délai.
        # `start` n'est relevé qu'une fois le créneau obtenu (ticket-348).
        async with _acquis(en_attente):
            start = time.monotonic()
            etapes: list[EtapeTest] = []
            sorties: list[str] = []
            code = 0
            for args in etapes_args:
                issue = await self._executer(args, dossier, cmd, timeout, start)
                if isinstance(issue, TestResult):
                    issue.etapes = etapes
                    return issue
                code, sortie = issue
                etapes.append(EtapeTest(commande=shlex.join(args), code=code))
                sorties.append(sortie)
                if code != 0:
                    break

            duration_ms = int((time.monotonic() - start) * 1000)
            result = _parse_output(code, "\n".join(sorties).strip(), duration_ms)
            result.etapes = etapes
            return result

    async def _executer(
        self, args: list[str], dossier: Path, cmd: str, timeout: int, start: float
    ) -> "tuple[int, str] | TestResult":
        """Run one step; a ``TestResult`` when it could not run to its end.

        ``timeout`` bounds the whole command, not each step: what earlier
        steps used is taken from what this one may use.
        """
        restant = max(float(timeout) - (time.monotonic() - start), 0.0)
        try:
            proc = await self._lancer(args, dossier)
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=restant
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
                expiree=True,
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
                    f"La commande de test n'a pas démarré : « {shlex.join(args)} » — "
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

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return proc.returncode or 0, (stdout + "\n" + stderr).strip()


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
    failure_details = _extract_failure_details(output) if not passed else ""
    return TestResult(
        passed=passed,
        total=total,
        failed=failed,
        output_summary=summary,
        errors=errors,
        failure_details=failure_details,
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
    """Extract the canonical summary line from pytest or vitest output.

    Prioritises the pytest timing banner (=== N failed, M passed in X.XXs ===)
    and the vitest summary line over the heuristic reverse scan, which can
    pick up warnings printed after the real summary (ticket-393).
    """
    import re

    # Priorité 1 : résumé final de pytest (=== N failed, M passed in X.XXs ===)
    for line in output.splitlines():
        stripped = line.strip()
        if (
            re.match(r"={4,}[^=]+={4,}$", stripped)
            and re.search(r"\d+.*in\s+[\d.]+s", stripped)
            and any(kw in stripped.lower() for kw in ("passed", "failed", "error"))
        ):
            return stripped[:200]

    # Priorité 2 : résumé vitest (Tests  N failed | M passed)
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"Tests\s+\d+", stripped, re.IGNORECASE) and any(
            kw in stripped.lower() for kw in ("passed", "failed")
        ):
            return stripped[:200]

    # Repli : heuristique (dernière ligne avec un mot-clé de test)
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line and any(
            kw in line.lower()
            for kw in ("passed", "failed", "error", "ok", "test")
        ):
            return line[:200]
    return ""


def _extract_failure_details(output: str, max_chars: int = 8000) -> str:
    """Extract structured failure details from pytest or vitest output.

    Returns, in order: the 'short test summary info' section of pytest (or
    FAIL/× lines of vitest), then the FAILURES/ERRORS detail blocks.
    Truncated to ``max_chars`` characters, keeping the beginning.
    """
    short = _extract_pytest_short_summary(output)
    failures = _extract_pytest_failures_section(output)

    parts: list[str] = [p for p in (short, failures) if p]
    if not parts:
        vitest = _extract_vitest_failures(output)
        if vitest:
            parts.append(vitest)

    combined = "\n\n".join(parts)
    return combined[:max_chars]


def _extract_pytest_short_summary(output: str) -> str:
    """Extract FAILED/ERROR lines from the pytest 'short test summary info' section."""
    import re

    in_section = False
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"={4,}\s+short test summary info\s+={4,}", stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("="):
                break
            if stripped:
                result.append(stripped)

    return "\n".join(result)


def _extract_pytest_failures_section(output: str) -> str:
    """Extract the FAILURES and ERRORS detail blocks from pytest output."""
    import re

    in_section = False
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        is_section_header = bool(re.match(r"={4,}[^=]+={4,}$", stripped))
        if is_section_header:
            if re.match(r"={4,}\s*(?:FAILURES|ERRORS)\s*={4,}$", stripped, re.IGNORECASE):
                in_section = True
                result.append(stripped)
            elif in_section:
                in_section = False
        elif in_section:
            result.append(line.rstrip())

    return "\n".join(result).strip()


def _extract_vitest_failures(output: str) -> str:
    """Extract failing test names and assertion errors from vitest output."""
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("×")
            or stripped.startswith("✗")
            or stripped.startswith("FAIL ")
            or stripped.startswith("AssertionError")
            or stripped.startswith("Error:")
        ):
            result.append(stripped)

    return "\n".join(result)


def _extract_errors(output: str, max_errors: int = 5) -> list[str]:
    errors: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if any(kw in stripped.upper() for kw in ("FAILED", "ERROR", "ASSERT")):
            errors.append(stripped[:300])
        if len(errors) >= max_errors:
            break
    return errors
