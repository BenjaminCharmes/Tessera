"""The rights of the agent account on a run worktree — ticket-895.

ADR-083. The CLI runs under `AGENT_USER`; the worktree belongs to the backend's
account. Three rules, set with `icacls`, never `F` (it includes deleting children):
modify on the worktree, read-only `.git`, write and delete refused on each
existing file that `motif_de_protection` designates (policy files, test script).
Without `AGENT_USER`, nothing is set.
"""
import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.providers.chemins_proteges import motif_de_protection
from tessera.services.providers.script_verification import script_de_verification
from tessera.services.worktrees.run_worktree import RunWorktree
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Runs `icacls` with these arguments; returns (exit code, output).
Icacls = Callable[[list[str]], Awaitable[tuple[int, str]]]

# Dossiers volumineux sans fichier de politique : on ne les parcourt pas.
_SANS_POLITIQUE = {".git", "node_modules", ".venv"}


class DroitsAgentRefuses(GitWorkspaceError):
    """`icacls` failed: the worktree is not safe to hand to the agent account (ADR-037)."""


async def _icacls_reel(args: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "icacls", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    sortie, _ = await proc.communicate()
    return proc.returncode or 0, sortie.decode(errors="replace")


async def _lancer(lanceur: Icacls, args: list[str]) -> None:
    code, sortie = await lanceur(args)
    if code != 0:
        raise DroitsAgentRefuses(f"icacls a échoué (code {code}) sur {args[0]} : {sortie.strip()}")


def fichiers_proteges(wt: RunWorktree, script: Path | None) -> list[Path]:
    """Existing files of the worktree that `motif_de_protection` designates."""
    trouves: list[Path] = []
    for dossier, sous_dossiers, fichiers in os.walk(wt.racine):
        sous_dossiers[:] = [d for d in sous_dossiers if d not in _SANS_POLITIQUE]
        for nom in fichiers:
            chemin = Path(dossier) / nom
            if motif_de_protection(str(chemin), wt.projet, wt.racine, script) is not None:
                trouves.append(chemin)
    return trouves


async def poser_ecriture(racine: Path, compte: str, lanceur: Icacls = _icacls_reel) -> None:
    """Give `compte` modify on `racine` and read-only on its `.git` (before each call)."""
    await _lancer(lanceur, [str(racine), "/grant", f"{compte}:(OI)(CI)M"])
    git = racine / ".git"
    if git.exists():
        droit = "(OI)(CI)RX" if git.is_dir() else "RX"
        await _lancer(lanceur, [str(git), "/inheritance:d"])
        await _lancer(lanceur, [str(git), "/remove:g", compte])
        await _lancer(lanceur, [str(git), "/grant:r", f"{compte}:{droit}"])


async def retirer_ecriture(racine: Path, compte: str, lanceur: Icacls = _icacls_reel) -> None:
    """Withdraw every grant of `compte` on `racine` and its `.git` (ticket-943).

    Les refus posés fichier par fichier restent : ils ne donnent rien au compte.
    """
    git = racine / ".git"
    if git.exists():
        await _lancer(lanceur, [str(git), "/remove:g", compte])
    await _lancer(lanceur, [str(racine), "/remove:g", compte])


async def accorder_droits_agent(
    wt: RunWorktree,
    commande_de_tests: str | None,
    lanceur: Icacls = _icacls_reel,
) -> None:
    """Set the three rules on `wt` when `AGENT_USER` is set; otherwise do nothing."""
    compte = settings.agent_user
    if not compte:
        return
    await poser_ecriture(wt.racine, compte, lanceur)
    script = script_de_verification(wt.projet, commande_de_tests)
    for fichier in fichiers_proteges(wt, script):
        await _lancer(lanceur, [str(fichier), "/deny", f"{compte}:(W,D)"])
    _logger.info("droits_agent_poses", extra={"racine": str(wt.racine)})
