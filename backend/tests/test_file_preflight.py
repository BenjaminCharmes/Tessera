"""A queue refuses, before it opens, a ticket missing from where its runs start — ticket-849."""
import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline.controle_base import absents_de_la_base, refus_avant_ouverture, refuser_absents_de_la_base
from tessera.services.pipeline.file_vivante import FileVivante, lecteur_sur_la_base, trier_ajouts
from tessera.services.pipeline.run_registry import RUN_REGISTRY
from tessera.services.projets.ticket_service import TicketService

_PROJET = "mon-projet"
_IDENTITE = ["-c", "user.name=tester", "-c", "user.email=tester@example.com"]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *_IDENTITE, *args], cwd=cwd, check=True, capture_output=True)


def _ecrire_ticket(projet: Path, tid: str) -> None:
    (projet / "tickets" / "todo").mkdir(parents=True, exist_ok=True)
    (projet / "tickets" / "todo" / f"{tid}-titre.md").write_text(
        f"---\nid: {tid}\ntitle: \"T {tid}\"\ntype: feat\nstatus: todo\n"
        f"priority: medium\nagent: codeur\n---\n\n# {tid}\n",
        encoding="utf-8",
    )


def _declarer_worktree(projet: Path) -> None:
    manifeste = {"artifacts": "tracked", "base_branch": "develop", "worktree": {}}
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


@pytest.fixture
def client(workspace: Path) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _projet_sans_git(workspace: Path) -> Path:
    projet = workspace / _PROJET
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    return projet


def _projet_a_worktree(workspace: Path, tmp_path: Path) -> Path:
    """A worktree project whose base holds ticket-001 and whose tree also holds ticket-002."""
    projet = _projet_sans_git(workspace)
    _declarer_worktree(projet)
    _ecrire_ticket(projet, "ticket-001")
    origine = tmp_path / "origine.git"
    subprocess.run(["git", "init", "--bare", str(origine)], check=True, capture_output=True)
    _git(projet, "init", "-b", "develop")
    _git(projet, "add", "CLAUDE.md", "agents.json", "tickets")
    _git(projet, "commit", "-m", "chore: seed")
    _git(projet, "remote", "add", "origin", str(origine))
    _git(projet, "push", "origin", "develop")
    _ecrire_ticket(projet, "ticket-002")  # dans l'arbre seulement, jamais poussé
    return projet


def _lancer(client: TestClient, ids: list[str]):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/v1/orchestrator/run",
        json={"project_id": _PROJET, "mode": "queue", "ticket_ids": ids, "force": True},
    )


def test_queue_with_ticket_missing_from_base_is_refused_with_names(
    client: TestClient, workspace: Path, tmp_path: Path
) -> None:
    _projet_a_worktree(workspace, tmp_path)

    reponse = _lancer(client, ["ticket-001", "ticket-002"])

    assert reponse.status_code == 422, reponse.text
    detail = reponse.json()["detail"]
    assert "ticket-002" in detail
    assert "ticket-001" not in detail
    assert "origin/develop" in detail


def test_refused_queue_takes_no_lock(
    client: TestClient, workspace: Path, tmp_path: Path
) -> None:
    _projet_a_worktree(workspace, tmp_path)

    assert _lancer(client, ["ticket-002"]).status_code == 422

    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001")  # lève RunAlreadyInProgress si pris
    RUN_REGISTRY.fermer(run.run_id)


def test_unreadable_git_opens_the_queue(
    client: TestClient, workspace: Path
) -> None:
    projet = _projet_sans_git(workspace)
    _declarer_worktree(projet)  # un worktree déclaré, mais aucun dépôt git à lire
    _ecrire_ticket(projet, "ticket-002")

    reponse = _lancer(client, ["ticket-002"])

    # Le contrôle ne juge pas : le refus éventuel vient d'une autre règle.
    assert "absent(s) de la base" not in str(reponse.json().get("detail", ""))


async def test_unreadable_git_reports_no_absent_ticket(workspace: Path) -> None:
    projet = _projet_sans_git(workspace)
    _declarer_worktree(projet)

    assert await absents_de_la_base(projet, ["ticket-002"]) == []


