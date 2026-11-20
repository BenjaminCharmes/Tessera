"""Read `preuve_reelle` of a ticket as the base branch holds it — ticket-964.

Au redémarrage, la fiche du dossier du run a pu être réécrite par le codeur :
seule la fiche de `origin/<base>` dit si la PR attend une preuve réelle.
"""

from pathlib import Path

import frontmatter

from tessera.services.git_workspace import GitCommandError
from tessera.services.git_workspace.textes import _chemin_du_ticket
from tessera.services.worktrees.temporary_worktree import run_git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def preuve_reelle_sur_la_base(
    projet: Path, ticket_id: str, base: str | None
) -> bool | None:
    """True/False from the ticket on `origin/<base>`; None when it cannot be read.

    Lecture seule, sans fetch : la référence distante telle que le dernier
    fetch l'a laissée. None : pas de base déclarée, ticket absent de la base,
    git illisible ou frontmatter invalide.
    """
    if not base:
        return None
    ref = f"refs/remotes/origin/{base}"
    try:
        prefix = (await run_git(projet, "rev-parse", "--show-prefix")).strip()
        liste = await run_git(
            projet, "ls-tree", "--full-tree", "-r", "--name-only", ref, "--", f"{prefix}tickets/"
        )
        chemin = _chemin_du_ticket(liste, ticket_id)
        if chemin is None:
            return None
        texte = await run_git(projet, "show", f"{ref}:{chemin}")
        return bool(frontmatter.loads(texte).metadata.get("preuve_reelle") is True)
    except (GitCommandError, ValueError) as exc:
        _logger.info(
            "preuve_sur_la_base_illisible",
            extra={"ticket_id": ticket_id, "erreur": str(exc)[:200]},
        )
        return None
