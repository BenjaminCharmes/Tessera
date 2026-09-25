"""Lire le diff ne doit pas modifier l'index — ticket-170.

Deux files lancees, deux arrets au meme endroit : `git rebase` refuse sur un
index non vide, et le ticket suivant trouve un arbre sale. En cause,
`current_diff()` qui fait `git add -A -N` et laisse les entrees derriere lui.
"""

import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()


async def _index(repo: Path) -> str:
    """Ce que `is_clean()` regarde : les chemins suivis, index compris.

    `git diff --cached --name-only` ne suffit pas — une entree *intent-to-add*
    n'y apparait pas toujours, alors qu'elle suffit a faire refuser `git
    rebase` et a faire echouer la garde d'arbre propre.
    """
    proc = await asyncio.create_subprocess_exec(
        "git", "status", "--porcelain", "--untracked-files=no", cwd=str(repo),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return out.decode().strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@Tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def test_un_fichier_non_suivi_le_reste_apres_la_lecture(repo: Path) -> None:
    """`memory/documentation.json` finissait dans l'index, objet vide, jamais commite."""
    (repo / "documentation.json").write_text("{}\n", encoding="utf-8")

    await GitWorkspaceService(repo).current_diff()

    assert await _index(repo) == ""


async def test_le_diff_montre_quand_meme_le_fichier_neuf(repo: Path) -> None:
    """Sans ca, le reviewer ne verrait pas ce que le codeur vient d'ecrire."""
    (repo / "grille.ts").write_text("export const N = 1;\n", encoding="utf-8")

    diff = await GitWorkspaceService(repo).current_diff()

    assert "grille.ts" in diff
    assert "export const N = 1;" in diff


async def test_ce_qui_etait_stage_le_reste(repo: Path) -> None:
    """Le nettoyage ne porte que sur ce que la lecture a elle-meme ajoute."""
    (repo / "voulu.ts").write_text("export const A = 1;\n", encoding="utf-8")
    await _git(repo, "add", "voulu.ts")

    await GitWorkspaceService(repo).current_diff()

    assert "voulu.ts" in await _index(repo)


async def test_rejouer_reussit_apres_une_lecture(repo: Path) -> None:
    """Le symptome complet : la livraison rejoue juste apres avoir lu le diff."""
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "code.ts").write_text("export const B = 2;\n", encoding="utf-8")
    await _git(repo, "add", "code.ts")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")
    (repo / "documentation.json").write_text("{}\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    await service.current_diff()

    assert await service.rejouer_sur("main") == ()


async def test_un_depot_sans_commit_ne_leve_pas(tmp_path: Path) -> None:
    """`git reset` sans HEAD echoue : le nettoyage doit s'en accommoder."""
    root = tmp_path / "neuf"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@Tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "code.ts").write_text("export const C = 3;\n", encoding="utf-8")

    diff = await GitWorkspaceService(root).current_diff()

    assert "code.ts" in diff
