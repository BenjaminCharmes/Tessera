"""Session limit errors pause the queue gracefully — ticket-388.

Quand le CLI répond « You've hit your session limit · resets 5pm (Europe/Paris) »,
le ticket en cours repasse en `todo` (pas `blocked`) et la file s'arrête avant
le ticket suivant. Les autres exceptions gardent le comportement actuel.
"""
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline_run import PipelineRun
from tessera.services.session_limit import (
    extract_reset_time,
    is_session_limit,
)

# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

_SESSION_LIMIT_MSG = (
    "You've hit your session limit · resets 5pm (Europe/Paris)"
)


def _ticket(tid: str = "ticket-001") -> Ticket:
    return Ticket(
        id=tid,
        title=f"Ticket {tid}",
        type=TicketType.feat,
        status=TicketStatus.in_progress,
        priority=TicketPriority.medium,
        agent="codeur",
        body="",
    )


class _Git:
    """Git minimal : commit réussit, pas d'avancement de ref de base."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def commit_all(self, message: str) -> str:
        self.messages.append(message)
        return "abc1234"

    async def advance_base_ref(self) -> None:
        raise AssertionError("session limit ne doit pas avancer la ref de base")


class _Tickets:
    """Service ticket minimal : mémorise le dernier statut appliqué."""

    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    """Orchestrateur minimal pour tester les sorties de pipeline."""

    def __init__(self) -> None:
        self._git_workspace = _Git()
        self._ticket_svc = _Tickets()
        self._max_review_rounds = 3
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(tid: str = "ticket-001") -> tuple[PipelineRun, list[OrchestratorEvent]]:
    events: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="p", ticket=_ticket(tid), on_event=_on_event)
    run.branch = f"{tid}-x"
    run.round_num = 1
    return run, events


# ---------------------------------------------------------------------------
# Test 1 — Reconnaissance de l'erreur avec heure de reprise
# ---------------------------------------------------------------------------


def test_session_limit_is_recognized_with_reset_time() -> None:
    """The session limit message is detected and the reset time extracted."""
    msg = _SESSION_LIMIT_MSG
    assert is_session_limit(msg) is True
    assert extract_reset_time(msg) == "5pm (Europe/Paris)"


def test_session_limit_is_recognized_without_reset_time() -> None:
    """A session limit message without a reset time is still recognized."""
    msg = "You've hit your session limit."
    assert is_session_limit(msg) is True
    assert extract_reset_time(msg) is None


def test_other_error_is_not_session_limit() -> None:
    """An ordinary exception message is not mistaken for a session limit."""
    msg = "Connection refused"
    assert is_session_limit(msg) is False


# ---------------------------------------------------------------------------
# Test 2 — Le ticket en cours repasse en todo
# ---------------------------------------------------------------------------


async def test_session_limit_sets_ticket_to_todo() -> None:
    """A run interrupted by a session limit resets the ticket to todo."""
    orch = _Orch()
    run, events = _run()
    exc = RuntimeError(_SESSION_LIMIT_MSG)

    result = await outcomes.finish_session_limit(orch, run, exc, "5pm (Europe/Paris)")

    # Le ticket repasse en todo, pas blocked
    assert orch._ticket_svc.statut is TicketStatus.todo
    assert result.final_status is TicketStatus.todo
    assert result.approved is False
    # Le run est bien annoncé terminé
    pipeline_done = [e for e in events if e.type is EventType.PIPELINE_DONE]
    assert pipeline_done, "PIPELINE_DONE doit être émis"
    assert pipeline_done[0].data.get("reason") == "session_limit"
    # L'arret contient l'heure de reprise
    assert result.arret is not None
    assert "session_limit" in result.arret
    assert "5pm (Europe/Paris)" in result.arret


# ---------------------------------------------------------------------------
# Test 3 — La file s'arrête proprement et log l'heure de reprise
# ---------------------------------------------------------------------------


class _OrchFile:
    """Double d'orchestrateur : run_queue réel, run_pipeline contrôlé."""

    def __init__(
        self,
        session_limit_on: str | None = None,
        log_path: Path | None = None,
    ) -> None:
        self.lances: list[str] = []
        self._session_limit_on = session_limit_on
        self._quota_tracker = None
        self._run_max_budget_usd = 0.0
        self._spent_usd = 0.0
        self.run_queue = Orchestrator.run_queue.__get__(self)  # type: ignore[attr-defined]
        self._documenter = None
        self.budget_exhausted = lambda: False
        self._log_lines: list[str] = []
        self._log_path = log_path
        self._ticket_svc = _ServiceTickets({})
        self._est_termine = Orchestrator._est_termine.__get__(self)  # type: ignore[attr-defined]
        self._ci_watcher = None

    def _log(self, message: str) -> None:
        self._log_lines.append(message)
        if self._log_path is not None:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(f"- {message}\n")

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: object = None,
        dialogue: object = None,
        envelope_run_id: object = None,
    ) -> PipelineResult:
        self.lances.append(ticket_id)
        if ticket_id == self._session_limit_on:
            # Simule un run interrompu par la limite de session
            return PipelineResult(
                ticket_id=ticket_id,
                final_status=TicketStatus.todo,
                rounds=1,
                approved=False,
                arret="session_limit (reprise : 5pm (Europe/Paris))",
            )
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.done,
            rounds=1,
            approved=True,
        )


