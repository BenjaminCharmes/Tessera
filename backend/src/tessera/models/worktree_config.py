"""What a project declares about the worktree its runs execute in — ticket-521.

The `worktree` key of `agents.json` (ADR-056). Nothing consumes it yet: the
policy of a run reads it once, with the rest of `PolitiqueRun`.
"""
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict


class EntreePopulate(BaseModel):
    """One path copied or linked from the checkout into a fresh worktree."""

    model_config = ConfigDict(frozen=True)

    #: Relative to the repository root, without `..`.
    path: str
    mode: Literal["copy", "link"]


class ConfigWorktree(BaseModel):
    """The validated `worktree` declaration of a project."""

    model_config = ConfigDict(frozen=True)

    populate: tuple[EntreePopulate, ...] = ()
    env: Mapping[str, str] = {}
    #: Replaces the project `test_command` inside the worktree.
    test_command: str | None = None
    #: Runs once in the fresh worktree, before the coder (ticket-536): typically
    #: the dependency install the coder needs to read library types.
    setup: str | None = None
