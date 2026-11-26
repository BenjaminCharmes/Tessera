"""Tests for scripts/banc_codeur_cellule.py and banc_codeur.py (ticket-1055). No model is called."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import banc_codeur as bc  # noqa: E402
import banc_codeur_cellule as cell  # noqa: E402
from banc_codeur_bras import Bras  # noqa: E402
from banc_codeur_cellule import Appel, Controle, IndisponibleErreur, Roles  # noqa: E402
from banc_codeur_corpus import Corpus, CorpusInvalide, Entree, sans_frontmatter, somme_texte  # noqa: E402

_TICKET = "---\nid: 1\n---\n# Ticket\n\n## Critères d'acceptation\n- [ ] ok\n"
_GEL = "g" * 64


def _git(depot: Path, *args: str) -> str:
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@localhost", "-c", "commit.gpgsign=false"]
    sortie = subprocess.run([*cmd, "-C", str(depot), *args], capture_output=True, check=True)
    return sortie.stdout.decode().strip()


@pytest.fixture
def depot(tmp_path: Path) -> tuple[Path, Entree]:
    d = tmp_path / "depot"
    d.mkdir()
    _git(d, "init", "-q")
    (d / "tickets").mkdir()
    (d / "tickets" / "ticket-1-x.md").write_text(_TICKET, encoding="utf-8")
    (d / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "base")
    base = _git(d, "rev-parse", "HEAD")
    (d / "code.py").write_text("x = 2\n", encoding="utf-8")
    (d / "test_code.py").write_text("def test_x(): pass\n", encoding="utf-8")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "solution")
    sha = _git(d, "rev-parse", "HEAD")
    entree = Entree(
        id="e1", ticket="1", sha=sha, base_sha=base, ticket_chemin="tickets/ticket-1-x.md",
        ticket_sha256=somme_texte(sans_frontmatter(_TICKET)),
        fichiers=("code.py", "test_code.py"), lignes_ajoutees=40, pilote=False,
    )
    return d, entree


def _roles(*, env: bool = True, verts: bool = True, approuve: list[bool] | None = None,
           cout: float = 0.5, appels: list[str] | None = None) -> Roles:
    decisions = list(approuve if approuve is not None else [True])

    async def faire_env(_: Path) -> bool:
        return env

    async def coder(cwd: Path, ticket: str, retour: str) -> Appel:
        if appels is not None:
            appels.append(retour)
        (cwd / "code.py").write_text("x = 3\n", encoding="utf-8")
        return Appel(cout, (10, 20, 30), 100)

    async def tester(_: Path) -> bool:
        return verts

    async def controler(_c: Path, _t: str, _v: bool) -> Controle:
        return Controle(decisions.pop(0), "corrige", 0.1)

    return Roles(env=faire_env, coder=coder, tester=tester, controler=controler)


async def _cellule(depot: tuple[Path, Entree], tmp: Path, roles: Roles) -> cell.Resultat:
    return await cell.rejouer_cellule(
        depot[1], "A", "modele", _GEL, roles, depot=depot[0], racine_copies=tmp / "copies"
    )


def test_copy_has_one_commit_and_no_real_diff(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    cible = tmp_path / "copie"
    cell.copier_sans_historique(d, entree.base_sha, cible)
    assert len(_git(cible, "log", "--all", "--format=%H").splitlines()) == 1
    assert (cible / "code.py").read_text() == "x = 1\n"
    assert not (cible / "test_code.py").exists()
    assert entree.sha not in _git(cible, "log", "--all", "--format=%H%n%B")


@pytest.mark.asyncio
async def test_first_round_approval(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    res = await _cellule(depot, tmp_path, _roles())
    assert (res.etat, res.tours, res.approuve_t1, res.approuve_final) == ("ok", 1, True, True)
    assert res.jetons == {"entree": 10, "sortie": 20, "cache": 30}
    assert res.cout_codeur_usd == 0.5 and res.cout_controles_usd == 0.1
    assert res.gel_sha256 == _GEL and res.tests_reference_verts is True


@pytest.mark.asyncio
async def test_three_rounds_then_stop_with_feedback(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    appels: list[str] = []
    res = await _cellule(depot, tmp_path, _roles(approuve=[False, False, False], appels=appels))
    assert (res.tours, res.approuve_t1, res.approuve_final) == (3, False, False)
    assert appels == ["", "corrige", "corrige"]


@pytest.mark.asyncio
async def test_red_tests_refuse_even_when_reviewers_approve(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    res = await _cellule(depot, tmp_path, _roles(verts=False, approuve=[True, True, True]))
    assert not res.approuve_final and not res.tests_verts


@pytest.mark.asyncio
async def test_cell_cap_and_env_failure(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    cher = await _cellule(depot, tmp_path, _roles(cout=7.0))
    assert cher.etat == "plafond_cellule" and cher.tours == 1
    ko = await _cellule(depot, tmp_path, _roles(env=False))
    assert ko.etat == "echec_env" and ko.tours is None


@pytest.mark.asyncio
async def test_unavailable_provider_is_recorded(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    base = _roles()

    async def coder(*_: object) -> Appel:
        raise IndisponibleErreur("hors ligne")

    roles = Roles(env=base.env, coder=coder, tester=base.tester, controler=base.controler)
    assert (await _cellule(depot, tmp_path, roles)).etat == "indisponible"


@pytest.mark.asyncio
async def test_ticket_sum_mismatch_refuses(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    mauvais = replace(depot[1], ticket_sha256="0" * 64)
    with pytest.raises(CorpusInvalide):
        await _cellule((depot[0], mauvais), tmp_path, _roles())


def test_reference_tests_are_laid_after_the_fact(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    cible = tmp_path / "copie"
    cell.copier_sans_historique(d, entree.base_sha, cible)
    cell.poser_tests_reference(d, entree, cible)
    assert (cible / "test_code.py").exists()
    assert (cible / "code.py").read_text() == "x = 1\n"


@pytest.mark.asyncio
async def test_rejouer_resumes_checks_gel_and_budget(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    corpus = Corpus(entrees=(entree,), gel_sha256=_GEL)
    bras = Bras(id="A", modele="m", provider="agent_sdk", prompt="p")
    sortie = tmp_path / "r.jsonl"
    args = {"depot": d, "sortie": sortie, "racine_copies": tmp_path / "c"}
    premiers = await bc.rejouer(corpus, bras, _roles(), budget_usd=20, **args)
    assert len(premiers) == 1
    assert await bc.rejouer(corpus, bras, _roles(), budget_usd=20, **args) == []  # déjà ok
    autre = Corpus(entrees=(entree,), gel_sha256="h" * 64)
    with pytest.raises(bc.ResultatsIncompatibles):
        await bc.rejouer(autre, bras, _roles(), budget_usd=20, **args)
    sortie.write_text("", encoding="utf-8")
    with pytest.raises(bc.BudgetAtteint):
        await bc.rejouer(corpus, bras, _roles(), budget_usd=1, **args)


@pytest.mark.asyncio
async def test_cell_calls_no_push_pr_lock_or_database(
    depot: tuple[Path, Entree], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    appels: list[list[str]] = []
    reel = subprocess.run

    def espion(cmd: list[str], *a: object, **k: object) -> subprocess.CompletedProcess[bytes]:
        appels.append([str(x) for x in cmd])
        return reel(cmd, *a, **k)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", espion)
    await _cellule(depot, tmp_path, _roles())
    assert {x for c in appels for x in c if x in {"push", "gh", "pr", "remote", "fetch"}} == set()
    source = "".join(
        (_SCRIPTS_DIR / f).read_text(encoding="utf-8")
        for f in ("banc_codeur.py", "banc_codeur_cellule.py", "banc_codeur_roles.py")
    )
    for interdit in ("Orchestrator", "RunLock", "aiosqlite", "services.livraison"):
        assert f"import {interdit}" not in source
        assert f"from tessera.services.{interdit}" not in source


def test_copies_live_outside_worktrees_dir() -> None:
    assert bc._COPIES.parts[-2:] == (".tessera", "banc-codeur")
