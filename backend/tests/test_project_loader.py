import tempfile
from pathlib import Path

import pytest

from vibe_ide.services.project_loader import list_projects, load_project


def test_load_project_with_claude_md(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text("# my-project\n\nDescription du projet.")

    project = load_project(project_dir)

    assert project.id == "my-project"
    assert project.name == "my-project"
    assert project.path == project_dir
    assert "my-project" in project.description


def test_load_project_without_claude_md(tmp_path: Path) -> None:
    project_dir = tmp_path / "bare-project"
    project_dir.mkdir()

    project = load_project(project_dir)

    assert project.id == "bare-project"
    assert project.description == ""


def test_load_project_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Dossier introuvable"):
        load_project(tmp_path / "nonexistent")


def test_list_projects_empty_workspace(tmp_path: Path) -> None:
    assert list_projects(tmp_path) == []


def test_list_projects_nonexistent_workspace(tmp_path: Path) -> None:
    assert list_projects(tmp_path / "missing") == []


def test_list_projects_returns_all(tmp_path: Path) -> None:
    for name in ["project-a", "project-b", "project-c"]:
        (tmp_path / name).mkdir()

    projects = list_projects(tmp_path)

    assert len(projects) == 3
    assert [p.id for p in projects] == ["project-a", "project-b", "project-c"]


def test_list_projects_skips_hidden_dirs(tmp_path: Path) -> None:
    (tmp_path / "visible").mkdir()
    (tmp_path / ".hidden").mkdir()

    projects = list_projects(tmp_path)

    assert len(projects) == 1
    assert projects[0].id == "visible"
