"""The anomaly detector watches live runs and reports each anomaly once — ticket-839 (ADR-078)."""
import ast
import asyncio
import json
import logging
import sqlite3
import subprocess
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.anomalies import detecteur as module_detecteur
from tessera.services.anomalies import lecture_evenements
from tessera.services.anomalies.detecteur import DetecteurDAnomalies
from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_registry import RunActif, RunRegistry
from tests.anomalies_base import appel_d_agent, evenement, ligne_de_run

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
LOGGER = "tessera.services.anomalies.detecteur"


def _iso(secondes_avant: float) -> str:
    return (NOW - timedelta(seconds=secondes_avant)).isoformat()


class Monde:
    """A registry with one live run on a real (empty) database, and a detector over it."""

    def __init__(self) -> None:
        self.db = settings.ide_db_path
        self.registre = RunRegistry()
        self.hub = EventHub()
        self.abonnement = self.hub.subscribe()
        self.maintenant = NOW
        self.detecteur = DetecteurDAnomalies(
            self.registre, self.hub, self.db, settings, horloge=lambda: self.maintenant
        )
        self.run: RunActif

    async def ouvrir(
        self, run_id: str = "r1", ticket: str | None = "ticket-001", mode: str = "single",
        projet: str = "p",
    ) -> RunActif:
        await ligne_de_run(self.db, run_id, project_id=projet, mode=mode,
                           ticket_id=ticket or mode, started_at=_iso(3600))
        run = self.registre.ouvrir(projet, ticket, mode=mode, run_id=run_id)
        run.db_run_id = run_id
        run.dernier_evenement_a = NOW
        self.run = run
        return run

    def evenements(self) -> list[OrchestratorEvent]:
        return [e for e in self.abonnement.vider() if e.type is EventType.RUN_ANOMALY]


@pytest.fixture
def monde() -> Monde:
    return Monde()


# -- les six scénarios, un par règle ----------------------------------------


async def _outil_repete(m: Monde) -> None:
    for _ in range(4):
        await evenement(m.db, "r1", "agent_tool_use", ts=_iso(10), agent="codeur",
                        data={"tool": "Bash", "input": {"command": "pytest"}})


async def _historique_de_tests(m: Monde, duree_s: int) -> None:
    await ligne_de_run(m.db, "h", started_at=_iso(7200), finished_at=_iso(7000),
                       ticket_id="ticket-000", final_status="approved")
    for i in range(10):
        debut = datetime(2026, 11, 4, 8, i, tzinfo=timezone.utc)
        await evenement(m.db, "h", "test_started", ts=debut.isoformat(), ticket_id="ticket-000")
        await evenement(m.db, "h", "test_result", ts=(debut + timedelta(seconds=duree_s)).isoformat(),
                        ticket_id="ticket-000")


async def _etape_longue(m: Monde) -> None:
    await _historique_de_tests(m, 600)
    await evenement(m.db, "r1", "test_started", ts=_iso(1900))


async def _silence(m: Monde) -> None:
    m.run.dernier_evenement_a = NOW - timedelta(seconds=901)


async def _cout(m: Monde) -> None:
    for i in range(10):
        await ligne_de_run(m.db, f"c{i}", ticket_id=f"ticket-1{i:02d}", finished_at=_iso(5000 - i),
                           final_status="approved", started_at=_iso(6000 - i))
        await appel_d_agent(m.db, f"c{i}", 2.0)
    await appel_d_agent(m.db, "r1", 6.5)


async def _tours(m: Monde) -> None:
    m.run.tour = 3


async def _blocages(m: Monde) -> None:
    for i, arret in enumerate(("cause réseau 1", "cause réseau 2")):
        await ligne_de_run(m.db, f"b{i}", finished_at=_iso(4000 - i), final_status="blocked",
                           arret=arret, started_at=_iso(5000 - i))


SCENARIOS: list[tuple[str, Callable[[Monde], Awaitable[None]]]] = [
    ("outil_repete", _outil_repete),
    ("etape_longue", _etape_longue),
    ("silence", _silence),
    ("cout_anormal", _cout),
    ("tours_de_revue", _tours),
    ("blocages_identiques", _blocages),
]


async def test_passe_without_live_runs_returns_nothing(monde: Monde) -> None:
    assert await monde.detecteur.passe() == []
    assert monde.evenements() == []


