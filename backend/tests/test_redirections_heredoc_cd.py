"""Heredocs et `cd` de tête dans la garde d'écriture Bash — ticket-925."""
import posixpath
from pathlib import Path

import pytest

from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.redirections_bash import cibles_ecrites
from tessera.services.providers.suivi_cd import DOSSIER_INCERTAIN


async def _refuse(projet: Path, commande: str) -> bool:
    hook = hook_refus_hors_perimetre(projet)
    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": commande}}, None, None
    )
    return bool(sortie) and sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


def _projet(tmp_path: Path) -> Path:
    projet = tmp_path / "projects" / "client"
    (projet / "backend").mkdir(parents=True)
    return projet


def test_heredoc_body_is_not_read_as_commands() -> None:
    commande = "cat > fixtures/a.html <<'EOF'\n<p>prix > 10</p> voir ../app/m.py\nEOF"

    assert cibles_ecrites(commande) == ["fixtures/a.html"]


def test_heredoc_variants_and_text_after_the_end_line() -> None:
    for marque in ("<<EOF", '<<"EOF"', "<<-EOF"):
        commande = f"cat > a.txt {marque}\nx > b\n\tEOF\necho y > c.txt"
        assert cibles_ecrites(commande) == ["a.txt", "c.txt"]


def test_unclosed_heredoc_reads_nothing_more() -> None:
    assert cibles_ecrites("cat > a <<EOF\nx > b") == ["a"]


def test_cd_prefix_makes_targets_relative_to_that_folder() -> None:
    cibles = cibles_ecrites("cd backend/tests && echo x > ../app/y.py")

    assert [posixpath.normpath(c) for c in cibles] == ["backend/app/y.py"]


async def test_cd_then_write_inside_the_project_is_accepted(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert await _refuse(projet, "cd backend/tests && echo x > ../app/y.py") is False


async def test_cd_then_escape_stays_refused(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert await _refuse(projet, "cd backend && echo x > ../../dehors.txt") is True


async def test_cd_to_absolute_folder_outside_the_project_is_refused(tmp_path: Path) -> None:
    projet = _projet(tmp_path)
    dehors = tmp_path / "ailleurs"
    dehors.mkdir()

    assert await _refuse(projet, f"cd {dehors.as_posix()} && echo x > f") is True


async def test_cd_to_absolute_project_subfolder_is_accepted(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert await _refuse(projet, f"cd {(projet / 'backend').as_posix()} && echo x > f") is False


async def test_cd_with_undefined_variable_refuses_relative_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("X", raising=False)
    projet = _projet(tmp_path)

    assert await _refuse(projet, 'cd "$X" && echo x > y') is True
    assert await _refuse(projet, "cd - && echo x > y") is True


async def test_home_and_variable_targets_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    assert await _refuse(projet, "echo x >> ~/.bashrc") is True
    assert await _refuse(projet, "echo x > $HOME/.bashrc") is True
    assert await _refuse(projet, "echo x > $NOPE/f") is True


def test_successive_readable_cd_compose() -> None:
    cibles = cibles_ecrites("cd backend && cd tests && echo x > ../y")

    assert [posixpath.normpath(c) for c in cibles] == ["backend/y"]


def test_opaque_directory_change_marks_relative_targets_uncertain() -> None:
    for suite in ("popd", "(cd ..)"):
        commande = f"cd backend && {suite} && echo x > ../dehors.txt"
        assert cibles_ecrites(commande)[0].startswith(DOSSIER_INCERTAIN)


async def test_cd_then_cd_up_then_escape_is_refused(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert await _refuse(projet, "cd backend && cd .. && echo x > ../dehors.txt") is True
