"""Un checkout resté sur la branche d'un autre travail ne part pas — ticket-1048.

Un projet sans worktree travaille dans son arbre. Si cet arbre est sur la
branche d'une autre session, le run bifurquerait de ce travail et lirait un
`agents.json` plus vieux que la base. Le refus se lit avant toute réservation,
en lecture seule ; le réalignement de la base, lui, se fait avant que la
politique soit figée dans l'orchestrateur.
"""
import asyncio
import re
from pathlib import Path

from tessera.services.gardes.base_du_projet import base_du_projet
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from tessera.services.noyau.numerotation import GitIllisible, lire_git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_BRANCHE_DE_TICKET = re.compile(r"^ticket-(\d+)-")


def _branche_courante(project_path: Path) -> str | None:
    """The checked-out branch; None when git cannot tell or HEAD is detached."""
    if not project_path.is_dir():
        return None
    try:
        nom = lire_git(project_path, "branch", "--show-current").strip()
    except GitIllisible:
        return None
    return nom or None


def _ticket_existe(project_path: Path, numero: str) -> bool:
    """Whether a `ticket-<numero>[-slug].md` sits anywhere under `tickets/`."""
    racine = project_path / "tickets"
    if not racine.is_dir():
        return False
    motif = re.compile(rf"^ticket-0*{int(numero)}(?:-.*)?\.md$")
    return any(motif.match(f.name) for f in racine.rglob("ticket-*.md"))


def refus_checkout_etranger(project_path: Path, politique: PolitiqueRun | None = None) -> str | None:
    """The refusal when the checkout is on a foreign branch, None when the run may open.

    Un projet à worktree n'est jamais refusé : son run ne touche pas au
    checkout. Git illisible ou HEAD détaché : ce n'est pas ce contrôle qui juge.
    """
    politique = politique or PolitiqueRun.lire(project_path)
    if politique.worktree is not None:
        return None
    branche = _branche_courante(project_path)
    if branche is None or branche == base_du_projet(politique):
        return None
    correspond = _BRANCHE_DE_TICKET.match(branche)
    if correspond and _ticket_existe(project_path, correspond.group(1)):
        return None
    return (
        f"Le checkout est sur la branche `{branche}`, qui n'est ni la base "
        f"`{base_du_projet(politique)}` ni celle d'un ticket du projet. Revenir sur la base, "
        "ou travailler dans un worktree manuel, avant de lancer."
    )


async def _realigner(project_path: Path, politique: PolitiqueRun) -> None:
    """Put the tree on the base and fast-forward it; a refusal is journaled, never fatal."""
    base = base_du_projet(politique)
    git = GitWorkspaceService(project_path, politique=politique)
    try:
        if await git.branche_courante() != base:
            await git.retourner_sur_base(base)
        raison = await git.sync_base_depuis_distant(base)
    except GitWorkspaceError as exc:
        _logger.warning("realignement_avant_politique_echoue", extra={"error": str(exc)})
        return
    if raison:
        _logger.warning("realignement_avant_politique_refuse", extra={"raison": raison})


async def realigner_avant_construction(project_path: Path) -> PolitiqueRun:
    """Realign the base, then read the policy the run will apply (ticket-1048).

    Un `base_branch` arrivé par la base change la base elle-même : un second
    tour réaligne alors sur la nouvelle.
    """
    politique = await asyncio.to_thread(PolitiqueRun.lire, project_path)
    await _realigner(project_path, politique)
    relue = await asyncio.to_thread(PolitiqueRun.lire, project_path)
    if base_du_projet(relue) != base_du_projet(politique):
        await _realigner(project_path, relue)
        relue = await asyncio.to_thread(PolitiqueRun.lire, project_path)
    return relue
