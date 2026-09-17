"""Relire ce qu'un run a produit, sans quitter l'IDE — ticket-069."""
import asyncio
from pathlib import Path

import pytest

from vibe_ide.services.ticket_diff import TicketDiff, diff_du_ticket


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


async def test_le_diff_d_une_branche_de_ticket_est_lisible(depot: Path) -> None:
    # Sans ca, juger un run demande d'ouvrir VSCode et de taper git diff — ce
    # qui vide le cockpit d'une bonne part de son interet.
    await _git(depot, "checkout", "-q", "-b", "ticket-001-ajout-help")
    (depot / "app.py").write_text("x = 2\n", encoding="utf-8")
    await _git(depot, "commit", "-qam", "feat: ticket-001 — x")
    await _git(depot, "checkout", "-q", "main")

    resultat = await diff_du_ticket(depot, "ticket-001")

    assert isinstance(resultat, TicketDiff)
    assert resultat.branch == "ticket-001-ajout-help"
    assert "-x = 1" in resultat.diff
    assert "+x = 2" in resultat.diff
    assert resultat.files == ["app.py"]


async def test_sans_branche_le_diff_est_vide_et_le_dit(depot: Path) -> None:
    resultat = await diff_du_ticket(depot, "ticket-404")

    assert resultat.branch is None
    assert resultat.diff == ""
    assert resultat.files == []


async def test_une_branche_sans_commit_ne_montre_rien(depot: Path) -> None:
    # Cas vecu : un run qui n'a rien commite laisse une branche identique a sa
    # base. L'ecran doit le dire, pas afficher un diff trompeur.
    await _git(depot, "branch", "ticket-002-rien")

    resultat = await diff_du_ticket(depot, "ticket-002")

    assert resultat.branch == "ticket-002-rien"
    assert resultat.diff == ""
    assert resultat.files == []


async def test_le_diff_ignore_les_artefacts_de_vibe_ide(depot: Path) -> None:
    # Ce que l'utilisateur relit, c'est le travail du codeur — pas le ticket
    # que l'orchestrateur vient de reecrire.
    await _git(depot, "checkout", "-q", "-b", "ticket-003-x")
    (depot / "tickets").mkdir()
    (depot / "tickets" / "t.md").write_text("statut\n", encoding="utf-8")
    (depot / "app.py").write_text("x = 3\n", encoding="utf-8")
    await _git(depot, "add", "-A")
    await _git(depot, "commit", "-qm", "feat: ticket-003 — x")
    await _git(depot, "checkout", "-q", "main")

    resultat = await diff_du_ticket(depot, "ticket-003")

    assert resultat.files == ["app.py"]
