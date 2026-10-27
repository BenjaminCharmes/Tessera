"""Le retest après rebase ne repasse que si la base touche une chaîne de la branche — ticket-584.

Couverture :
- base frontend seule, branche backend seule : pas de retest ;
- base et branche sur backend (ou scripts + backend) : retest ;
- chemins illisibles (git qui lève, `None`) : retest ;
- projet sans `scripts/verifier.py` : retest dès que la base a avancé ;
- les préfixes de chaînes du backend sont ceux de `scripts/verifier.py` ;
- `chemins_modifies` lit les deux côtés d'un vrai dépôt git.
"""
import importlib.util
import inspect
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from tessera.services.chaines_de_test import (
    PREFIXES_BACKEND,
    PREFIXES_FRONTEND,
    chaine_commune,
    chaines_touchees,
)
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.retest_apres_rebase import RetestApresRebase, retest_du_run
from tessera.services.test_runner import TestResult

_VERIFIER = Path(__file__).resolve().parents[2] / "scripts" / "verifier.py"


class _Git:
    """A git double: the ancestry answer, and the paths each side of the range brings."""

    def __init__(
        self,
        base: list[str] | None,
        branche: list[str] | None,
        leve: bool = False,
    ) -> None:
        self.base = base
        self.branche = branche
        self.leve = leve
        self.appels: list[tuple[str, str]] = []

    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None:
        return False

    async def chemins_modifies(self, gauche: str, droite: str) -> list[str] | None:
        self.appels.append((gauche, droite))
        if self.leve:
            raise OSError("git absent")
        return self.base if gauche == "HEAD" else self.branche


async def _lancer() -> TestResult:
    return TestResult(passed=True, total=1, failed=0, output_summary="ok")


def _retest(git: _Git, verifier: bool = True, worktree: bool = False) -> RetestApresRebase:
    return RetestApresRebase(git, _lancer, worktree=worktree, verifier=verifier)


async def test_frontend_only_base_does_not_retest_a_backend_branch() -> None:
    git = _Git(["frontend/src/a.tsx", "projects/x/tickets/t.md"], ["backend/src/a.py"])

    assert await _retest(git).base_a_avance("develop") is False
    assert git.appels == [("HEAD", "develop"), ("develop", "HEAD")]


@pytest.mark.parametrize(
    ("base", "branche"),
    [
        (["backend/src/a.py"], ["backend/tests/test_a.py"]),
        (["scripts/verifier.py"], ["backend/src/a.py"]),
        (["backend/src/a.py"], ["scripts/x.py", "docs/a.md"]),
        (["frontend/a.ts"], ["frontend/b.ts", "backend/c.py"]),
    ],
)
async def test_shared_chain_retests(base: list[str], branche: list[str]) -> None:
    assert await _retest(_Git(base, branche)).base_a_avance("develop") is True


async def test_base_and_branch_outside_every_chain_do_not_retest() -> None:
    git = _Git(["docs/a.md"], ["tickets/t.md"])

    assert await _retest(git).base_a_avance("develop") is False


@pytest.mark.parametrize(
    "git",
    [_Git(None, ["backend/a.py"]), _Git(["frontend/a.ts"], None), _Git(None, None),
     _Git(["frontend/a.ts"], ["backend/a.py"], leve=True)],
)
async def test_unreadable_paths_retest(git: _Git) -> None:
    assert await _retest(git).base_a_avance("develop") is True


async def test_project_without_verifier_retests_as_soon_as_the_base_moved() -> None:
    git = _Git(["frontend/a.ts"], ["backend/a.py"])

    assert await _retest(git, verifier=False).base_a_avance("develop") is True
    assert git.appels == []


async def test_worktree_compares_the_paths_with_the_remote_base() -> None:
    git = _Git(["frontend/a.ts"], ["backend/a.py"])

    await _retest(git, worktree=True).base_a_avance("develop")

    assert git.appels == [("HEAD", "origin/develop"), ("origin/develop", "HEAD")]


def test_retest_du_run_detects_the_verifier_in_the_test_cwd(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "verifier.py").write_text("", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    # Comme ide-core : le code est au-dessus du projet (ADR-028).
    (projet / "agents.json").write_text('{"git_root": "ancestor"}', encoding="utf-8")

    avec = retest_du_run(MagicMock(), False, MagicMock(), projet, "cmd", "../..")
    sans = retest_du_run(MagicMock(), False, MagicMock(), projet, "cmd")
    hors = retest_du_run(MagicMock(), False, MagicMock(), projet, "cmd", "../../..")

    assert avec is not None and avec._verifier is True
    assert sans is not None and sans._verifier is False
    assert hors is not None and hors._verifier is False


def test_chaines_touchees_names_each_chain() -> None:
    assert chaines_touchees(["backend/a.py"]) == {"backend"}
    assert chaines_touchees(["scripts/v.py", "frontend/a.ts"]) == {"backend", "frontend"}
    assert chaines_touchees(["docs/a.md", "backendx/a.py"]) == frozenset()
    assert chaine_commune([], ["backend/a.py"]) is False


def _charger_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verifier_du_depot", _VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Ses dataclasses retrouvent leur module par `sys.modules`.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not _VERIFIER.is_file(), reason="scripts/verifier.py absent de ce clone")
def test_prefixes_are_those_of_the_verifier() -> None:
    verifier = _charger_verifier()

    for prefixe in PREFIXES_BACKEND:
        assert verifier.chains_for([prefixe + "x"]) == (True, False)
    for prefixe in PREFIXES_FRONTEND:
        assert verifier.chains_for([prefixe + "x"]) == (False, True)
    assert verifier.chains_for(["docs/x", "tickets/x"]) == (False, False)
    # Un préfixe ajouté au verifier sans l'être ici se voit dans sa source.
    cites = set(re.findall(r'"([a-z]+/)"', inspect.getsource(verifier.chains_for)))
    assert cites == set(PREFIXES_BACKEND) | set(PREFIXES_FRONTEND)


def _git(depot: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=depot, check=True, capture_output=True,
    )


async def test_chemins_modifies_reads_each_side_of_a_real_repository(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "init")
    _git(tmp_path, "checkout", "-q", "-b", "ticket")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "b.py").write_text("b", encoding="utf-8")
    _git(tmp_path, "add", "backend/b.py")
    _git(tmp_path, "commit", "-q", "-m", "branche")
    _git(tmp_path, "checkout", "-q", "main")
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "c.ts").write_text("c", encoding="utf-8")
    _git(tmp_path, "add", "frontend/c.ts")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "checkout", "-q", "ticket")
    espace = GitWorkspaceService(tmp_path)

    assert await espace.chemins_modifies("HEAD", "main") == ["frontend/c.ts"]
    assert await espace.chemins_modifies("main", "HEAD") == ["backend/b.py"]
    assert await espace.chemins_modifies("HEAD", "inconnue") is None
