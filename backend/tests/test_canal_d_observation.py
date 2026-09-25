"""Launch by POST, observe on a shared channel — ticket-128.

Le run était lancé **par** sa WebSocket : il n'était donc observable que
depuis l'onglet qui l'avait ouverte. Recharger la page rendait aveugle
jusqu'à la fin, et répondre à un agent qui pose une question (ADR-025) était
impossible depuis ailleurs.

Ici le POST démarre et rend la main ; tout le monde observe sur `/observe`.
"""
import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import init_db
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for project_id in ("mon-projet", "autre-projet"):
        project = ws / project_id
        (project / "memory").mkdir(parents=True)
        (project / "CLAUDE.md").write_text(f"# {project_id}\n", encoding="utf-8")
        for status in ("todo", "in-progress", "in-review", "done", "blocked"):
            (project / "tickets" / status).mkdir(parents=True)
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    # Sans borne, une question jamais reçue bloque le test cinq minutes
    # (le défaut d'ADR-025) au lieu d'échouer tout de suite.
    monkeypatch.setattr(settings, "dialogue_timeout_s", 10.0)
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client whose event loop outlives each request.

    `TestClient(app)` sans `with` ouvre un portail par requête et le referme
    avec elle : la tâche asyncio qui porte le run était tuée dès la réponse
    du POST, et le run n'existait que le temps de la requête. C'est le
    découplage lui-même que ce détail met en défaut.
    """
    with TestClient(app) as c:
        yield c


def _approved(ticket_id: str) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
    )


class _OrchestrateurQuiAttend:
    """Suspends on a question: the run stays live until someone answers."""

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(
                type=EventType.AGENT_TOKEN, ticket_id=ticket_id, data={"text": "hop"}
            )
        )
        if dialogue is not None:
            await dialogue.ask("on continue ?")  # type: ignore[attr-defined]
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(
                type=EventType.PIPELINE_DONE,
                ticket_id=ticket_id,
                data={"approved": True, "rounds": 1},
            )
        )
        return _approved(ticket_id)

    async def run_queue(
        self,
        project_id: str,
        ticket_ids: list[str],
        on_event: object = None,
        dialogue: object = None,
    ) -> list[PipelineResult]:
        return [_approved(t) for t in ticket_ids]

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5, on_event: object = None
    ) -> list[PipelineResult]:
        return [_approved("ticket-001")]


def _brancher(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _build(project_id: str) -> _OrchestrateurQuiAttend:
        return _OrchestrateurQuiAttend()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)


def _demarrer(client: TestClient, project_id: str, ticket_id: str) -> str:
    resp = client.post(
        "/api/v1/orchestrator/run",
        json={"project_id": project_id, "ticket_id": ticket_id},
    )
    assert resp.status_code == 202, resp.text
    return str(resp.json()["run_id"])


def _attendre(
    ws: object, type_attendu: str, run_id: str | None = None, limite: int = 40
) -> dict:
    """Read until the awaited event shows up, optionally for one run only.

    Le filtre par `run_id` n'est pas un confort : deux runs suspendus en même
    temps publient les mêmes types d'événements, et attendre « le prochain
    pipeline_done » attrape celui du voisin.
    """
    for _ in range(limite):
        message = ws.receive_json()  # type: ignore[attr-defined]
        if message.get("type") != type_attendu:
            continue
        if run_id is None or message.get("run_id") == run_id:
            return dict(message)
    raise AssertionError(f"« {type_attendu} » jamais reçu")


def _attendre_tous(ws: object, type_attendu: str, run_ids: list[str]) -> None:
    """Wait until every named run has emitted that event, in any order.

    Attendre run par run ne marche pas : si le second parle en premier, son
    événement est consommé par l'attente du premier, et l'attente suivante
    ne verra jamais rien.
    """
    restants = set(run_ids)
    for _ in range(40 * max(len(run_ids), 1)):
        message = ws.receive_json()  # type: ignore[attr-defined]
        if message.get("type") == type_attendu:
            restants.discard(str(message.get("run_id")))
        if not restants:
            return
    raise AssertionError(f"« {type_attendu} » manquant pour {restants}")


# --------------------------------------------------------------------------
# Le lancement
# --------------------------------------------------------------------------


def test_le_lancement_rend_un_run_id_sans_attendre_la_fin(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Tout le ticket tient là-dedans : le POST ne porte plus le run, il le
    # démarre. Sinon l'UI reste bloquée sur une requête de dix minutes.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        assert run_id
        question = _attendre(observateur, "agent_question")
        assert question["run_id"] == run_id
        observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        _attendre(observateur, "pipeline_done")


def test_un_second_run_sur_le_meme_projet_recoit_409(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # ADR-038 : deux runs sur le même arbre se marchent dessus. Le refus doit
    # nommer ce qui tourne — « attends » sans dire quoi n'aide personne.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        _attendre(observateur, "agent_question")

        refus = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "mon-projet", "ticket_id": "ticket-002"},
        )
        assert refus.status_code == 409
        assert "ticket-001" in refus.json()["detail"]

        observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        _attendre(observateur, "pipeline_done")


def test_deux_projets_tournent_ensemble(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Le parallélisme réel de Tessera, et ce que la supervision doit montrer.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        premier = _demarrer(client, "mon-projet", "ticket-001")
        second = _demarrer(client, "autre-projet", "ticket-009")
        assert premier != second

        _attendre_tous(observateur, "agent_question", [premier, second])
        for run_id in (premier, second):
            observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
            _attendre(observateur, "pipeline_done", run_id)


def test_l_ancienne_route_de_stream_n_existe_plus(client: TestClient) -> None:
    # Deux façons de lancer un run divergeraient (ADR-034). La WebSocket de
    # lancement n'a plus de raison d'être une fois `/observe` en place.
    #
    # Test de comportement et non d'inventaire : `app` est enveloppée par le
    # middleware d'authentification (ticket-120), donc `app.routes` ne liste
    # pas les routes des routeurs — une version structurelle de ce test
    # passait au vert alors que la route existait toujours.
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/api/v1/orchestrator/stream/mon-projet"
        ) as ws:
            ws.send_json({"ticket_id": "ticket-001"})
            ws.receive_json()


# --------------------------------------------------------------------------
# Le canal d'observation
# --------------------------------------------------------------------------


def test_un_observateur_recoit_l_instantane_a_la_connexion(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Quelqu'un qui ouvre l'IDE alors qu'un run tourne doit le voir. Sans
    # instantané, il attendrait le prochain événement pour apprendre son
    # existence.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as premier:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        _attendre(premier, "agent_question")

        with client.websocket_connect("/api/v1/orchestrator/observe") as second:
            instantane = second.receive_json()
            assert instantane["type"] == "snapshot"
            runs = instantane["runs"]
            assert [run["project_id"] for run in runs] == ["mon-projet"]
            assert runs[0]["run_id"] == run_id

        premier.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        _attendre(premier, "pipeline_done")


def test_les_tokens_n_arrivent_qu_apres_abonnement(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Le compromis du canal : tout est disponible, on ne paie que ce qu'on
    # regarde. Un observateur non abonné ne doit voir aucun token.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        question = _attendre(observateur, "agent_question")
        assert question["type"] == "agent_question"

        observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        fin = _attendre(observateur, "pipeline_done")
        assert fin["run_id"] == run_id


def test_un_abonne_recoit_les_tokens_de_son_run(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # L'autre moitié du compromis : cliquer sur un run donne bien son texte.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        _attendre(observateur, "agent_question")
        observateur.send_json({"subscribe": run_id})
        observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})

        vus = []
        for _ in range(40):
            message = observateur.receive_json()
            vus.append(message.get("type"))
            if message.get("type") == "pipeline_done":
                break
        assert "pipeline_done" in vus


def test_une_reponse_atteint_le_run_qu_elle_nomme(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Deux runs suspendus en même temps : une réponse adressée au mauvais
    # canal débloquerait le mauvais agent, avec le mauvais texte.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        premier = _demarrer(client, "mon-projet", "ticket-001")
        second = _demarrer(client, "autre-projet", "ticket-009")

        # Attendre la question de chacun : répondre avant qu'un run ait posé
        # son canal de dialogue laisserait la réponse sans destinataire, et
        # l'agent reprendrait sur une hypothèse (ADR-025) — le test passerait
        # en testant autre chose.
        _attendre_tous(observateur, "agent_question", [premier, second])

        observateur.send_json({"type": "answer", "run_id": second, "text": "oui"})
        fin = _attendre(observateur, "pipeline_done", second)
        assert fin["run_id"] == second

        observateur.send_json({"type": "answer", "run_id": premier, "text": "oui"})
        _attendre(observateur, "pipeline_done", premier)


def test_le_run_se_poursuit_sans_observateur(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Le découplage lui-même : fermer l'onglet ne doit plus rien interrompre.
    # Avant, l'émetteur écrivait sur la socket qui portait le run.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        run_id = _demarrer(client, "mon-projet", "ticket-001")
        _attendre(observateur, "agent_question")

    # Plus personne n'écoute ; le run doit malgré tout accepter sa réponse.
    with client.websocket_connect("/api/v1/orchestrator/observe") as repris:
        instantane = repris.receive_json()
        assert instantane["runs"][0]["run_id"] == run_id
        repris.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        _attendre(repris, "pipeline_done")
