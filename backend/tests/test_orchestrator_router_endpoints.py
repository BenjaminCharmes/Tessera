"""Endpoints du router orchestrateur — ticket-053."""
import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import init_db
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Fixture *synchrone* : `init_db` tourne dans sa propre boucle, close et
    # drainée avant que celle du test n'existe. Avec une fixture `async`, le
    # thread interne d'aiosqlite survit parfois à la fermeture de la boucle du
    # test précédent, et la suite complète se termine sur un
    # « RuntimeError: Event loop is closed ».
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n\nTest.\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "tickets" / "todo" / "ticket-001.md").write_text(
        "---\n"
        "id: ticket-001\n"
        'title: "Un ticket"\n'
        "type: feat\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n# ticket-001\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))

    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def _approved(ticket_id: str = "ticket-001") -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch=f"{ticket_id}-slug",
        commit_sha="abc1234",
    )


class _FakeOrchestrator:
    """Orchestrateur doublé : émet quelques événements puis approuve."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        self.calls.append((project_id, ticket_id))
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.BRANCH_CREATED, ticket_id=ticket_id,
                              data={"branch": f"{ticket_id}-slug"})
        )
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id=ticket_id,
                              data={"approved": True, "rounds": 1})
        )
        return _approved(ticket_id)

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5, on_event: object = None
    ) -> list[PipelineResult]:
        self.calls.append((project_id, f"autonomous:{max_tickets}"))
        if on_event is not None:
            # Le vrai orchestrateur relaie ses événements : les émettre permet
            # au test de se synchroniser sur la fin du traitement au lieu de
            # fermer la socket en plein vol.
            await on_event(  # type: ignore[operator]
                OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id="ticket-001",
                                  data={"approved": True, "rounds": 1})
            )
        return [_approved()]


# ------------------------------------------------------------------
# POST /orchestrator/run
# ------------------------------------------------------------------


def test_run_sur_un_projet_inexistant_renvoie_404() -> None:
    resp = _client().post(
        "/api/v1/orchestrator/run",
        json={"project_id": "jamais-vu", "ticket_id": "ticket-001"},
    )
    assert resp.status_code == 404


def test_run_sans_ticket_id_est_refuse() -> None:
    resp = _client().post("/api/v1/orchestrator/run", json={"project_id": "mon-projet"})
    assert resp.status_code == 422


def test_run_renvoie_le_resultat_du_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/orchestrator/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is True
    assert body["branch"] == "ticket-001-slug"
    assert body["commit_sha"] == "abc1234"
    assert fake.calls == [("mon-projet", "ticket-001")]


# ------------------------------------------------------------------
# POST /orchestrator/run-autonomous
# ------------------------------------------------------------------


def test_run_autonome_transmet_max_tickets(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/orchestrator/run-autonomous",
        json={"project_id": "mon-projet", "max_tickets": 3},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert fake.calls == [("mon-projet", "autonomous:3")]


# ------------------------------------------------------------------
# WS /orchestrator/stream/{project_id}
# ------------------------------------------------------------------


def test_stream_sans_ticket_ni_mode_renvoie_une_erreur_explicite() -> None:
    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({})
        assert "ticket_id" in ws.receive_json()["error"]


def test_stream_diffuse_les_evenements_du_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})

        first = ws.receive_json()
        second = ws.receive_json()

    assert first["type"] == "branch_created"
    assert second["type"] == "pipeline_done"
    assert second["data"]["approved"] is True


def test_stream_en_mode_autonome(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"mode": "autonomous", "max_tickets": 2})
        assert ws.receive_json()["type"] == "pipeline_done"

    assert fake.calls == [("mon-projet", "autonomous:2")]


# ------------------------------------------------------------------
# Dialogue pendant un run — ticket-066
# ------------------------------------------------------------------


class _OrchestrateurQuiDemande:
    """Orchestrateur double : pose une question, puis rend ce qu'on lui repond."""

    def __init__(self) -> None:
        self.reponse: str | None = None
        self.contexte_utilisateur: list[str] = []

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        assert dialogue is not None, "le run doit recevoir un canal de dialogue"
        self.reponse = await dialogue.ask("On casse l'API ?")  # type: ignore[attr-defined]
        self.contexte_utilisateur = dialogue.drain()  # type: ignore[attr-defined]
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id=ticket_id,
                              data={"approved": True, "rounds": 1})
        )
        return _approved(ticket_id)


