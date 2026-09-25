"""Un run a la fois par projet, sur tous les points d'entree — ticket-121.

`RunLock` n'existait que pour `/chat/run`. Deux `POST /orchestrator/run` sur
le meme projet passaient `ensure_clean_tree`, puis le second `create_branch`
faisait un checkout sous le premier codeur.

Depuis ticket-128 le lancement se fait par POST et l'observation sur
`/orchestrator/observe` : ce fichier garde ce qui lui est propre — le verrou
lui-meme et son partage entre points d'entree. Le comportement du canal est
couvert par `test_canal_d_observation.py`.
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
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.run_lock import RUN_LOCK, RunAlreadyInProgress, RunLock


# ------------------------------------------------------------------
# Le verrou lui-meme
# ------------------------------------------------------------------


async def test_le_refus_nomme_le_ticket_en_cours() -> None:
    # Celui qui clique deux fois veut savoir ce qui tourne, pas seulement
    # qu'on lui dit non.
    lock = RunLock()
    async with lock.acquire("mon-projet", "ticket-007"):
        with pytest.raises(RunAlreadyInProgress) as exc:
            async with lock.acquire("mon-projet", "ticket-008"):
                pass
    assert "ticket-007" in str(exc.value)
    assert exc.value.ticket_id == "ticket-007"
    assert lock.ticket_en_cours("mon-projet") is None


async def test_un_verrou_construit_a_la_main_est_independant() -> None:
    # Depuis ticket-127 le verrou délègue à un registre. S'il retombait sur
    # le registre partagé, deux verrous censés être indépendants auraient le
    # même état : un run ouvert ailleurs bloquerait celui-ci sans raison.
    premier = RunLock()
    second = RunLock()
    async with premier.acquire("mon-projet", "ticket-007"):
        assert second.is_running("mon-projet") is False


async def test_le_verrou_est_partage_entre_les_routeurs() -> None:
    # Un verrou par module serait deux verrous : le chat et l'orchestrateur
    # doivent voir le meme etat.
    from tessera.routers import chat, orchestrator

    assert chat._RUN_LOCK is RUN_LOCK
    assert orchestrator.RUN_REGISTRY is RUN_LOCK._registry


# ------------------------------------------------------------------
# Les endpoints
# ------------------------------------------------------------------


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
    monkeypatch.setattr(settings, "dialogue_timeout_s", 10.0)
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Le portail doit survivre a la requete : c'est une tache asyncio qui
    # porte le run depuis ticket-128.
    with TestClient(app) as c:
        yield c


def _approved(ticket_id: str) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1, approved=True,
    )


class _OrchestrateurQuiAttend:
    """Se suspend sur une question : le run reste « en cours » tant qu'on ne repond pas."""

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        if dialogue is not None:
            await dialogue.ask("on continue ?")  # type: ignore[attr-defined]
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id=ticket_id,
                              data={"approved": True, "rounds": 1})
        )
        return _approved(ticket_id)

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5, on_event: object = None
    ) -> list[PipelineResult]:
        return [_approved("ticket-001")]


def _brancher(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _build(project_id: str) -> _OrchestrateurQuiAttend:
        return _OrchestrateurQuiAttend()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)


def _attendre(ws: object, type_attendu: str, limite: int = 40) -> dict:
    for _ in range(limite):
        message = ws.receive_json()  # type: ignore[attr-defined]
        if message.get("type") == type_attendu:
            return dict(message)
    raise AssertionError(f"« {type_attendu} » jamais recu")


def test_le_chat_refuse_de_lancer_sur_un_projet_deja_occupe(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # La valeur propre de ce fichier : deux **points d'entree differents**
    # partagent le verrou. Un run lance depuis le tableau doit bloquer le
    # chat, et pas seulement un second clic au meme endroit.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/orchestrator/observe") as observateur:
        demarrage = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
        )
        assert demarrage.status_code == 202
        run_id = demarrage.json()["run_id"]
        _attendre(observateur, "agent_question")

        refus = client.post(
            "/api/v1/projects/mon-projet/chat/run",
            json={"conversation_id": "c1", "ticket_id": "ticket-042"},
        )
        assert refus.status_code == 409
        assert "ticket-001" in refus.json()["detail"]

        observateur.send_json({"type": "answer", "run_id": run_id, "text": "oui"})
        _attendre(observateur, "pipeline_done")

    # Pas d'assertion sur la liberation ici : `pipeline_done` est publie par
    # l'orchestrateur, donc avant que l'executeur ne ferme l'entree. La
    # liberation elle-meme est verifiee sans course par
    # `test_un_run_termine_sort_de_l_instantane`.
