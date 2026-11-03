"""Arrêt à la fin du tour du codeur sur une règle écrite hors `## Proposées` — ticket-493.

Un run qui modifie `contraintes.md` ailleurs que sous `## Proposées` changerait
la consigne de tous les agents suivants sans relecture humaine. Il s'arrête en
`blocked` avec son commit, comme tout run non approuvé (ADR-018, ADR-037) ; la
raison part dans le journal et dans l'événement d'erreur.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.contraintes_touchees import lignes_hors_proposees
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
    """Block the run after the coder's turn when it wrote a rule outside the proposals."""
    raison = raison_contraintes_hors_proposees(orch, run)
    if raison is None:
        return None
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="constraints_outside_proposed", detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch,
        run,
        _unapproved_commit_message(
            run.ticket_id, "contraintes.md changed outside the Proposées section"
        ),
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="constraints_outside_proposed",
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