def test_le_stream_transmet_la_reponse_de_l_utilisateur_a_l_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Panne de conception : la socket ne lisait qu'un seul message entrant, la
    # commande de demarrage, puis n'emettait plus. Impossible de repondre a un
    # agent qui bloque.
    fake = _OrchestrateurQuiDemande()

    async def _build(project_id: str) -> _OrchestrateurQuiDemande:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})

        question = ws.receive_json()
        assert question["type"] == "agent_question"
        assert question["data"]["question"] == "On casse l'API ?"

        ws.send_json({"type": "answer", "text": "non, on ajoute un champ"})
        assert ws.receive_json()["type"] == "pipeline_done"

    assert fake.reponse == "non, on ajoute un champ"


def test_le_stream_transmet_un_message_spontane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Un message spontane ne doit pas etre pris pour la reponse a la question
    # en cours : il attend le tour d'agent suivant.
    fake = _OrchestrateurQuiDemande()

    async def _build(project_id: str) -> _OrchestrateurQuiDemande:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})
        assert ws.receive_json()["type"] == "agent_question"

        ws.send_json({"type": "interject", "text": "pense aux tests"})
        ws.send_json({"type": "answer", "text": "non"})
        assert ws.receive_json()["type"] == "pipeline_done"

    assert fake.reponse == "non"
    assert fake.contexte_utilisateur == ["pense aux tests"]


def test_un_run_interrompu_est_clos_en_base(monkeypatch: pytest.MonkeyPatch) -> None:
    # Panne vecue : `finish_run` n'etait appele que sur le chemin nominal. Une
    # socket fermee ou une exception laissait la ligne ouverte, et l'historique
    # affichait « en cours » pour toujours (ticket-079).
    class _OrchestrateurQuiEchoue:
        async def run_pipeline(
            self, project_id, ticket_id, on_event, run_id=None, dialogue=None,
        ):
            raise ValueError("panne pendant le run")

    async def _build(project_id: str) -> _OrchestrateurQuiEchoue:
        return _OrchestrateurQuiEchoue()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    try:
        with _client().websocket_connect(
            "/api/v1/orchestrator/stream/mon-projet"
        ) as ws:
            ws.send_json({"ticket_id": "ticket-001"})
            ws.receive_json()
    except Exception:  # la socket se ferme apres l'erreur, c'est attendu
        pass

    # Le serveur finit d'écrire après la fermeture de la socket : on laisse
    # à `finish_run` le temps d'atterrir plutôt que de courir contre lui.
    for _ in range(50):
        if asyncio.run(_runs_ouverts()) == 0:
            break
        time.sleep(0.05)

    assert asyncio.run(_runs_ouverts()) == 0, "aucun run ne doit rester ouvert"