@pytest.mark.parametrize(("regle", "preparer"), SCENARIOS)
async def test_passe_reports_each_rule_once_per_episode(
    monde: Monde, regle: str, preparer: Callable[[Monde], Awaitable[None]]
) -> None:
    await monde.ouvrir()
    await preparer(monde)
    premiere = await monde.detecteur.passe()
    seconde = await monde.detecteur.passe()
    assert [a.regle for a in premiere].count(regle) == 1
    assert seconde == []
    assert [e.data["regle"] for e in monde.evenements()].count(regle) == 1


async def test_passe_reports_again_after_the_series_breaks_and_reforms(monde: Monde) -> None:
    run = await monde.ouvrir()
    await _outil_repete(monde)
    await monde.detecteur.passe()
    await evenement(monde.db, "r1", "agent_tool_use", ts=_iso(5), agent="codeur",
                    data={"tool": "Read", "input": {"path": "x"}})
    await _outil_repete(monde)
    await monde.detecteur.passe()
    assert [e.data["regle"] for e in monde.evenements()] == ["outil_repete", "outil_repete"]

    # Un silence rompu, puis repris : un autre `dernier_evenement_a`, donc une autre clé.
    run.dernier_evenement_a = NOW - timedelta(seconds=901)
    await monde.detecteur.passe()
    run.dernier_evenement_a = NOW + timedelta(seconds=60)
    monde.maintenant = NOW + timedelta(seconds=60 + 901)
    await monde.detecteur.passe()
    assert [e.data["regle"] for e in monde.evenements()].count("silence") == 2


async def test_passe_marks_the_key_seen_only_after_the_emission(monde: Monde) -> None:
    run = await monde.ouvrir()
    await _tours(monde)
    vues_pendant_l_emission: list[bool] = []
    publier = monde.hub.publish

    async def espion(event: OrchestratorEvent) -> None:
        vues_pendant_l_emission.append("tours:ticket-001" in run.anomalies_vues)
        await publier(event)

    monde.hub.publish = espion  # type: ignore[method-assign]
    await monde.detecteur.passe()
    assert vues_pendant_l_emission == [False]
    assert "tours:ticket-001" in run.anomalies_vues

    # Une émission qui échoue ne note rien : la passe suivante réessaie.
    run.anomalies_vues.clear()

    async def echec(event: OrchestratorEvent) -> None:
        raise RuntimeError("hub en panne")

    monde.hub.publish = echec  # type: ignore[method-assign]
    await monde.detecteur.passe()
    assert run.anomalies_vues == set()


async def test_passe_emits_through_the_hub_and_persists_in_agent_events(monde: Monde) -> None:
    run = await monde.ouvrir()
    await _tours(monde)
    await monde.detecteur.passe()
    (event,) = monde.evenements()
    assert (event.run_id, event.project_id, event.ticket_id) == ("r1", "p", "ticket-001")
    assert event.data["cle"] == "tours:ticket-001"
    ligne = sqlite3.connect(str(monde.db)).execute(
        "SELECT run_id, ticket_id, data_json FROM agent_events WHERE type = 'run_anomaly'"
    ).fetchall()
    assert [(r[0], r[1], json.loads(r[2])["regle"]) for r in ligne] == [
        ("r1", "ticket-001", "tours_de_revue")
    ]
    assert [a["regle"] for a in run.anomalies] == ["tours_de_revue"]


async def test_passe_on_a_queue_persists_under_the_envelope_with_the_ticket_id(
    monde: Monde,
) -> None:
    run = await monde.ouvrir(run_id="env", ticket="ticket-007", mode="queue")
    run.tour = 3
    await monde.detecteur.passe()
    lignes = sqlite3.connect(str(monde.db)).execute(
        "SELECT run_id, ticket_id FROM agent_events WHERE type = 'run_anomaly'"
    ).fetchall()
    assert lignes == [("env", "ticket-007")]


