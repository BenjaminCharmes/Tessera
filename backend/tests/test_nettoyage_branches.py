"""Nettoyage des branches creees par Tessera — ticket-070."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.branch_cleanup import plan_de_nettoyage, supprimer_branches


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def depot(tmp_path: Path) -> Path:
    p = tmp_path / "projet"
    p.mkdir()
    await _git(p, "init", "-q", "-b", "main")
    await _git(p, "config", "user.email", "t@t.local")
    await _git(p, "config", "user.name", "t")
    (p / "app.py").write_text("x = 1\n", encoding="utf-8")
    await _git(p, "add", "app.py")
    await _git(p, "commit", "-qm", "init")
    return p


async def test_une_branche_identique_a_sa_base_est_nettoyable(depot: Path) -> None:
    # Cas vecu le 2026-09-17 : deux runs `done` ont laisse deux branches
    # identiques a main. Elles ne portent rien, elles encombrent.
    await _git(depot, "branch", "ticket-001-rien")

    plan = await plan_de_nettoyage(depot)

    assert plan.nettoyables == ["ticket-001-rien"]
    assert plan.conservees == []


async def test_une_branche_qui_porte_du_travail_est_conservee(depot: Path) -> None:
    # Un run rejete commite quand meme (ADR-018). Supprimer sa branche
    # detruirait le seul exemplaire de ce travail.
    await _git(depot, "checkout", "-q", "-b", "ticket-002-travail")
    (depot / "app.py").write_text("x = 2\n", encoding="utf-8")
    await _git(depot, "commit", "-qam", "chore: ticket-002 — unapproved")
    await _git(depot, "checkout", "-q", "main")

    plan = await plan_de_nettoyage(depot)

    assert plan.nettoyables == []
    assert ("ticket-002-travail", "porte du travail absent de la base") in plan.conservees


async def test_la_branche_courante_n_est_jamais_nettoyee(depot: Path) -> None:
    await _git(depot, "checkout", "-q", "-b", "ticket-003-courante")

    plan = await plan_de_nettoyage(depot)

    assert "ticket-003-courante" not in plan.nettoyables


async def test_les_branches_hors_tessera_ne_sont_pas_touchees(depot: Path) -> None:
    # On ne nettoie que ce qu'on a cree. Le reste appartient a l'utilisateur.
    await _git(depot, "branch", "ma-feature-perso")
    await _git(depot, "branch", "ticket-004-rien")

    plan = await plan_de_nettoyage(depot)

    assert plan.nettoyables == ["ticket-004-rien"]


async def test_les_branches_de_chat_sont_nettoyables(depot: Path) -> None:
    await _git(depot, "branch", "chat/20260917-1100")

    plan = await plan_de_nettoyage(depot)

    assert plan.nettoyables == ["chat/20260917-1100"]


async def test_la_suppression_ne_touche_que_le_plan(depot: Path) -> None:
    await _git(depot, "branch", "ticket-005-rien")
    await _git(depot, "checkout", "-q", "-b", "ticket-006-travail")
    (depot / "app.py").write_text("x = 6\n", encoding="utf-8")
    await _git(depot, "commit", "-qam", "chore: ticket-006")
    await _git(depot, "checkout", "-q", "main")

    supprimees = await supprimer_branches(depot, ["ticket-005-rien", "ticket-006-travail"])

    restantes = (await _git(depot, "branch", "--format=%(refname:short)")).split()
    assert supprimees == ["ticket-005-rien"]
    assert "ticket-006-travail" in restantes, "une branche hors plan ne se supprime pas"
