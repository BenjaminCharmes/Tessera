import asyncio
import os
import shlex
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any
import time
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.commande_chainee import decouper
from tessera.services.detail_du_delai import detail_du_delai
from tessera.services.erreur_de_sortie import detail_avec_erreur
from tessera.services.groupe_d_etape import GroupeDEtape
from tessera.services.lancement import essais_de_commande
from tessera.services.minuteur_d_etape import MinuteurDEtape
from tessera.services.outil_introuvable import outil_introuvable
from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.services.sortie_de_test import (
    extract_counts,
    extract_errors,
    extract_failure_details,
    extract_summary_line,
)
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

# Nombre de lignes finales gardées comme détail d'échec quand la sortie de
# l'étape n'a aucune structure pytest ou vitest (ticket-401).
_LIGNES_DE_QUEUE = 60


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
    #: Quand ``expiree`` : l'étape en cours à la coupure et ce qu'elle avait
    #: déjà consommé. Elle n'est pas dans ``etapes``, qui ne garde que les
    #: étapes terminées avec un code de sortie (ticket-514).
    etape_coupee: "EtapeCoupee | None" = None
    #: Le délai global, en secondes, qui a expiré (0 tant qu'il n'a pas expiré).
    delai_s: float = 0.0


@dataclass
class EtapeTest:
    """One step of the test command, as it was launched."""

    commande: str
    code: int
    #: Durée de l'étape, du lancement à la fin du processus (ticket-514).
    duree_ms: int = 0


@dataclass
class EtapeCoupee:
    """The step that was running when the global timeout expired."""

    commande: str
    duree_ms: int


