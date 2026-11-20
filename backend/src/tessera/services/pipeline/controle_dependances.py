"""Les dépendances d'un ticket lancé seul — ticket-958.

La file refuse un ticket dont une dépendance n'est ni dans la file ni `done`
(`file_vivante`). Le mode `single` n'avait aucun contrôle : un ticket partait
sur une base qui n'avait pas encore le travail dont il dépend. Même lecture que
la file : l'arbre du projet, puis `origin/<base>` en repli.
"""
from pathlib import Path

from tessera.models.ticket import TicketStatus
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline.file_vivante import _lire, lecteur_sur_la_base
from tessera.services.projets.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def dependance_non_terminee(
    project_path: Path, project_id: str, ticket_svc: TicketService, ticket_id: str,
    force: bool = False,
) -> str | None:
    """The refusal message for the first unfinished dependency, None when all are done.

    Avec `force`, le message se journalise et rien ne refuse (ticket-477).

    Le ticket lui-même introuvable ne se juge pas ici : le run le dira. Le
    repli sur la base (un `fetch`) ne part que si une dépendance manque dans
    l'arbre.
    """
    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None or not ticket.depends_on:
        return None
    repli = lecteur_sur_la_base(
        GitWorkspaceService(project_path, politique=PolitiqueRun.lire(project_path)),
        project_id,
    )
    for dep in ticket.depends_on:
        trouve = await _lire(ticket_svc, repli, dep)
        statut = trouve.status.value if trouve is not None else "introuvable"
        if trouve is None or trouve.status != TicketStatus.done:
            message = f"dépendance {dep} non terminée (statut : {statut})"
            if force:
                _logger.warning("dependance_forcee", extra={"project_id": project_id, "detail": message})
                return None
            return message
    return None
