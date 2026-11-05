"""A project review is a `design` run that writes only tickets/** and memory/** — ticket-864, ADR-080."""
import asyncio
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tessera import reglages
from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import Ticket, TicketStatus, TicketType
from tessera.services.noyau.database import init_db
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline.pipeline_contraintes import arret_contraintes_hors_proposees
from tessera.services.pipeline.revue_projet import (
    MAX_SIGNALEMENTS,
    MAX_TICKETS_CREES,
    PLAFOND_REVUE_USD,
    fichiers_hors_perimetre,
    ouvrir_revue,
    plafond_de_revue,
    raison_de_revue,
    ticket_de_revue,
    tickets_crees,
)
from tessera.services.pipeline.run_registry import RUN_REGISTRY
from tessera.services.pipeline.signaler_du_run import signaler_for
from tessera.services.projets.ticket_service import TicketService
from tests.test_lecons_gardees import _Orch as _OrchBase
from tests.test_lecons_gardees import _run
from tests.test_signaler import _make_ticket

PROJET = "mon-projet"


def _nouveau(chemin: str) -> str:
    return (
        f"diff --git a/{chemin} b/{chemin}\nnew file mode 100644\n--- /dev/null\n+++ b/{chemin}\n"
        "@@ -0,0 +1,1 @@\n+x\n"
    )


def _modifie(chemin: str) -> str:
    return f"diff --git a/{chemin} b/{chemin}\n--- a/{chemin}\n+++ b/{chemin}\n@@ -1 +1 @@\n-a\n+b\n"


@contextmanager
def _run_de_revue(projet: str = "proj", mode: str = "revue") -> Iterator[None]:
    """Hold `projet` in the registry the way the route does for a review."""
    run = RUN_REGISTRY.ouvrir(projet, "ticket-864", mode=mode)
    try:
        yield
    finally:
        RUN_REGISTRY.fermer(run.run_id)


# ------------------------------------------------------------------
# POST /orchestrator/run, mode « revue »
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _etat_propre() -> Iterator[None]:
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)
    yield
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / PROJET
    (projet / "memory").mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n\nTest.\n", encoding="utf-8")
    for statut in ("todo", "in-progress", "in-review", "done", "blocked"):
        (projet / "tickets" / statut).mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-premier.md").write_text(
        "---\nid: ticket-001\ntitle: Premier\ntype: feat\nstatus: done\npriority: medium\n"
        "agent: codeur\n---\n\n# ticket-001\n",
        encoding="utf-8",
    )
    base = tmp_path / "tessera.db"
    asyncio.run(init_db(base))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", base)
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


class _OrchestrateurDouble:
    """Records what the route hands to a review run, and ends it approved."""

    def __init__(self) -> None:
        self.fiches: list[Ticket] = []
        self._run_max_budget_usd = 9.0
        self._ticket_svc = self
        self.appels: list[tuple[str, str]] = []

    async def create_ticket(self, fiche: Ticket) -> Ticket:
        """The summary ticket, as the run's own ticket service receives it."""
        self.fiches.append(fiche)
        return fiche

    async def run_pipeline(
        self, project_id: str, ticket_id: str, on_event: Any, **_: Any
    ) -> PipelineResult:
        self.appels.append((project_id, ticket_id))
        await on_event(OrchestratorEvent(
            type=EventType.PIPELINE_DONE, ticket_id=ticket_id, data={"approved": True, "rounds": 1}
        ))
        return PipelineResult(
            ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1, approved=True,
            branch=f"{ticket_id}-x", commit_sha="abc1234",
        )


def _poser_le_double(monkeypatch: pytest.MonkeyPatch) -> _OrchestrateurDouble:
    double = _OrchestrateurDouble()

    async def _construire(project_id: str, *_: Any, **__: Any) -> _OrchestrateurDouble:
        return double

    monkeypatch.setattr("tessera.routers.orchestrator.build_orchestrator", _construire)
    return double