class TestRunnerService:
    def __init__(
        self,
        cwd: str | None = None,
        timeout: int | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        """``cwd`` and ``timeout`` come from the project's pipeline config.

        Les tests d'ide-core vivent dans `../../backend`, et la suite dure plus
        que le délai par défaut : sans ces deux réglages, le testeur ne pouvait
        être activé sur aucun projet dont les tests ne sont pas à sa racine
        (ticket-241).

        ``env`` est fusionné par-dessus l'environnement hérité, à chaque
        étape : c'est ainsi qu'un worktree pointe `PYTHONPATH` sur ses sources
        (ticket-524). Sans lui, l'environnement hérité passe tel quel.
        """
        self._cwd = cwd
        self._timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
        self._env = dict(env) if env else None

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
                    # `None` : le processus hérite de l'environnement du backend.
                    env={**os.environ, **self._env} if self._env else None,
                    # Entrée fermée : une commande de test n'est jamais
                    # interactive, et l'entrée héritée du backend (console
                    # Windows) laissait un postinstall attendre une saisie
                    # sans fin (ticket-512).
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    # Unix : l'étape chef de son groupe, pour tuer son arbre
                    # (ticket-507). Windows a le job, et ignore ce drapeau.
                    start_new_session=os.name != "nt",
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
                debut_etape = time.monotonic()
                issue = await self._executer(args, dossier, cmd, timeout, start)
                duree_etape_ms = int((time.monotonic() - debut_etape) * 1000)
                if isinstance(issue, TestResult):
                    issue.etapes = etapes
                    if issue.expiree:
                        # Coupée par le minuteur : sa durée est déjà posée.
                        coupee = issue.etape_coupee
                        duree = coupee.duree_ms if coupee else duree_etape_ms
                        _noter_la_coupure(issue, args, duree, timeout)
                    return issue
                code, sortie = issue
                etapes.append(
                    EtapeTest(
                        commande=shlex.join(args), code=code, duree_ms=duree_etape_ms
                    )
                )
                sorties.append(sortie)
                if code != 0:
                    break

            duration_ms = int((time.monotonic() - start) * 1000)
            if code != 0:
                # Seule la sortie de l'étape en échec est lue : les étapes
                # précédentes, vertes, masquaient son résumé (ticket-401).
                result = _parse_failed_step(
                    etapes[-1], sorties[-1].strip(), duration_ms, len(etapes_args) > 1
                )
                outil = outil_introuvable(sorties[-1], dossier, project_path)
                if outil:
                    _marquer_panne_d_environnement(result, etapes[-1], outil)
            else:
                result = _parse_output(code, "\n".join(sorties).strip(), duration_ms)
            result.etapes = etapes
            return result

    async def _executer(
        self, args: list[str], dossier: Path, cmd: str, timeout: int, start: float
    ) -> "tuple[int, str] | TestResult":
        """Run one step; a ``TestResult`` when it could not run to its end.

        ``timeout`` bounds the whole command, not each step: what earlier
        steps used is taken from what this one may use.

        Each step has its own process group, closed when the step ends — even
        green, so no descendant outlives it (ticket-507).
        """
        groupe = GroupeDEtape()
        try:
            return await self._executer_dans(groupe, args, dossier, cmd, timeout, start)
        finally:
            groupe.fermer()

    async def _executer_dans(
        self,
        groupe: GroupeDEtape,
        args: list[str],
        dossier: Path,
        cmd: str,
        timeout: int,
        start: float,
    ) -> "tuple[int, str] | TestResult":
        """Run one step inside ``groupe``; see ``_executer``.

        Un minuteur indépendant de la boucle double le ``wait_for`` : boucle
        bloquée, il tue l'arbre à l'échéance, et la sortie tardive de
        ``communicate()`` est lue comme un délai dépassé (ticket-571).
        """
        restant = max(float(timeout) - (time.monotonic() - start), 0.0)
        debut = time.monotonic()
        minuteur: MinuteurDEtape | None = None
        try:
            try:
                proc = await self._lancer(args, dossier)
                groupe.rattacher(proc.pid)
                minuteur = MinuteurDEtape(groupe, proc.pid, restant)
                minuteur.armer()
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=restant
                )
            except asyncio.TimeoutError:
                # Tuer le seul processus direct laissait ses petits-enfants garder
                # les tubes ouverts, et `wait()` ne revenait plus : on tue l'arbre
                # (ticket-507), et l'attente est bornée. `kill()` sans `wait()`
                # laisserait un zombie (ticket-122).
                await groupe.terminer(proc)
                return _resultat_expire(cmd, args, timeout, start, debut, minuteur)
            except Exception as exc:  # noqa: BLE001 — traité par `_echec_de_lancement`
                return _echec_de_lancement(exc, cmd, args, start)
            if minuteur is not None and minuteur.coupee_a is not None:
                return _resultat_expire(cmd, args, timeout, start, debut, minuteur)
        finally:
            if minuteur is not None:
                minuteur.annuler()

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return proc.returncode or 0, (stdout + "\n" + stderr).strip()


def _resultat_expire(
    cmd: str,
    args: list[str],
    timeout: int,
    start: float,
    debut: float,
    minuteur: "MinuteurDEtape | None",
) -> TestResult:
    """Build the result of a step that overran its deadline.

    Quand le minuteur a coupé, les durées partent de son instant de coupure et
    non du moment où la boucle a repris la main : c'est la durée réelle de la
    commande qui est rapportée (ticket-571).
    """
    coupee_a = minuteur.coupee_a if minuteur is not None else None
    fin = coupee_a if coupee_a is not None else time.monotonic()
    _logger.warning(
        "test_runner_timeout",
        extra={"cmd": cmd, "timeout": timeout, "minuteur": coupee_a is not None},
    )
    result = TestResult(
        passed=False,
        expiree=True,
        total=0,
        failed=0,
        output_summary=f"Timeout après {timeout}s — {cmd}",
        errors=[f"Timeout après {timeout}s"],
        duration_ms=int((fin - start) * 1000),
    )
    if coupee_a is not None:
        result.etape_coupee = EtapeCoupee(
            commande=shlex.join(args), duree_ms=int((fin - debut) * 1000)
        )
    return result


