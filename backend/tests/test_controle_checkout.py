"""A run refuses a checkout left on a foreign branch — ticket-1048."""
import json
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from tessera.config import settings
from tessera.models.run_request import RunRequest
from tessera.routers import orchestrator as routeur
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.pipeline.controle_checkout import realigner_avant_construction, refus_checkout_etranger
from tessera.services.pipeline.run_registry import RUN_REGISTRY


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _manifeste(root: Path, **champs: object) -> None:
    (root / "agents.json").write_text(json.dumps(champs), encoding="utf-8")


def _depot(root: Path, **manifeste: object) -> Path:
    root.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@Tessera.local")
    _git(root, "config", "user.name", "Tessera test")
    _manifeste(root, base_branch="main", **manifeste)
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def test_foreign_branch_is_refused_and_names_it(tmp_path: Path) -> None:
    projet = _depot(tmp_path / "projet")
    _git(projet, "checkout", "-q", "-b", "autre-travail")
    branches_avant = _git(projet, "branch", "--list")

    refus = refus_checkout_etranger(projet, PolitiqueRun.lire(projet))

    assert refus is not None and "autre-travail" in refus
    assert _git(projet, "branch", "--list") == branches_avant


def test_base_branch_is_accepted(tmp_path: Path) -> None:
    projet = _depot(tmp_path / "projet")

    assert refus_checkout_etranger(projet, PolitiqueRun.lire(projet)) is None


def test_branch_of_an_existing_ticket_is_accepted(tmp_path: Path) -> None:
    projet = _depot(tmp_path / "projet")
    (projet / "tickets" / "todo").mkdir(parents=True)
    (projet / "tickets" / "todo" / "ticket-007-x.md").write_text("# t\n", encoding="utf-8")
    _git(projet, "checkout", "-q", "-b", "ticket-007-x")

    assert refus_checkout_etranger(projet, PolitiqueRun.lire(projet)) is None


def test_branch_of_a_missing_ticket_is_refused(tmp_path: Path) -> None:
    projet = _depot(tmp_path / "projet")
    _git(projet, "checkout", "-q", "-b", "ticket-008-y")

    refus = refus_checkout_etranger(projet, PolitiqueRun.lire(projet))

    assert refus is not None and "ticket-008-y" in refus


def test_worktree_project_is_never_refused(tmp_path: Path) -> None:
    projet = _depot(tmp_path / "projet", worktree={}, artifacts="tracked")
    _git(projet, "checkout", "-q", "-b", "autre-travail")
    politique = PolitiqueRun.lire(projet)

    assert politique.worktree is not None
    assert refus_checkout_etranger(projet, politique) is None


@pytest.mark.asyncio
async def test_policy_comes_from_the_realigned_base(tmp_path: Path) -> None:
    distant = tmp_path / "distant.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(distant))
    projet = _depot(tmp_path / "projet", autonomy="pr")
    _git(projet, "remote", "add", "origin", str(distant))
    _git(projet, "push", "-q", "origin", "main")
    autre = tmp_path / "autre"
    _git(tmp_path, "clone", "-q", str(distant), str(autre))
    _git(autre, "config", "user.email", "test@Tessera.local")
    _git(autre, "config", "user.name", "Tessera test")
    _manifeste(autre, base_branch="main", autonomy="merge")
    _git(autre, "commit", "-q", "-am", "autonomy")
    _git(autre, "push", "-q", "origin", "main")
    assert PolitiqueRun.lire(projet).autonomy.value == "pr"

    politique = await realigner_avant_construction(projet)

    assert politique.autonomy.value == "merge"


@pytest.mark.asyncio
async def test_route_refuses_before_reserving_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    _depot(tmp_path / "p1")
    _git(tmp_path / "p1", "checkout", "-q", "-b", "autre-travail")
    monkeypatch.setattr(routeur, "refus_des_manques", lambda *a, **k: None)
    ouverts: list[object] = []
    monkeypatch.setattr(RUN_REGISTRY, "ouvrir", lambda *a, **k: ouverts.append(a))

    with pytest.raises(HTTPException) as exc:
        await routeur.run_pipeline(RunRequest(project_id="p1", mode="single", ticket_id="ticket-001"))

    assert exc.value.status_code == 422
    assert "autre-travail" in str(exc.value.detail)
    assert ouverts == []
