"""An approved ticket whose delivery failed is reported and retried — ticket-792."""
import sqlite3
from typing import Any

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.file.pipeline_file_reprise import est_non_livre
from tessera.services.file.pipeline_file_tour import Tour
from tessera.services.run_status import classer_les_tickets

_REFUS = "Livraison interrompue : GitCommandError push Internal Server Error"


def _lignes(*lignes: tuple[str, int, str | None, str | None, str | None]) -> list[Any]:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE r (ticket_id, approved, final_status, arret, finished_at)"
    )
    for ligne in lignes:
        db.execute("INSERT INTO r VALUES (?,?,?,?,?)", ligne)
    return list(db.execute("SELECT * FROM r"))


def test_an_approved_ticket_with_an_arret_and_no_pr_is_not_delivered() -> None:
    lignes = _lignes(
        ("ticket-752", 1, "done", None, "2026-11-04T10:00:00"),
        ("ticket-753", 1, "blocked", _REFUS, "2026-11-04T11:00:00"),
    )

    classement = classer_les_tickets(lignes, True)

    assert classement.approuves == ["ticket-752"]
    assert classement.non_livres == ["ticket-753"]
    assert classement.arretes == []


def test_an_unapproved_blocked_ticket_stays_stopped_not_undelivered() -> None:
    lignes = _lignes(("ticket-754", 0, "blocked", "testeur", "2026-11-04T10:00:00"))

    classement = classer_les_tickets(lignes, True)

    assert classement.non_livres == []
    assert [a.ticket_id for a in classement.arretes] == ["ticket-754"]


def test_queue_progress_payload_carries_the_undelivered_tickets() -> None:
    tour = Tour("p", ["a", "b", "c"], 3, "c", non_livres=("a",))

    assert tour.donnees()["non_livres"] == ["a"]
    assert Tour("p", ["a"], 1, "a").donnees()["non_livres"] == []


def _resultat(ticket_id: str, livraison: Livraison | None = None) -> PipelineResult:
    bloque = livraison is not None and livraison.bloque_le_ticket
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.blocked if bloque else TicketStatus.done,
        rounds=1, approved=True, branch=f"{ticket_id}-b",
        arret=livraison.arret if bloque and livraison else None,
        livraison=livraison,
    )


def test_est_non_livre_needs_an_arret_without_a_pr() -> None:
    assert est_non_livre(_resultat("t", Livraison(arret=_REFUS)))
    assert not est_non_livre(_resultat("t", Livraison(pr_number=4)))
    assert not est_non_livre(_resultat("t", Livraison(arret="voulu", arret_voulu=True)))
    assert not est_non_livre(_resultat("t"))


class _Tickets:
    async def get_ticket(self, ticket_id: str) -> Ticket:
        return Ticket(
            id=ticket_id, title="T", type=TicketType.feat, status=TicketStatus.todo,
            priority=TicketPriority.medium, agent="codeur", body="",
        )


class _Orch:
    """The real `run_queue` and delivery, with the pipeline and the delivery doubled."""

    def __init__(self, livraisons: dict[str, list[Livraison]]) -> None:
        self._livraisons = livraisons
        self.livrees: list[str] = []
        self._quota_tracker = None
        self._run_max_budget_usd = 0.0
        self._spent_usd = 0.0
        self._log = lambda m: None
        self._ticket_svc = _Tickets()
        self._git_workspace = None
        self._base_branch = None
        self._ci_watcher = None
        self._merge_without_ci = False
        self._surveiller = None
        self._run_recorder = None
        self._interruption: str | None = None
        self._est_termine = _jamais
        self._interrompre = Orchestrator._interrompre.__get__(self)  # type: ignore[attr-defined]
        self._bloquer_branche_modifiee = Orchestrator._bloquer_branche_modifiee.__get__(self)  # type: ignore[attr-defined]
        self.run_queue = Orchestrator.run_queue.__get__(self)  # type: ignore[attr-defined]

    async def run_pipeline(self, project_id: str, ticket_id: str, on_event: Any, **_: Any) -> PipelineResult:
        from tessera.services.pipeline_livraison import livrer_le_resultat

        resultat = PipelineResult(
            ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1,
            approved=True, branch=f"{ticket_id}-b",
        )
        return await livrer_le_resultat(self, resultat, project_id, on_event)  # type: ignore[arg-type]

    async def _livrer(self, resultat: PipelineResult) -> Livraison:
        self.livrees.append(resultat.ticket_id)
        return self._livraisons[resultat.ticket_id].pop(0)


async def _jamais(ticket_id: str) -> bool:
    return False


async def _file(orch: _Orch, ids: list[str]) -> tuple[list[PipelineResult], list[OrchestratorEvent]]:
    recus: list[OrchestratorEvent] = []

    async def collecter(event: OrchestratorEvent) -> None:
        recus.append(event)

    return await orch.run_queue("p", ids, collecter), recus


def _non_livres(recus: list[OrchestratorEvent]) -> list[list[str]]:
    return [
        list(e.data["non_livres"]) for e in recus if e.type == EventType.QUEUE_PROGRESS
    ]


async def test_the_undelivered_ticket_is_retried_once_at_the_end_and_joins_the_approved() -> None:
    orch = _Orch({
        "ticket-753": [Livraison(arret=_REFUS), Livraison(pr_number=9)],
        "ticket-754": [Livraison(pr_number=10)],
    })

    results, recus = await _file(orch, ["ticket-753", "ticket-754"])

    assert orch.livrees == ["ticket-753", "ticket-754", "ticket-753"]
    assert [r.ticket_id for r in results] == ["ticket-753", "ticket-754"]
    assert results[0].livraison is not None and results[0].livraison.pr_number == 9
    assert results[0].final_status == TicketStatus.done
    assert _non_livres(recus)[-1] == []
    assert ["ticket-753"] in _non_livres(recus)


async def test_a_second_failure_keeps_the_ticket_undelivered_without_a_third_attempt() -> None:
    orch = _Orch({"ticket-753": [Livraison(arret=_REFUS), Livraison(arret=_REFUS)]})

    results, recus = await _file(orch, ["ticket-753"])

    assert orch.livrees == ["ticket-753", "ticket-753"]
    assert est_non_livre(results[0])
    assert _non_livres(recus)[-1] == ["ticket-753"]


async def test_a_retry_that_raises_leaves_the_ticket_undelivered() -> None:
    orch = _Orch({"ticket-753": [Livraison(arret=_REFUS)]})  # la 2e pop lève IndexError

    results, recus = await _file(orch, ["ticket-753"])

    assert orch.livrees == ["ticket-753", "ticket-753"]
    assert est_non_livre(results[0])
    assert _non_livres(recus)[-1] == ["ticket-753"]
