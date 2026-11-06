"""The loop reads the delivered runs and the interrupted queues (ticket-867)."""
import json
from pathlib import Path

import aiosqlite

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.noyau.database import init_db
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.supervision.superviseur_actions import Action
from tessera.services.supervision.superviseur_collecte_file import SourcesFile, candidats_file, files_coupees
from tessera.services.supervision.superviseur_collecte_pr import RunPousse, SourcesPr, candidats_pr, runs_pousses
from tessera.services.supervision.superviseur_file import FileCoupee, SuperviseurFile
from tessera.services.supervision.superviseur_pr import SuperviseurPr

PUSHED = "a" * 40
AUTRE = "b" * 40
COUPURE_PR = "GitCommandError: git push a échoué (réseau coupé)"
PREFIXE = "file interrompue : "
COUPURE_FILE = PREFIXE + "GitCommandError: git fetch a échoué (réseau coupé)"
NON_APPROUVE = PREFIXE + "ticket-760 non approuvé après 3 tours"


class _Watcher:
    def __init__(self) -> None:
        self.confiees: list[tuple[str, str, int]] = []

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        return ()

    async def surveiller(self, project_id: str, ticket_id: str, pr: int, on_event: object) -> None:
        self.confiees.append((project_id, ticket_id, pr))


async def _ignorer(evenement: OrchestratorEvent) -> None:
    return None


def _sources_pr(run: RunPousse, tete: str | None, pr: int | None = 913) -> SourcesPr:
    async def runs() -> list[RunPousse]:
        return [run]

    async def ouvertes() -> dict[str, int]:
        return {} if pr is None else {run.ticket_id: pr}

    async def lire_tete(numero: int) -> str | None:
        return tete

    return SourcesPr(runs, ouvertes, lire_tete)


def _superviseur_pr(watcher: _Watcher, tete: str | None) -> SuperviseurPr:
    async def etat(project_id: str, pr: int) -> str:
        return "open"

    async def lire(project_id: str, pr: int) -> str | None:
        return tete

    return SuperviseurPr(watcher, watcher.surveiller, etat, lire)


async def test_an_approved_run_with_its_pushed_head_offers_one_hand_back() -> None:
    watcher = _Watcher()
    run = RunPousse("ticket-776", True, COUPURE_PR, PUSHED)

    candidats = await candidats_pr("demo", _sources_pr(run, PUSHED), lambda: _superviseur_pr(watcher, PUSHED), _ignorer)

    assert [(c.action, c.sha, c.sans_modele) for c in candidats] == [(Action.RECONFIER_PR, PUSHED, True)]
    decisions = await candidats[0].executer()
    assert [d.verdict for d in decisions] == ["agir"]
    assert watcher.confiees == [("demo", "ticket-776", 913)]


async def test_a_delivered_run_with_a_moved_head_offers_no_hand_back() -> None:
    run = RunPousse("ticket-776", True, COUPURE_PR, PUSHED)

    deplacee = await candidats_pr("demo", _sources_pr(run, AUTRE), lambda: _superviseur_pr(_Watcher(), AUTRE), _ignorer)
    illisible = await candidats_pr("demo", _sources_pr(run, None), lambda: _superviseur_pr(_Watcher(), None), _ignorer)

    assert deplacee == []
    assert illisible == []


async def test_a_run_without_an_open_pr_or_not_approved_offers_no_hand_back() -> None:
    approuve = RunPousse("ticket-776", True, COUPURE_PR, PUSHED)
    refuse = RunPousse("ticket-776", False, COUPURE_PR, PUSHED)

    sans_pr = await candidats_pr("demo", _sources_pr(approuve, PUSHED, pr=None), lambda: _superviseur_pr(_Watcher(), PUSHED), _ignorer)
    non_approuve = await candidats_pr("demo", _sources_pr(refuse, PUSHED), lambda: _superviseur_pr(_Watcher(), PUSHED), _ignorer)

    assert sans_pr == []
    assert non_approuve == []


def _coupee(ligne: str) -> FileCoupee:
    return FileCoupee("demo", "run-0", ligne, ("ticket-760", "ticket-761"))


def _sources_file(ligne: str) -> SourcesFile:
    async def files() -> list[FileCoupee]:
        return [_coupee(ligne)]

    return SourcesFile(files)


def _superviseur_file(rouvertes: list[list[str]]) -> SuperviseurFile:
    async def rouvrir(project_id: str, tickets: list[str]) -> str:
        rouvertes.append(tickets)
        return f"run-{len(rouvertes)}"

    async def depense() -> float:
        return 0.0

    async def quota() -> bool:
        return False

    return SuperviseurFile(ConfigSuperviseur(relance_file=True), rouvrir, lambda _p: False, depense, quota)


