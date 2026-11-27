"""Tests for the pilot mode of scripts/banc_codeur.py (ticket-1057). No model is called."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import banc_codeur as bc  # noqa: E402
import banc_codeur_cellule as cell  # noqa: E402
import banc_codeur_roles as roles_reels  # noqa: E402
from banc_codeur_bras import Bras  # noqa: E402
from banc_codeur_cellule import Appel, Controle, Roles  # noqa: E402
from banc_codeur_corpus import Entree, sans_frontmatter, somme_gel, somme_texte  # noqa: E402

_TICKET = "---\nid: 1\n---\n# Ticket\n\n## Critères d'acceptation\n- [ ] ok\n"


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
    (d / "vieux.py").write_text("y = 1\n", encoding="utf-8")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "base")
    base = _git(d, "rev-parse", "HEAD")
    (d / "code.py").write_text("x = 2\n", encoding="utf-8")
    (d / "test_code.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (d / "vieux.py").unlink()
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "solution")
    entree = Entree(
        id="e1", ticket="1", sha=_git(d, "rev-parse", "HEAD"), base_sha=base,
        ticket_chemin="tickets/ticket-1-x.md", ticket_sha256=somme_texte(sans_frontmatter(_TICKET)),
        fichiers=("code.py", "test_code.py", "vieux.py"), lignes_ajoutees=40, pilote=True,
    )
    return d, entree


def _roles(cout: float = 0.5) -> Roles:
    async def oui(_: Path) -> bool:
        return True

    async def coder(cwd: Path, _t: str, _r: str) -> Appel:
        (cwd / "code.py").write_text("x = 3\n", encoding="utf-8")
        return Appel(cout, (1, 2, 3), 10)

    async def controler(_c: Path, _t: str, _v: bool) -> Controle:
        return Controle(True, "", 0.1)

    return Roles(env=oui, coder=coder, tester=oui, controler=controler)


def test_copy_carries_a_base_ref_for_the_impact_mode(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    cible = tmp_path / "copie"
    cell.copier_sans_historique(d, entree.base_sha, cible)
    assert _git(cible, "rev-parse", "origin/develop") == _git(cible, "rev-parse", "HEAD")
    assert _git(cible, "remote") == ""
    # test_aucune_trace_professionnelle refuse un auteur hors de sa liste : la référence virait au rouge.
    assert _git(cible, "log", "--format=%ae %ce") == "banc@example.com banc@example.com"


def test_solution_is_laid_on_the_base_copy(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    cible = tmp_path / "copie"
    cell.copier_sans_historique(d, entree.base_sha, cible)
    cell.poser_solution(d, entree, cible)
    assert (cible / "code.py").read_text() == "x = 2\n"
    assert (cible / "test_code.py").exists() and not (cible / "vieux.py").exists()


def test_env_and_tests_install_and_keep_the_dev_extra() -> None:
    assert roles_reels.COMMANDE_ENV[:2] == ["uv", "sync"]
    for commande in (roles_reels.COMMANDE_ENV, roles_reels.COMMANDE_TESTS):
        assert "--frozen" in commande and commande[commande.index("--extra") + 1] == "dev"
    assert roles_reels.COMMANDE_TESTS[-2:] == ["--impact", "base"]


@pytest.mark.asyncio
async def test_rejouer_skips_pilot_entries_in_the_trial(depot: tuple[Path, Entree], tmp_path: Path) -> None:
    d, entree = depot
    gele = replace(entree, id="e2", sha="f" * 40, pilote=False)
    corpus = bc.Corpus(entrees=(entree, gele), gel_sha256="g" * 64)
    bras = Bras(id="A", modele="m", provider="agent_sdk", prompt="p")
    args = {"depot": d, "sortie": tmp_path / "r.jsonl", "racine_copies": tmp_path / "c"}
    lignes = await bc.rejouer(bc.Corpus(entrees=(entree,), gel_sha256="g" * 64), bras, _roles(),
                              budget_usd=20, **args)
    assert lignes == []
    assert [x.id for x in await bc.rejouer(corpus, bras, _roles(), budget_usd=20, pilote=True,
                                          **args)] == ["e1"]


@pytest.mark.asyncio
async def test_pilot_crosses_entries_and_arms_under_one_budget(
    depot: tuple[Path, Entree], tmp_path: Path
) -> None:
    d, entree = depot
    deux = replace(entree, id="e2")
    paires = [(Bras(id=x, modele="m", provider="agent_sdk", prompt="p"), _roles(cout=2.0)) for x in "AMP"]
    sortie = tmp_path / "pilote.jsonl"
    with pytest.raises(bc.BudgetAtteint):
        await bc.rejouer_pilote(bc.Corpus(entrees=(entree, deux), gel_sha256="g" * 64), paires,
                                depot=d, sortie=sortie, racine_copies=tmp_path / "c", budget_usd=15)
    lues = cell.lire_resultats(sortie)
    # 2,1 $ par cellule : la cinquième passe (8,4 $ + 6 $ ≤ 15 $), la sixième non (10,5 + 6 > 15).
    assert [(r.id, r.bras) for r in lues] == [
        ("e1", "A"), ("e1", "M"), ("e1", "P"), ("e2", "A"), ("e2", "M"),
    ]
    assert sum(r.cout_usd for r in lues) <= 15


def test_main_pilote_writes_its_own_file(
    depot: tuple[Path, Entree], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d, entree = depot
    gelees = [replace(entree, id=f"g{i}", sha=f"{i:040d}", pilote=False) for i in range(16)]
    entrees = [entree, *gelees]
    chemin = tmp_path / "corpus.json"
    chemin.write_text(json.dumps({"gel_sha256": somme_gel(entrees),
                                  "entrees": [asdict(e) for e in entrees]}), encoding="utf-8")
    monkeypatch.setattr(bc, "_COPIES", tmp_path / "copies")
    sortie = tmp_path / "pilote.jsonl"
    code = bc.main(["rejouer", "--pilote", "--budget-usd", "15", "--corpus", str(chemin),
                    "--sortie", str(sortie), "--depot", str(d)],
                   construire=lambda _d, _b: _roles())
    assert code == 0
    assert sorted(r.bras for r in cell.lire_resultats(sortie)) == ["A", "M", "P"]
    assert {r.id for r in cell.lire_resultats(sortie)} == {"e1"}
