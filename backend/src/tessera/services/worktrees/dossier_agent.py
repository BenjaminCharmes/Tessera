"""The worktrees folder of projects that run under the agent account — ticket-947.

The CLI of the agent account cannot resolve paths under the user profile, so
these projects get their worktrees under `IDE_WORKTREES_DIR_AGENT`. The folder
is created once, with an explicit ACL and no inheritance: SYSTEM and the
administrators full control, the backend's user modify. The agent account gets
nothing here beyond what `accorder_droits_agent` sets on the worktree of a run.
"""
import asyncio
import getpass
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceError
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Runs `icacls` with these arguments; returns (exit code, output).
Icacls = Callable[[list[str]], Awaitable[tuple[int, str]]]

_SYSTEME = "*S-1-5-18"
_ADMINISTRATEURS = "*S-1-5-32-544"


class DossierAgentRefuse(GitWorkspaceError):
    """The agent worktrees folder could not be created or secured (ADR-037)."""


async def _icacls_reel(args: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "icacls", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    sortie, _ = await proc.communicate()
    return proc.returncode or 0, sortie.decode(errors="replace")


def dossier_des_worktrees(compte_agent: bool) -> Path:
    """The worktrees folder for a project: the agent one only with `AGENT_USER` set."""
    if compte_agent and settings.agent_user:
        return settings.ide_worktrees_dir_agent
    return settings.ide_worktrees_dir


async def preparer_dossier_agent(
    lanceur: Icacls | None = None, utilisateur: str | None = None
) -> Path:
    """Create the agent worktrees folder with its ACL on first use; return it.

    An existing folder is left as it is: its ACL is checked by `agent doctor`.
    """
    lanceur = lanceur or _icacls_reel
    dossier = settings.ide_worktrees_dir_agent
    if dossier.exists():
        return dossier
    dossier.mkdir(parents=True)
    compte = utilisateur or getpass.getuser()
    etapes = [
        [str(dossier), "/inheritance:r"],
        [str(dossier), "/grant:r", f"{_SYSTEME}:(OI)(CI)F", f"{_ADMINISTRATEURS}:(OI)(CI)F",
         f"{compte}:(OI)(CI)M"],
    ]
    for args in etapes:
        code, sortie = await lanceur(args)
        if code != 0:
            raise DossierAgentRefuse(f"icacls a échoué (code {code}) sur {dossier} : {sortie.strip()}")
    _logger.info("dossier_worktrees_agent_cree", extra={"dossier": str(dossier)})
    return dossier
