"""The command and environment of a run inside a worktree — ticket-524."""
from pathlib import Path

import pytest

from tessera.models.worktree_config import ConfigWorktree
from tessera.services.commande_effective import (
    PlaceholderInconnu,
    commande_effective,
    environnement_effectif,
)
from tessera.services.politique_run import PolitiqueRun

_WT = Path("/work/wt")
_DEPOT = Path("/work/repo")


def _politique(
    test_command: str | None = "uv run pytest", worktree: ConfigWorktree | None = None
) -> PolitiqueRun:
    return PolitiqueRun(test_command=test_command, worktree=worktree)


def test_the_worktree_command_replaces_the_project_one() -> None:
    politique = _politique(worktree=ConfigWorktree(test_command="python -m pytest"))

    assert commande_effective(politique, _WT, _DEPOT) == "python -m pytest"


def test_the_project_command_is_kept_without_an_override() -> None:
    assert commande_effective(_politique(), _WT, _DEPOT) == "uv run pytest"
    sans_commande = _politique(worktree=ConfigWorktree(env={"A": "b"}))
    assert commande_effective(sans_commande, _WT, _DEPOT) == "uv run pytest"


def test_a_blank_override_counts_as_undeclared() -> None:
    politique = _politique(worktree=ConfigWorktree(test_command="   "))

    assert commande_effective(politique, _WT, _DEPOT) == "uv run pytest"


def test_no_command_at_all_gives_none() -> None:
    assert commande_effective(_politique(test_command=None), _WT, _DEPOT) is None


def test_worktree_and_repo_placeholders_are_replaced() -> None:
    politique = _politique(
        worktree=ConfigWorktree(
            test_command="{repo}/.venv/Scripts/python.exe -m pytest {worktree}/backend/tests"
        )
    )

    assert commande_effective(politique, _WT, _DEPOT) == (
        "/work/repo/.venv/Scripts/python.exe -m pytest /work/wt/backend/tests"
    )


def test_placeholders_of_the_project_command_are_replaced_too() -> None:
    politique = _politique(test_command="pytest {worktree}/tests")

    assert commande_effective(politique, _WT, _DEPOT) == "pytest /work/wt/tests"


def test_an_unknown_placeholder_refuses_the_command_with_its_name() -> None:
    politique = _politique(worktree=ConfigWorktree(test_command="{depot}/python -m pytest"))

    with pytest.raises(PlaceholderInconnu) as erreur:
        commande_effective(politique, _WT, _DEPOT)

    message = str(erreur.value)
    assert "{depot}" in message
    assert "{worktree}" in message and "{repo}" in message


def test_a_shell_variable_is_not_a_placeholder() -> None:
    politique = _politique(test_command="echo ${HOME} {worktree}")

    assert commande_effective(politique, _WT, _DEPOT) == "echo ${HOME} /work/wt"


def test_env_placeholders_are_replaced_and_keys_left_alone() -> None:
    config = ConfigWorktree(
        env={"PYTHONPATH": "{worktree}/backend/src", "{worktree}": "{repo}"}
    )

    assert environnement_effectif(config, _WT, _DEPOT) == {
        "PYTHONPATH": "/work/wt/backend/src",
        "{worktree}": "/work/repo",
    }


def test_env_without_placeholder_is_returned_as_declared() -> None:
    config = ConfigWorktree(env={"CI": "1"})

    assert environnement_effectif(config, _WT, _DEPOT) == {"CI": "1"}
    assert environnement_effectif(ConfigWorktree(), _WT, _DEPOT) == {}


def test_an_unknown_placeholder_in_env_is_refused() -> None:
    config = ConfigWorktree(env={"PYTHONPATH": "{tree}/src"})

    with pytest.raises(PlaceholderInconnu, match="tree"):
        environnement_effectif(config, _WT, _DEPOT)


def test_an_unknown_placeholder_is_a_value_error() -> None:
    # Le testeur attrape `ValueError` pour une commande qui ne démarre pas.
    assert issubclass(PlaceholderInconnu, ValueError)
