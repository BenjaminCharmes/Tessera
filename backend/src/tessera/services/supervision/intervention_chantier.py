"""Le chantier git d'une intervention : worktree, commits, livraison — ticket-854, ADR-080.

Une intervention s'écrit toujours dans son propre worktree (ADR-056), que le
projet déclare `worktree` ou non : le checkout, où une session humaine ou un run
peut travailler, n'est jamais touché. Le chantier ne décide de rien ; il ouvre,
liste, commite, livre et referme.
"""
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from tessera.config import settings
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from tessera.services.github.github_service import GitHubService
from tessera.services.github.github_workflow import GitHubWorkflowService
from tessera.services.livraison.livraison import LivraisonService
from tessera.services.livraison.livraison_intervention import ControleDuDiff
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.pipeline.run_dans_worktree import base_du_projet
from tessera.services.projets.project_loader import load_project
from tessera.services.worktrees.run_worktree import LienPersistant, RunWorktree, TravailNonSauve, creer, supprimer
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class Chantier(Protocol):
    """What an intervention needs of git: a place to write, its commits, its delivery."""

    async def ouvrir(self, branche: str) -> Path: ...
    async def fichiers_modifies(self) -> list[str]: ...
    async def commiter(self, message: str, chemins: list[str]) -> str | None: ...
    async def livrer(self, branche: str, sha: str, controle: ControleDuDiff, titre: str) -> Livraison: ...
    async def fermer(self) -> None: ...


NouveauChantier = Callable[[str], Chantier]


class ChantierGit:
    """The real chantier: a worktree of the project on `supervision-<horodatage>`."""

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._depot = settings.ide_workspace_dir / project_id
        self._politique = PolitiqueRun.lire(self._depot)
        self._base = base_du_projet(self._politique)
        self._wt: RunWorktree | None = None
        self._git: GitWorkspaceService | None = None

    async def ouvrir(self, branche: str) -> Path:
        """Create the worktree on `branche`, forked from `origin/<base>`; the project folder in it."""
        wt = await creer(self._depot, self._depot, self._project_id, branche, branche, self._base)
        self._wt = wt
        self._git = GitWorkspaceService(wt.projet, politique=self._politique, worktree=wt)
        await self._git.adopter_worktree(branche, self._base)
        return wt.projet

    def _espace(self) -> GitWorkspaceService:
        if self._git is None:
            raise GitWorkspaceError("Le chantier n'est pas ouvert.")
        return self._git

    async def fichiers_modifies(self) -> list[str]:
        """Paths the worktree changes against HEAD, relative to the project folder."""
        return await self._espace().fichiers_modifies()

    async def commiter(self, message: str, chemins: list[str]) -> str | None:
        """Commit exactly `chemins`; the full SHA of the commit, None when nothing was committed."""
        espace = self._espace()
        if not await espace.commit_chemins(message, chemins):
            return None
        return await espace.head_sha()

    async def livrer(self, branche: str, sha: str, controle: ControleDuDiff, titre: str) -> Livraison:
        """Rebase, push and open the PR, never merge it (`livrer_intervention`)."""
        wt = self._wt
        if wt is None:
            raise GitWorkspaceError("Le chantier n'est pas ouvert.")
        project = load_project(self._depot)
        github = None
        if project.github_remote and settings.github_token:
            github = GitHubService(token=settings.github_token, repo=project.github_remote)
        espace = self._espace()
        workflow = GitHubWorkflowService(
            git_workspace=espace, github=github, base_branch=self._base,
            project_path=wt.projet, politique=self._politique,
        )
        service = LivraisonService(
            git_workspace=espace, workflow=workflow, project_path=wt.projet,
            base_branch=self._base, politique=self._politique,
        )
        return await service.livrer_intervention(branche, sha, controle=controle, titre=titre)

    async def fermer(self) -> None:
        """Remove the worktree; one that holds unsaved work, or fails to go, stays and is logged."""
        if self._wt is None:
            return
        try:
            await supprimer(self._wt, self._depot)
        except (TravailNonSauve, LienPersistant, GitWorkspaceError, OSError) as exc:
            _logger.warning("intervention_worktree_conserve", extra={"racine": str(self._wt.racine), "erreur": str(exc)})
