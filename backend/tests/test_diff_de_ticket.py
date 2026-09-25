"""Relire ce qu'un run a produit, sans quitter l'IDE — ticket-069."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.ticket_diff import TicketDiff, diff_du_ticket


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


async def test_le_diff_ignore_les_artefacts_de_tessera(depot: Path) -> None:
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


async def test_le_diff_survit_a_la_suppression_de_la_branche(depot: Path) -> None:
    """Deleting the branch after merging is the normal practice — it is what
    `gh pr merge --delete-branch` does, and what `ticket-workflow` prescribes.

    The diff was looked up by `git branch --list`, so it vanished for every
    properly finished ticket, and the screen claimed the ticket had "never
    been run". It had: only its branch was gone, the work still in history.
    """
    await _git(depot, "checkout", "-q", "-b", "ticket-002-ajout")
    (depot / "app.py").write_text("x = 42\n", encoding="utf-8")
    await _git(depot, "commit", "-qam", "feat: ticket-002 — la reponse")
    await _git(depot, "checkout", "-q", "main")
    await _git(depot, "merge", "-q", "--squash", "ticket-002-ajout")
    await _git(depot, "commit", "-qm", "feat: ticket-002 — la reponse (#42)")
    await _git(depot, "branch", "-qD", "ticket-002-ajout")

    resultat = await diff_du_ticket(depot, "ticket-002")

    assert resultat.branch is None
    assert resultat.commit is not None, "le commit du ticket n'a pas ete retrouve"
    assert "x = 42" in resultat.diff
    assert "app.py" in resultat.files


async def test_un_commit_de_cloture_n_est_pas_pris_pour_le_travail(
    depot: Path,
) -> None:
    """The closing commit touches only `tickets/`, which `_ARTEFACTS` already
    excludes — so its diff is empty once filtered. Walking from the most
    recent commit down, the first non-empty diff is the real work.
    """
    await _git(depot, "checkout", "-q", "-b", "ticket-003-travail")
    (depot / "app.py").write_text("x = 3\n", encoding="utf-8")
    await _git(depot, "commit", "-qam", "feat: ticket-003 — le travail")
    await _git(depot, "checkout", "-q", "main")
    await _git(depot, "merge", "-q", "--squash", "ticket-003-travail")
    await _git(depot, "commit", "-qm", "feat: ticket-003 — le travail (#43)")
    await _git(depot, "branch", "-qD", "ticket-003-travail")

    # Puis la cloture, plus recente, qui ne touche qu'un artefact.
    (depot / "tickets").mkdir(exist_ok=True)
    (depot / "tickets" / "ticket-003.md").write_text("status: done\n", encoding="utf-8")
    await _git(depot, "add", "tickets/ticket-003.md")
    await _git(depot, "commit", "-qm", "chore: ticket-003 — close (#44)")

    resultat = await diff_du_ticket(depot, "ticket-003")

    assert "x = 3" in resultat.diff, "le diff rendu est celui de la cloture"


async def test_un_ticket_jamais_lance_n_a_ni_branche_ni_commit(depot: Path) -> None:
    resultat = await diff_du_ticket(depot, "ticket-999")

    assert resultat.branch is None
    assert resultat.commit is None
    assert resultat.diff == ""