async def test_passe_never_changes_a_run_beyond_its_anomaly_fields(monde: Monde) -> None:
    class Sonde:
        def __init__(self) -> None:
            self.appels: list[str] = []

        def __getattr__(self, nom: str) -> Any:
            self.appels.append(nom)
            raise AssertionError(f"le détecteur a touché au dialogue : {nom}")

    fermetures: list[str] = []
    run = await monde.ouvrir()
    sonde = Sonde()
    run.dialogue = sonde
    monde.registre.fermer = fermetures.append  # type: ignore[method-assign]
    await _outil_repete(monde)
    await _silence(monde)
    run.tour = 3
    avant = {k: str(v) for k, v in vars(run).items() if k not in ("anomalies", "anomalies_vues")}
    await monde.detecteur.passe()
    apres = {k: str(v) for k, v in vars(run).items() if k not in ("anomalies", "anomalies_vues")}
    assert apres == avant
    assert fermetures == [] and sonde.appels == []
    assert len(run.anomalies) >= 3


async def test_passe_calls_no_provider_and_runs_no_git_command(
    monde: Monde, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interdit(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("le détecteur a lancé un processus")

    for nom in ("Popen", "run", "call", "check_output"):
        monkeypatch.setattr(subprocess, nom, interdit)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", interdit)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", interdit)
    await monde.ouvrir()
    for _, preparer in SCENARIOS:
        await preparer(monde)
    signalees = await monde.detecteur.passe()
    assert len(signalees) >= 5


def test_detector_package_imports_no_provider_no_git_no_subprocess() -> None:
    interdits = ("subprocess", "anthropic", "claude_agent_sdk", "tessera.services.providers",
                 "tessera.services.git", "tessera.services.github", "tessera.services.livraison")
    dossier = Path(module_detecteur.__file__).parent
    for fichier in dossier.glob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            noms = (
                [a.name for a in noeud.names] if isinstance(noeud, ast.Import)
                else [noeud.module or ""] if isinstance(noeud, ast.ImportFrom) else []
            )
            for nom in noms:
                assert not nom.startswith(interdits), f"{fichier.name} importe {nom}"


async def test_passe_survives_a_failing_run_and_still_checks_the_others(
    monde: Monde, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    mauvais = await monde.ouvrir(run_id="mauvais", projet="p1")
    mauvais.tour = 3
    bon = await monde.ouvrir(run_id="bon", projet="p2")
    bon.tour = 3
    lire = lecture_evenements.derniers_appels_d_outils

    async def piege(db: Any, run_id: str, ticket: str, n: int = 8) -> Any:
        if run_id == "mauvais":
            raise RuntimeError("lecture impossible")
        return await lire(db, run_id, ticket, n)

    monkeypatch.setattr(lecture_evenements, "derniers_appels_d_outils", piege)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        signalees = await monde.detecteur.passe()
    assert [a.ticket_id for a in signalees] == ["ticket-001"]
    assert bon.anomalies and not mauvais.anomalies
    assert any(r.getMessage() == "anomalie_passe_en_echec" for r in caplog.records)


async def test_silence_is_exempt_during_a_silent_stage_with_an_armed_median(monde: Monde) -> None:
    run = await monde.ouvrir()
    await _historique_de_tests(monde, 60)
    await evenement(monde.db, "r1", "test_started", ts=_iso(100))
    run.dernier_evenement_a = NOW - timedelta(seconds=1000)
    assert await monde.detecteur.passe() == []


async def test_silence_is_reported_during_a_silent_stage_without_a_median(monde: Monde) -> None:
    run = await monde.ouvrir()
    await evenement(monde.db, "r1", "test_started", ts=_iso(1000))
    run.dernier_evenement_a = NOW - timedelta(seconds=1000)
    assert [a.regle for a in await monde.detecteur.passe()] == ["silence"]


async def test_silence_is_exempt_while_a_question_waits_and_during_an_external_wait(
    monde: Monde,
) -> None:
    run = await monde.ouvrir()
    run.dernier_evenement_a = NOW - timedelta(seconds=5000)
    run.question = "Quelle branche ?"
    assert await monde.detecteur.passe() == []
    run.question = None
    run.attente_exterieure = True
    assert await monde.detecteur.passe() == []
    run.attente_exterieure = False
    assert [a.regle for a in await monde.detecteur.passe()] == ["silence"]


async def test_cout_budget_is_evaluated_only_for_an_autonomous_run(monde: Monde) -> None:
    run = await monde.ouvrir()
    run.cout_usd = 4.5
    assert await monde.detecteur.passe() == []
    run.mode = "autonomous"
    signalees = await monde.detecteur.passe()
    assert [(a.regle, a.cle) for a in signalees] == [("cout_anormal", "cout_budget:r1")]


async def test_passe_late_by_601s_logs_the_gap_and_late_by_600s_does_not(
    monde: Monde, caplog: pytest.LogCaptureFixture
) -> None:
    run = await monde.ouvrir()
    run.tour = 3
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        await monde.detecteur.passe()
        monde.maintenant = NOW + timedelta(seconds=600)
        run.dernier_evenement_a = monde.maintenant
        await monde.detecteur.passe()
        assert not any(r.getMessage() == "anomalie_passe_tardive" for r in caplog.records)
        monde.maintenant = NOW + timedelta(seconds=600 + 601)
        run.dernier_evenement_a = monde.maintenant
        run.tour = 3
        run.anomalies_vues.clear()
        signalees = await monde.detecteur.passe()
    tardives = [r for r in caplog.records if r.getMessage() == "anomalie_passe_tardive"]
    assert len(tardives) == 1 and getattr(tardives[0], "ecart_s") == 601.0
    assert signalees, "une passe en retard émet quand même"


async def test_boucle_does_nothing_when_anomalies_actives_is_false(monde: Monde) -> None:
    inactif = settings.model_copy(update={"anomalies_actives": False})
    detecteur = DetecteurDAnomalies(monde.registre, monde.hub, monde.db, inactif)
    passes: list[int] = []

    async def passe() -> list[Any]:
        passes.append(1)
        return []

    detecteur.passe = passe  # type: ignore[method-assign]
    await asyncio.wait_for(detecteur.boucle(), timeout=2)
    assert passes == []


async def test_boucle_passes_then_sleeps_and_stops_when_cancelled(monde: Monde) -> None:
    rapide = settings.model_copy(update={"anomalie_intervalle_s": 0.01})
    detecteur = DetecteurDAnomalies(monde.registre, monde.hub, monde.db, rapide)
    passes: list[int] = []

    async def passe() -> list[Any]:
        passes.append(1)
        if len(passes) == 1:
            raise RuntimeError("une passe qui échoue ne tue pas la boucle")
        return []

    detecteur.passe = passe  # type: ignore[method-assign]
    tache = asyncio.create_task(detecteur.boucle())
    while len(passes) < 3:
        await asyncio.sleep(0.01)
    await module_detecteur.arreter_le_detecteur(tache)
    assert tache.cancelled() or tache.done()


def test_lifespan_starts_the_detector_and_cancels_it_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    etat: list[str] = []

    async def boucle(self: DetecteurDAnomalies) -> None:
        etat.append("demarre")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            etat.append("annule")
            raise

    monkeypatch.setattr(DetecteurDAnomalies, "boucle", boucle)
    with TestClient(app):
        for _ in range(200):
            if etat:
                break
            time.sleep(0.01)
        assert etat == ["demarre"]
    assert etat == ["demarre", "annule"]


async def test_anomaly_log_line_has_no_tool_input(
    monde: Monde, caplog: pytest.LogCaptureFixture
) -> None:
    run = await monde.ouvrir()
    secret = "ghp_FAKE_TOKEN_0123456789"
    for _ in range(4):
        await evenement(monde.db, "r1", "agent_tool_use", ts=_iso(10), agent="codeur",
                        data={"tool": "Bash", "input": {"command": f"curl -H {secret}"}})
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        await monde.detecteur.passe()
    lignes = [r for r in caplog.records if r.getMessage() == "anomalie_de_run"]
    assert len(lignes) == 1
    assert lignes[0].__dict__["regle"] == "outil_repete"
    tout = json.dumps([r.__dict__ for r in caplog.records], default=str)
    assert secret not in tout
    assert secret not in json.dumps(run.anomalies)
    assert secret not in json.dumps([e.model_dump(mode="json") for e in monde.evenements()])
    ligne_bd = sqlite3.connect(str(monde.db)).execute(
        "SELECT data_json FROM agent_events WHERE type = 'run_anomaly'"
    ).fetchone()
    assert secret not in ligne_bd[0]


async def test_the_detector_does_not_reset_the_silence_clock(monde: Monde) -> None:
    run = await monde.ouvrir()
    run.dernier_evenement_a = NOW - timedelta(seconds=901)
    await monde.detecteur.passe()
    assert run.dernier_evenement_a == NOW - timedelta(seconds=901)
    monde.maintenant = NOW + timedelta(seconds=3600)
    assert await monde.detecteur.passe() == []
