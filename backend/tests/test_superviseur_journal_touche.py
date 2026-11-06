"""A run diff that touches the supervision journal blocks the run, except a supervision run (ticket-853)."""
import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.gardes.journal_touche import lignes_du_journal
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.pipeline_contraintes import arret_contraintes_hors_proposees, arret_journal_modifie
from tessera.services.pipeline.pipeline_journal import MODE_SUPERVISION, projet_en_supervision
from tessera.services.pipeline.run_registry import RUN_REGISTRY
from tests.test_lecons_gardees import _diff, _Orch, _run

LIGNE = "+- 2026-11-06 | trier | ticket-900 | abc1234 | résumé"


@pytest.mark.parametrize(
    "chemin", ["memory/supervision.md", "projects/ide-core/memory/supervision.md"]
)
async def test_run_diff_touching_journal_blocks_the_run(chemin: str) -> None:
    events: list[OrchestratorEvent] = []
    orch = _Orch()
    run = _run(_diff(chemin, 6, [LIGNE]), events)

    resultat = await arret_journal_modifie(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert "unapproved" in orch._git_workspace.messages[0]
    assert orch._ticket_svc.statut is TicketStatus.blocked
    raisons = [e.data.get("reason") for e in events if e.type is EventType.ERROR]
    assert "supervision_journal_modified" in raisons
    assert any("BLOCKED" in ligne and "supervision.md" in ligne for ligne in orch.logs)


async def test_the_coder_turn_check_also_stops_on_the_journal() -> None:
    orch = _Orch()
    run = _run(_diff("memory/supervision.md", 6, [LIGNE]))

    resultat = await arret_contraintes_hors_proposees(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert "supervision.md" in (resultat.arret or "")


async def test_supervision_run_is_not_blocked() -> None:
    orch = _Orch()
    run = _run(_diff("memory/supervision.md", 6, [LIGNE]))
    ouvert = RUN_REGISTRY.ouvrir(run.project_id, "ticket-853", mode=MODE_SUPERVISION)
    try:
        assert projet_en_supervision(run.project_id) is True
        assert await arret_journal_modifie(orch, run) is None  # type: ignore[arg-type]
        assert await arret_contraintes_hors_proposees(orch, run) is None  # type: ignore[arg-type]
    finally:
        RUN_REGISTRY.fermer(ouvert.run_id)

    assert projet_en_supervision(run.project_id) is False
    assert orch.logs == []


async def test_an_ordinary_run_on_the_project_is_still_blocked() -> None:
    orch = _Orch()
    run = _run(_diff("memory/supervision.md", 6, [LIGNE]))
    ouvert = RUN_REGISTRY.ouvrir(run.project_id, "ticket-853", mode="single")
    try:
        assert await arret_journal_modifie(orch, run) is not None  # type: ignore[arg-type]
    finally:
        RUN_REGISTRY.fermer(ouvert.run_id)


async def test_a_diff_that_leaves_the_journal_alone_goes_on() -> None:
    orch = _Orch()
    run = _run(_diff("memory/decisions.md", 3, ["+## ADR-099"]))

    assert await arret_journal_modifie(orch, run) is None  # type: ignore[arg-type]
    assert orch.logs == []


def test_lignes_du_journal_marks_a_file_touched_without_a_line() -> None:
    diff = "diff --git a/memory/supervision.md b/memory/supervision.md\nnew file mode 100644\n"

    assert lignes_du_journal(diff) == ["memory/supervision.md (fichier touché)"]
