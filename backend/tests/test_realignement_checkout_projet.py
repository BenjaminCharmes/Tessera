"""The project checkout follows its base — ticket-978.

Couverture :
- `surveillance_pour` donne à `CIWatcher` un `Realignement` sur le checkout du
  projet quand le run a un worktree.
- `_realigner_si_libre` réaligne un projet à worktree même occupé, jamais un
  projet sans worktree occupé.
- `lancer_les_services` lit l'`agents.json` du commit avancé, et démarre quand
  le réalignement refuse.
"""
import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.config import settings
from tessera.routers.services import lancer_les_services
from tessera.services.livraison import ci_watcher as ci_module
from tessera.services.livraison import surveillance_run
from tessera.services.livraison.ci_watcher import CIWatcher
from tessera.services.livraison.realignement_base import Realignement
from tessera.services.pipeline.run_registry import RUN_REGISTRY
from tessera.services.verification.process_registry import ProcessRegistry
from tessera.services.worktrees.run_worktree import RunWorktree

_DORMEUR = f'"{sys.executable}" -c "import time; time.sleep(30)"'


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


def _ecrire_manifeste(dossier: Path, nom: str) -> None:
    manifeste = {"project_id": "alpha", "base_branch": "main", "services": [{"nom": nom, "commande": _DORMEUR}]}
    (dossier / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")


@pytest.fixture
async def depot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[Path, Path]]:
    """A workspace holding `alpha`, one commit behind `origin/main` (clean tree)."""
    distant = tmp_path / "distant.git"
    await _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(distant))
    amont = tmp_path / "amont"
    await _git(tmp_path, "clone", "-q", str(distant), str(amont))
    for cle, val in (("user.email", "t@tessera.local"), ("user.name", "Test")):
        await _git(amont, "config", cle, val)
    await _git(amont, "symbolic-ref", "HEAD", "refs/heads/main")
    (amont / "CLAUDE.md").write_text("# alpha\n", encoding="utf-8")
    _ecrire_manifeste(amont, "ancien")
    await _git(amont, "add", ".")
    await _git(amont, "commit", "-q", "-m", "init")
    await _git(amont, "push", "-q", "-u", "origin", "main")
    ws = tmp_path / "workspace"
    ws.mkdir()
    await _git(tmp_path, "clone", "-q", str(distant), str(ws / "alpha"))
    _ecrire_manifeste(amont, "nouveau")
    await _git(amont, "commit", "-q", "-am", "services")
    await _git(amont, "push", "-q", "origin", "main")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    yield ws / "alpha", amont


async def _lancer() -> list[str]:
    registre = ProcessRegistry()
    sonde = MagicMock()
    sonde.ecouteurs = AsyncMock(return_value={})
    sonde.processus = AsyncMock(return_value={})
    try:
        etat = await lancer_les_services("alpha", sonde, registre)
        return [s.nom for s in etat.services]
    finally:
        await registre.tout_arreter()


async def test_services_read_the_advanced_manifest(depot: tuple[Path, Path]) -> None:
    assert await _lancer() == ["nouveau"]


async def test_services_start_when_realignment_refuses(depot: tuple[Path, Path]) -> None:
    local, _ = depot
    await _git(local, "checkout", "-q", "-b", "ticket-001-autre")

    assert await _lancer() == ["ancien"]


def test_surveillance_hands_the_checkout_to_the_watcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    (ws / "alpha").mkdir(parents=True)
    (ws / "alpha" / "CLAUDE.md").write_text("# alpha\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    watcher = MagicMock()
    watcher.surveiller = AsyncMock()
    monkeypatch.setattr(ci_module, "CI_WATCHER", watcher)
    wt = RunWorktree(racine=tmp_path / "wt", projet=tmp_path / "wt", branche="b")
    surveiller = surveillance_run.surveillance_pour("alpha", wt=wt)

    asyncio.run(surveiller("alpha", "ticket-001", 5, AsyncMock()))

    donne = watcher.surveiller.await_args.kwargs["realignement"]
    assert donne.racine == ws / "alpha"
    assert donne.projet_a_worktree is True


@pytest.mark.parametrize("worktree, appele", [(True, True), (False, False)])
async def test_realignement_while_a_run_holds_the_project(
    monkeypatch: pytest.MonkeyPatch, worktree: bool, appele: bool
) -> None:
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(ci_module, "realigner_base", mock)
    watcher = CIWatcher()
    watcher._realignements["p-978:t-1"] = Realignement(Path("x"), "main", worktree)
    run = RUN_REGISTRY.ouvrir("p-978", "t-2")
    try:
        await watcher._realigner_si_libre("p-978", "t-1")
    finally:
        RUN_REGISTRY.fermer(run.run_id)

    assert mock.await_count == (1 if appele else 0)
