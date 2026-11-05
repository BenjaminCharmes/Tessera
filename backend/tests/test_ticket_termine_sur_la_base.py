"""A ticket finished on the base branch is skipped by the queue — ticket-736."""
from tessera.models.ticket import TicketStatus
from tessera.services.pipeline.orchestrator import Orchestrator

from tests.test_file_de_tickets import _OrchestrateurFile, _ServiceTickets, _events


def _contenu(ticket_id: str) -> str:
    return (
        f"---\nid: {ticket_id}\ntitle: T\ntype: feat\nstatus: todo\n"
        "priority: medium\nagent: codeur\n---\n\nCorps\n"
    )


class _EspaceGit:
    """Double of the workspace: serves a ticket as the base holds it."""

    def __init__(self, dossier: str | None) -> None:
        self._dossier = dossier
        self.lectures: list[str] = []

    async def lire_ticket_sur_la_base(
        self, ticket_id: str, *, fetch: bool = True
    ) -> tuple[str, str] | None:
        self.lectures.append(ticket_id)
        if self._dossier is None:
            return None
        return f"tickets/{self._dossier}/{ticket_id}-t.md", _contenu(ticket_id)


class _OrchestrateurObsolete:
    """Only what `_est_termine` reads: a tree that says `todo`, a workspace."""

    def __init__(self, statut_arbre: TicketStatus, espace: _EspaceGit | None) -> None:
        self._ticket_svc = _ServiceTickets({"ticket-001": statut_arbre})
        self._git_workspace = espace
        self.journal: list[str] = []
        self._log = self.journal.append
        self._est_termine = Orchestrator._est_termine.__get__(self)  # type: ignore[attr-defined]


async def test_a_todo_in_the_tree_but_done_on_the_base_is_finished() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, _EspaceGit("done"))

    assert await orch._est_termine("ticket-001") is True


async def test_a_cancelled_ticket_on_the_base_is_finished() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, _EspaceGit("cancelled"))

    assert await orch._est_termine("ticket-001") is True


async def test_an_unreadable_base_keeps_the_verdict_of_the_tree() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, _EspaceGit(None))

    assert await orch._est_termine("ticket-001") is False


class _EspaceQuiLeve:
    """Double whose read of the base raises, as a broken git or network would."""

    async def lire_ticket_sur_la_base(
        self, ticket_id: str, *, fetch: bool = True
    ) -> tuple[str, str] | None:
        raise RuntimeError("git indisponible")


async def test_a_base_read_that_raises_keeps_the_verdict_of_the_tree() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, _EspaceQuiLeve())  # type: ignore[arg-type]

    assert await orch._est_termine("ticket-001") is False


async def test_a_ticket_still_todo_on_the_base_is_not_finished() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, _EspaceGit("todo"))

    assert await orch._est_termine("ticket-001") is False


async def test_a_ticket_finished_in_the_tree_does_not_read_the_base() -> None:
    espace = _EspaceGit("todo")
    orch = _OrchestrateurObsolete(TicketStatus.done, espace)

    assert await orch._est_termine("ticket-001") is True
    assert espace.lectures == []


async def test_without_a_workspace_the_tree_decides() -> None:
    orch = _OrchestrateurObsolete(TicketStatus.todo, None)

    assert await orch._est_termine("ticket-001") is False


async def test_the_queue_skips_a_ticket_finished_on_the_base_and_says_why() -> None:
    orch = _OrchestrateurFile()
    orch._git_workspace = _EspaceGit("done")  # type: ignore[attr-defined]
    journal: list[str] = []
    orch._log = journal.append  # type: ignore[attr-defined]
    _, on_event = await _events()

    await orch.run_queue("projet", ["ticket-001"], on_event)

    assert orch.lances == []
    assert any("déjà terminé sur la base" in ligne for ligne in journal)
