"""La livraison commite le journal avant de rebaser — ticket-303.

Contexte : depuis ticket-288, le pipeline journalise des durées après son
commit de fin de run. Si aucun fichier de documentation n'a été modifié,
ces lignes restent non commitées sur la branche. `git rebase` exige un arbre
entièrement propre, sans exception : la livraison butte alors sur
"cannot rebase: You have unstaged changes", même si `is_clean` les tolère
(ticket-301).

La correction : juste avant `rejoyer_sur`, la livraison appelle
`commit_bookkeeping`, qui commite ces artefacts. Un fichier de code modifié
doit toujours bloquer la livraison — `commit_bookkeeping` ne le concerne pas.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import LivraisonService, Livraison


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)} a échoué : {stderr.decode()}"


async def _git_out(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """Dépôt git minimal avec un commit initial sur main."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


class _FauxWorkflow:
    """Workflow qui ouvre une PR sans attendre de CI ni merger."""

    async def open_pull_request(self, **kwargs: object) -> object:
        class _R:
            pr_number = 7

        return _R()

    async def etat_ci(self, pr_number: int) -> str:
        return "passing"

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        return True


async def _ne_dort_pas(_secondes: float) -> None:
    return None


def _service(repo: Path, git: GitWorkspaceService) -> LivraisonService:
    """LivraisonService en mode `pr`, sans attente de CI."""
    (repo / "agents.json").write_text(
        json.dumps({"autonomy": "pr"}), encoding="utf-8"
    )
    return LivraisonService(
        git_workspace=git,
        workflow=_FauxWorkflow(),
        project_path=repo,
        base_branch="main",
        attente_ci_max_s=0,
        dormir=_ne_dort_pas,
    )


async def _preparer_branche(repo: Path) -> None:
    """Crée la branche de ticket avec un commit, laisse le dépôt sur cette branche."""
    await _git(repo, "checkout", "-q", "-b", "ticket-001-slug")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")


# ------------------------------------------------------------------
# Critère 1 — seul le journal est modifié → rebase sans erreur
# ------------------------------------------------------------------


async def test_seul_journal_modifie_rebase_sans_erreur(repo: Path) -> None:
    """Un pipeline-log non commité ne bloque plus le rebase — ticket-303.

    Avant le correctif, `git rebase` échouait avec
    "cannot rebase: You have unstaged changes" dès que le pipeline avait
    journalisé des étapes après son dernier commit, sans qu'aucun fichier de
    documentation ne les emporte dans un commit de bookkeeping.
    """
    await _preparer_branche(repo)

    # Simule les lignes de journal écrites par la livraison après le commit du run.
    log_dir = repo / "memory"
    log_dir.mkdir()
    (log_dir / "pipeline-log.md").write_text(
        "## ticket-001\n- livraison démarrée\n", encoding="utf-8"
    )

    git = GitWorkspaceService(repo)
    svc = _service(repo, git)

    resultat = await svc.livrer(
        ticket_id="ticket-001",
        ticket_title="Du travail",
        ticket_body="",
        branch="ticket-001-slug",
        approuve=True,
    )

    assert resultat.arret is None, (
        f"le journal non commité ne doit pas bloquer la livraison : {resultat.arret}"
    )


# ------------------------------------------------------------------
# Critère 2 — les lignes de journal en attente sont commitées avant le rebase
# ------------------------------------------------------------------


async def test_lignes_de_journal_commitees_avant_rebase(repo: Path) -> None:
    """Les lignes de journal en attente sont dans un commit bookkeeping sur la branche."""
    await _preparer_branche(repo)

    # Écrire le journal non commité, comme le pipeline le ferait.
    log_dir = repo / "memory"
    log_dir.mkdir()
    (log_dir / "pipeline-log.md").write_text(
        "## ticket-001\n- étape\n", encoding="utf-8"
    )

    git = GitWorkspaceService(repo)
    svc = _service(repo, git)

    await svc.livrer(
        ticket_id="ticket-001",
        ticket_title="Du travail",
        ticket_body="",
        branch="ticket-001-slug",
        approuve=True,
    )

    # Après la livraison, le commit de tenue de livres doit figurer dans le log.
    journal_git = await _git_out(repo, "log", "--oneline", "--all")
    assert "tessera pipeline bookkeeping" in journal_git, (
        "le commit de tenue de livres doit exister dans la branche avant le rebase : "
        + journal_git
    )


# ------------------------------------------------------------------
# Critère 3 — un fichier de code modifié fait toujours échouer la livraison
# ------------------------------------------------------------------


async def test_fichier_de_code_modifie_bloque_la_livraison(repo: Path) -> None:
    """Un fichier de code non commité fait toujours échouer la livraison.

    `commit_bookkeeping` ne commite que les artefacts Tessera. Une modification
    de code laissée dans l'arbre de travail doit toujours bloquer le rebase,
    et la livraison doit rendre un `arret` qui le dit.
    """
    await _preparer_branche(repo)

    # Modifier un fichier de code sans le commiter.
    (repo / "code.py").write_text("x = 2  # modification oubliee\n", encoding="utf-8")

    git = GitWorkspaceService(repo)
    svc = _service(repo, git)

    resultat = await svc.livrer(
        ticket_id="ticket-001",
        ticket_title="Du travail",
        ticket_body="",
        branch="ticket-001-slug",
        approuve=True,
    )

    assert resultat.arret is not None, (
        "un fichier de code modifié doit bloquer la livraison"
    )
    assert "rebase" in resultat.arret.lower(), (
        f"l'arret doit mentionner le rebase : {resultat.arret}"
    )
