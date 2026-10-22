"""The setup command of a run worktree, before the coder starts — ticket-536.

A fresh worktree has no `node_modules`: `populate` links none on purpose (a
junction emptied one on 14/10), and only the tester installed them. The coder
could not read library types and invented an API. A project now declares
`worktree.setup`; it runs once in the worktree, with `worktree.env`, under the
tester's timeout. A failure ends the run `blocked` before any agent is called
(ADR-037).
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.services.commande_effective import setup_effectif
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.politique_run import PolitiqueRun
from tessera.services.test_runner import TestResult, TestRunnerService
from tessera.models.ticket import TicketStatus
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


@dataclass
class ResultatPreparation:
    """How the setup ended: what ran, for how long, and why it failed if it did."""

    commande: str
    duree_ms: int
    #: Code de sortie de la dernière étape ; `None` si rien n'a démarré ou si le délai a coupé.
    code: int | None
    #: La raison de l'échec, `None` quand la préparation a réussi.
    arret: str | None


#: Runs the setup and reports how it ended.
Preparation = Callable[[], Awaitable[ResultatPreparation]]


def _raison_de_l_echec(commande: str, resultat: TestResult) -> str:
    """The refusal text: the command, how it ended, and the end of its output."""
    if resultat.expiree:
        cause = f"délai dépassé ({resultat.output_summary})"
    elif not resultat.demarree:
        cause = f"commande non démarrée ({resultat.output_summary})"
    else:
        cause = resultat.output_summary
    texte = f"La préparation du worktree a échoué : `{commande}` — {cause}"
    if resultat.failure_details:
        texte = f"{texte}\n{resultat.failure_details}"
    return texte


def preparation_du_run(
    politique: PolitiqueRun,
    racine: Path | None,
    depot: Path,
    env: dict[str, str] | None,
    timeout: int | None,
    runner: TestRunnerService | None = None,
) -> Preparation | None:
    """The setup of the run, or `None` when the project declares none.

    `racine` is the worktree root, `None` outside a worktree; `env` is the
    already-resolved `worktree.env`. Raises `PlaceholderInconnu`
    when the command names a placeholder that does not exist.
    """
    if racine is None or politique.worktree is None:
        return None
    commande = setup_effectif(politique.worktree, racine, depot)
    if commande is None:
        return None
    lanceur = runner or TestRunnerService(cwd=None, timeout=timeout, env=env)

    async def preparer() -> ResultatPreparation:
        # La racine du worktree, pas le dossier du projet : le gestionnaire de paquets
        # y cherche son fichier de verrou.
        resultat = await lanceur.run_tests(racine, test_command=commande)
        code = resultat.etapes[-1].code if resultat.etapes else None
        if resultat.passed:
            return ResultatPreparation(commande, resultat.duration_ms, code, None)
        _logger.warning("worktree_setup_echoue", extra={"commande": commande})
        arret = _raison_de_l_echec(commande, resultat)
        return ResultatPreparation(commande, resultat.duration_ms, code, arret)

    return preparer


def _ligne_du_journal(ticket_id: str, resultat: ResultatPreparation) -> str:
    """The pipeline-log line: command, outcome, exit code and duration."""
    issue = "échec" if resultat.arret is not None else "ok"
    code = "aucun" if resultat.code is None else str(resultat.code)
    return (
        f"[{ticket_id}] préparation: {issue} — `{resultat.commande}` "
        f"(code {code}, {resultat.duree_ms} ms)"
    )


async def _annoncer(
    orch: "Orchestrator", run: PipelineRun, resultat: ResultatPreparation
) -> None:
    """Emit `worktree_setup` and write the log line, success or failure alike."""
    await emit(
        run, EventType.WORKTREE_SETUP, command=resultat.commande,
        duration_ms=resultat.duree_ms, exit_code=resultat.code,
    )
    orch._log(_ligne_du_journal(run.ticket_id, resultat))


async def preparer_le_worktree(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Run the declared setup; a blocked result when it fails, `None` otherwise."""
    if orch._preparation is None:
        return None
    resultat = await orch._preparation()
    await _annoncer(orch, run, resultat)
    arret = resultat.arret
    if arret is None:
        return None
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason=arret)
    return PipelineResult(
        ticket_id=run.ticket_id, final_status=TicketStatus.blocked,
        rounds=0, approved=False, arret=arret,
    )