async def _runs_ouverts() -> int:
    import aiosqlite

    async with aiosqlite.connect(str(settings.ide_db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE finished_at IS NULL"
        ) as cursor:
            row = await cursor.fetchone()
    return int(row[0]) if row else 0


# ------------------------------------------------------------------
# La livraison suit le run — ticket-083, ticket-084
# ------------------------------------------------------------------
#
# Le routeur **fabrique** la livraison ; c'est l'orchestrateur qui l'appelle,
# après chaque run approuvé et quel que soit le mode (voir
# `test_orchestrator_livraison.py`). Ce qui se teste ici est donc la fabrique :
# ce qu'elle passe au service, et ce qu'elle fait d'une panne.


def test_le_livreur_passe_le_titre_et_le_corps_du_ticket(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le corps de la PR se rédige depuis le ticket : passer son identifiant en
    # guise de titre donnait une PR nommée « ticket-001 — ticket-001 ».
    from tessera.routers.orchestrator import _livreur
    from tessera.services.livraison import Livraison

    recu: dict[str, object] = {}

    async def _livrer(self: object, **kwargs: object) -> Livraison:
        recu.update(kwargs)
        return Livraison(pr_number=7)

    monkeypatch.setattr("tessera.services.livraison.LivraisonService.livrer", _livrer)

    livraison = asyncio.run(_livreur("mon-projet")(_approved()))

    assert livraison.pr_number == 7
    assert recu["ticket_title"] == "Un ticket"
    assert recu["branch"] == "ticket-001-slug"
    assert recu["approuve"] is True


def test_une_livraison_qui_leve_ne_fait_pas_echouer_le_run(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le travail est commité : perdre la réponse du run parce que GitHub est
    # injoignable ferait croire que le pipeline lui-même a échoué.
    from tessera.routers.orchestrator import _livreur

    async def _livrer(self: object, **kwargs: object) -> object:
        raise RuntimeError("GitHub injoignable")

    monkeypatch.setattr("tessera.services.livraison.LivraisonService.livrer", _livrer)

    livraison = asyncio.run(_livreur("mon-projet")(_approved()))

    assert livraison.merged is False
    assert "injoignable" in (livraison.arret or "")


def test_un_run_autonome_peut_partir_des_issues_github(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le dernier maillon : écrire une issue sur GitHub et ne plus toucher à
    # l'IDE. Le pull existait, mais restait un bouton à part.
    import json

    (workspace / "mon-projet" / "agents.json").write_text(
        json.dumps({"github_remote": "owner/repo"}), encoding="utf-8"
    )
    monkeypatch.setattr(settings, "github_token", "ghp_test")

    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    tires: list[str] = []

    async def _run(self: object, direction: str = "pull") -> object:
        tires.append(direction)

        class _R:
            pulled, pushed, skipped = 2, 0, 0

        return _R()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)
    monkeypatch.setattr("tessera.agents.github_sync.GithubSyncAgent.run", _run)

    resp = _client().post(
        "/api/v1/orchestrator/run-autonomous",
        json={"project_id": "mon-projet", "depuis_github": True},
    )

    assert resp.status_code == 200
    assert tires == ["pull"]
    assert ("mon-projet", "autonomous:5") in fake.calls


def test_un_run_autonome_ne_touche_pas_a_github_sans_le_demander(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Un appel réseau qui part sans qu'on l'ait demandé, sur le dépôt d'un
    # client, n'est pas une commodité.
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    tires: list[str] = []

    async def _run(self: object, direction: str = "pull") -> object:
        tires.append(direction)
        raise AssertionError("github-sync ne doit pas tourner ici")

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)
    monkeypatch.setattr("tessera.agents.github_sync.GithubSyncAgent.run", _run)

    resp = _client().post(
        "/api/v1/orchestrator/run-autonomous", json={"project_id": "mon-projet"}
    )

    assert resp.status_code == 200
    assert tires == []


def test_run_interrompu_clot_le_run_et_ne_renvoie_pas_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interrupted run answers 200 with a non-approved result, and its DB
    record is closed.

    Reproduces the ticket-101 run: the pipeline raised mid-turn, the exception
    reached FastAPI, and `finish_run` was never called — the run stayed
    `finished_at` null and showed as forever in progress. The pipeline now
    returns a result, so the endpoint closes the record like any other run.
    """

    class _InterruptedOrchestrator:
        async def run_pipeline(
            self, project_id: str, ticket_id: str, on_event: object, **kwargs: object
        ) -> PipelineResult:
            return PipelineResult(
                ticket_id=ticket_id,
                final_status=TicketStatus.blocked,
                rounds=1,
                approved=False,
                branch="ticket-001-slug",
                commit_sha="abc1234",
                arret="RuntimeError: Reached maximum budget ($1)",
            )

    async def _build(project_id: str) -> _InterruptedOrchestrator:
        return _InterruptedOrchestrator()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/orchestrator/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is False
    # La cause doit être lisible dans la réponse : dans les logs du backend,
    # l'utilisateur de l'IDE ne va pas la chercher.
    assert "budget" in body["arret"]

    runs = asyncio.run(_lister_runs())
    assert len(runs) == 1
    assert runs[0]["finished_at"] is not None
    assert runs[0]["approved"] is False


async def _lister_runs() -> list[dict[str, object]]:
    from tessera.services.database import list_runs

    return await list_runs(settings.ide_db_path, "mon-projet")
