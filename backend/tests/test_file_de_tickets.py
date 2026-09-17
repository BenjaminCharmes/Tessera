"""Enchainer une selection de tickets — ticket-074."""
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.dialogue import DialogueChannel
from vibe_ide.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult


def _ticket(tid: str) -> Ticket:
    return Ticket(
        id=tid, title=f"T {tid}", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body="",
    )


class _OrchestrateurFile:
    """Le vrai `run_queue`, avec `run_pipeline` double."""

    def __init__(self, echecs: set[str] | None = None) -> None:
        from vibe_ide.services.orchestrator import Orchestrator

        self.lances: list[str] = []
        self._echecs = echecs or set()
        self._quota_tracker = None
        self._run_max_budget_usd = 0.0
        self._spent_usd = 0.0
        self.run_queue = Orchestrator.run_queue.__get__(self)  # type: ignore[attr-defined]
        self.budget_exhausted = lambda: False
        self._log = lambda m: None

    async def run_pipeline(
        self, project_id, ticket_id, on_event, run_id=None, dialogue=None,
    ) -> PipelineResult:
        self.lances.append(ticket_id)
        approuve = ticket_id not in self._echecs
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.done if approuve else TicketStatus.blocked,
            rounds=1, approved=approuve,
        )


async def _events() -> tuple[list[OrchestratorEvent], object]:
    collectes: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        collectes.append(event)

    return collectes, _on_event


async def test_la_file_lance_les_tickets_dans_l_ordre_demande() -> None:
    orch = _OrchestrateurFile()
    _, on_event = await _events()

    resultats = await orch.run_queue("p", ["ticket-003", "ticket-001"], on_event)

    assert orch.lances == ["ticket-003", "ticket-001"]
    assert len(resultats) == 2


async def test_un_ticket_bloque_arrete_la_file() -> None:
    # Les tickets d'un lot dependent souvent les uns des autres : enchainer sur
    # une base qui n'a pas ete approuvee ferait travailler le suivant sur un
    # etat que personne n'a valide.
    orch = _OrchestrateurFile(echecs={"ticket-001"})
    _, on_event = await _events()

    resultats = await orch.run_queue("p", ["ticket-001", "ticket-002"], on_event)

    assert orch.lances == ["ticket-001"]
    assert len(resultats) == 1


async def test_un_arret_demande_vide_la_file() -> None:
    orch = _OrchestrateurFile()
    canal = DialogueChannel(interactive=True)
    canal.request_stop()
    _, on_event = await _events()

    resultats = await orch.run_queue("p", ["ticket-001", "ticket-002"], on_event, canal)

    assert orch.lances == []
    assert resultats == []


async def test_la_file_annonce_sa_progression() -> None:
    # Sans cela on ne sait pas, devant l'ecran, ou en est le lot.
    orch = _OrchestrateurFile()
    collectes, on_event = await _events()

    await orch.run_queue("p", ["ticket-001", "ticket-002"], on_event)

    progression = [e for e in collectes if e.type is EventType.QUEUE_PROGRESS]
    assert [e.data["index"] for e in progression] == [1, 2]
    assert progression[0].data["total"] == 2
