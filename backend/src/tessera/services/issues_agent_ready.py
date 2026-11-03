"""Pulls the `agent-ready` issues of a project's repository into tickets — ticket-084."""
from tessera.agents.github_sync import GithubSyncAgent
from tessera.config import settings
from tessera.services.github_service import GitHubService
from tessera.services.project_loader import load_project
from tessera.services.sync_map import SyncMapService
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def tirer_les_issues(project_id: str) -> int:
    """Crée les tickets manquants depuis les issues `agent-ready` du dépôt.

    Le dernier maillon de la boucle : une issue écrite sur GitHub devient un
    ticket, que le run autonome prend ensuite comme les autres. Le pull
    existait déjà — il n'était qu'un bouton à part (ticket-084).

    Un échec n'empêche pas le run : les tickets déjà là méritent de tourner.
    """
    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    if not project.github_remote or not settings.github_token:
        return 0
    agent = GithubSyncAgent(
        github_svc=GitHubService(
            token=settings.github_token, repo=project.github_remote
        ),
        ticket_svc=TicketService(project_path, project_id),
        sync_map_svc=SyncMapService(),
        project_path=project_path,
    )
    try:
        resultat = await agent.run("pull")
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        _logger.warning("pull_des_issues_echoue", extra={"erreur": str(exc)})
        return 0
    return int(resultat.pulled)
