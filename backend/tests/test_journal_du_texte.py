"""What a late observer gets back — ticket-185."""
from tessera.services.journal_du_texte import JournalDuTexte
from tessera.services.pipeline_events import EventType, OrchestratorEvent


def _texte(run_id: str, contenu: str) -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.AGENT_TOKEN,
        ticket_id="ticket-001",
        run_id=run_id,
        data={"content": contenu},
    )


def test_replays_the_text_of_a_run_in_order() -> None:
    journal = JournalDuTexte()
    journal.retenir(_texte("run-a", "un "))
    journal.retenir(_texte("run-a", "deux"))

    relu = [e.data["content"] for e in journal.relire("run-a")]

    assert relu == ["un ", "deux"]


def test_keeps_each_run_apart() -> None:
    journal = JournalDuTexte()
    journal.retenir(_texte("run-a", "a"))
    journal.retenir(_texte("run-b", "b"))

    assert [e.data["content"] for e in journal.relire("run-b")] == ["b"]


def test_a_run_never_seen_replays_nothing() -> None:
    assert JournalDuTexte().relire("inconnu") == []


def test_transitions_are_not_retained() -> None:
    """Le snapshot les porte déjà, et les rejouer rejouerait le run."""
    journal = JournalDuTexte()
    journal.retenir(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED, ticket_id="ticket-001", run_id="run-a"
        )
    )

    assert journal.relire("run-a") == []


def test_an_event_without_a_run_is_ignored() -> None:
    journal = JournalDuTexte()
    journal.retenir(
        OrchestratorEvent(
            type=EventType.AGENT_TOKEN, ticket_id="ticket-001", data={"content": "x"}
        )
    )

    assert journal.runs_suivis == 0


def test_the_oldest_text_goes_first_once_the_cap_is_reached() -> None:
    journal = JournalDuTexte(caracteres=10)
    journal.retenir(_texte("run-a", "aaaaa"))
    journal.retenir(_texte("run-a", "bbbbb"))
    journal.retenir(_texte("run-a", "ccccc"))

    relu = [e.data["content"] for e in journal.relire("run-a")]

    assert relu == ["bbbbb", "ccccc"]


def test_a_single_event_larger_than_the_cap_is_still_readable() -> None:
    """Amputer la dernière sortie d'outil rendrait le tampon inutile."""
    journal = JournalDuTexte(caracteres=10)
    journal.retenir(_texte("run-a", "x" * 50))

    assert [e.data["content"] for e in journal.relire("run-a")] == ["x" * 50]


def test_a_closed_run_is_forgotten() -> None:
    journal = JournalDuTexte()
    journal.retenir(_texte("run-a", "a"))
    journal.retenir(
        OrchestratorEvent(
            type=EventType.RUN_CLOSED, ticket_id="ticket-001", run_id="run-a"
        )
    )

    assert journal.relire("run-a") == []
    assert journal.runs_suivis == 0
