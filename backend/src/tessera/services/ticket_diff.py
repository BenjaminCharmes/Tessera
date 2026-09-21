"""Relire ce qu'un run a produit, sans quitter l'IDE — ticket-069.

Le pipeline relit le diff git réel depuis ADR-018, et `GitWorkspaceService`
sait déjà le produire — mais rien ne l'exposait. Pour juger un run, il fallait
donc ouvrir VSCode et taper `git diff`, ce qui vide le cockpit d'une bonne part
de son intérêt : on y pilote la flotte sans pouvoir regarder ce qu'elle a fait.

`current_diff()` ne convient pas ici : elle compare l'arbre de travail à `HEAD`,
or un run se termine toujours par un commit et laisse l'arbre propre. Ce qu'on
veut relire, c'est **la branche du ticket contre sa base**.
"""
import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Ce que l'orchestrateur réécrit lui-même — statut des tickets, journal de
#: pipeline. Ce n'est pas le travail du codeur, et le montrer noierait le diff
#: réel sous de la tenue de livres.
_ARTEFACTS = (":(exclude)tickets/", ":(exclude)memory/", ":(exclude)agents.json")


class TicketDiff(BaseModel):
    """Le diff d'un ticket, et de quoi l'afficher sans le relire."""

    ticket_id: str
    branch: str | None = None
    diff: str = ""
    files: list[str] = Field(default_factory=list)


async def _git(project_path: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", errors="replace")


async def _branche_du_ticket(project_path: Path, ticket_id: str) -> str | None:
    code, sortie = await _git(
        project_path, "branch", "--list", f"{ticket_id}-*", "--format=%(refname:short)"
    )
    if code != 0:
        return None
    branches = [ligne.strip() for ligne in sortie.splitlines() if ligne.strip()]
    return branches[0] if branches else None


async def diff_du_ticket(project_path: Path, ticket_id: str) -> TicketDiff:
    """Le diff de la branche du ticket contre le point où elle a divergé.

    `base...branche` — trois points — compare à l'ancêtre commun, pas à la
    pointe de la base : sans cela, tout ce qui a avancé sur la base depuis la
    création de la branche apparaîtrait comme retiré par le ticket.
    """
    branche = await _branche_du_ticket(project_path, ticket_id)
    if branche is None:
        return TicketDiff(ticket_id=ticket_id)

    code, base = await _git(project_path, "symbolic-ref", "--short", "HEAD")
    reference = base.strip() if code == 0 and base.strip() != branche else "main"

    code, diff = await _git(
        project_path, "diff", f"{reference}...{branche}", "--", ".", *_ARTEFACTS
    )
    if code != 0:
        _logger.warning("diff_indisponible", extra={"ticket": ticket_id})
        return TicketDiff(ticket_id=ticket_id, branch=branche)

    code, noms = await _git(
        project_path, "diff", "--name-only", f"{reference}...{branche}",
        "--", ".", *_ARTEFACTS,
    )
    fichiers = [n.strip() for n in noms.splitlines() if n.strip()] if code == 0 else []

    return TicketDiff(
        ticket_id=ticket_id, branch=branche, diff=diff.strip(), files=fichiers
    )
