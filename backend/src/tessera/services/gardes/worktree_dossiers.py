"""The shape of a run worktree as the write perimeter and ADR-024 see it (ticket-525).

Un Protocol plutôt qu'un import : ces services ne dépendent pas du module qui
crée les worktrees, seulement de deux dossiers. Le branchement dans le run est
le ticket-519.
"""
from pathlib import Path
from typing import Protocol


class DossiersWorktree(Protocol):
    """Where a worktree lives: its root, and the project folder inside it."""

    @property
    def racine(self) -> Path: ...

    @property
    def projet(self) -> Path: ...
