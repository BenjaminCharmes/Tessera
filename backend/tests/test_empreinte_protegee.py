"""L'empreinte des fichiers protégés voit ce que les gardes lexicales ne lisent pas — ticket-933."""
import subprocess
from pathlib import Path

import pytest

from tessera.services.pipeline.pipeline_empreinte import Empreinte, empreinte, noms_changes

_IDENTITE = ["-c", "user.name=Test", "-c", "user.email=test@example.com"]


class _Orch:
    def __init__(self, projet: Path | None, commande: str | None = None) -> None:
        self._project_path = projet
        self._test_command = commande


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *_IDENTITE, *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    racine = tmp_path / "depot"
    racine.mkdir()
    _git(racine, "init", "-b", "main")
    (racine / "agents.json").write_text('{"autonomy": "pr"}', encoding="utf-8")
    (racine / "CLAUDE.md").write_text("# P\n", encoding="utf-8")
    _git(racine, "add", "agents.json", "CLAUDE.md")
    _git(racine, "commit", "-m", "init")
    return racine


async def test_empreinte_is_identical_when_nothing_changes(depot: Path) -> None:
    assert await empreinte(_Orch(depot)) == await empreinte(_Orch(depot))  # type: ignore[arg-type]


async def test_empreinte_changes_when_a_git_hook_is_created(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]

    (depot / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n", encoding="utf-8")

    apres = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    assert noms_changes(avant, apres) == [".git/hooks/pre-commit"]


async def test_empreinte_changes_when_git_config_is_modified(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]

    with (depot / ".git" / "config").open("a", encoding="utf-8") as fichier:
        fichier.write("[core]\n\tfsmonitor = true\n")

    assert noms_changes(avant, await empreinte(_Orch(depot))) == [".git/config"]  # type: ignore[arg-type]


async def test_empreinte_changes_when_agents_json_is_rewritten(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]

    (depot / "agents.json").write_text('{"autonomy": "merge"}', encoding="utf-8")

    assert noms_changes(avant, await empreinte(_Orch(depot))) == ["agents.json"]  # type: ignore[arg-type]


async def test_empreinte_covers_the_common_git_config_under_a_worktree(
    depot: Path, tmp_path: Path
) -> None:
    arbre = tmp_path / "wt"
    _git(depot, "worktree", "add", "-b", "ticket-1-x", str(arbre))
    avant = await empreinte(_Orch(arbre))  # type: ignore[arg-type]

    with (depot / ".git" / "config").open("a", encoding="utf-8") as fichier:
        fichier.write("[diff]\n\texternal = x\n")

    assert ".git/config" in avant
    assert noms_changes(avant, await empreinte(_Orch(arbre))) == [".git/config"]  # type: ignore[arg-type]


async def test_empreinte_sees_a_file_that_appears_or_disappears(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]

    (depot / ".mcp.json").write_text("{}", encoding="utf-8")
    (depot / "CLAUDE.md").unlink()

    assert noms_changes(avant, await empreinte(_Orch(depot))) == [".mcp.json", "CLAUDE.md"]  # type: ignore[arg-type]


async def test_empreinte_covers_the_test_command_script(depot: Path) -> None:
    (depot / "verif.py").write_text("print(1)\n", encoding="utf-8")
    avant = await empreinte(_Orch(depot, "python verif.py"))  # type: ignore[arg-type]

    (depot / "verif.py").write_text("print(2)\n", encoding="utf-8")

    assert noms_changes(avant, await empreinte(_Orch(depot, "python verif.py"))) == ["verif.py"]  # type: ignore[arg-type]


async def test_empreinte_ignores_unprotected_files(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]

    (depot / "app.py").write_text("x = 1\n", encoding="utf-8")

    assert await empreinte(_Orch(depot)) == avant  # type: ignore[arg-type]


async def test_every_enumerated_path_is_protected_and_without_a_project_it_is_empty(
    depot: Path,
) -> None:
    assert await empreinte(_Orch(None)) == {}  # type: ignore[arg-type]
    (depot / ".github" / "workflows").mkdir(parents=True)
    (depot / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    (depot / "README.md").write_text("x\n", encoding="utf-8")

    noms = (await empreinte(_Orch(depot))).keys()  # type: ignore[arg-type]

    assert ".github/workflows/ci.yml" in noms
    assert "README.md" not in noms


def test_names_changed_never_carry_a_content() -> None:
    avant: Empreinte = {"a": "1", "b": None, "c": "3"}
    apres: Empreinte = {"a": "2", "b": None, "d": "4"}

    assert noms_changes(avant, apres) == ["a", "c", "d"]
