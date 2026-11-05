"""Arrêt à la fin du tour du codeur sur une règle écrite hors `## Proposées` — ticket-493.

Un run qui modifie `contraintes.md` ailleurs que sous `## Proposées` changerait
la consigne de tous les agents suivants sans relecture humaine. Il s'arrête en
`blocked` avec son commit, comme tout run non approuvé (ADR-018, ADR-037) ; la
raison part dans le journal et dans l'événement d'erreur.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.gardes.contraintes_touchees import lignes_hors_proposees
from tessera.services.gardes.lecons_touchees import lignes_de_lecons
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline_outcomes import commit_ou_bloquer
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline_text import _unapproved_commit_message

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator


def raison_contraintes_hors_proposees(orch: "Orchestrator", run: PipelineRun) -> str | None:
    """Why the run must stop, or None when contraintes.md is untouched or only proposed to."""
    chemin = orch._project_path
    if chemin is None:
        return None
    racines = [chemin.resolve(), *chemin.resolve().parents]
    hors = lignes_hors_proposees(run.reviewed_code, racines)
    if not hors:
        return None
    return (
        "contraintes.md modifié hors de « ## Proposées » — une règle nouvelle "
        "s'y écrit, avec son ADR, et un humain la déplace : " + " ; ".join(hors)
    )


async def arret_contraintes_hors_proposees(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run after the coder's turn when it wrote a rule outside the proposals.

    Le même point d'arrêt garde `memory/lecons.md` (ticket-804) : le contrôle
    des leçons passe juste après, sur le même diff.
    """
    raison = raison_contraintes_hors_proposees(orch, run)
    if raison is None:
        return await arret_lecons_modifiees(orch, run)
    return await _bloquer(
        orch, run, "constraints_outside_proposed", raison,
        "contraintes.md changed outside the Proposées section",
    )


def raison_lecons_modifiees(run: PipelineRun) -> str | None:
    """Why the run must stop, or None when the diff leaves lecons.md alone."""
    touchees = lignes_de_lecons(run.reviewed_code)
    if not touchees:
        return None
    return (
        "lecons.md modifié par un agent — seul le service écrit ce fichier ; "
        "un humain déplace une leçon sous « ## En vigueur » : " + " ; ".join(touchees)
    )


async def arret_lecons_modifiees(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run after the coder's turn when its diff touches lecons.md.

    La leçon que le service propose s'écrit **après** ce contrôle, à
    l'approbation (ticket-803) : elle n'est jamais dans le diff relu ici.
    """
    raison = raison_lecons_modifiees(run)
    if raison is None:
        return None
    return await _bloquer(
        orch, run, "lessons_file_modified", raison, "lecons.md changed by an agent"
    )


async def _bloquer(
    orch: "Orchestrator", run: PipelineRun, code: str, raison: str, resume: str
) -> PipelineResult:
    """End the run `blocked`, with its unapproved commit, naming `raison`."""
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason=code, detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, resume)
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason=code,
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret or raison,
    )
