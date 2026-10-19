"""A ticket merged on the base while a queue runs can be appended — ticket-504.

Pendant une file, l'arbre du projet est sur la branche du ticket en cours,
partie de la base telle qu'elle était au lancement. Un ticket mergé depuis
n'y est pas : il n'existe que sur `origin/<base>`. Vrais dépôts git (un distant
nu, le dépôt du run, un second clone qui merge le ticket).
"""
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.file_vivante import FileVivante
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.run_registry import RUN_REGISTRY

_PROJET = "mon-projet"
_NOUVEAU = "tickets/todo/ticket-503-sante.md"


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _clone(cwd: Path, bare: Path) -> None:
    cwd.mkdir(parents=True)
    _git(cwd, "init", "-q")
    _git(cwd, "config", "user.email", "test@tessera.local")
    _git(cwd, "config", "user.name", "Tessera test")
    _git(cwd, "remote", "add", "origin", str(bare))


def _contenu(tid: str, statut: str = "todo", depends_on: str = "") -> str:
    deps = f"depends_on: [{depends_on}]\n" if depends_on else ""
    return (
        f"---\nid: {tid}\ntitle: \"T {tid}\"\ntype: feat\nstatus: {statut}\n"
        f"priority: medium\nagent: codeur\n{deps}---\n\n# {tid}\n"
    )


def _ecrire(depot: Path, chemin: str, contenu: str) -> None:
    cible = depot / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(contenu, encoding="utf-8")


def _publier(depot: Path, message: str) -> None:
    _git(depot, "add", ".")
    _git(depot, "commit", "-q", "-m", message)
    _git(depot, "push", "-q", "origin", "develop")


@pytest.fixture
def depot_du_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Le dépôt du run, sur la branche du ticket-001 ; le ticket-503 n'y est pas."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "-q")
    ws = tmp_path / "workspace"
    local = ws / _PROJET
    _clone(local, bare)
    (local / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (local / "agents.json").write_text('{"base_branch": "develop"}', encoding="utf-8")
    _ecrire(local, "tickets/todo/ticket-001-premier.md", _contenu("ticket-001"))
    (local / "tickets" / "done").mkdir()
    (local / "tickets" / "done" / ".gitkeep").write_text("", encoding="utf-8")
    _git(local, "add", ".")
    _git(local, "commit", "-q", "-m", "init")
    _git(local, "branch", "-M", "develop")
    _git(local, "push", "-q", "--set-upstream", "origin", "develop")
    _git(local, "checkout", "-q", "-b", "ticket-001-en-cours")

    # Le merge de `chore: add ticket 503`, fait depuis un autre clone.
    autre = tmp_path / "autre"
    _clone(autre, bare)
    _git(autre, "fetch", "-q", "origin")
    _git(autre, "checkout", "-q", "-b", "develop", "origin/develop")
    _ecrire(autre, _NOUVEAU, _contenu("ticket-503"))
    _ecrire(autre, "tickets/done/ticket-502-livre.md", _contenu("ticket-502", "done"))
    _ecrire(
        autre, "tickets/todo/ticket-601-suite.md",
        _contenu("ticket-601", depends_on="ticket-502"),
    )
    _publier(autre, "chore: add ticket 503")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return local


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def run_file() -> Iterator[tuple[str, FileVivante]]:
    file = FileVivante(["ticket-001"])
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = file
    yield run.run_id, file
    RUN_REGISTRY.fermer(run.run_id)


def _ajouter(client: TestClient, run_id: str, ids: list[str]) -> dict[str, object]:
    resp = client.post(
        f"/api/v1/orchestrator/runs/{run_id}/append", json={"ticket_ids": ids}
    )
    assert resp.status_code == 200, resp.text
    body: dict[str, object] = resp.json()
    return body


def test_a_ticket_only_on_the_remote_base_is_accepted(
    client: TestClient, depot_du_run: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    assert not (depot_du_run / _NOUVEAU).exists()

    corps = _ajouter(client, run_id, ["ticket-503"])

    assert corps["ajoutes"] == ["ticket-503"]
    assert list(file) == ["ticket-001", "ticket-503"]


def test_a_ticket_absent_from_the_tree_and_the_base_stays_refused(
    client: TestClient, depot_du_run: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file

    corps = _ajouter(client, run_id, ["ticket-404"])

    assert corps["refuses"] == {"ticket-404": "ticket introuvable"}
    assert list(file) == ["ticket-001"]


def test_a_dependency_done_only_on_the_remote_base_is_met(
    client: TestClient, depot_du_run: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file

    corps = _ajouter(client, run_id, ["ticket-601"])

    assert corps["refuses"] == {}
    assert list(file) == ["ticket-001", "ticket-601"]


def _etat(depot: Path) -> dict[str, str]:
    return {
        "branche": _git(depot, "branch", "--show-current"),
        "head": _git(depot, "rev-parse", "HEAD"),
        "develop": _git(depot, "rev-parse", "develop"),
        "status": _git(depot, "status", "--porcelain"),
        "refs": _git(depot, "for-each-ref", "refs/heads"),
    }


def test_appending_leaves_the_run_tree_and_branches_untouched(
    client: TestClient, depot_du_run: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, _ = run_file
    avant = _etat(depot_du_run)

    corps = _ajouter(client, run_id, ["ticket-503", "ticket-601"])

    assert corps["ajoutes"] == ["ticket-503", "ticket-601"]
    assert _etat(depot_du_run) == avant
    assert avant["branche"] == "ticket-001-en-cours"
    assert not (depot_du_run / _NOUVEAU).exists()


async def test_the_reader_needs_a_declared_base(depot_du_run: Path) -> None:
    sans_base = GitWorkspaceService(depot_du_run, politique=PolitiqueRun())

    assert await sans_base.lire_ticket_sur_la_base("ticket-503") is None


async def test_the_reader_matches_the_id_strictly(depot_du_run: Path) -> None:
    espace = GitWorkspaceService(depot_du_run, politique=PolitiqueRun(base_branch="develop"))

    assert await espace.lire_ticket_sur_la_base("ticket-50") is None
    lu = await espace.lire_ticket_sur_la_base("ticket-503")
    assert lu is not None
    assert lu[0] == _NOUVEAU
    assert "id: ticket-503" in lu[1]


async def test_the_appended_ticket_later_starts_from_a_branch_that_holds_it(
    depot_du_run: Path,
) -> None:
    # Son tour : la file remet l'arbre sur la base, l'aligne sur le distant,
    # puis le ticket part de cette base (ticket-406, ticket-457).
    espace = GitWorkspaceService(depot_du_run, politique=PolitiqueRun(base_branch="develop"))
    assert await espace.lire_ticket_sur_la_base("ticket-503") is not None

    await espace.retourner_sur_base("develop")
    assert await espace.sync_base_depuis_distant("develop") is None
    branche = await espace.create_branch("ticket-503", "sante")

    contenu = _git(depot_du_run, "ls-tree", "-r", "--name-only", branche)
    assert _NOUVEAU in contenu.splitlines()
