"""Ticket-414: a hosted project must not inherit Tessera's own CLAUDE files."""
import json
from pathlib import Path

import pytest

import tessera.services.providers.agent_sdk as agent_sdk_module
from tessera.services.providers.agent_sdk import (
    _build_options,
    claude_md_ancetres_a_exclure,
)


def _p(chemin: Path) -> str:
    return chemin.resolve().as_posix()


def test_hosted_project_excludes_every_ancestor_claude_file(tmp_path: Path) -> None:
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    exclus = claude_md_ancetres_a_exclure(projet, tmp_path, ancestor=False)
    racine = tmp_path.resolve()
    assert exclus == [
        _p(racine / "CLAUDE.md"),
        _p(racine / "CLAUDE.local.md"),
        _p(racine / "projects" / "CLAUDE.md"),
        _p(racine / "projects" / "CLAUDE.local.md"),
    ]
    assert _p(projet / "CLAUDE.md") not in exclus


def test_ancestor_project_excludes_nothing(tmp_path: Path) -> None:
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    assert claude_md_ancetres_a_exclure(projet, tmp_path, ancestor=True) == []


def test_directory_outside_the_root_excludes_nothing(tmp_path: Path) -> None:
    racine = tmp_path / "depot"
    dehors = tmp_path / "ailleurs" / "p"
    racine.mkdir()
    dehors.mkdir(parents=True)
    assert claude_md_ancetres_a_exclure(dehors, racine, ancestor=False) == []


def test_root_itself_excludes_nothing(tmp_path: Path) -> None:
    assert claude_md_ancetres_a_exclure(tmp_path, tmp_path, ancestor=False) == []


def test_paths_use_forward_slashes(tmp_path: Path) -> None:
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    exclus = claude_md_ancetres_a_exclure(projet, tmp_path, ancestor=False)
    assert all("\\" not in chemin for chemin in exclus)


@pytest.fixture
def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(agent_sdk_module, "_REPO_ROOT", tmp_path)
    return tmp_path


def _options_pour(projet: Path, **extra: object):  # type: ignore[no-untyped-def]
    return _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=3,
        max_budget_usd=None, cwd=projet, **extra,  # type: ignore[arg-type]
    )


def test_options_of_hosted_project_carry_claude_md_excludes(depot: Path) -> None:
    projet = depot / "projects" / "curio"
    projet.mkdir(parents=True)
    options = _options_pour(projet)
    assert isinstance(options.settings, str)
    exclus = json.loads(options.settings)["claudeMdExcludes"]
    assert _p(depot / "CLAUDE.md") in exclus
    assert _p(depot / "projects" / "CLAUDE.local.md") in exclus
    assert _p(projet / "CLAUDE.md") not in exclus


def test_options_of_ancestor_project_carry_no_excludes(depot: Path) -> None:
    projet = depot / "projects" / "ide-core"
    projet.mkdir(parents=True)
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )
    (depot / ".git").mkdir()
    assert _options_pour(projet).settings is None


def test_options_use_the_frozen_write_root(depot: Path) -> None:
    projet = depot / "projects" / "ide-core"
    projet.mkdir(parents=True)
    # Racine figée par le run : le projet est ancestor même sans agents.json.
    assert _options_pour(projet, racine_ecriture=depot).settings is None


def test_options_without_cwd_carry_no_settings() -> None:
    options = _build_options(
        system="sys", model="m", max_turns=1, max_budget_usd=None, cwd=None
    )
    assert options.settings is None


def _worktree_hors_depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The project folder inside a linked worktree that lies outside `_REPO_ROOT`."""
    depot = tmp_path / "depot"
    depot.mkdir()
    monkeypatch.setattr(agent_sdk_module, "_REPO_ROOT", depot)
    racine = tmp_path / "worktrees" / "curio" / "ticket-1"
    projet = racine / "projects" / "curio"
    projet.mkdir(parents=True)
    (racine / ".git").write_text("gitdir: ailleurs\n", encoding="utf-8")
    return projet


def test_worktree_outside_the_repo_excludes_from_its_own_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _worktree_hors_depot(tmp_path, monkeypatch)
    racine = projet.parents[1]

    options = _options_pour(projet, racine_ecriture=projet)

    assert isinstance(options.settings, str)
    exclus = json.loads(options.settings)["claudeMdExcludes"]
    assert _p(racine / "CLAUDE.md") in exclus
    assert _p(racine / "projects" / "CLAUDE.local.md") in exclus
    assert _p(projet / "CLAUDE.md") not in exclus
    # Rien au-dessus du worktree : ni le dossier des worktrees, ni le disque.
    assert _p(racine.parent / "CLAUDE.md") not in exclus


def test_ancestor_worktree_outside_the_repo_excludes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _worktree_hors_depot(tmp_path, monkeypatch)

    assert _options_pour(projet, racine_ecriture=projet.parents[1]).settings is None
