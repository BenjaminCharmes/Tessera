"""Tests TDD pour create_tickets_batch — ticket-029, ticket-359."""
from pathlib import Path

import pytest

from tessera.models.ticket import TicketDraftPlan, TicketStatus
from tessera.services.pipeline_text import _extract_criteria
from tessera.services.ticket_service import TicketService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _svc(tmp_path: Path) -> TicketService:
    project_dir = tmp_path / "my-project"
    (project_dir / "tickets" / "todo").mkdir(parents=True)
    return TicketService(project_dir, "my-project")


def _draft(
    title: str,
    depends_on_index: list[int] | None = None,
    priority: str = "medium",
) -> TicketDraftPlan:
    return TicketDraftPlan(
        title=title,
        type="feat",
        priority=priority,
        agent="codeur",
        description=f"Description de {title}",
        acceptance_criteria=["Critère 1"],
        depends_on_index=depends_on_index or [],
    )


# ------------------------------------------------------------------
# Résultat retourné
# ------------------------------------------------------------------


async def test_batch_empty_returns_empty_list(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([])
    assert result == []


async def test_batch_single_ticket_creates_one_ticket(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("Ticket A")])
    assert len(result) == 1


async def test_batch_three_tickets_creates_three(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    drafts = [_draft("A"), _draft("B"), _draft("C")]
    result = await svc.create_tickets_batch(drafts)
    assert len(result) == 3


# ------------------------------------------------------------------
# IDs séquentiels
# ------------------------------------------------------------------


async def test_batch_assigns_sequential_ids(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    drafts = [_draft("A"), _draft("B"), _draft("C")]
    result = await svc.create_tickets_batch(drafts)
    ids = [t.id for t in result]
    assert ids == ["ticket-001", "ticket-002", "ticket-003"]


async def test_batch_ids_continue_after_existing_tickets(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    # Créer un ticket existant manuellement
    await svc.create_tickets_batch([_draft("Préexistant")])

    result = await svc.create_tickets_batch([_draft("Nouveau A"), _draft("Nouveau B")])
    ids = [t.id for t in result]
    assert ids == ["ticket-002", "ticket-003"]


# ------------------------------------------------------------------
# Résolution depends_on_index → vrais IDs
# ------------------------------------------------------------------


async def test_batch_no_dependencies_creates_empty_depends_on(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("A"), _draft("B")])
    assert result[0].depends_on == []
    assert result[1].depends_on == []


async def test_batch_dependency_resolves_to_real_id(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    drafts = [_draft("Backend"), _draft("Frontend", depends_on_index=[0])]
    result = await svc.create_tickets_batch(drafts)
    assert result[1].depends_on == [result[0].id]


async def test_batch_chain_dependency_resolves_correctly(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    drafts = [
        _draft("A"),
        _draft("B", depends_on_index=[0]),
        _draft("C", depends_on_index=[1]),
    ]
    result = await svc.create_tickets_batch(drafts)
    assert result[1].depends_on == [result[0].id]
    assert result[2].depends_on == [result[1].id]


async def test_batch_multiple_dependencies(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    drafts = [
        _draft("A"),
        _draft("B"),
        _draft("C", depends_on_index=[0, 1]),
    ]
    result = await svc.create_tickets_batch(drafts)
    assert set(result[2].depends_on) == {result[0].id, result[1].id}


# ------------------------------------------------------------------
# Propriétés des tickets créés
# ------------------------------------------------------------------


async def test_batch_ticket_has_todo_status(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("A")])
    assert result[0].status == TicketStatus.todo


async def test_batch_ticket_preserves_title(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("Mon titre précis")])
    assert result[0].title == "Mon titre précis"


async def test_batch_ticket_preserves_priority(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("A", priority="high")])
    assert result[0].priority.value == "high"


async def test_batch_ticket_preserves_description_as_body(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("A")])
    assert "Description de A" in result[0].body


# ------------------------------------------------------------------
# Persistance sur disque
# ------------------------------------------------------------------


async def test_batch_tickets_are_written_to_disk(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    result = await svc.create_tickets_batch([_draft("A"), _draft("B")])
    files = list((tmp_path / "my-project" / "tickets" / "todo").glob("ticket-*.md"))
    assert len(files) == 2


async def test_batch_tickets_visible_via_list_tickets(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    await svc.create_tickets_batch([_draft("A"), _draft("B")])
    all_tickets = await svc.list_tickets()
    assert len(all_tickets) == 2


# ------------------------------------------------------------------
# Critères d'acceptation dans le corps du ticket — ticket-359
# ------------------------------------------------------------------


async def test_batch_body_contains_criteria_heading(tmp_path: Path) -> None:
    """A draft with two criteria produces a body with the criteria heading."""
    svc = _svc(tmp_path)
    draft = TicketDraftPlan(
        title="Avec critères",
        type="feat",
        priority="medium",
        agent="codeur",
        description="La description du ticket.",
        acceptance_criteria=["Premier critère", "Deuxième critère"],
        depends_on_index=[],
    )
    result = await svc.create_tickets_batch([draft])
    body = result[0].body
    assert "## Critères d'acceptation" in body
    assert body.count("- [ ]") == 2


async def test_batch_extract_criteria_matches_draft(tmp_path: Path) -> None:
    """_extract_criteria applied to the created body returns the draft's criteria."""
    svc = _svc(tmp_path)
    criteria = ["Vérifier que X fonctionne", "Vérifier que Y ne régresse pas"]
    draft = TicketDraftPlan(
        title="Test extraction",
        type="feat",
        priority="medium",
        agent="codeur",
        description="Description courte.",
        acceptance_criteria=criteria,
        depends_on_index=[],
    )
    result = await svc.create_tickets_batch([draft])
    extracted = _extract_criteria(result[0].body)
    assert extracted == criteria


async def test_batch_draft_without_criteria_has_no_criteria_section(tmp_path: Path) -> None:
    """A draft without criteria produces a body without an acceptance-criteria section."""
    svc = _svc(tmp_path)
    draft = TicketDraftPlan(
        title="Sans critères",
        type="chore",
        priority="low",
        agent="codeur",
        description="Juste une description.",
        acceptance_criteria=[],
        depends_on_index=[],
    )
    result = await svc.create_tickets_batch([draft])
    body = result[0].body
    assert "## Critères" not in body
    assert "- [ ]" not in body


async def test_batch_description_is_at_start_of_body(tmp_path: Path) -> None:
    """The draft description is at the head of the body, unchanged."""
    svc = _svc(tmp_path)
    description = "Voici la description originale du ticket."
    draft = TicketDraftPlan(
        title="Ordre du corps",
        type="feat",
        priority="high",
        agent="codeur",
        description=description,
        acceptance_criteria=["Un critère"],
        depends_on_index=[],
    )
    result = await svc.create_tickets_batch([draft])
    body = result[0].body
    assert body.startswith(description)