class _ServiceTickets:
    def __init__(self, statuts: dict[str, TicketStatus]) -> None:
        self._statuts = statuts

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        t = _ticket(ticket_id)
        return t.model_copy(
            update={"status": self._statuts.get(ticket_id, TicketStatus.todo)}
        )


async def _collect_events() -> tuple[list[OrchestratorEvent], object]:
    collectes: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        collectes.append(event)

    return collectes, _on_event


async def test_queue_stops_on_session_limit_without_launching_next(
    tmp_path: Path,
) -> None:
    """A queue of two tickets stops after the first on a session limit error."""
    log_path = tmp_path / "memory" / "pipeline-log.md"
    orch = _OrchFile(session_limit_on="ticket-001", log_path=log_path)
    events, on_event = await _collect_events()

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"], on_event)

    # Le second ticket n'est pas lancé
    assert orch.lances == ["ticket-001"], (
        "le second ticket ne doit pas démarrer après une limite de session"
    )
    assert len(results) == 1

    # La ligne de pipeline-log contient l'heure de reprise
    assert log_path.exists(), "pipeline-log.md doit être écrit"
    content = log_path.read_text(encoding="utf-8")
    assert "file interrompue : limite de session" in content, (
        f"pipeline-log.md doit contenir la ligne d'arrêt — contenu : {content!r}"
    )
    assert "5pm (Europe/Paris)" in content, (
        f"pipeline-log.md doit contenir l'heure de reprise — contenu : {content!r}"
    )

    # Un événement QUEUE_PROGRESS avec raison session_limit est émis
    session_events = [
        e for e in events
        if e.type is EventType.QUEUE_PROGRESS
        and e.data.get("raison") == "session_limit"
    ]
    assert session_events, "un événement QUEUE_PROGRESS session_limit doit être émis"
    assert session_events[0].data.get("reset_time") == "5pm (Europe/Paris)"


# ---------------------------------------------------------------------------
# Test 4 — Une autre exception garde le comportement actuel (blocked)
# ---------------------------------------------------------------------------


async def test_other_exception_keeps_blocked_behavior() -> None:
    """An ordinary exception still sets the ticket to blocked."""
    orch = _Orch()
    run, events = _run()
    exc = RuntimeError("Connection refused")

    result = await outcomes.finish_interrupted(orch, run, exc)

    assert orch._ticket_svc.statut is TicketStatus.blocked
    assert result.final_status is TicketStatus.blocked
    assert result.approved is False


def test_extract_reset_time_ignores_exit_code_suffix() -> None:
    # Message réel du CLI, relevé dans un pipeline-log le 2026-10-05.
    message = (
        "Claude Code returned an error result: You've hit your session limit"
        " · resets 12:50pm (Europe/Paris) (exit code: 1)"
    )

    assert extract_reset_time(message) == "12:50pm (Europe/Paris)"

