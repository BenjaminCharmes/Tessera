"""Git Bash path detection for Windows agents — ticket-319.

Claude Code n'active l'outil ``Bash`` sous Windows que si la variable
``CLAUDE_CODE_GIT_BASH_PATH`` pointe vers un ``bash.exe``. Sans elle, l'outil
disparaît en silence — aucune erreur, et le prompt continue de le promettre.

Ce module résout le chemin une fois, en avertit si introuvable, et expose
``agent_shell_ok`` pour signaler l'état dans ``GET /health``.
"""
import platform
import shutil
from collections.abc import Callable
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def resolve_git_bash(
    env_value: str = "",
    which_fn: Callable[[str], str | None] = shutil.which,
) -> str | None:
    """Returns the Git Bash executable path for Windows agents, or ``None``.

    Non-Windows platforms always return ``None`` — the Bash tool is natively
    available there without any extra configuration. Under Windows, priority
    is given to ``env_value`` (i.e. the ``CLAUDE_CODE_GIT_BASH_PATH``
    setting), then to a path deduced from the ``git`` executable located by
    ``which_fn``.

    ``which_fn`` defaults to ``shutil.which`` and can be replaced in tests.
    """
    if platform.system() != "Windows":
        return None
    if env_value:
        return env_value
    git = which_fn("git")
    if git is None:
        return None
    # Standard layout followed by scoop, Git for Windows installer and most
    # package managers: git lives at <root>/cmd/git.exe, bash at
    # <root>/bin/bash.exe.
    bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
    if bash.is_file():
        return str(bash)
    return None


def agent_shell_ok(git_bash_path: str | None) -> bool:
    """True when agents can use the Bash tool on this platform.

    On non-Windows systems the tool is always available.
    On Windows it requires a resolvable Git Bash path.
    """
    if platform.system() != "Windows":
        return True
    return bool(git_bash_path)


def warn_if_shell_missing(git_bash_path: str | None) -> None:
    """Logs a warning on Windows when no usable Git Bash is found."""
    if platform.system() != "Windows":
        return
    if not git_bash_path:
        _logger.warning(
            "git_bash_not_found",
            extra={
                "hint": (
                    "Agents will not have the Bash tool. "
                    "Set CLAUDE_CODE_GIT_BASH_PATH to the bash.exe path, "
                    "or ensure Git is reachable via PATH."
                )
            },
        )
