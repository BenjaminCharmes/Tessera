"""La salle des serveurs de Tessera — ticket-726.

La sonde est un faux, le journal et le dossier des worktrees sont écrits dans
`tmp_path` : la salle ne dit que ce qu'on lui donne.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from tessera.main import app
from tessera.routers.services_running import get_sonde
from tessera.services.providers import ollama
from tessera.services.salle_tessera import (
    PORT_DU_FRONTEND,
    ci_en_attente,
    fin_du_journal,
    nombre_de_worktrees,
    processus_de_tessera,
    runs_vivants,
    salle_tessera,
    taille_mo,
)
from tessera.services.sonde_systeme import InfoProcessus


@dataclass
class FausseSonde:
    ports: dict[int, int] = field(default_factory=dict)
    procs: dict[int, InfoProcessus] = field(default_factory=dict)

    async def ecouteurs(self) -> dict[int, int]:
        return self.ports

    async def processus(self) -> dict[int, InfoProcessus]:
        return self.procs


def _info(ppid: int, memoire_mo: float) -> InfoProcessus:
    return InfoProcessus(ppid=ppid, memoire_mo=memoire_mo, demarre_a=None)


async def test_backend_counts_only_itself_and_frontend_counts_its_tree() -> None:
    moi = os.getpid()
    sonde = FausseSonde(
        ports={8100: moi, PORT_DU_FRONTEND: 50},
        procs={moi: _info(1, 400.0), 900: _info(moi, 300.0), 50: _info(1, 100.0), 51: _info(50, 20.5)},
    )

    backend, frontend = await processus_de_tessera(sonde)

    assert (backend.nom, backend.port, backend.memoire_mo) == ("backend", 8100, 400.0)
    assert (frontend.nom, frontend.pid, frontend.memoire_mo) == ("frontend", 50, 120.5)


async def test_a_frontend_nobody_serves_has_no_pid() -> None:
    _, frontend = await processus_de_tessera(FausseSonde(procs={os.getpid(): _info(1, 1.0)}))

    assert frontend.pid is None
    assert frontend.memoire_mo == 0.0


def test_live_runs_keep_their_queue_position_and_three_next_tickets() -> None:
    runs = runs_vivants(
        [{"project_id": "ide-core", "ticket_id": "ticket-718", "agent": "testeur", "etape": "tests",
          "file_index": 3, "file_total": 40, "file_restants": ["a", "b", "c", "d"]}]
    )

    assert runs[0].file_index == 3 and runs[0].file_total == 40
    assert runs[0].suivants == ["a", "b", "c"]


def test_the_log_shows_only_the_event_never_the_payload(tmp_path: Path) -> None:
    journal = tmp_path / "tessera.log"
    lignes = [
        json.dumps({"ts": f"t{i}", "level": "INFO", "message": f"evt{i}", "path": "C:\\secret"})
        for i in range(10)
    ]
    journal.write_text("\n".join([*lignes, "pas du json"]) + "\n", encoding="utf-8")

    fin = fin_du_journal(journal)

    assert [l.evenement for l in fin] == [f"evt{i}" for i in range(4, 10)]
    assert "secret" not in json.dumps([l.model_dump() for l in fin])


def test_a_missing_log_gives_no_line(tmp_path: Path) -> None:
    assert fin_du_journal(tmp_path / "absent.log") == []


def test_worktrees_are_counted_per_project_and_ticket(tmp_path: Path) -> None:
    (tmp_path / "curio" / "ticket-070").mkdir(parents=True)
    (tmp_path / "ide-core" / "ticket-718").mkdir(parents=True)
    (tmp_path / "ide-core" / "ticket-719").mkdir(parents=True)

    assert nombre_de_worktrees(tmp_path) == 3
    assert nombre_de_worktrees(tmp_path / "absent") == 0


def test_database_size_is_in_megabytes(tmp_path: Path) -> None:
    base = tmp_path / "tessera.db"
    base.write_bytes(b"x" * 2_097_152)

    assert taille_mo(base) == 2.0
    assert taille_mo(tmp_path / "absent.db") == 0.0


def test_ollama_cooldown_is_reported_then_clears() -> None:
    url = "http://ollama.test:11434"
    try:
        ollama._COOLDOWNS[url] = ollama._clock() + 30
        reste = ollama.secondes_de_refroidissement(url)
        assert reste is not None and 0 < reste <= 30
        ollama._COOLDOWNS[url] = ollama._clock() - 1
        assert ollama.secondes_de_refroidissement(url) is None
    finally:
        ollama._COOLDOWNS.pop(url, None)


def test_ci_waiting_lists_only_projects_with_a_pending_pr() -> None:
    attente = {"ide-core": ("ticket-2", "ticket-1"), "curio": ()}

    assert ci_en_attente(["curio", "ide-core", "vigie"], lambda p: attente.get(p, ())) == {
        "ide-core": ("ticket-1", "ticket-2")
    }


async def test_the_room_assembles_every_fact(tmp_path: Path) -> None:
    salle = await salle_tessera(
        FausseSonde(procs={os.getpid(): _info(1, 10.0)}),
        instantane=[],
        ci_en_attente={"ide-core": ("ticket-1",)},
        ollama_url="http://127.0.0.1:11434",
        refroidissement_s=12.0,
        journal=tmp_path / "absent.log",
        base=tmp_path / "absent.db",
        worktrees=tmp_path,
    )

    assert salle.ollama.refroidissement_s == 12.0
    assert salle.ci_en_attente == {"ide-core": ["ticket-1"]}
    assert [p.nom for p in salle.processus] == ["backend", "frontend"]


def test_the_route_answers_with_the_room() -> None:
    app.dependency_overrides[get_sonde] = lambda: FausseSonde()
    try:
        reponse = TestClient(app).get("/api/v1/tessera/salle")
    finally:
        app.dependency_overrides.pop(get_sonde, None)

    assert reponse.status_code == 200
    assert set(reponse.json()) == {"processus", "ollama", "runs", "ci_en_attente", "journal", "base_mo", "worktrees"}
