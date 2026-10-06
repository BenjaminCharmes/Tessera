import asyncio
import logging
import os
import time
from pathlib import Path
from unittest.mock import patch

import frontmatter  # type: ignore[import-untyped]
import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.ticket_service import TicketService, _normalize_depends_on


def _svc(project_path: Path) -> TicketService:
    return TicketService(project_path, "test-project")


def _write_ticket(
    path: Path,
    ticket_id: str,
    status: str = "todo",
    title: str = "Test ticket",
    **extra: object,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="Corps du ticket.",
        id=ticket_id,
        title=title,
        type="chore",
        status=status,
        priority="medium",
        agent="codeur",
        created="2025-06-01",
        **extra,
    )
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


# ------------------------------------------------------------------
# list_tickets
# ------------------------------------------------------------------


async def test_list_tickets_empty(tmp_path: Path) -> None:
    result = await _svc(tmp_path).list_tickets()
    assert result == []


async def test_list_tickets_returns_all(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")
    _write_ticket(tmp_path / "tickets/done/ticket-002-b.md", "ticket-002", status="done")

    result = await _svc(tmp_path).list_tickets()

    assert len(result) == 2
    assert result[0].id == "ticket-001"
    assert result[1].id == "ticket-002"


async def test_list_tickets_filter_by_status(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")
    _write_ticket(tmp_path / "tickets/done/ticket-002-b.md", "ticket-002", status="done")

    result = await _svc(tmp_path).list_tickets(TicketStatus.todo)

    assert len(result) == 1
    assert result[0].status == TicketStatus.todo


async def test_list_tickets_sets_project_id(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")

    result = await _svc(tmp_path).list_tickets()

    assert result[0].project_id == "test-project"
    assert result[0].file_path != ""


async def test_list_tickets_skips_archive(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")
    _write_ticket(
        tmp_path / "tickets/archive/done/2025-01/ticket-002-old.md",
        "ticket-002",
        status="done",
    )

    result = await _svc(tmp_path).list_tickets()

    assert len(result) == 1


# ------------------------------------------------------------------
# list_tickets_with_unreadable — ticket-210
# ------------------------------------------------------------------


async def test_list_tickets_with_unreadable_surfaces_missing_type(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A ticket-*.md without `type` appears in unreadable, not in tickets."""
    bad = tmp_path / "tickets/todo/ticket-099-x.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    # Frontmatter without `type` — model validation will reject it.
    bad.write_text(
        "---\nid: ticket-099\ntitle: Bad ticket\nstatus: todo\npriority: medium\nagent: codeur\n---\n",
        encoding="utf-8",
    )
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")

    with caplog.at_level(logging.WARNING, logger="tessera.services.ticket_service"):
        tickets, unreadable = await _svc(tmp_path).list_tickets_with_unreadable()

    # The valid ticket is listed; the broken file is not
    assert len(tickets) == 1
    assert tickets[0].id == "ticket-001"

    # The unreadable file is surfaced with its path and an error mentioning `type`
    assert len(unreadable) == 1
    assert "ticket-099-x.md" in unreadable[0].file_path
    assert "type" in unreadable[0].error.lower()

    # A structured log entry was emitted
    assert any("ticket_unreadable" in r.message for r in caplog.records)


async def test_list_tickets_does_not_raise_on_unreadable(tmp_path: Path) -> None:
    """list_tickets() silently skips bad files — backward-compatible."""
    bad = tmp_path / "tickets/todo/ticket-099-x.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(
        "---\nid: ticket-099\ntitle: Bad\nstatus: todo\npriority: medium\nagent: codeur\n---\n",
        encoding="utf-8",
    )

    result = await _svc(tmp_path).list_tickets()
    assert result == []


# ------------------------------------------------------------------
# get_ticket
# ------------------------------------------------------------------


async def test_get_ticket_found(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-042-foo.md", "ticket-042")

    result = await _svc(tmp_path).get_ticket("ticket-042")

    assert result is not None
    assert result.id == "ticket-042"


async def test_get_ticket_ne_confond_pas_un_prefixe_d_identifiant(tmp_path: Path) -> None:
    # `stem.startswith(ticket_id)` : `ticket-1` trouvait `ticket-100`, et
    # `update_status("ticket-1")` déplaçait le mauvais fichier (ticket-122).
    _write_ticket(tmp_path / "tickets" / "todo" / "ticket-100-cent.md", "ticket-100")

    assert await _svc(tmp_path).get_ticket("ticket-1") is None
    with pytest.raises(ValueError):
        await _svc(tmp_path).update_status("ticket-1", TicketStatus.in_progress)


async def test_get_ticket_accepte_l_identifiant_seul_ou_suivi_d_un_slug(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets" / "todo" / "ticket-001.md", "ticket-001")
    _write_ticket(tmp_path / "tickets" / "todo" / "ticket-002-slug.md", "ticket-002")

    premier = await _svc(tmp_path).get_ticket("ticket-001")
    second = await _svc(tmp_path).get_ticket("ticket-002")

    assert premier is not None and premier.id == "ticket-001"
    assert second is not None and second.id == "ticket-002"


async def test_get_ticket_not_found(tmp_path: Path) -> None:
    result = await _svc(tmp_path).get_ticket("ticket-999")
    assert result is None


# ------------------------------------------------------------------
# update_status
# ------------------------------------------------------------------


async def test_update_status_moves_file(tmp_path: Path) -> None:
    src = tmp_path / "tickets/todo/ticket-001-a.md"
    _write_ticket(src, "ticket-001")

    ticket = await _svc(tmp_path).update_status("ticket-001", TicketStatus.done)

    assert ticket.status == TicketStatus.done
    assert not src.exists()
    assert (tmp_path / "tickets/done/ticket-001-a.md").exists()


async def test_update_status_not_found(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Ticket introuvable"):
        await _svc(tmp_path).update_status("ticket-999", TicketStatus.done)


async def test_update_status_same_dir(tmp_path: Path) -> None:
    src = tmp_path / "tickets/todo/ticket-001-a.md"
    _write_ticket(src, "ticket-001")

    ticket = await _svc(tmp_path).update_status("ticket-001", TicketStatus.todo)

    assert ticket.status == TicketStatus.todo
    assert src.exists()


async def test_update_status_supprime_les_doublons(tmp_path: Path) -> None:
    # Scenario: branch resume leaves one copy in todo/ (base branch) and one in
    # blocked/ (ticket branch).  update_status must consolidate to a single file
    # in the target folder (ticket-220).
    todo_copy = tmp_path / "tickets/todo/ticket-042-foo.md"
    blocked_copy = tmp_path / "tickets/blocked/ticket-042-foo.md"
    _write_ticket(todo_copy, "ticket-042")
    _write_ticket(blocked_copy, "ticket-042", status="blocked")

    ticket = await _svc(tmp_path).update_status("ticket-042", TicketStatus.in_review)

    assert ticket.status == TicketStatus.in_review
    assert not todo_copy.exists()
    assert not blocked_copy.exists()
    # Exactly one file remains, in the target folder.
    in_review_files = list((tmp_path / "tickets/in-review").glob("ticket-042*.md"))
    assert len(in_review_files) == 1


async def test_update_status_ne_leve_pas_si_dest_existe(tmp_path: Path) -> None:
    # On Windows Path.rename raises FileExistsError when the destination already
    # exists.  Path.replace is used instead and must not raise (ticket-220).
    src = tmp_path / "tickets/todo/ticket-007-bar.md"
    existing_dest = tmp_path / "tickets/in-review/ticket-007-bar.md"
    _write_ticket(src, "ticket-007")
    _write_ticket(existing_dest, "ticket-007", status="in-review")

    # Must not raise even though the destination file already exists.
    ticket = await _svc(tmp_path).update_status("ticket-007", TicketStatus.in_review)

    assert ticket.status == TicketStatus.in_review
    assert not src.exists()
    in_review_files = list((tmp_path / "tickets/in-review").glob("ticket-007*.md"))
    assert len(in_review_files) == 1


# ------------------------------------------------------------------
# create_ticket
# ------------------------------------------------------------------


async def test_create_ticket_writes_file(tmp_path: Path) -> None:
    ticket = Ticket(
        id="",
        title="Ma nouvelle feature",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.high,
        agent="codeur",
    )

    result = await _svc(tmp_path).create_ticket(ticket)

    assert result.id.startswith("ticket-")
    assert result.project_id == "test-project"
    assert result.file_path != ""
    assert Path(result.file_path).exists()


async def test_create_ticket_with_explicit_id(tmp_path: Path) -> None:
    ticket = Ticket(
        id="ticket-042",
        title="Ticket avec id fourni",
        type=TicketType.chore,
        status=TicketStatus.todo,
        priority=TicketPriority.low,
        agent="codeur",
    )

    result = await _svc(tmp_path).create_ticket(ticket)

    assert result.id == "ticket-042"


async def test_create_ticket_next_id_auto_increments(tmp_path: Path) -> None:
    _write_ticket(tmp_path / "tickets/todo/ticket-005-x.md", "ticket-005")

    ticket = Ticket(
        id="",
        title="Auto increment",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
    )

    result = await _svc(tmp_path).create_ticket(ticket)

    assert result.id == "ticket-006"


async def test_create_ticket_sets_created_date(tmp_path: Path) -> None:
    ticket = Ticket(
        id="ticket-010",
        title="Date auto",
        type=TicketType.chore,
        status=TicketStatus.todo,
        priority=TicketPriority.low,
        agent="codeur",
    )

    result = await _svc(tmp_path).create_ticket(ticket)

    assert result.created != ""


# ------------------------------------------------------------------
# archive_old_tickets
# ------------------------------------------------------------------


def _age_file(path: Path, seconds: int) -> None:
    ts = time.time() - seconds
    os.utime(path, (ts, ts))


async def test_archive_old_tickets_moves_old(tmp_path: Path) -> None:
    ticket_path = tmp_path / "tickets/done/ticket-001-old.md"
    _write_ticket(ticket_path, "ticket-001", status="done")
    _age_file(ticket_path, 31 * 86400)

    archived = await _svc(tmp_path).archive_old_tickets(days=30)

    assert len(archived) == 1
    assert not ticket_path.exists()
    assert any((tmp_path / "tickets/archive").rglob("ticket-001-old.md"))


async def test_archive_old_tickets_keeps_recent(tmp_path: Path) -> None:
    ticket_path = tmp_path / "tickets/done/ticket-002-new.md"
    _write_ticket(ticket_path, "ticket-002", status="done")

    archived = await _svc(tmp_path).archive_old_tickets(days=30)

    assert archived == []
    assert ticket_path.exists()


# ------------------------------------------------------------------
# list_archived_tickets
# ------------------------------------------------------------------


async def test_list_archived_tickets_empty(tmp_path: Path) -> None:
    assert await _svc(tmp_path).list_archived_tickets() == []


async def test_list_archived_tickets_returns_archived(tmp_path: Path) -> None:
    path = tmp_path / "tickets/archive/done/2025-01/ticket-005-x.md"
    _write_ticket(path, "ticket-005", status="done")

    result = await _svc(tmp_path).list_archived_tickets()

    assert len(result) == 1
    assert result[0].id == "ticket-005"


# ------------------------------------------------------------------
# rotate_pipeline_log
# ------------------------------------------------------------------


async def test_rotate_pipeline_log_no_file(tmp_path: Path) -> None:
    await _svc(tmp_path).rotate_pipeline_log()  # no exception


async def test_rotate_pipeline_log_short_file(tmp_path: Path) -> None:
    log = tmp_path / "memory" / "pipeline-log.md"
    log.parent.mkdir()
    log.write_text("\n".join(f"line {i}" for i in range(50)), encoding="utf-8")
    original = log.read_text(encoding="utf-8")

    await _svc(tmp_path).rotate_pipeline_log()

    assert log.read_text(encoding="utf-8") == original


async def test_rotate_pipeline_log_agit_sur_memory_pipeline_log(tmp_path: Path) -> None:
    # La rotation lisait `<projet>/pipeline-log.md` alors que l'orchestrateur
    # écrit `<projet>/memory/pipeline-log.md` : elle ne tournait jamais sur le
    # vrai fichier, qui grossissait sans borne (ticket-122).
    log = tmp_path / "memory" / "pipeline-log.md"
    log.parent.mkdir()
    lines = [f"line {i}\n" for i in range(300)]
    log.write_text("".join(lines), encoding="utf-8")

    await _svc(tmp_path).rotate_pipeline_log()

    result = log.read_text(encoding="utf-8").splitlines()
    assert len(result) == 200
    assert result[0] == "line 100"
    assert result[-1] == "line 299"


async def test_rotate_pipeline_log_accepte_le_chemin_reel(tmp_path: Path) -> None:
    # L'orchestrateur connaît le chemin qu'il ecrit : il peut le transmettre.
    log = tmp_path / "ailleurs" / "journal.md"
    log.parent.mkdir()
    log.write_text("".join(f"line {i}\n" for i in range(300)), encoding="utf-8")

    await _svc(tmp_path).rotate_pipeline_log(log)

    assert len(log.read_text(encoding="utf-8").splitlines()) == 200


# ------------------------------------------------------------------
# Le dossier fait foi (ticket-059)
# ------------------------------------------------------------------


async def test_ticket_type_couvre_les_types_conventional_commits(tmp_path: Path) -> None:
    # CLAUDE.md impose Conventional Commits, et des tickets existants utilisent
    # déjà `refactor`. Un type manquant de l'enum fait échouer le parsing du
    # fichier — et donc tout endpoint qui liste les tickets du projet.
    from tessera.models.ticket import TicketType

    values = {t.value for t in TicketType}
    assert {"feat", "fix", "chore", "docs", "refactor", "test"} <= values


# ------------------------------------------------------------------
# _normalize_depends_on — ticket-275
# ------------------------------------------------------------------


def test_normalize_depends_on_string_single() -> None:
    """A plain string 'ticket-001' becomes ['ticket-001']."""
    assert _normalize_depends_on("ticket-001") == ["ticket-001"]


def test_normalize_depends_on_string_multiple() -> None:
    """A comma-separated string becomes a list of ticket ids."""
    assert _normalize_depends_on("ticket-008, ticket-009") == ["ticket-008", "ticket-009"]


def test_normalize_depends_on_list_unchanged() -> None:
    """A proper YAML list is returned as-is."""
    assert _normalize_depends_on(["ticket-001"]) == ["ticket-001"]


def test_normalize_depends_on_empty_gives_empty_list() -> None:
    """None and empty string both give []."""
    assert _normalize_depends_on(None) == []
    assert _normalize_depends_on("") == []
    assert _normalize_depends_on([]) == []


def test_normalize_depends_on_invalid_id_is_discarded(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An item that does not match ticket-NNN is dropped and logged."""
    with caplog.at_level(logging.WARNING, logger="tessera.services.ticket_service"):
        result = _normalize_depends_on("ticket-001, not-a-ticket, ticket-002")

    assert result == ["ticket-001", "ticket-002"]
    assert any("depends_on_invalid_id" in r.message for r in caplog.records)


async def test_parse_depends_on_string_in_file(tmp_path: Path) -> None:
    """A ticket file with depends_on as a YAML scalar is parsed correctly."""
    ticket_path = tmp_path / "tickets" / "todo" / "ticket-010-deps.md"
    ticket_path.parent.mkdir(parents=True, exist_ok=True)
    ticket_path.write_text(
        "---\n"
        "id: ticket-010\n"
        "title: Test depends_on string\n"
        "type: chore\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "depends_on: ticket-001\n"
        "---\n",
        encoding="utf-8",
    )

    svc = TicketService(tmp_path, "test-project")
    ticket = await svc.get_ticket("ticket-010")

    assert ticket is not None
    assert ticket.depends_on == ["ticket-001"]


async def test_parse_depends_on_csv_string_in_file(tmp_path: Path) -> None:
    """A comma-separated depends_on string in a file is split into ids."""
    ticket_path = tmp_path / "tickets" / "todo" / "ticket-011-deps.md"
    ticket_path.parent.mkdir(parents=True, exist_ok=True)
    ticket_path.write_text(
        "---\n"
        "id: ticket-011\n"
        "title: Test depends_on csv\n"
        "type: chore\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "depends_on: ticket-008, ticket-009\n"
        "---\n",
        encoding="utf-8",
    )

    svc = TicketService(tmp_path, "test-project")
    ticket = await svc.get_ticket("ticket-011")

    assert ticket is not None
    assert ticket.depends_on == ["ticket-008", "ticket-009"]


# ------------------------------------------------------------------
# Cache de parsing par fichier — ticket-352
# ------------------------------------------------------------------


def _advance_mtime(path: Path, seconds: float = 1.0) -> None:
    """Force the mtime of a file ahead by `seconds` to guarantee a cache miss."""
    ts = time.time() + seconds
    os.utime(path, (ts, ts))


async def test_cache_avoids_double_parse_on_unchanged_files(tmp_path: Path) -> None:
    """Two successive listings without file changes parse each file only once."""
    path1 = tmp_path / "tickets/todo/ticket-001-a.md"
    path2 = tmp_path / "tickets/todo/ticket-002-b.md"
    _write_ticket(path1, "ticket-001")
    _write_ticket(path2, "ticket-002")

    svc = _svc(tmp_path)
    with patch.object(svc, "_parse", wraps=svc._parse) as mock_parse:
        await svc.list_tickets()
        after_first = mock_parse.call_count
        await svc.list_tickets()
        after_second = mock_parse.call_count

    assert after_first == 2   # both files parsed on first listing
    assert after_second == 2  # no additional parse on second listing


async def test_cache_invalidated_when_file_modified(tmp_path: Path) -> None:
    """A file modified between two listings is re-parsed with its new content."""
    path = tmp_path / "tickets/todo/ticket-001-a.md"
    _write_ticket(path, "ticket-001", title="Titre original")

    svc = _svc(tmp_path)
    result1 = await svc.list_tickets()
    assert result1[0].title == "Titre original"

    _write_ticket(path, "ticket-001", title="Titre modifié")
    _advance_mtime(path)

    result2 = await svc.list_tickets()
    assert result2[0].title == "Titre modifié"


async def test_cache_reflects_ticket_moved_to_done(tmp_path: Path) -> None:
    """A ticket moved to done/ is listed with done status after the move."""
    todo_path = tmp_path / "tickets/todo/ticket-001-a.md"
    done_dir = tmp_path / "tickets/done"
    done_dir.mkdir(parents=True, exist_ok=True)
    _write_ticket(todo_path, "ticket-001", status="todo")

    svc = _svc(tmp_path)
    result1 = await svc.list_tickets()
    assert result1[0].status == TicketStatus.todo

    done_path = done_dir / "ticket-001-a.md"
    todo_path.rename(done_path)

    result2 = await svc.list_tickets()
    assert len(result2) == 1
    assert result2[0].status == TicketStatus.done


async def test_cache_purges_deleted_file(tmp_path: Path) -> None:
    """A deleted file no longer appears in the listing and its cache entry is removed."""
    from tessera.services import ticket_service as ts_module

    path = tmp_path / "tickets/todo/ticket-001-a.md"
    _write_ticket(path, "ticket-001")

    svc = _svc(tmp_path)
    result1 = await svc.list_tickets()
    assert len(result1) == 1

    resolved = str(path.resolve())
    assert any(k[0] == resolved for k in ts_module._ticket_cache)

    path.unlink()

    result2 = await svc.list_tickets()
    assert result2 == []
    assert not any(k[0] == resolved for k in ts_module._ticket_cache)


async def test_list_tickets_uses_asyncio_to_thread(tmp_path: Path) -> None:
    """list_tickets_with_unreadable delegates its disk work to asyncio.to_thread."""
    svc = _svc(tmp_path)
    with patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_thread:
        await svc.list_tickets_with_unreadable()
    assert mock_thread.called


async def test_get_ticket_uses_asyncio_to_thread(tmp_path: Path) -> None:
    """get_ticket delegates its disk work to asyncio.to_thread."""
    _write_ticket(tmp_path / "tickets/todo/ticket-001-a.md", "ticket-001")
    svc = _svc(tmp_path)
    with patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_thread:
        await svc.get_ticket("ticket-001")
    assert mock_thread.called


async def test_le_dossier_fait_foi_sur_le_statut(tmp_path: Path) -> None:
    # Cas réel : douze tickets de ide-core étaient dans `done/` avec
    # `status: todo` dans leur frontmatter, et l'UI les affichait comme à
    # faire. Le dossier ne peut pas mentir — c'est le service qui y place les
    # fichiers ; le champ, lui, dérive (ticket-059).
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (tmp_path / "tickets" / status).mkdir(parents=True)

    (tmp_path / "tickets" / "done" / "ticket-017.md").write_text(
        "---\n"
        "id: ticket-017\n"
        'title: "Terminé il y a longtemps"\n'
        "type: feat\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n# ticket-017\n",
        encoding="utf-8",
    )

    svc = TicketService(tmp_path, "projet")

    ticket = await svc.get_ticket("ticket-017")
    assert ticket is not None
    assert ticket.status == TicketStatus.done

    assert await svc.list_tickets(TicketStatus.todo) == []
    assert [t.id for t in await svc.list_tickets(TicketStatus.done)] == ["ticket-017"]
