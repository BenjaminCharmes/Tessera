"""Arrêt avant le codeur sur un critère impossible — ticket-476.

Un critère qui exige d'écrire un fichier que le garde-fou refuse aux agents ne
peut pas être satisfait par un run : le codeur le tente, se fait refuser, et
chaque tour suivant le redemande. Le run s'arrête donc avant le premier tour,
en `blocked` avec son commit comme tout run non approuvé (ADR-018, ADR-037).
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.critere_protege import criteres_sur_chemins_proteges
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline_outcomes import commit_ou_bloquer
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline_text import _extract_criteria, _unapproved_commit_message
from tessera.services.providers.perimetre import racine_autorisee

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator


def raison_critere_protege(orch: "Orchestrator", run: PipelineRun) -> str | None:
    """Why the ticket cannot run, or None when no criterion asks for a protected write."""
    projet = orch._project_path
    if projet is None:
        return None
    retenus = criteres_sur_chemins_proteges(
        _extract_criteria(run.ticket.body), projet, racine_autorisee(projet)
    )
    if not retenus:
        return None
    return " ; ".join(
        f"le critère {numero} demande d'écrire {chemin}, que le pipeline refuse "
        "aux agents : à faire à la main"
        for numero, chemin in retenus
    )


async def arret_critere_protege(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run before the coder when a criterion needs a protected file."""
    raison = raison_critere_protege(orch, run)
    if raison is None:
        return None
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="protected_criterion", detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, raison)
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="protected_criterion",
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
