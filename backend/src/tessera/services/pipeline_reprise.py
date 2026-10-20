"""Reprise d'un ticket sur une branche déjà travaillée — ticket-497.

Une branche reprise (interruption, quota épuisé, redémarrage) porte parfois un
travail fini. Rejouer un tour de codeur pour le redécouvrir est l'étape la plus
chère du pipeline : on lance donc les tests d'abord, et un travail vert va
droit à l'audit.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.pipeline_events import EventType
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline_stages import (
    _capture_artifact_diff,
    _capture_diff,
    run_tests,
)
from tessera.services.pipeline_text import _echec_de_tests
from tessera.services.refus_precedent import Refus, refus_precedent, retour_apres_refus

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_TESTS_SANS_RESULTAT = (
    "La branche reprise porte déjà du travail, mais ses tests n'ont pas pu aller "
    "au bout (délai dépassé, commande introuvable ou panne du lanceur). Rien ne "
    "prouve que ce travail tient : relis-le et vérifie-le avant d'y ajouter quoi "
    "que ce soit."
)


def _commits_repris(orch: "Orchestrator") -> int:
    """Commits portés par la branche reprise ; 0 si le workspace ne le dit pas."""
    valeur = getattr(orch._git_workspace, "commits_repris", 0)
    return valeur if isinstance(valeur, int) else 0


def _retour_sans_resultat(run: PipelineRun) -> str:
    """The feedback for tests that did not finish, with the step durations if known.

    Un délai dépassé laisse sa liste d'étapes dans ``run.test_context`` ; sans la
    reprendre ici, elle serait effacée avant que le codeur ne la lise
    (ticket-514).
    """
    detail = run.test_context.strip()
    return f"{_TESTS_SANS_RESULTAT}\n\n{detail}" if detail else _TESTS_SANS_RESULTAT


async def _reprendre_apres_refus(
    orch: "Orchestrator", run: PipelineRun, commits: int, refus: Refus
) -> None:
    """Le run d'avant a été refusé : le codeur passe en premier, tests non lancés.

    Des tests verts ne disent rien d'un refus d'audit ou de revue ; le tour de
    codeur lance les siens, et le motif du refus part dans ses retours.
    """
    await emit(
        run,
        EventType.RUN_RESUMED_FROM_EXISTING_WORK,
        commits=commits,
        verdict="refused",
        refus=refus.porte,
    )
    orch._log(
        f"[{run.ticket_id}] branche reprise ({commits} commit(s)) — "
        f"refus précédent : {refus.porte}, codeur en premier"
    )
    run.review_feedback.append(retour_apres_refus(refus))


async def verifier_travail_repris(orch: "Orchestrator", run: PipelineRun) -> bool:
    """Lance les tests sur une branche reprise ; ``True`` si le codeur peut être sauté.

    Ne fait rien — et rend ``False`` — sur une branche neuve ou sur un projet
    sans testeur : sans tests, rien ne prouve que le travail repris tient. Après
    le refus d'une porte au run précédent, rend ``False`` sans lancer les tests
    (ticket-528). Sur des tests rouges, ou qui n'ont pas abouti, le résultat part dans les retours
    que lit le codeur, et le déroulé habituel reprend.
    """
    commits = _commits_repris(orch)
    if commits <= 0 or not (orch._test_runner and orch._project_path):
        return False

    refus = refus_precedent(getattr(orch, "_log_path", None), run.ticket_id)
    if refus is not None:
        await _reprendre_apres_refus(orch, run, commits, refus)
        return False

    vert = await run_tests(orch, run, reprise=True) is True
    verdict = "green" if vert else "red"
    await emit(
        run, EventType.RUN_RESUMED_FROM_EXISTING_WORK, commits=commits, verdict=verdict
    )
    suite = "codeur sauté" if vert else "codeur en premier"
    orch._log(
        f"[{run.ticket_id}] branche reprise ({commits} commit(s)) — "
        f"tests {verdict}, {suite}"
    )
    if not vert:
        run.review_feedback.append(
            _echec_de_tests(run) if run.test_result is not None else _retour_sans_resultat(run)
        )
        # Ce résultat date d'avant le codeur : le tour qui suit lance ses propres
        # tests, et un résultat périmé ne doit pas survivre à leur absence.
        run.test_result = None
        run.test_context = ""
    return vert


async def reprendre_sans_codeur(orch: "Orchestrator", run: PipelineRun) -> None:
    """Pose ce que pose la fin d'un tour de codeur, sans en lancer un.

    ``run.test_result`` et ``run.test_context`` viennent du contrôle qui
    précède : le reviewer et le validateur les lisent comme après un tour normal.
    """
    run.reviewed_code = await _capture_diff(orch, run, "")
    _capture_artifact_diff(orch, run)
    await set_status(orch, run, TicketStatus.in_review)
