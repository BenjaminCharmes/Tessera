"""Un worktree se délie avant de se supprimer, et le `.env` de Tessera n'y entre pas — ticket-523."""
import ast
import json
import os
import shutil
from pathlib import Path

import pytest

from tessera.config import Settings, settings
from tessera.models.worktree_config import ConfigWorktree
from tessera.services import run_worktree
from tessera.services.run_worktree import RunWorktree, creer, supprimer
from tessera.services.run_worktree_populate import peupler
from tessera.services.worktree_politique import lire_worktree
from tests.depot_worktree import BRANCHE, construire


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return construire(tmp_path, monkeypatch)


async def test_supprimer_unlinks_before_any_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    racine = settings.ide_worktrees_dir / "demo" / "ticket-1"
    racine.mkdir(parents=True)
    appels: list[str] = []

    def liens(_racine: Path) -> list[Path]:
        appels.append("liens")
        return []

    async def git(_cwd: Path, *args: str) -> str:
        appels.append("git " + " ".join(args[:2]))
        return ""

    def arbre(*_args: object, **_kwargs: object) -> None:
        appels.append("rmtree")

    monkeypatch.setattr(run_worktree, "retirer_les_liens", liens)
    monkeypatch.setattr(run_worktree, "run_git", git)
    monkeypatch.setattr(shutil, "rmtree", arbre)
    await supprimer(RunWorktree(racine=racine, projet=racine, branche=BRANCHE), tmp_path)
    destructifs = [i for i, a in enumerate(appels) if a in ("rmtree", "git worktree remove")]
    assert "git worktree remove" in appels
    assert appels[0] == "liens"
    assert all(i > appels.index("liens") for i in destructifs)


def _noeuds_de_suppression(fonction: ast.FunctionDef | ast.AsyncFunctionDef) -> list[int]:
    """Lines of the calls that delete: `rmtree`, or a git call carrying `"remove"`."""
    lignes: list[int] = []
    for noeud in ast.walk(fonction):
        if not isinstance(noeud, ast.Call):
            continue
        nom = noeud.func.attr if isinstance(noeud.func, ast.Attribute) else ""
        porte_remove = any(isinstance(a, ast.Constant) and a.value == "remove" for a in noeud.args)
        if nom == "rmtree" or porte_remove:
            lignes.append(noeud.lineno)
    return lignes


def _lignes_de_liens(fonction: ast.FunctionDef | ast.AsyncFunctionDef) -> list[int]:
    return [
        n.lineno for n in ast.walk(fonction)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "retirer_les_liens"
    ]


def test_every_function_that_deletes_unlinks_first() -> None:
    source = Path(run_worktree.__file__).read_text(encoding="utf-8")
    verifiees = 0
    for noeud in ast.walk(ast.parse(source)):
        if not isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        suppressions = _noeuds_de_suppression(noeud)
        if suppressions:
            verifiees += 1
            liens = _lignes_de_liens(noeud)
            assert liens and min(liens) < min(suppressions), noeud.name
    assert verifiees >= 1


async def test_the_env_file_of_tessera_is_neither_copied_nor_linked(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (checkout / ".env").write_text("JETON=secret", encoding="utf-8")
    monkeypatch.setattr(Settings, "env_file", checkout / ".env")
    populate = [{"path": ".env", "mode": "copy"}, {"path": ".env", "mode": "link"},
                {"path": "secret.cfg", "mode": "copy"}]
    (checkout / "agents.json").write_text(
        json.dumps({"worktree": {"populate": populate}}), encoding="utf-8"
    )
    config = lire_worktree(checkout, checkout, "tracked")
    assert isinstance(config, ConfigWorktree)
    wt = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop")
    absents = await peupler(wt, checkout, config)
    assert absents == []
    assert not os.path.lexists(wt.racine / ".env")
    assert (wt.racine / "secret.cfg").is_file()
