"""Un ticket de type `design` va à l'architecte — ticket-098."""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.agent import AgentRole
from tessera.models.ticket import (
    Ticket,
    TicketPriority,
    TicketStatus,
    TicketType,
)
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent


def _ticket(type_: TicketType) -> Ticket:
    return Ticket(
        id="ticket-001",
        title="T",
        type=type_,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="corps",
        project_id="p",
        file_path="/w/t.md",
        created="",
    )


async def _rien(event: OrchestratorEvent) -> None:
    return None


async def _lance(
    tmp_path: Path,
    monkeypatch: Any,
    type_: TicketType,
    events: list[OrchestratorEvent] | None = None,
) -> list[str]:
    """Rend les rôles que le pipeline a réellement appelés."""
    roles: list[str] = []
    collected = events if events is not None else []

    async def _collect(event: OrchestratorEvent) -> None:
        collected.append(event)

    runner = MagicMock()

    async def _run(**kwargs: Any) -> Any:
        role = kwargs.get("role")
        roles.append(getattr(role, "value", str(role)))
        stream = kwargs.get("stream_callback")
        if stream is not None:
            await stream("jeton")
        tool = kwargs.get("tool_callback")
        if tool is not None:
            await tool("Write", {"path": "x"})

        class _R:
            content = "fait"
            cost_usd = 0.0
            input_tokens = output_tokens = cache_read_tokens = 0
            duration_ms = 0
            model = "m"
            suggested_status = None
            session_id = None

        return _R()

    runner.run = _run

    tickets = AsyncMock()
    tickets.get_ticket.return_value = _ticket(type_)
    tickets.update_status.return_value = _ticket(type_)
    git = AsyncMock()
    git.initialiser_base_ref.return_value = None
    git.is_clean.return_value = True
    git.create_branch.return_value = "b"
    git.current_diff.return_value = "diff --git a/x b/x\n+x\n"
    git.commit_all.return_value = "abc"

    from tessera.services import pipeline_stages as stages

    async def _revue(orch: Any, run: Any, contexte: Any) -> tuple[bool, str, str]:
        return True, "", "APPROVED"

    monkeypatch.setattr(stages, "run_review", _revue)

    orch = Orchestrator(
        runner=runner,
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "log.md",
        project_path=tmp_path,
        git_workspace=git,
    )
    await orch.run_pipeline("p", "ticket-001", _collect)
    return roles


async def test_un_ticket_design_va_a_l_architecte(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # `ide-core/CLAUDE.md` l'annonçait depuis le premier commit : « architect —
    # intervient sur les tickets de type design ». Rien ne routait par type, et
    # un ticket d'architecture recevait un développeur.
    roles = await _lance(tmp_path, monkeypatch, TicketType.design)

    assert "architect" in roles
    assert "codeur" not in roles


async def test_un_ticket_feat_va_toujours_au_codeur(
    tmp_path: Path, monkeypatch: Any
) -> None:
    roles = await _lance(tmp_path, monkeypatch, TicketType.feat)

    assert "codeur" in roles
    assert "architect" not in roles


async def test_un_ticket_fix_va_au_codeur(tmp_path: Path, monkeypatch: Any) -> None:
    roles = await _lance(tmp_path, monkeypatch, TicketType.fix)

    assert "codeur" in roles


async def test_les_evenements_de_l_architecte_portent_son_nom(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # `agent=codeur` était codé en dur sur AGENT_STARTED, AGENT_TOKEN et
    # AGENT_TOOL_USE : sur un ticket `design`, l'UI montrait un codeur au
    # travail alors que l'architecte produisait (ticket-122).
    events: list[OrchestratorEvent] = []
    await _lance(tmp_path, monkeypatch, TicketType.design, events)

    producteur = [
        e for e in events
        if e.type in (
            EventType.AGENT_STARTED, EventType.AGENT_TOKEN,
            EventType.AGENT_TOOL_USE, EventType.AGENT_DONE,
        )
    ]
    assert {e.type for e in producteur} == {
        EventType.AGENT_STARTED, EventType.AGENT_TOKEN,
        EventType.AGENT_TOOL_USE, EventType.AGENT_DONE,
    }
    assert {e.agent for e in producteur} == {AgentRole.architect}
