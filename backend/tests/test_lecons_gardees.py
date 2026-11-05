"""A run diff that touches the lessons file blocks the run (ticket-804, ADR-074)."""
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.pipeline import lecons_run
from tessera.services.gardes.lecons import lire_lecons
from tessera.services.gardes.lecons_touchees import lignes_de_lecons
from tessera.services.pipeline.lecons_run import proposer_lecon
from tessera.services.pipeline.pipeline_contraintes import (
    arret_contraintes_hors_proposees,
    arret_lecons_modifiees,
)
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.pipeline_run import PipelineRun
from tests.doubles_git import GitWorkspaceDouble
from tests.test_lecons_run import LECON, PREUVE, RETOUR, _Fournisseur, _projet, _reponse

_SERVICES = Path(__file__).resolve().parents[1] / "src" / "tessera" / "services"


def _diff(chemin: str, debut: int, lignes: list[str]) -> str:
    return (
        f"diff --git a/{chemin} b/{chemin}\n--- a/{chemin}\n+++ b/{chemin}\n"
        f"@@ -{debut},0 +{debut},{len(lignes)} @@\n" + "\n".join(lignes) + "\n"
    )


class _Git(GitWorkspaceDouble):
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def commit_all(self, message: str) -> str:
        self.messages.append(message)
        return "abc1234"


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    def __init__(self, projet: Path | None = None) -> None:
        self._git_workspace = _Git()
        self._ticket_svc = _Tickets()
        self._project_path = projet
        self._worktree = None
        self._max_review_rounds = 3
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(diff: str, events: list[OrchestratorEvent] | None = None) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        if events is not None:
            events.append(event)

    run = PipelineRun(
        project_id="proj",
        ticket=Ticket(
            id="ticket-736", title="T", type=TicketType.feat,
            status=TicketStatus.in_progress, priority=TicketPriority.medium,
            agent="codeur", body="",
        ),
        on_event=_on_event,
    )
    run.branch = "ticket-736-x"
    run.round_num = 1
    run.reviewed_code = diff
    return run


@pytest.mark.parametrize(
    ("chemin", "debut", "lignes"),
    [
        ("memory/lecons.md", 6, ["+- Quand a, b."]),  # sous « En vigueur »
        ("memory/lecons.md", 3, ["+- Quand a, b. (source : ticket-1, 2026-11-05)"]),  # « Proposées »
        ("memory/lecons.md", 6, ["-- Quand a, b."]),  # une suppression
        ("projects/ide-core/memory/lecons.md", 6, ["+- Quand a, b."]),  # dépôt ancêtre
    ],
)
async def test_a_diff_touching_the_lessons_file_blocks_the_run(
    chemin: str, debut: int, lignes: list[str]
) -> None:
    events: list[OrchestratorEvent] = []
    orch = _Orch()
    run = _run(_diff(chemin, debut, lignes), events)

    resultat = await arret_lecons_modifiees(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert "unapproved" in orch._git_workspace.messages[0]
    assert orch._ticket_svc.statut is TicketStatus.blocked
    raisons = [e.data.get("reason") for e in events if e.type is EventType.ERROR]
    assert "lessons_file_modified" in raisons
    assert any("BLOCKED" in ligne and "lecons.md" in ligne for ligne in orch.logs)


async def test_the_coder_turn_check_also_stops_on_the_lessons_file() -> None:
    orch = _Orch()
    run = _run(_diff("memory/lecons.md", 6, ["+- Quand a, b."]))

    resultat = await arret_contraintes_hors_proposees(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert "lecons.md" in (resultat.arret or "")


async def test_a_diff_that_leaves_the_lessons_file_alone_goes_on() -> None:
    orch = _Orch()
    run = _run(_diff("memory/decisions.md", 3, ["+## ADR-099"]))

    assert await arret_lecons_modifiees(orch, run) is None  # type: ignore[arg-type]
    assert await arret_contraintes_hors_proposees(orch, run) is None  # type: ignore[arg-type]
    assert orch.logs == []


def test_lignes_de_lecons_marks_a_file_touched_without_a_line() -> None:
    diff = "diff --git a/memory/lecons.md b/memory/lecons.md\nnew file mode 100644\n"
    assert lignes_de_lecons(diff) == ["memory/lecons.md (fichier touché)"]


async def test_a_lesson_added_by_the_service_after_the_coder_turn_does_not_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, True)
    monkeypatch.setattr(
        lecons_run, "_fournisseur", lambda *a, **k: _Fournisseur(_reponse(LECON, PREUVE))
    )
    orch = _Orch(projet)
    # Le diff relu à la fin du tour du codeur ne contient pas la leçon…
    run = _run(_diff("src/x.py", 1, ["+x = 1"]))
    run.review_feedback = [RETOUR]
    assert await arret_lecons_modifiees(orch, run) is None  # type: ignore[arg-type]

    # … que le service écrit ensuite : le fichier existe, et le run n'est pas arrêté.
    assert await proposer_lecon(orch, run) is True  # type: ignore[arg-type]
    assert lire_lecons(projet / "memory").proposees
    assert await arret_lecons_modifiees(orch, run) is None  # type: ignore[arg-type]


def test_the_lessons_check_runs_before_the_service_writes_its_lesson() -> None:
    # Le garde est au tour du codeur ; la leçon s'écrit à l'approbation.
    orchestrateur = (_SERVICES / "pipeline" / "orchestrator.py").read_text(encoding="utf-8")
    tour = orchestrateur.index("async def _produire_et_tester")
    assert "arret_contraintes_hors_proposees(self, run)" in orchestrateur[tour:]
    # `_run_pipeline` produit (donc garde) avant d'approuver.
    assert orchestrateur.index("self._produire_et_tester(") < orchestrateur.index(
        "outcomes.finish_approved(self, run)"
    )

    approuve = (_SERVICES / "pipeline" / "pipeline_outcomes.py").read_text(encoding="utf-8")
    assert "proposer_lecon(orch, run)" in approuve[approuve.index("async def finish_approved") :]

