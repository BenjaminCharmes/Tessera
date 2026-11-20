"""The supervisor's background task: events, sweep, idempotence, daily budget — ticket-859 (ADR-080)."""
import asyncio
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.noyau.database import init_db
from tessera.services.noyau.event_hub import EventHub
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.run_registry import RunRegistry
from tessera.services.supervision.superviseur_actions import Action, Decision, Verdict
from tessera.services.supervision.superviseur_boucle import SuperviseurBoucle
from tessera.services.supervision.superviseur_boucle_etat import EtatIdempotence
from tessera.services.supervision.superviseur_boucle_ports import Candidat, ProjetSupervise, depense_du_jour, projets_supervises
from tessera.services.usage.agent_calls import save_agent_call


class _Banc:
    """A registry, a hub, one declared project and fake candidates that count their runs."""

    def __init__(self, tmp_path: Path, *, depense: float = 0.0, actif: bool = True) -> None:
        self.registre = RunRegistry()
        self.hub = EventHub()
        self.abonnement = self.hub.subscribe()
        self.depense = depense
        self.collectes: list[str] = []
        self.executions: list[str] = []
        self.candidats: list[Candidat] = []
        self.collecte_en_panne = False
        projets = [ProjetSupervise("demo", tmp_path, ConfigSuperviseur(budget_jour_usd=2.0))] if actif else []
        self.etat = EtatIdempotence(tmp_path / "cles.json")
        self.boucle = SuperviseurBoucle(
            self.registre, self.hub, lambda: projets, self._collecter, self._lire_depense, self.etat,
            intervalle_s=0.01, decalage_s=0.0,
        )

    async def _collecter(self, project_id: str, project_path: Path) -> list[Candidat]:
        self.collectes.append(project_id)
        if self.collecte_en_panne:
            raise RuntimeError("collecte en panne")
        return self.candidats

    async def _lire_depense(self) -> float:
        return self.depense

    def candidat(
        self, cible: str, *, sans_modele: bool = False, echoue: bool = False, verdict: Verdict = "agir", sha: str = "abc",
    ) -> Candidat:
        action = Action.RECONFIER_PR if sans_modele else Action.TRIER

        async def executer() -> list[Decision]:
            self.executions.append(cible)
            if echoue:
                raise RuntimeError("l'action a échoué")
            return [Decision(action, cible, verdict, "raison")]

        candidat = Candidat("demo", action, cible, sha, sans_modele, executer)
        self.candidats.append(candidat)
        return candidat

    def evenements(self) -> list[OrchestratorEvent]:
        return self.abonnement.vider()


