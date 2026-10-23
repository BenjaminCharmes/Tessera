"""Exceptions raised by the git workspace service."""

class GitWorkspaceError(Exception):
    """Base class for all errors raised by GitWorkspaceService."""


class GitCommandError(GitWorkspaceError):
    """A git command failed; carries the context for logging."""

    def __init__(self, command: list[str], returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"git command failed (code {returncode}): {' '.join(command)}\n{stderr}"
        )


class BaseIntrouvable(GitWorkspaceError):
    """La branche de base du rejeu n'existe pas dans ce dépôt — ticket-166.

    `git rebase` répond `fatal: invalid upstream 'develop'`, qui ne dit ni que
    la branche vient d'un réglage, ni lequel, ni où le corriger.
    """

    def __init__(self, base: str) -> None:
        super().__init__(
            f"La branche de base « {base} » n'existe pas dans ce dépôt. "
            f"Déclare `base_branch` dans son agents.json, ou crée la branche."
        )
        self.base = base


class NotAGitRepository(GitCommandError):
    """The target directory is not (or no longer) a git repository."""


class InvalidSlugError(GitWorkspaceError):
    """Raised when a slug sanitizes to an empty string and cannot form a branch name."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(
            f"slug sanitizes to an empty string, cannot build a branch name: {slug!r}"
        )