async def test_a_queue_cut_by_the_infrastructure_offers_one_restart_per_cause() -> None:
    rouvertes: list[list[str]] = []
    config = ConfigSuperviseur(relance_file=True)
    superviseur = _superviseur_file(rouvertes)

    premiere = await candidats_file("demo", config, _sources_file(COUPURE_FILE), lambda: superviseur)
    seconde = await candidats_file("demo", config, _sources_file(COUPURE_FILE), lambda: superviseur)

    assert [(c.action, c.sha, c.sans_modele) for c in premiere] == [(Action.RELANCER_FILE, "infrastructure", True)]
    assert premiere[0].cle == seconde[0].cle
    decisions = await premiere[0].executer()
    assert [d.verdict for d in decisions] == ["agir"]
    assert rouvertes == [["ticket-760", "ticket-761"]]


async def test_a_not_approved_queue_offers_no_restart() -> None:
    config = ConfigSuperviseur(relance_file=True)

    candidats = await candidats_file("demo", config, _sources_file(NON_APPROUVE), lambda: _superviseur_file([]))

    assert candidats == []


async def test_a_queue_offers_no_restart_when_relance_file_is_not_declared() -> None:
    candidats = await candidats_file("demo", ConfigSuperviseur(), _sources_file(COUPURE_FILE), lambda: _superviseur_file([]))

    assert candidats == []


async def _inserer(db_path: Path, requete: str, valeurs: tuple[object, ...]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(requete, valeurs)
        await db.commit()


_RUN = (
    "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at, approved, final_status, arret, mode, parent_run_id, pushed_sha)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


async def test_the_pushed_runs_are_read_newest_first_one_per_ticket(tmp_path: Path) -> None:
    db_path = tmp_path / "ide.db"
    await init_db(db_path)
    await _inserer(db_path, _RUN, ("r1", "demo", "ticket-1", "2026-11-05T01:00:00", 1, "done", None, "single", None, AUTRE))
    await _inserer(db_path, _RUN, ("r2", "demo", "ticket-1", "2026-11-05T02:00:00", 1, "done", COUPURE_PR, "single", None, PUSHED))
    await _inserer(db_path, _RUN, ("r3", "demo", "ticket-2", "2026-11-05T03:00:00", 1, "done", None, "single", None, None))
    await _inserer(db_path, _RUN, ("r4", "autre", "ticket-9", "2026-11-05T03:00:00", 1, "done", None, "single", None, AUTRE))

    runs = await runs_pousses(db_path, "demo")

    assert runs == [RunPousse("ticket-1", True, COUPURE_PR, PUSHED)]


async def test_an_interrupted_queue_is_read_with_the_tickets_it_still_held(tmp_path: Path) -> None:
    db_path = tmp_path / "ide.db"
    await init_db(db_path)
    await _inserer(db_path, _RUN, ("q1", "demo", "", "2026-11-05T01:00:00", 0, "interrupted", COUPURE_FILE, "queue", None, None))
    await _inserer(db_path, _RUN, ("t1", "demo", "ticket-759", "2026-11-05T01:01:00", 1, "done", None, "single", "q1", None))
    donnees = json.dumps({"index": 2, "total": 4, "restants": ["ticket-761"]})
    evenement = (
        "INSERT INTO agent_events (run_id, type, data_json, ts, ticket_id) VALUES (?, ?, ?, ?, ?)"
    )
    await _inserer(db_path, evenement, ("q1", EventType.QUEUE_PROGRESS.value, donnees, "2026-11-05T01:02:00", "ticket-760"))

    async def finis() -> set[str]:
        return {"ticket-761"}

    files = await files_coupees(db_path, "demo", finis)

    assert files == [FileCoupee("demo", "q1", COUPURE_FILE, ("ticket-760",))]


async def test_a_queue_followed_by_another_run_is_no_longer_offered(tmp_path: Path) -> None:
    db_path = tmp_path / "ide.db"
    await init_db(db_path)
    await _inserer(db_path, _RUN, ("q1", "demo", "", "2026-11-05T01:00:00", 0, "interrupted", COUPURE_FILE, "queue", None, None))
    await _inserer(db_path, _RUN, ("s1", "demo", "ticket-770", "2026-11-05T02:00:00", 1, "done", None, "single", None, None))

    async def finis() -> set[str]:
        return set()

    assert await files_coupees(db_path, "demo", finis) == []
