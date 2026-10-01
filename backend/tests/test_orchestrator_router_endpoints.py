"""Endpoints du router orchestrateur — ticket-053."""
import asyncio
import time
from collections.abc import Iterator
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


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client whose loop outlives each request — ticket-128.

    Le run est porte par une tache asyncio : sans portail persistant, elle
    est tuee des que le POST repond, et le run n'existe jamais.
    """
    with TestClient(app) as c:
        yield c


def _demarrer(client: TestClient, corps: dict) -> str:
    resp = client.post("/api/v1/orchestrator/run", json=corps)
    assert resp.status_code == 202, resp.text
    return str(resp.json()["run_id"])


def _attendre(ws: object, type_attendu: str, limite: int = 60) -> dict:
    for _ in range(limite):
        message = ws.receive_json()  # type: ignore[attr-defined]
        if message.get("type") == type_attendu:
            return dict(message)
    raise AssertionError(f"« {type_attendu} » jamais recu")


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


def test_run_demarre_le_pipeline_et_rend_son_resultat_sur_le_canal(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Depuis ticket-128 le POST ne porte plus le resultat : il demarre le run
    # et rend son identifiant. Le resultat arrive sur `/observe`, dans
    # `run_closed` — le seul evenement publie apres la liberation du projet.
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        run_id = _demarrer(
            client, {"project_id": "mon-projet", "ticket_id": "ticket-001"}
        )
        fin = _attendre(ws, "run_closed")

    assert fin["run_id"] == run_id
    assert fin["data"]["approved"] is True
    assert fin["data"]["branch"] == "ticket-001-slug"
    assert fin["data"]["commit_sha"] == "abc1234"
    assert fake.calls == [("mon-projet", "ticket-001")]


# ------------------------------------------------------------------
# POST /orchestrator/run-autonomous
# ------------------------------------------------------------------


def test_run_autonome_transmet_max_tickets(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # `/run-autonomous` a disparu : les trois modes passent par `/run`, sinon
    # il y aurait deux facons de lancer un run (ADR-034).
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        _demarrer(
            client,
            {"project_id": "mon-projet", "mode": "autonomous", "max_tickets": 3},
        )
        _attendre(ws, "run_closed")

    assert fake.calls == [("mon-projet", "autonomous:3")]


# ------------------------------------------------------------------
# WS /orchestrator/observe — ticket-128
# ------------------------------------------------------------------


def test_le_canal_diffuse_les_evenements_du_pipeline(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        _demarrer(client, {"project_id": "mon-projet", "ticket_id": "ticket-001"})

        assert _attendre(ws, "branch_created")["project_id"] == "mon-projet"
        fin = _attendre(ws, "pipeline_done")

    assert fin["data"]["approved"] is True


def test_le_canal_couvre_le_mode_autonome(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        _demarrer(
            client,
            {"project_id": "mon-projet", "mode": "autonomous", "max_tickets": 2},
        )
        _attendre(ws, "run_closed")

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


def test_le_canal_transmet_la_reponse_de_l_utilisateur_a_l_agent(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Panne de conception : la socket ne lisait qu'un seul message entrant, la
    # commande de demarrage, puis n'emettait plus. Impossible de repondre a un
    # agent qui bloque.
    fake = _OrchestrateurQuiDemande()

    async def _build(project_id: str) -> _OrchestrateurQuiDemande:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        run_id = _demarrer(
            client, {"project_id": "mon-projet", "ticket_id": "ticket-001"}
        )

        question = _attendre(ws, "agent_question")
        assert question["data"]["question"] == "On casse l'API ?"

        ws.send_json(
            {"type": "answer", "run_id": run_id, "text": "non, on ajoute un champ"}
        )
        _attendre(ws, "pipeline_done")

    assert fake.reponse == "non, on ajoute un champ"


def test_le_canal_transmet_un_message_spontane(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Un message spontane ne doit pas etre pris pour la reponse a la question
    # en cours : il attend le tour d'agent suivant.
    fake = _OrchestrateurQuiDemande()

    async def _build(project_id: str) -> _OrchestrateurQuiDemande:
        return fake

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        run_id = _demarrer(
            client, {"project_id": "mon-projet", "ticket_id": "ticket-001"}
        )
        _attendre(ws, "agent_question")

        ws.send_json(
            {"type": "interject", "run_id": run_id, "text": "pense aux tests"}
        )
        ws.send_json({"type": "answer", "run_id": run_id, "text": "non"})
        _attendre(ws, "pipeline_done")

    assert fake.reponse == "non"
    assert fake.contexte_utilisateur == ["pense aux tests"]


def _client_persistant() -> TestClient:
    return TestClient(app)


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

    with _client_persistant() as client:
        with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
            _demarrer(client, {"project_id": "mon-projet", "ticket_id": "ticket-001"})
            _attendre(ws, "run_closed")

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


def _livrer_la_pr(numero: int) -> object:
    from tessera.services.livraison import Livraison

    async def _livrer(self: object, **kwargs: object) -> Livraison:
        # Simule le comportement réel : livrer() appelle post_pr_callback avant
        # de retourner, ce que les tests de notation de PR vérifient (ticket-270).
        callback = getattr(self, "_post_pr_callback", None)
        if callback is not None:
            try:
                ticket_id = str(kwargs.get("ticket_id", ""))
                branch = str(kwargs.get("branch", ""))
                await callback(ticket_id, numero, branch)
            except Exception:  # noqa: BLE001
                pass
        return Livraison(pr_number=numero, merged=True)

    return _livrer


def test_le_livreur_note_la_pr_dans_le_ticket(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La livraison ouvrait et mergeait la PR sans jamais l'écrire : la carte
    # du ticket, qui lit `pr_number`, proposait d'en ouvrir une (ticket-205).
    from tessera.routers.orchestrator import _livreur

    monkeypatch.setattr(
        "tessera.services.livraison.LivraisonService.livrer", _livrer_la_pr(7)
    )

    asyncio.run(_livreur("mon-projet")(_approved()))

    fichier = workspace / "mon-projet" / "tickets" / "todo" / "ticket-001.md"
    assert "pr_number: 7" in fichier.read_text(encoding="utf-8")


def test_noter_la_pr_laisse_l_arbre_propre(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sur un projet dont les tickets sont versionnés, un ticket modifié après
    # coup enverrait le run suivant en `blocked` (ADR-018).
    import subprocess

    from tessera.routers.orchestrator import _livreur

    projet = workspace / "mon-projet"

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=projet, check=True, capture_output=True, text=True
        ).stdout

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    monkeypatch.setattr(
        "tessera.services.livraison.LivraisonService.livrer", _livrer_la_pr(7)
    )

    asyncio.run(_livreur("mon-projet")(_approved()))

    assert git("status", "--porcelain", "--untracked-files=no") == ""
    assert "pr_number: 7" in git("show", "HEAD:tickets/todo/ticket-001.md")


def test_noter_la_pr_avance_la_base_du_run(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # En file, chaque ticket part de la base mémorisée à l'approbation : sans
    # l'avancer, le commit du numéro disparaissait dès le ticket suivant.
    from tessera.routers.orchestrator import _livreur

    appels: list[str] = []

    class _Espace:
        async def commit_bookkeeping(self) -> None:
            appels.append("commit")

        async def push_branch(self, branch: str) -> None:
            appels.append("push")

        async def advance_base_ref(self) -> None:
            appels.append("avance")

        async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
            # ticket-264 : après un merge, la base locale se réaligne.
            appels.append("sync")
            return None

    monkeypatch.setattr(
        "tessera.services.livraison.LivraisonService.livrer", _livrer_la_pr(7)
    )

    asyncio.run(_livreur("mon-projet", espace=_Espace())(_approved()))  # type: ignore[arg-type]

    assert appels == ["commit", "push", "avance", "sync"]


def test_noter_la_pr_qui_echoue_ne_change_pas_la_livraison(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La PR est mergée : un ticket qu'on n'a pas pu réécrire ne fait pas
    # croire que la livraison a échoué (ADR-030).
    from tessera.routers.orchestrator import _livreur

    async def _leve(self: object, ticket_id: str, pr_number: int) -> object:
        raise OSError("disque plein")

    monkeypatch.setattr(
        "tessera.services.livraison.LivraisonService.livrer", _livrer_la_pr(7)
    )
    monkeypatch.setattr(
        "tessera.services.ticket_service.TicketService.set_pr_number", _leve
    )

    livraison = asyncio.run(_livreur("mon-projet")(_approved()))

    assert livraison.pr_number == 7
    assert livraison.merged is True
    assert livraison.arret is None


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

    with _client_persistant() as client:
        with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
            _demarrer(
                client,
                {
                    "project_id": "mon-projet",
                    "mode": "autonomous",
                    "depuis_github": True,
                },
            )
            _attendre(ws, "run_closed")

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

    with _client_persistant() as client:
        with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
            _demarrer(
                client, {"project_id": "mon-projet", "mode": "autonomous"}
            )
            _attendre(ws, "run_closed")

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

    with _client_persistant() as client:
        with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
            _demarrer(
                client, {"project_id": "mon-projet", "ticket_id": "ticket-001"}
            )
            fin = _attendre(ws, "run_closed")

    assert fin["data"]["approved"] is False
    # La cause doit rester lisible : dans les logs du backend, l'utilisateur
    # de l'IDE ne va pas la chercher. Depuis ticket-128 le POST ne rend plus
    # le resultat, c'est `run_closed` qui la porte (ADR-037).
    assert "budget" in fin["data"]["arret"]

    runs = asyncio.run(_lister_runs())
    assert len(runs) == 1
    assert runs[0]["finished_at"] is not None
    assert runs[0]["approved"] is False


async def _lister_runs() -> list[dict[str, object]]:
    from tessera.services.database import list_runs

    return await list_runs(settings.ide_db_path, "mon-projet")
