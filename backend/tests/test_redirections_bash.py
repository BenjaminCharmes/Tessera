"""Les cibles d'écriture d'une ligne Bash — ticket-750."""
from pathlib import Path

import pytest

from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.redirections_bash import cibles_ecrites


@pytest.mark.parametrize(
    "commande",
    [
        "echo x>../f",
        "echo x 2>../f",
        "echo x 1>../f",
        "echo x &>../f",
        "echo x >|../f",
        "echo x >| ../f",
    ],
)
def test_glued_redirection_is_a_target(commande: str) -> None:
    assert cibles_ecrites(commande) == ["../f"]


def test_every_tee_argument_is_a_target() -> None:
    assert cibles_ecrites("tee a ../b") == ["a", "../b"]
    assert cibles_ecrites("make | tee -a a ../b | wc -l") == ["a", "../b"]


async def _verdict(projet: Path, commande: str) -> bool:
    hook = hook_refus_hors_perimetre(projet)
    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": commande}}, None, None
    )
    return bool(sortie) and sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    "commande", ["cp x ../y", "mv x ../y", "rm -r ../autre", "cp -t ../d x", "mv x y ../z"]
)
async def test_cp_mv_rm_targets_outside_the_root_are_refused(
    tmp_path: Path, commande: str
) -> None:
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True)

    assert await _verdict(projet, commande) is True


@pytest.mark.parametrize(
    "commande", ["cp x y", "mv x y", "rm -r build", "cp ../source.txt y", "cp -r a b 2>&1"]
)
async def test_cp_mv_rm_targets_inside_the_root_pass(
    tmp_path: Path, commande: str
) -> None:
    projet = tmp_path / "projects" / "client"
    projet.mkdir(parents=True)

    assert await _verdict(projet, commande) is False


def test_descriptor_after_a_cp_does_not_hide_its_destination() -> None:
    assert cibles_ecrites("cp x ../y 2>&1") == ["../y"]


def test_windows_backslash_path_is_not_eaten() -> None:
    assert cibles_ecrites("echo x > ..\\f") == ["..\\f"]


def test_command_words_in_arguments_are_not_commands() -> None:
    assert cibles_ecrites("grep rm ../notes.txt") == []
    assert cibles_ecrites("echo 'a > b'") == []
    assert cibles_ecrites("pytest 2>&1 >&2") == []
    assert cibles_ecrites("echo 'oups > ../f") == []