def _attendre_la_fin(ws: Any) -> None:
    for _ in range(60):
        if ws.receive_json().get("type") == "run_closed":
            return
    raise AssertionError("run_closed jamais reçu")


def test_review_run_creates_a_design_ticket_with_a_reserved_number(
    workspace: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    double = _poser_le_double(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        premiere = client.post("/api/v1/orchestrator/run", json={"project_id": PROJET, "mode": "revue"})
        _attendre_la_fin(ws)
        seconde = client.post("/api/v1/orchestrator/run", json={"project_id": PROJET, "mode": "revue"})
        _attendre_la_fin(ws)

    assert premiere.status_code == 202, premiere.text
    assert premiere.json()["ticket_id"] == "ticket-002"
    fiche = double.fiches[0]
    assert (fiche.id, fiche.type, fiche.agent) == ("ticket-002", TicketType.design, "architect")
    assert fiche.title == f"Revue de {PROJET}"
    assert "sans rien implémenter" in fiche.body
    assert double.appels[0] == (PROJET, "ticket-002")
    # Le numéro est pris à l'appel : la fiche n'ayant jamais été écrite sur le disque
    # (le double ne l'écrit pas), la revue suivante ne le reprend pas.
    assert seconde.json()["ticket_id"] == "ticket-003"


async def test_the_summary_ticket_is_written_in_the_run_root(tmp_path: Path) -> None:
    (tmp_path / "tickets").mkdir()
    orch = SimpleNamespace(_ticket_svc=TicketService(tmp_path, PROJET), _run_max_budget_usd=9.0)

    await ouvrir_revue(orch, ticket_de_revue(PROJET, 12), 2.0)  # type: ignore[arg-type]

    assert list((tmp_path / "tickets" / "todo").glob("ticket-012-*.md"))
    assert orch._run_max_budget_usd == 2.0


# ------------------------------------------------------------------
# Les bornes du diff
# ------------------------------------------------------------------


async def test_file_outside_tickets_and_memory_blocks_the_run() -> None:
    events: list[OrchestratorEvent] = []
    orch = _OrchBase()
    run = _run(_modifie("memory/decisions.md") + _modifie("src/app.py"), events)

    with _run_de_revue():
        resultat = await arret_contraintes_hors_proposees(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert resultat.final_status is TicketStatus.blocked and resultat.approved is False
    assert "unapproved" in orch._git_workspace.messages[0]
    assert "src/app.py" in (resultat.arret or "")
    assert [e.data.get("reason") for e in events if e.type is EventType.ERROR] == ["review_outside_scope"]


async def test_a_review_that_stays_in_its_scope_goes_on() -> None:
    orch = _OrchBase()
    diff = _nouveau("tickets/todo/ticket-900-a.md") + _modifie("memory/pipeline-log.md")

    with _run_de_revue():
        assert await arret_contraintes_hors_proposees(orch, _run(diff)) is None  # type: ignore[arg-type]


async def test_an_ordinary_run_is_never_stopped_by_the_review_guard() -> None:
    with _run_de_revue(mode="single"):
        assert await arret_contraintes_hors_proposees(_OrchBase(), _run(_modifie("src/app.py"))) is None  # type: ignore[arg-type]


def test_the_project_folder_inside_the_repository_is_not_outside() -> None:
    diff = _nouveau("projects/p/tickets/todo/ticket-9-a.md") + _modifie("projects/p/backend/x.py")
    assert fichiers_hors_perimetre(diff, "projects/p/") == ["projects/p/backend/x.py"]


async def test_eleventh_ticket_blocks_delivery() -> None:
    dix = "".join(_nouveau(f"tickets/todo/ticket-{900 + i}-a.md") for i in range(MAX_TICKETS_CREES))
    onze = dix + _nouveau("tickets/todo/ticket-910-a.md")
    assert raison_de_revue(dix, "ticket-899") is None

    orch = _OrchBase()
    with _run_de_revue():
        resultat = await arret_contraintes_hors_proposees(orch, _run(onze))  # type: ignore[arg-type]

    # Non approuvé : ni push ni PR, le run garde son commit (ADR-018, ADR-030).
    assert resultat is not None and resultat.approved is False
    assert resultat.final_status is TicketStatus.blocked
    assert "11 tickets" in (resultat.arret or "")


def test_the_summary_ticket_moving_between_folders_is_not_a_proposal() -> None:
    diff = "".join(_nouveau(f"tickets/todo/ticket-{900 + i}-a.md") for i in range(MAX_TICKETS_CREES))
    diff += _nouveau("tickets/in-review/ticket-899-revue-de-p.md")
    assert tickets_crees(diff, "ticket-899") == {900 + i for i in range(MAX_TICKETS_CREES)}
    assert raison_de_revue(diff, "ticket-899") is None


# ------------------------------------------------------------------
# Plafond de dépense
# ------------------------------------------------------------------


def test_spending_cap_is_the_smaller_of_three_dollars_and_the_run_cap(
    workspace: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert plafond_de_revue(10.0) == PLAFOND_REVUE_USD == 3.0
    assert plafond_de_revue(1.5) == 1.5
    assert plafond_de_revue(0.0) == 3.0  # « sans plafond » de run : la revue garde ses 3 $

    double = _poser_le_double(monkeypatch)
    # Plafond de run baissé avant l'ouverture : c'est celui que le run fige.
    monkeypatch.setitem(reglages._SURCHARGES, "run_max_budget_usd", 1.5)
    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        reponse = client.post("/api/v1/orchestrator/run", json={"project_id": PROJET, "mode": "revue"})
        _attendre_la_fin(ws)

    corps = reponse.json()
    assert double._run_max_budget_usd == 1.5
    # Le coût estimé est rendu avant le lancement (ADR-020).
    assert (corps["plafond_usd"], corps["cout_estime_usd"]) == (1.5, 1.5)


# ------------------------------------------------------------------
# Signalements et verrou
# ------------------------------------------------------------------


def _contexte(chemin: Path, confidentialite: str, *, revue: bool) -> Any:
    from tessera.services.pipeline.pipeline_run import PipelineRun

    async def _rien(_e: object) -> None:
        return None

    (chemin / "agents.json").write_text(json.dumps({"confidentiality": confidentialite}), encoding="utf-8")
    run = PipelineRun(project_id=PROJET, ticket=_make_ticket(id="ticket-864"), on_event=_rien)
    orch = SimpleNamespace(_project_path=chemin)
    with _run_de_revue(PROJET, "revue" if revue else "single"):
        return signaler_for(orch, run)  # type: ignore[arg-type]


def test_professional_project_review_emits_no_report(tmp_path: Path) -> None:
    assert _contexte(tmp_path, "professional", revue=True) is None


def test_a_personal_review_may_report_five_times_and_an_ordinary_run_three(tmp_path: Path) -> None:
    assert _contexte(tmp_path, "personal", revue=True).max_par_run == MAX_SIGNALEMENTS == 5
    assert _contexte(tmp_path, "personal", revue=False).max_par_run == 3
    # Un run ordinaire d'un projet professionnel garde l'outil, par énumérations seules.
    assert _contexte(tmp_path, "professional", revue=False) is not None


def test_review_takes_the_project_lock(
    workspace: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _poser_le_double(monkeypatch)
    occupant = RUN_REGISTRY.ouvrir(PROJET, "ticket-001")
    try:
        occupe = client.post("/api/v1/orchestrator/run", json={"project_id": PROJET, "mode": "revue"})
    finally:
        RUN_REGISTRY.fermer(occupant.run_id)

    assert occupe.status_code == 409
    # Le projet occupé a répondu avant toute réservation : le numéro 2 est encore libre.
    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        libre = client.post("/api/v1/orchestrator/run", json={"project_id": PROJET, "mode": "revue"})
        _attendre_la_fin(ws)
    assert libre.json()["ticket_id"] == "ticket-002"
    assert RUN_REGISTRY.projet_occupe(PROJET) is False