def _echec_de_lancement(
    exc: Exception, cmd: str, args: list[str], start: float
) -> TestResult:
    """Build the result of a step that could not run at all."""
    duration_ms = int((time.monotonic() - start) * 1000)
    if isinstance(exc, FileNotFoundError):
        # Pas un test rouge : la commande n'a pas démarré. Le dire
        # explicitement évite au codeur de corriger du code qui n'est pas
        # en cause (ticket-157).
        _logger.warning(
            "test_runner_commande_introuvable", extra={"cmd": cmd, "error": str(exc)}
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
    _logger.warning("test_runner_exec_failed", extra={"error": str(exc)})
    return TestResult(
        passed=False,
        total=0,
        failed=0,
        output_summary=f"Erreur d'exécution : {exc}",
        errors=[str(exc)],
        duration_ms=duration_ms,
    )


def _noter_la_coupure(
    result: TestResult, args: list[str], duree_ms: int, timeout: float
) -> None:
    """Record on an expired ``result`` which step was cut, and for how long it ran.

    Le détail des étapes (terminées puis coupée) rejoint le résumé : c'est ce
    que le journal et le codeur lisent (ticket-514).
    """
    result.etape_coupee = EtapeCoupee(commande=shlex.join(args), duree_ms=duree_ms)
    result.delai_s = float(timeout)
    detail = detail_du_delai(result)
    if detail:
        result.output_summary = f"{result.output_summary}\nÉtapes : {detail}"


def _marquer_panne_d_environnement(
    result: TestResult, etape: EtapeTest, outil: str
) -> None:
    """Turn a red step into an environment failure: the tool, not the code, is missing.

    Le détail de l'échec reste : c'est la sortie qui prouve le diagnostic
    (ticket-496).
    """
    _logger.warning(
        "test_runner_outil_introuvable", extra={"outil": outil, "etape": etape.commande}
    )
    result.demarree = False
    result.output_summary = (
        f"étape `{etape.commande}` — panne d'environnement : outil `{outil}` "
        "introuvable. Réinstaller les dépendances du projet. "
        "Ce n'est pas un test en échec."
    )
    result.errors = [result.output_summary]


def _parse_failed_step(
    etape: EtapeTest, sortie: str, duration_ms: int, enchainee: bool
) -> TestResult:
    """Build the result of a chain stopped by ``etape``, from its own output.

    Pour une commande enchaînée, le résumé nomme l'étape et son code de
    sortie : sans cela, rien n'indique laquelle des étapes a échoué. Une
    commande à étape unique garde son résumé tel quel.
    """
    result = _parse_output(etape.code, sortie, duration_ms)
    if result.passed:
        return result
    if enchainee:
        result.output_summary = (
            f"étape `{etape.commande}` (exit {etape.code}) — {result.output_summary}"
        )
    if not result.failure_details:
        # Une étape lint ou tsc n'a ni bandeau pytest ni ligne vitest :
        # la fin de sa sortie est ce qui explique l'échec.
        # La cause réelle (commande introuvable, module absent) est souvent bien
        # avant la dernière ligne, qui n'est que celle du gestionnaire de paquets
        # (ticket-473) : on la place en tête.
        queue = "\n".join(sortie.splitlines()[-_LIGNES_DE_QUEUE:])
        result.failure_details = detail_avec_erreur(sortie, queue)
    return result


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
    total, failed = extract_counts(output)
    summary = extract_summary_line(output) or (
        f"{'OK' if passed else 'FAILED'} (exit {returncode})"
    )
    errors = extract_errors(output) if not passed else []
    failure_details = extract_failure_details(output) if not passed else ""
    return TestResult(
        passed=passed,
        total=total,
        failed=failed,
        output_summary=summary,
        errors=errors,
        failure_details=failure_details,
        duration_ms=duration_ms,
    )
