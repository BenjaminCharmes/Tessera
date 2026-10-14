"""Vérification des fichiers de tickets d'un projet — ticket-433."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import ticket_check
from tessera.services.ticket_check import verifier_tickets

_TEMPLATE = """---
id: {id}
title: "Un ticket"
type: {type}
status: {status}
priority: medium
agent: codeur
created: {created}
---

# {id}
"""


def _write(
    root: Path,
    folder: str,
    name: str,
    *,
    id: str = "ticket-001",
    type: str = "feat",
    status: str | None = None,
    created: str = "2026-10-14",
) -> Path:
    directory = root / "tickets" / folder
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(
        _TEMPLATE.format(id=id, type=type, status=status or folder, created=created),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "workspace" / "mon-projet"
    (root / "memory").mkdir(parents=True)
    (root / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    return root


def test_sound_project_has_no_problem(project: Path) -> None:
    _write(project, "todo", "ticket-001-a")
    _write(project, "done", "ticket-002-b", id="ticket-002")
    assert verifier_tickets(project) == []


def test_type_outside_enum_is_reported_with_path_and_field(project: Path) -> None:
    _write(project, "todo", "ticket-001-a", type="feature")
    problems = verifier_tickets(project)
    assert len(problems) == 1
    assert problems[0].chemin == "tickets/todo/ticket-001-a.md"
    assert problems[0].champ == "type"
    assert problems[0].valeur == "feature"
    assert "feat" in problems[0].message


def test_created_read_by_yaml_as_a_date_is_accepted(project: Path) -> None:
    # `created: 2026-10-14` sans guillemets est une date pour YAML, pas une chaîne.
    _write(project, "todo", "ticket-001-a", created="2026-10-14")
    assert verifier_tickets(project) == []


def test_file_in_a_folder_contradicting_its_status_is_reported(project: Path) -> None:
    _write(project, "todo", "ticket-001-a", status="done")
    problems = verifier_tickets(project)
    assert [(p.chemin, p.champ, p.valeur) for p in problems] == [
        ("tickets/todo/ticket-001-a.md", "status", "done")
    ]
    assert "todo/" in problems[0].message


def test_two_files_with_the_same_id_are_reported(project: Path) -> None:
    _write(project, "todo", "ticket-001-a")
    _write(project, "done", "ticket-001-b")
    problems = verifier_tickets(project)
    assert sorted(p.chemin for p in problems) == [
        "tickets/done/ticket-001-b.md",
        "tickets/todo/ticket-001-a.md",
    ]
    assert {p.champ for p in problems} == {"id"}


def test_missing_required_field_is_reported(project: Path) -> None:
    path = _write(project, "todo", "ticket-001-a")
    path.write_text(
        path.read_text(encoding="utf-8").replace("agent: codeur\n", ""),
        encoding="utf-8",
    )
    assert [p.champ for p in verifier_tickets(project)] == ["agent"]


def test_unreadable_frontmatter_is_reported(project: Path) -> None:
    path = _write(project, "todo", "ticket-001-a")
    path.write_text("---\nid: [oups\n---\n", encoding="utf-8")
    problems = verifier_tickets(project)
    assert [p.champ for p in problems] == ["frontmatter"]


def test_archive_is_not_checked_as_the_loader_skips_it(project: Path) -> None:
    _write(project, "archive", "ticket-001-a", type="feature")
    assert verifier_tickets(project) == []


def test_every_problem_of_a_file_is_listed(project: Path) -> None:
    path = _write(project, "todo", "ticket-001-a", type="feature")
    path.write_text(
        path.read_text(encoding="utf-8").replace("medium", "urgent"),
        encoding="utf-8",
    )
    assert sorted(p.champ for p in verifier_tickets(project)) == ["priority", "type"]


def test_cli_exit_code_follows_the_problems(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", project.parent)
    _write(project, "todo", "ticket-001-a")
    assert ticket_check.main(["mon-projet"]) == 0
    _write(project, "todo", "ticket-002-b", id="ticket-002", type="feature")
    assert ticket_check.main(["mon-projet"]) == 1
    out = capsys.readouterr().out
    assert "tickets/todo/ticket-002-b.md : type = 'feature'" in out


def test_cli_refuses_a_missing_project(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", project.parent)
    assert ticket_check.main(["absent"]) == 2
    assert ticket_check.main([]) == 2


def test_endpoint_returns_an_empty_list_on_a_sound_project(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", project.parent)
    _write(project, "todo", "ticket-001-a")
    response = TestClient(app).get("/api/v1/projects/mon-projet/tickets/check")
    assert response.status_code == 200
    assert response.json() == []


def test_endpoint_lists_the_faulty_file(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", project.parent)
    _write(project, "todo", "ticket-001-a", type="feature")
    body = TestClient(app).get("/api/v1/projects/mon-projet/tickets/check").json()
    assert body[0]["chemin"] == "tickets/todo/ticket-001-a.md"
    assert body[0]["champ"] == "type"
