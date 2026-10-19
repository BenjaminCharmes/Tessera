"""Tool calls refused by the embedded CLI are noticed and journaled — ticket-515.

Covers:
- the provider reports each tool whose ``tool_result`` carries the CLI refusal;
- an ordinary tool error, or a refusal-looking text that is not an error, is ignored;
- a resumed round keeps the same cwd, allowed tools and permission mode;
- ``run_coder`` writes ``codeur: outil <nom> refusé par le CLI`` in the journal.
"""
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

import tessera.services.providers.agent_sdk as agent_sdk_module
from tessera.models.agent import AgentResult
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.refus_cli import MESSAGE_REFUS_CLI

_REFUS = (
    f"{MESSAGE_REFUS_CLI}. STOP what you are doing and wait for the user "
    "to tell you how to proceed."
)


def _resultat() -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id="sess-1", total_cost_usd=None, usage=None,
    )


def _appel(identifiant: str, outil: str) -> AssistantMessage:
    return AssistantMessage(
        content=[
            TextBlock(text="j'essaie"),
            ToolUseBlock(id=identifiant, name=outil, input={}),
        ],
        model="claude-sonnet-4-6",
    )


def _retour(identifiant: str, contenu: Any, erreur: bool | None = True) -> UserMessage:
    bloc = ToolResultBlock(tool_use_id=identifiant, content=contenu, is_error=erreur)
    return UserMessage(content=[bloc])


def _patch_query(monkeypatch: pytest.MonkeyPatch, messages: list[Any]) -> None:
    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        for message in messages:
            yield message

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)


async def _appeler() -> list[str]:
    resultat = await ClaudeAgentSDKProvider().complete(
        system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100
    )
    return resultat.outils_refuses


async def test_un_refus_du_cli_nomme_l_outil_refuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_query(monkeypatch, [
        _appel("t1", "Edit"), _retour("t1", _REFUS),
        _appel("t2", "Grep"), _retour("t2", [{"type": "text", "text": _REFUS}]),
        _resultat(),
    ])
    assert await _appeler() == ["Edit", "Grep"]


async def test_un_refus_sans_appel_connu_nomme_l_outil_inconnu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_query(monkeypatch, [_retour("absent", _REFUS), _resultat()])
    assert await _appeler() == ["inconnu"]


async def test_une_erreur_ordinaire_ne_produit_aucun_refus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_query(monkeypatch, [
        _appel("t1", "Edit"), _retour("t1", "File not found"),
        _appel("t2", "Read"), _retour("t2", None),
        _appel("t3", "Grep"), _retour("t3", _REFUS, erreur=False),
        _resultat(),
    ])
    assert await _appeler() == []


async def test_un_tour_repris_garde_cwd_outils_et_mode_de_permission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captures: list[Any] = []

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captures.append(options)
        yield _resultat()

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)
    provider = ClaudeAgentSDKProvider()
    for session in (None, "sess-1"):
        await provider.complete(
            system="sys", user="user", model="claude-sonnet-4-6",
            max_tokens=100, cwd=tmp_path, session=session,
        )

    initial, repris = captures
    assert repris.resume == "sess-1" and initial.resume is None
    assert repris.cwd == initial.cwd == str(tmp_path.resolve())
    assert repris.allowed_tools == initial.allowed_tools
    assert repris.tools == initial.tools
    assert repris.permission_mode == initial.permission_mode == "acceptEdits"
    assert repris.settings == initial.settings


async def test_run_coder_ecrit_une_ligne_par_outil_refuse(tmp_path: Path) -> None:
    journal = tmp_path / "memory" / "pipeline-log.md"
    journal.parent.mkdir(parents=True)
    ticket = Ticket(
        id="ticket-515", title="t", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body="## Critères\n- [ ] ok\n",
    )
    runner = AsyncMock()
    runner.run.return_value = AgentResult(
        role="codeur", ticket_id=ticket.id, content="fini",
        suggested_status=TicketStatus.in_review, duration_ms=5,
        outils_refuses=["Edit", "Grep"],
    )
    ticket_svc = AsyncMock()
    orch = Orchestrator(
        runner=runner, ticket_service=ticket_svc, project_context="ctx",
        agent_configs=[], pipeline_log_path=journal,
    )

    async def _on_event(event: OrchestratorEvent) -> None:
        return None

    run = PipelineRun(project_id="proj", ticket=ticket, on_event=_on_event)
    await stages.run_coder(orch, run, "contexte")

    lignes = journal.read_text(encoding="utf-8").splitlines()
    assert any(l.endswith("[ticket-515] codeur: outil Edit refusé par le CLI") for l in lignes)
    assert any(l.endswith("[ticket-515] codeur: outil Grep refusé par le CLI") for l in lignes)


async def test_run_coder_sans_refus_n_ecrit_aucune_ligne_de_refus(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "pipeline-log.md"
    orch = Orchestrator(
        runner=AsyncMock(), ticket_service=AsyncMock(), project_context="ctx",
        agent_configs=[], pipeline_log_path=journal,
    )
    stages.journaliser_refus_cli(orch, "ticket-515", stages.AgentRole.codeur, [])
    assert not journal.exists()
