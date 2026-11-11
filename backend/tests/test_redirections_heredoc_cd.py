"""Heredocs et `cd` de tête dans la garde d'écriture Bash — ticket-925."""
import posixpath
from pathlib import Path

from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.redirections_bash import cibles_ecrites


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


def test_unreadable_cd_keeps_current_behaviour() -> None:
    assert cibles_ecrites('cd "$X" && echo x > y') == ["y"]
    assert cibles_ecrites("cd - && echo x > y") == ["y"]
    assert cibles_ecrites("cd /abs && echo x > y") == ["y"]


def test_a_second_directory_change_keeps_current_behaviour() -> None:
    for suite in ("cd ..", "pushd ..", "popd", "(cd ..)"):
        commande = f"cd backend && {suite} && echo x > ../dehors.txt"
        assert cibles_ecrites(commande) == ["../dehors.txt"]


async def test_cd_then_cd_up_then_escape_is_refused(tmp_path: Path) -> None:
    projet = _projet(tmp_path)

    assert await _refuse(projet, "cd backend && cd .. && echo x > ../dehors.txt") is True
