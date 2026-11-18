"""End of a run whose tree holds a link git would follow — ticket-1005 (ADR-037, ticket-996)."""
import asyncio
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.git_workspace.liens import LienNonDeclare, retirer_ces_liens
from tessera.services.noyau.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline.pipeline_outcomes import commit_ou_bloquer, finish_interrupted
from tessera.services.pipeline.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline.pipeline_text import _unapproved_commit_message
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def _retirer_les_liens_refuses(orch: "Orchestrator", exc: LienNonDeclare) -> list[str]:
    """Unlink the refused links, never their targets; return those that stay."""
    workspace = orch._git_workspace
    if workspace is None:
        return list(exc.liens)
    try:
        racine = await workspace.racine_de_l_arbre()
        restants = await asyncio.to_thread(retirer_ces_liens, racine, exc.liens)
    except OSError as erreur:
        _logger.warning("liens_refuses_non_retires", extra={"error": str(erreur)})
        return list(exc.liens)
    return [str(chemin) for chemin in restants]


async def finish_lien_refuse(
    orch: "Orchestrator", run: PipelineRun, exc: LienNonDeclare
) -> PipelineResult:
    """Block the run at once, naming the link(s); commit the work without them.

    Aucun autre appel d'agent : un diff illisible à cause d'un lien ne se lit
    pas sur la prose du codeur. Un lien qui ne se retire pas laisse le commit
    échouer (nommé dans `arret`) et le worktree en place.
    """
    liens = ", ".join(exc.liens)
    raison = f"lien non déclaré dans l'arbre : {liens}"
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="lien_non_declare", detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    restants = await _retirer_les_liens_refuses(orch, exc)
    commit_sha, echec = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, "lien non déclaré")
    )
    if restants:
        raison += f" (non retiré : {', '.join(restants)})"
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="lien_non_declare",
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=f"{raison} ; {echec}" if echec else raison,
    )


async def finish_apres_panne(
    orch: "Orchestrator", run: PipelineRun, cause: Exception
) -> PipelineResult:
    """End a run an exception interrupted: a refused link has its own exit, the rest is `interrupted`."""
    if isinstance(cause, LienNonDeclare):
        return await finish_lien_refuse(orch, run, cause)
    return await finish_interrupted(orch, run, cause)
