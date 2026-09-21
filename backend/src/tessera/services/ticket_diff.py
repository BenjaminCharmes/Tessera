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
    #: Le commit retrouvé quand la branche n'existe plus (ticket-116).
    #: Supprimer la branche après le merge est la pratique normale ; sans ce
    #: repli, le diff disparaissait pour tout ticket proprement terminé.
    commit: str | None = None
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
        return await _diff_par_commit(project_path, ticket_id)

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


async def _diff_par_commit(project_path: Path, ticket_id: str) -> TicketDiff:
    """Le diff retrouvé par le message de commit, faute de branche.

    Supprimer la branche après le merge est la pratique normale — c'est ce que
    fait `gh pr merge --delete-branch`. Chercher uniquement `git branch --list`
    faisait donc disparaître le diff de **tout ticket proprement terminé**, et
    l'écran annonçait « jamais lancé », ce qui était faux (ticket-116).

    Les messages portent tous l'identifiant du ticket — `CLAUDE.md` l'impose et
    le pipeline l'applique — y compris après un squash.

    Plusieurs commits peuvent le mentionner : celui du travail, puis celui de
    clôture. Le second ne touche que `tickets/`, que `_ARTEFACTS` exclut déjà,
    donc son diff est **vide** une fois filtré. On descend du plus récent au
    plus ancien et on rend le premier diff non vide.
    """
    code, sortie = await _git(
        project_path, "log", "--all", f"--grep={ticket_id}", "--format=%H", "-n", "20"
    )
    if code != 0:
        return TicketDiff(ticket_id=ticket_id)

    for sha in (l.strip() for l in sortie.splitlines() if l.strip()):
        code, diff = await _git(
            project_path, "show", sha, "--format=", "--", ".", *_ARTEFACTS
        )
        if code != 0 or not diff.strip():
            continue

        code, noms = await _git(
            project_path, "show", sha, "--format=", "--name-only", "--", ".", *_ARTEFACTS
        )
        fichiers = [n.strip() for n in noms.splitlines() if n.strip()] if code == 0 else []
        return TicketDiff(
            ticket_id=ticket_id, commit=sha[:12], diff=diff.strip(), files=fichiers
        )

    return TicketDiff(ticket_id=ticket_id)
