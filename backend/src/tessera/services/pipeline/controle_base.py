"""Les tickets d'une file qui n'existent pas là d'où part le run — ticket-849.

Un projet à worktree (ADR-056) ouvre chaque run depuis `origin/<base>` : un
ticket qui n'est que dans l'arbre de travail y est introuvable, et la file
s'interrompait au milieu. Le contrôle se fait avant d'ouvrir, sous aucun verrou.

Il n'est pas une porte : git illisible (pas de remote, fetch en échec), il ne
juge pas et laisse la file s'ouvrir comme avant (ADR-037 ne s'applique qu'aux
portes ; celle-ci n'en était pas une).
"""
import asyncio
import re
from pathlib import Path

from tessera.config import settings
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.noyau.numerotation import GitIllisible, lire_git, noms_de_tickets_sur_la_base
from tessera.services.projets.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def base_du_projet(politique: PolitiqueRun) -> str:
    """The base branch a run starts from: the declared one, else the global default."""
    return politique.base_branch or settings.github_base_branch


def _present(ticket_id: str, noms: set[str]) -> bool:
    """Whether a file named `<ticket_id>[-slug].md` is in `noms`.

    Motif strict : `ticket-84` ne doit pas retrouver `ticket-849-....md`.
    """
    motif = re.compile(rf"^{re.escape(ticket_id)}(?:-[\w-]+)?\.md$")
    return any(motif.match(nom) for nom in noms)


def _absents_sur_la_base(
    project_path: Path, base: str, ticket_ids: list[str]
) -> list[str] | None:
    """Ids missing from `origin/<base>` after a fetch; None when git cannot tell."""
    try:
        lire_git(project_path, "fetch", "--no-write-fetch-head", "origin", base)
        noms = noms_de_tickets_sur_la_base(project_path, base)
    except GitIllisible as exc:
        _logger.info("controle_base_ignore", extra={"base": base, "erreur": str(exc)})
        return None
    return [tid for tid in ticket_ids if not _present(tid, noms)]


def _sans_doublon(ticket_ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ticket_ids))


async def absents_de_la_base(project_path: Path, ticket_ids: list[str]) -> list[str]:
    """The ids absent from `origin/<base>` for a worktree project; [] for any other.

    Un projet sans worktree travaille dans son arbre : la base n'est pas son
    point de départ, rien à contrôler ici.
    """
    politique = PolitiqueRun.lire(project_path)
    if politique.worktree is None or not ticket_ids:
        return []
    absents = await asyncio.to_thread(
        _absents_sur_la_base, project_path, base_du_projet(politique), _sans_doublon(ticket_ids)
    )
    return absents or []


async def refuser_absents_de_la_base(
    project_path: Path, acceptes: list[str], refuses: dict[str, str]
) -> None:
    """Move the accepted ids absent from the base of a worktree project to `refuses`.

    Un ajout à une file vivante suit la règle de l'ouverture (ticket-849) : un
    ticket que le worktree ne trouvera pas n'entre pas dans la file.
    """
    for ticket_id in await absents_de_la_base(project_path, acceptes):
        acceptes.remove(ticket_id)
        refuses[ticket_id] = "absent de la base : le pousser avant de l'ajouter"


def message_de_refus_base(absents: list[str], base: str) -> str:
    """The 422 detail for tickets missing from the base: which, and what to do."""
    return (
        f"Ticket(s) absent(s) de la base `origin/{base}` : {', '.join(absents)}. "
        f"Les pousser sur `{base}` avant de lancer la file."
    )


async def refus_avant_ouverture(
    project_path: Path, ticket_svc: TicketService, ticket_ids: list[str]
) -> str | None:
    """The 422 detail when a queue cannot start from these tickets, else None.

    Projet à worktree : chaque ticket doit être sur `origin/<base>`. Sinon, le
    run travaille dans l'arbre du projet : chaque ticket doit y être.
    """
    ids = _sans_doublon(ticket_ids)
    politique = PolitiqueRun.lire(project_path)
    if politique.worktree is not None:
        absents = await absents_de_la_base(project_path, ids)
        return message_de_refus_base(absents, base_du_projet(politique)) if absents else None
    absents = [tid for tid in ids if await ticket_svc.get_ticket(tid) is None]
    if not absents:
        return None
    return f"Ticket(s) introuvable(s) dans le projet : {', '.join(absents)}."
