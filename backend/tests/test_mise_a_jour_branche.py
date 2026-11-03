"""Merging a PR's base into its pushed head, in a throwaway worktree — ticket-732.

Chaque scénario monte un vrai dépôt et un distant nu : le checkout du projet
(`local`) ne connaît pas encore la tête de la branche, un second clone (`autre`)
joue les pushes qui ont eu lieu entre-temps.
"""
import json
import subprocess
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path

import pytest

from tessera.services import mise_a_jour_branche as module
from tessera.services.git_runner import GitResult
from tessera.services.mise_a_jour_branche import MiseAJour, mettre_a_jour_branche
from tessera.services.retest_apres_rebase import RetestApresRebase
from tessera.services.test_runner import TestResult

_BRANCHE = "ticket-732-merge"
_BASE = "develop"
_DOC = "memory/documentation.json"
_LOG = "memory/pipeline-log.md"
_SEED = {_DOC: '["a"]\n', _LOG: "l1\n", "src/app.py": "v0\n"}


def _sync(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _commit(clone: Path, branche: str, fichiers: dict[str, str], message: str) -> None:
    if _sync(clone, "branch", "--show-current") != branche:
        _sync(clone, "checkout", "-q", branche)
    for nom, contenu in fichiers.items():
        (clone / nom).parent.mkdir(parents=True, exist_ok=True)
        (clone / nom).write_text(contenu, encoding="utf-8", newline="")
        _sync(clone, "add", "--", nom)
    _sync(clone, "commit", "-q", "-m", message)
    _sync(clone, "push", "-q", "origin", branche)


def _cloner(bare: Path, cible: Path) -> Path:
    _sync(bare.parent, "clone", "-q", str(bare), str(cible))
    _sync(cible, "config", "user.email", "t@t.local")
    _sync(cible, "config", "user.name", "t")
    return cible


@dataclass
class Monde:
    bare: Path
    local: Path
    autre: Path
    tete: str

    def distante(self, branche: str) -> str:
        return _sync(self.bare, "rev-parse", f"refs/heads/{branche}")


def _monde(tmp_path: Path, branche: dict[str, str], base: dict[str, str]) -> Monde:
    bare = tmp_path / "bare.git"
    bare.mkdir()
    _sync(bare, "init", "-q", "--bare", "-b", _BASE)
    graine = _cloner(bare, tmp_path / "graine")
    _sync(graine, "symbolic-ref", "HEAD", f"refs/heads/{_BASE}")
    _commit(graine, _BASE, _SEED, "seed")
    local = _cloner(bare, tmp_path / "local")
    autre = _cloner(bare, tmp_path / "autre")
    _sync(autre, "checkout", "-q", "-b", _BRANCHE)
    _sync(autre, "push", "-q", "origin", _BRANCHE)
    _commit(autre, _BRANCHE, branche, "branch work")
    if base:
        _commit(autre, _BASE, base, "base work")
    (local / "notes.txt").write_text("à moi\n", encoding="utf-8")
    monde = Monde(bare, local, autre, "")
    monde.tete = monde.distante(_BRANCHE)
    return monde


def _instantane(depot: Path) -> tuple[str, str, str]:
    return (
        _sync(depot, "status", "--porcelain"),
        _sync(depot, "rev-parse", "HEAD"),
        _sync(depot, "branch", "--show-current"),
    )


def _fichier(monde: Monde, sha: str, chemin: str) -> str:
    return _sync(monde.bare, "show", f"{sha}:{chemin}")


def _espionner(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    commandes: list[tuple[str, ...]] = []
    reel = module.git

    async def espion(cwd: Path, *args: str) -> GitResult:
        commandes.append(args)
        return await reel(cwd, *args)

    monkeypatch.setattr(module, "git", espion)
    return commandes


class _GitMuet:
    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None:
        return False

    async def chemins_modifies(self, gauche: str, droite: str) -> list[str] | None:
        return None


class _Lanceur:
    def __init__(self, vert: bool) -> None:
        self.vert = vert
        self.appels = 0

    async def __call__(self) -> TestResult:
        self.appels += 1
        return TestResult(
            passed=self.vert, total=1, failed=0 if self.vert else 1, output_summary="1 test"
        )


def _retest(lanceur: _Lanceur) -> RetestApresRebase:
    return RetestApresRebase(_GitMuet(), lanceur, worktree=True)


async def _mettre_a_jour(monde: Monde, retest: RetestApresRebase | None = None) -> MiseAJour:
    return await mettre_a_jour_branche(monde.local, _BRANCHE, _BASE, monde.tete, retest)


async def test_a_branch_behind_its_base_is_merged_and_pushed(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {"autre.py": "o\n"})
    base = monde.distante(_BASE)
    resultat = await _mettre_a_jour(monde)
    assert resultat.arret is None and resultat.sha is not None
    assert resultat.sha == monde.distante(_BRANCHE)
    assert _sync(monde.bare, "rev-parse", f"{resultat.sha}^1") == monde.tete
    assert _sync(monde.bare, "rev-parse", f"{resultat.sha}^2") == base
    assert _sync(monde.bare, "log", "-1", "--format=%s", resultat.sha) == (
        f"chore: merge {_BASE} into {_BRANCHE}"
    )
    assert resultat.etapes


async def test_a_documentation_json_conflict_is_resolved_in_union(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {_DOC: '["a","b"]\n'}, {_DOC: '["a","c"]\n'})
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is not None, resultat.arret
    assert sorted(json.loads(_fichier(monde, resultat.sha, _DOC))) == ["a", "b", "c"]


async def test_a_pipeline_log_conflict_puts_the_base_first(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {_LOG: "l1\nbranche\n"}, {_LOG: "l1\nbase\n"})
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is not None, resultat.arret
    assert _fichier(monde, resultat.sha, _LOG) == "l1\nbase\nbranche"


async def test_a_code_conflict_refuses_and_pushes_nothing(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {"src/app.py": "v1\n"}, {"src/app.py": "v2\n"})
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is None
    assert resultat.arret is not None and "src/app.py" in resultat.arret
    assert monde.distante(_BRANCHE) == monde.tete


async def test_a_journal_conflict_next_to_a_code_conflict_refuses(tmp_path: Path) -> None:
    monde = _monde(
        tmp_path, {_LOG: "l1\nx\n", "src/app.py": "v1\n"}, {_LOG: "l1\ny\n", "src/app.py": "v2\n"}
    )
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is None and monde.distante(_BRANCHE) == monde.tete


async def test_an_unreadable_documentation_json_refuses(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {_DOC: "pas du json\n"}, {_DOC: '["a","c"]\n'})
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is None and monde.distante(_BRANCHE) == monde.tete


async def test_a_different_remote_head_refuses_before_any_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {"autre.py": "o\n"})
    _commit(monde.autre, _BRANCHE, {"encore.py": "e\n"}, "someone pushed")
    avancee = monde.distante(_BRANCHE)
    creations: list[str] = []
    reel = module.detached_worktree

    def espion(repo: Path, ref: str) -> AbstractAsyncContextManager[Path]:
        creations.append(ref)
        return reel(repo, ref)

    monkeypatch.setattr(module, "detached_worktree", espion)
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is None and resultat.arret is not None
    assert creations == []
    assert monde.distante(_BRANCHE) == avancee


async def test_a_refused_push_is_not_retried_and_never_forced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {"autre.py": "o\n"})
    commandes = _espionner(monkeypatch)

    async def lancer() -> TestResult:
        _commit(monde.autre, _BRANCHE, {"entre.py": "x\n"}, "pushed meanwhile")
        return TestResult(passed=True, total=1, failed=0, output_summary="ok")

    resultat = await _mettre_a_jour(monde, RetestApresRebase(_GitMuet(), lancer, worktree=True))
    assert resultat.sha is None and resultat.arret is not None
    assert len([c for c in commandes if "push" in c]) == 1
    assert not [c for c in commandes if any(a.startswith("--force") for a in c)]
    assert "--force" not in Path(module.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("scenario", ["succes", "conflit", "tete"])
async def test_the_project_checkout_is_untouched(tmp_path: Path, scenario: str) -> None:
    base = {"src/app.py": "v2\n"} if scenario == "conflit" else {"o.py": "o\n"}
    monde = _monde(tmp_path, {"src/app.py": "v1\n"}, base)
    attendue = "0" * 40 if scenario == "tete" else monde.tete
    avant = _instantane(monde.local)
    resultat = await mettre_a_jour_branche(monde.local, _BRANCHE, _BASE, attendue)
    assert (resultat.sha is not None) == (scenario == "succes")
    assert _instantane(monde.local) == avant
    assert len(_sync(monde.local, "worktree", "list").splitlines()) == 1


async def test_a_red_retest_refuses_without_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {"autre.py": "o\n"})
    commandes = _espionner(monkeypatch)
    lanceur = _Lanceur(vert=False)
    resultat = await _mettre_a_jour(monde, _retest(lanceur))
    assert resultat.sha is None and resultat.arret is not None
    assert "rouges" in resultat.arret
    assert monde.distante(_BRANCHE) == monde.tete
    assert not [c for c in commandes if "push" in c]


async def test_a_green_retest_lets_the_update_through(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {"autre.py": "o\n"})
    lanceur = _Lanceur(vert=True)
    resultat = await _mettre_a_jour(monde, _retest(lanceur))
    assert lanceur.appels == 1
    assert resultat.sha == monde.distante(_BRANCHE)
    assert any("verts" in e for e in resultat.etapes)


async def test_a_branch_already_carrying_its_base_refuses(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {"feature.py": "f\n"}, {})
    resultat = await _mettre_a_jour(monde)
    assert resultat.sha is None and resultat.arret is not None
    assert monde.distante(_BRANCHE) == monde.tete


async def test_an_unreachable_repository_is_a_refusal_not_an_exception(tmp_path: Path) -> None:
    resultat = await mettre_a_jour_branche(tmp_path / "absent", _BRANCHE, _BASE, "a" * 40)
    assert resultat.sha is None and resultat.arret


async def test_the_worktree_is_removed_after_a_refusal(tmp_path: Path) -> None:
    monde = _monde(tmp_path, {"src/app.py": "v1\n"}, {"src/app.py": "v2\n"})
    await _mettre_a_jour(monde)
    assert len(_sync(monde.local, "worktree", "list").splitlines()) == 1

