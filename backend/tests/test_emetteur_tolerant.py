"""Un emetteur d'evenements qui leve n'interrompt jamais le run — ticket-121.

En mode single, `send_event` avalait deja les erreurs de socket. En mode file
et autonome, `send_queue_event` / `send_event_autonomous` ne le faisaient pas :
un onglet ferme en plein tour interrompait le run **avant** le commit, et
l'arbre restait sale pour le ticket suivant (ADR-018).
"""
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent


def _ticket(tid: str = "ticket-001") -> Ticket:
    return Ticket(
        id=tid, title="Un ticket", type=TicketType.feat,
        status=TicketStatus.in_progress, priority=TicketPriority.medium,
        agent="codeur", body="",
    )


class _GitQuiCommite:
    def __init__(self) -> None:
        self.commits: list[str] = []

    async def is_clean(self) -> bool:
        return True

    async def initialiser_base_ref(self, base_branch: str | None = None) -> str | None:
        return None

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        return f"{ticket_id}-slug"

    async def current_diff(self) -> str:
        return "diff --git a/x b/x\n+1\n"

    async def diff_depuis_base(self) -> str:
        return "diff --git a/x b/x\n+1\n"

    async def commit_all(self, message: str) -> str | None:
        self.commits.append(message)
        return "abc1234"

    async def advance_base_ref(self) -> None:
        return None


class _Runner:
    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        return AgentResult(
            role=role, ticket_id="ticket-001",  # type: ignore[arg-type]
            content="APPROVED" if role == AgentRole.reviewer else "fait",
            suggested_status=TicketStatus.in_review, duration_ms=1,
        )


async def test_un_on_event_qui_leve_en_mode_file_n_empeche_pas_le_commit(
    tmp_path: Path,
) -> None:
    # En mode file, l'emetteur WebSocket n'avalait pas les erreurs de socket :
    # un onglet ferme en plein tour interrompait le run **avant** le commit,
    # et l'arbre restait sale pour le ticket suivant (ADR-018).
    tickets = AsyncMock()
    tickets.get_ticket.return_value = _ticket()
    git = _GitQuiCommite()
    orch = Orchestrator(
        runner=_Runner(),  # type: ignore[arg-type]
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "log.md",
        git_workspace=git,  # type: ignore[arg-type]
    )

    async def _socket_morte(event: OrchestratorEvent) -> None:
        raise RuntimeError("WebSocket is not connected")

    resultats = await orch.run_queue("p", ["ticket-001"], _socket_morte)

    assert git.commits, "le travail doit etre commite malgre la socket morte"
    assert len(resultats) == 1
    assert resultats[0].approved is True
