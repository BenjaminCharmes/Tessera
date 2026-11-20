"""Align a ticket file on the text of another copy — ticket-987."""
import frontmatter

from tessera.models.ticket import Ticket
from tessera.services.projets.ticket_service import TicketService

#: Ce que le pipeline tient sur la fiche : la copie de la base ne l'écrase pas.
_CONSERVES = {"status", "pr_number", "github_issue_url"}


def aligner_sur_contenu(service: TicketService, ticket_id: str, contenu: str) -> Ticket | None:
    """Rewrite the ticket file with the text of ``contenu``, keeping what the pipeline holds.

    The status, the PR number and the issue URL of the file on disk stay;
    every other key and the body come from ``contenu``. Extra copies in other
    status folders are deleted, so one file remains. None when the ticket has
    no file.
    """
    sources = service._find_all_files(ticket_id)
    if not sources:
        return None
    cible = sources[0]
    garde = frontmatter.load(str(cible))
    base = frontmatter.loads(contenu)
    meta = {k: v for k, v in base.metadata.items() if k not in _CONSERVES}
    meta.update({k: v for k, v in garde.metadata.items() if k in _CONSERVES})
    garde.metadata = meta
    garde.content = base.content
    cible.write_text(frontmatter.dumps(garde), encoding="utf-8")
    for copie in sources[1:]:
        copie.unlink()
    return service._parse(cible)
