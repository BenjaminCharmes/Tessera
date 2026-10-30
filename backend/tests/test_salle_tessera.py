"""La salle des serveurs de Tessera — ticket-726.

La sonde est un faux, le journal et le dossier des worktrees sont écrits dans
`tmp_path` : la salle ne dit que ce qu'on lui donne.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite
from fastapi.testclient import TestClient

from tessera.main import app
from tessera.services.database import init_db
from tessera.routers.services_running import get_sonde
from tessera.services.providers import ollama
from tessera.services.salle_tessera import (
    PORT_DU_FRONTEND,
    ci_en_attente,
    fin_du_journal,
    agents_en_cours,
    processus_de_tessera,
    runs_vivants,
    runs_du_jour,
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


def test_live_runs_keep_their_queue_position_and_every_ticket_left() -> None:
    runs = runs_vivants(
        [{"project_id": "ide-core", "ticket_id": "ticket-718", "agent": "testeur", "etape": "tests",
          "file_index": 3, "file_total": 40, "file_restants": ["a", "b", "c", "d"]}]
    )

    assert runs[0].file_index == 3 and runs[0].file_total == 40
    assert runs[0].suivants == ["a", "b", "c", "d"]


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


def test_running_agents_are_the_claude_processes_under_the_backend() -> None:
    moi = os.getpid()
    procs = {
        moi: _info(1, 1.0),
        10: InfoProcessus(ppid=moi, memoire_mo=1.0, demarre_a=None, commande="C:/outils/claude.exe --print"),
        11: InfoProcessus(ppid=10, memoire_mo=1.0, demarre_a=None, commande="node claude-code/cli.js"),
        12: InfoProcessus(ppid=moi, memoire_mo=1.0, demarre_a=None, commande="git status"),
        13: InfoProcessus(ppid=1, memoire_mo=1.0, demarre_a=None, commande="claude.exe"),
    }

    assert agents_en_cours(moi, procs) == 2


async def test_runs_of_the_day_count_since_local_midnight(tmp_path: Path) -> None:
    base = tmp_path / "tessera.db"
    await init_db(base)
    maintenant = datetime.now(timezone.utc)
    async with aiosqlite.connect(base) as db:
        for i, depuis in enumerate([maintenant, maintenant - timedelta(days=3)]):
            await db.execute(
                "INSERT INTO pipeline_runs (id, ticket_id, project_id, started_at) VALUES (?, ?, ?, ?)",
                (f"r{i}", "ticket-1", "p", depuis.isoformat()),
            )
        await db.commit()

    assert await runs_du_jour(base) == 1
    assert await runs_du_jour(tmp_path / "absent" / "x.db") == 0


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
    assert set(reponse.json()) == {"processus", "ollama", "runs", "ci_en_attente", "journal", "base_mo", "agents", "runs_du_jour"}


def test_the_route_bounds_the_journal_length() -> None:
    app.dependency_overrides[get_sonde] = lambda: FausseSonde()
    try:
        client = TestClient(app)
        assert client.get("/api/v1/tessera/salle?journal=100").status_code == 200
        assert client.get("/api/v1/tessera/salle?journal=500").status_code == 422
    finally:
        app.dependency_overrides.pop(get_sonde, None)