async def test_run_closing_triggers_one_pass(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1")
    assert banc.boucle.demarrer() is True

    run = banc.registre.ouvrir("demo", "ticket-9")
    banc.registre.fermer(run.run_id)
    await banc.boucle.attendre()

    assert banc.collectes == ["demo"]
    assert banc.executions == ["ticket-1"]
    evenements = banc.evenements()
    assert [e.type for e in evenements] == [EventType.SUPERVISEUR_ACTION]
    assert evenements[0].project_id == "demo"
    assert evenements[0].data["verdict"] == "agir"
    assert evenements[0].data["action"] == "trier"


async def test_closing_a_project_the_supervisor_does_not_hold_starts_nothing(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1")
    banc.boucle.demarrer()

    run = banc.registre.ouvrir("autre", "ticket-9")
    banc.registre.fermer(run.run_id)
    await banc.boucle.attendre()

    assert banc.collectes == []


async def test_second_pass_repeats_nothing(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1")

    premiere = await banc.boucle.passe()
    seconde = await banc.boucle.passe()

    assert len(premiere) == 1
    assert seconde == []
    assert banc.executions == ["ticket-1"]
    assert len(banc.evenements()) == 1


async def test_a_new_sha_is_a_new_key(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1", sha="v1")
    await banc.boucle.passe()
    banc.candidats.clear()
    banc.candidat("ticket-1", sha="v2")

    await banc.boucle.passe()

    assert banc.executions == ["ticket-1", "ticket-1"]


async def test_two_failures_on_a_key_go_to_a_toi(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    candidat = banc.candidat("ticket-1", echoue=True)

    premiere = await banc.boucle.passe()
    assert premiere == []
    assert banc.etat.echecs(candidat.cle) == 1
    assert banc.evenements() == []

    seconde = await banc.boucle.passe()
    assert [d.verdict for d in seconde] == ["a_toi"]
    assert "2 échecs de suite" in seconde[0].raison
    assert [e.data["verdict"] for e in banc.evenements()] == ["a_toi"]

    await banc.boucle.passe()
    assert banc.executions == ["ticket-1", "ticket-1"]


async def test_a_success_between_two_failures_resets_the_count(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    candidat = banc.candidat("ticket-1", echoue=True)
    await banc.boucle.passe()
    assert banc.etat.echecs(candidat.cle) == 1

    banc.etat.marquer_faite(candidat.cle)

    assert banc.etat.echecs(candidat.cle) == 0
    assert banc.etat.deja_faite(candidat.cle)


async def test_a_model_answer_that_says_nothing_counts_as_a_failure(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1", verdict="rien")

    await banc.boucle.passe()
    seconde = await banc.boucle.passe()

    assert [d.verdict for d in seconde] == ["a_toi"]


async def test_a_model_free_nothing_is_neither_done_nor_a_failure(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    candidat = banc.candidat("ticket-1", sans_modele=True, verdict="rien")

    await banc.boucle.passe()
    await banc.boucle.passe()

    assert banc.executions == ["ticket-1", "ticket-1"]
    assert banc.etat.echecs(candidat.cle) == 0
    assert not banc.etat.deja_faite(candidat.cle)
    assert banc.evenements() == []


async def test_spent_daily_budget_keeps_only_model_free_actions(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, depense=2.0)
    banc.candidat("avec-modele")
    banc.candidat("sans-modele", sans_modele=True)

    await banc.boucle.passe()

    assert banc.executions == ["sans-modele"]
    banc.depense = 0.5
    await banc.boucle.passe()
    assert banc.executions == ["sans-modele", "avec-modele"]


async def test_an_unreadable_spend_holds_the_model_actions_back(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("avec-modele")

    async def illisible() -> float:
        raise RuntimeError("base illisible")

    boucle = SuperviseurBoucle(
        banc.registre, banc.hub, lambda: [ProjetSupervise("demo", tmp_path, ConfigSuperviseur())],
        banc._collecter, illisible, banc.etat,
    )
    await boucle.passe()

    assert banc.executions == []


async def test_inactive_role_starts_nothing(tmp_path: Path) -> None:
    banc = _Banc(tmp_path, actif=False)
    banc.candidat("ticket-1")

    assert banc.boucle.demarrer() is False
    await asyncio.wait_for(banc.boucle.boucle(), timeout=1.0)
    run = banc.registre.ouvrir("demo", "ticket-9")
    banc.registre.fermer(run.run_id)
    await banc.boucle.attendre()

    assert banc.collectes == []
    assert banc.executions == []


async def test_an_exception_never_reaches_a_run(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1", echoue=True)
    banc.boucle.demarrer()
    vivant = banc.registre.ouvrir("autre", "ticket-5")

    banc.collecte_en_panne = True
    assert await banc.boucle.passe() == []
    banc.collecte_en_panne = False
    run = banc.registre.ouvrir("demo", "ticket-9")
    banc.registre.fermer(run.run_id)  # la passe lancée par la fermeture échoue sur l'action
    await banc.boucle.attendre()

    assert [r.run_id for r in banc.registre.vivants()] == [vivant.run_id]
    banc.registre.fermer(vivant.run_id)


async def test_a_failing_projects_reader_activates_nothing(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)

    def en_panne() -> list[ProjetSupervise]:
        raise OSError("workspace illisible")

    boucle = SuperviseurBoucle(banc.registre, banc.hub, en_panne, banc._collecter, banc._lire_depense, banc.etat)

    assert boucle.demarrer() is False
    assert await boucle.passe() == []


async def test_two_passes_at_once_do_not_double(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    liberer = asyncio.Event()

    async def lente(project_id: str, project_path: Path) -> list[Candidat]:
        banc.collectes.append(project_id)
        await liberer.wait()
        return []

    boucle = SuperviseurBoucle(banc.registre, banc.hub, lambda: [ProjetSupervise("demo", tmp_path, ConfigSuperviseur())], lente, banc._lire_depense, banc.etat)
    premiere = asyncio.create_task(boucle.passe())
    await asyncio.sleep(0)

    assert await boucle.passe() == []
    liberer.set()
    await premiere

    assert banc.collectes == ["demo"]


async def test_the_loop_sweeps_after_its_offset_until_cancelled(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)
    banc.candidat("ticket-1")
    tache = asyncio.create_task(banc.boucle.boucle())
    await asyncio.sleep(0.1)
    tache.cancel()
    await asyncio.gather(tache, return_exceptions=True)

    assert len(banc.collectes) >= 2
    assert banc.executions == ["ticket-1"]


def test_key_names_action_project_target_and_sha(tmp_path: Path) -> None:
    banc = _Banc(tmp_path)

    assert banc.candidat("ticket-7", sha="f00").cle == "trier:demo/ticket-7:f00"


def test_ledger_survives_a_restart_and_reads_a_broken_file_as_empty(tmp_path: Path) -> None:
    fichier = tmp_path / "etat" / "cles.json"
    etat = EtatIdempotence(fichier)
    etat.marquer_faite("trier:demo/t:a")
    etat.noter_echec("trier:demo/t:b")

    relu = EtatIdempotence(fichier)
    assert relu.deja_faite("trier:demo/t:a")
    assert relu.echecs("trier:demo/t:b") == 1

    fichier.write_text("{pas du json", encoding="utf-8")
    assert not EtatIdempotence(fichier).deja_faite("trier:demo/t:a")


def _declarer(dossier: Path, *, actif: bool = True, confidentialite: str | None = None) -> None:
    dossier.mkdir(parents=True)
    manifeste: dict[str, object] = {
        "agents": [{"role": "superviseur", "model": "m", "max_tokens": 10, "prompt_file": "p.md", "active": actif}],
        "pipeline": {"superviseur": {"budget_jour_usd": 3.0}},
    }
    if confidentialite is not None:
        manifeste["confidentiality"] = confidentialite
    (dossier / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")


def test_supervised_projects_are_the_declared_active_non_professional_ones(tmp_path: Path) -> None:
    _declarer(tmp_path / "actif")
    _declarer(tmp_path / "eteint", actif=False)
    _declarer(tmp_path / "pro", confidentialite="professional")
    (tmp_path / "muet").mkdir()

    projets = projets_supervises(tmp_path)

    assert [p.project_id for p in projets] == ["actif"]
    assert projets[0].config.budget_jour_usd == 3.0
    assert projets_supervises(tmp_path / "absent") == []


async def test_daily_spend_sums_the_supervisor_calls_of_the_day_only(tmp_path: Path) -> None:
    base = tmp_path / "usage.db"
    await init_db(base)
    await save_agent_call(base, "r", "superviseur", "superviseur", "m", 1, 1, 0, 0.75, 10)
    await save_agent_call(base, "r", "superviseur", "superviseur", "m", 1, 1, 0, 0.5, 10)
    await save_agent_call(base, "r", "ticket-1", "codeur", "m", 1, 1, 0, 9.0, 10)
    hier = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with closing(sqlite3.connect(base)) as connexion:
        connexion.execute("UPDATE agent_calls SET created_at = ? WHERE cost_usd = 0.5", (hier,))
        connexion.commit()

    assert await depense_du_jour(base, datetime.now(UTC)) == 0.75
