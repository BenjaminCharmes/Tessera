"""GitWorkspaceService — ticket-045.

Isolates the git operations the orchestrator needs to drive an agent
pipeline on a dedicated branch: create/resume a branch, read the current
diff (including untracked files) and commit the work.

The service is one class assembled from one mixin per concern (ticket-546);
every module of the package keeps its own subject. The names other modules
import from here are re-exported below.
"""
import asyncio  # noqa: F401  # les tests patchent `tessera.services.git_workspace.asyncio`

from tessera.services.git_workspace.branche import GitBranch
from tessera.services.git_workspace.erreurs import (
    BaseIntrouvable,
    GitCommandError,
    GitWorkspaceError,
    InvalidSlugError,
    NotAGitRepository,
)
from tessera.services.git_workspace.lockfiles import (
    LOCKFILE_NAMES,
    _is_lockfile,
    _resumer_lockfiles,
)
from tessera.services.git_workspace.noms import _branch_name
from tessera.services.git_workspace.socle import _dossier_sans_hooks
from tessera.services.git_workspace.synchro import GitSync
from tessera.services.git_workspace.textes import _union_json_lists, _union_lines
from tessera.services.git_workspace.ticket_sur_base import GitTicketOnBase

__all__ = [
    "LOCKFILE_NAMES",
    "BaseIntrouvable",
    "GitCommandError",
    "GitWorkspaceError",
    "GitWorkspaceService",
    "InvalidSlugError",
    "NotAGitRepository",
    "_branch_name",
    "_dossier_sans_hooks",
    "_is_lockfile",
    "_resumer_lockfiles",
    "_union_json_lists",
    "_union_lines",
]


class GitWorkspaceService(GitTicketOnBase, GitSync, GitBranch):
    """Drives git on a single workspace project, never on Tessera itself."""
