"""Reading the run's diff for the review gates — ticket-1005 (split from `pipeline_production`)."""
from tessera.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from tessera.services.git_workspace.liens import LienNonDeclare
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def lire_le_diff(workspace: GitWorkspaceService) -> str:
    """The diff since the branch base; empty when unreadable (fails closed).

    Un lien non déclaré n'est pas un diff illisible comme les autres : l'erreur
    remonte, le run s'arrête et nomme le lien (`pipeline_lien_refuse`).
    """
    try:
        return await workspace.diff_depuis_base()
    except LienNonDeclare:
        raise
    except GitWorkspaceError as exc:
        _logger.warning("diff_failed", extra={"error": str(exc)})
        return ""  # échoue fermé : un diff inconnu vaut un diff vide
