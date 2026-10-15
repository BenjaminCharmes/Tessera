"""Cited files of a ``git_root: ancestor`` project live in its repository (ticket-448)."""

import json
from pathlib import Path

from tessera.services.validator_cited_files import (
    _find_file_in_project,
    build_cited_files_section,
    extract_file_refs,
)


def _make_repo(tmp_path: Path, ancestor: bool) -> Path:
    """A repo with ``projects/p/`` and ``backend/x.py``; returns the project."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    projet = repo / "projects" / "p"
    projet.mkdir(parents=True)
    manifeste = {"git_root": "ancestor"} if ancestor else {}
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")
    (repo / "backend").mkdir()
    (repo / "backend" / "x.py").write_text("VALUE = 1\n", encoding="utf-8")
    return projet


def test_ancestor_project_joins_a_file_of_its_repository(tmp_path: Path) -> None:
    projet = _make_repo(tmp_path, ancestor=True)

    section, report = build_cited_files_section(["x.py"], projet)

    assert report.joined == ["x.py"]
    assert report.absent == []
    assert "VALUE = 1" in section


def test_ancestor_project_resolves_a_path_from_the_repository_root(
    tmp_path: Path,
) -> None:
    projet = _make_repo(tmp_path, ancestor=True)

    found = _find_file_in_project("backend/x.py", projet)

    assert found is not None and found.name == "x.py"


def test_project_without_ancestor_keeps_a_file_above_it_absent(
    tmp_path: Path,
) -> None:
    projet = _make_repo(tmp_path, ancestor=False)

    section, report = build_cited_files_section(["x.py"], projet)

    assert report.joined == []
    assert report.absent == ["x.py"]
    assert "VALUE" not in section


def test_a_path_leaving_the_repository_is_refused_in_both_cases(
    tmp_path: Path,
) -> None:
    for ancestor in (True, False):
        base = tmp_path / str(ancestor)
        projet = _make_repo(base, ancestor=ancestor)
        # `../../.env` sort du projet ; `../../../.env` sort du dépôt.
        (base / "repo" / ".env").write_text("TOKEN=x", encoding="utf-8")
        (base / ".env").write_text("TOKEN=y", encoding="utf-8")

        assert _find_file_in_project("../../.env", projet) is None
        assert _find_file_in_project("../../../.env", projet) is None
        assert _find_file_in_project(str(base / ".env"), projet) is None


def test_ancestor_search_skips_excluded_directories(tmp_path: Path) -> None:
    projet = _make_repo(tmp_path, ancestor=True)
    cache = projet.parents[1] / "frontend" / "node_modules" / "lib"
    cache.mkdir(parents=True)
    (cache / "vendored.py").write_text("x", encoding="utf-8")

    assert _find_file_in_project("vendored.py", projet) is None


def test_extract_file_refs_ignores_a_command_with_a_space() -> None:
    refs = extract_file_refs(
        ["`git ls-files CLAUDE.md` liste le fichier, voir `git_workspace.py:44`"]
    )

    assert refs == ["git_workspace.py"]