def test_project_without_worktree_reads_the_tree(
    client: TestClient, workspace: Path
) -> None:
    projet = _projet_sans_git(workspace)
    _ecrire_ticket(projet, "ticket-001")

    reponse = _lancer(client, ["ticket-001", "ticket-009"])

    assert reponse.status_code == 422, reponse.text
    assert "ticket-009" in reponse.json()["detail"]
    assert "ticket-001" not in reponse.json()["detail"]


async def test_project_without_worktree_accepts_tickets_found_in_the_tree(
    workspace: Path,
) -> None:
    projet = _projet_sans_git(workspace)
    _ecrire_ticket(projet, "ticket-001")

    refus = await refus_avant_ouverture(
        projet, TicketService(projet, _PROJET), ["ticket-001"]
    )

    assert refus is None


async def test_append_refuses_a_ticket_absent_from_the_base(
    workspace: Path, tmp_path: Path
) -> None:
    _projet_a_worktree(workspace, tmp_path)
    acceptes = ["ticket-001", "ticket-002"]
    refuses: dict[str, str] = {}

    await refuser_absents_de_la_base(workspace / _PROJET, acceptes, refuses)

    assert acceptes == ["ticket-001"]
    assert list(refuses) == ["ticket-002"]


def _projet_ticket_sur_la_base_seulement(
    workspace: Path, tmp_path: Path, avec_remote: bool = True
) -> Path:
    """A project without worktree: ticket-001 only on origin/develop, not in the tree."""
    projet = _projet_sans_git(workspace)
    (projet / "agents.json").write_text(json.dumps({"base_branch": "develop"}), encoding="utf-8")
    _ecrire_ticket(projet, "ticket-001")
    _git(projet, "init", "-b", "develop")
    _git(projet, "add", "CLAUDE.md", "agents.json", "tickets")
    _git(projet, "commit", "-m", "chore: seed")
    if avec_remote:
        origine = tmp_path / "origine.git"
        subprocess.run(["git", "init", "--bare", str(origine)], check=True, capture_output=True)
        _git(projet, "remote", "add", "origin", str(origine))
        _git(projet, "push", "origin", "develop")
    shutil.rmtree(projet / "tickets")  # absent de l'arbre, présent sur la base
    return projet


async def test_no_worktree_ticket_only_on_the_base_is_not_refused(
    workspace: Path, tmp_path: Path
) -> None:
    projet = _projet_ticket_sur_la_base_seulement(workspace, tmp_path)

    refus = await refus_avant_ouverture(projet, TicketService(projet, _PROJET), ["ticket-001"])

    assert refus is None


async def test_no_worktree_ticket_absent_everywhere_is_still_refused(
    workspace: Path, tmp_path: Path
) -> None:
    projet = _projet_ticket_sur_la_base_seulement(workspace, tmp_path)

    refus = await refus_avant_ouverture(
        projet, TicketService(projet, _PROJET), ["ticket-001", "ticket-009"]
    )

    assert refus is not None and "introuvable" in refus
    assert "ticket-009" in refus and "ticket-001" not in refus


async def test_no_worktree_unreachable_remote_keeps_the_tree_rule(
    workspace: Path, tmp_path: Path
) -> None:
    projet = _projet_ticket_sur_la_base_seulement(workspace, tmp_path, avec_remote=False)

    refus = await refus_avant_ouverture(projet, TicketService(projet, _PROJET), ["ticket-001"])

    assert refus is not None and "introuvable" in refus


async def test_append_accepts_a_base_only_ticket_without_worktree(
    workspace: Path, tmp_path: Path
) -> None:
    projet = _projet_ticket_sur_la_base_seulement(workspace, tmp_path)
    repli = lecteur_sur_la_base(
        GitWorkspaceService(projet, politique=PolitiqueRun.lire(projet)), _PROJET
    )

    acceptes, _, refuses = await trier_ajouts(
        FileVivante(), TicketService(projet, _PROJET), ["ticket-001"], repli
    )
    await refuser_absents_de_la_base(projet, acceptes, refuses)

    assert acceptes == ["ticket-001"]
    assert refuses == {}
