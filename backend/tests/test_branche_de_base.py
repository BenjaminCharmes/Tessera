"""La branche de base se declare par projet — ticket-166.

Premier run du banc d'essai apres ticket-159 : approuve, commite, puis
`rebase develop` sur un depot qui n'a que `main`. Le reglage etait global.
"""

import asyncio
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.politique_run import PolitiqueRun


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()


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


def _manifeste(root: Path, **champs: object) -> None:
    (root / "agents.json").write_text(json.dumps(champs), encoding="utf-8")


# --- La declaration ---------------------------------------------------------


def test_la_politique_lit_la_branche_de_base_declaree(tmp_path: Path) -> None:
    _manifeste(tmp_path, base_branch="main")

    assert PolitiqueRun.lire(tmp_path).base_branch == "main"


def test_sans_declaration_la_branche_de_base_est_none(tmp_path: Path) -> None:
    """`None` et non le defaut global : c'est l'appelant qui choisit le repli."""
    _manifeste(tmp_path, autonomy="pr")

    assert PolitiqueRun.lire(tmp_path).base_branch is None


def test_un_manifeste_illisible_ne_fait_pas_echouer_la_lecture(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text("{ pas du json", encoding="utf-8")

    assert PolitiqueRun.lire(tmp_path).base_branch is None


def test_une_valeur_qui_n_est_pas_une_chaine_est_ignoree(tmp_path: Path) -> None:
    _manifeste(tmp_path, base_branch=42)

    assert PolitiqueRun.lire(tmp_path).base_branch is None


# --- L'erreur qui se lit ----------------------------------------------------


async def test_une_base_inexistante_nomme_la_branche_et_le_reglage(repo: Path) -> None:
    """`fatal: invalid upstream 'develop'` ne dit ni quoi corriger, ni ou.

    C'est le message qu'a recu le premier run livrable du banc d'essai.
    """
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")

    service = GitWorkspaceService(repo)
    with pytest.raises(Exception) as leve:
        await service.rejouer_sur("develop")

    message = str(leve.value)
    assert "develop" in message
    assert "base_branch" in message, f"le message doit dire quoi ecrire : {message}"
    assert "invalid upstream" not in message


async def test_une_base_existante_se_rejoue_normalement(repo: Path) -> None:
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: du travail")

    assert await GitWorkspaceService(repo).rejouer_sur("main") == ()


# --- Le cablage -------------------------------------------------------------


def test_le_defaut_global_reste_le_repli() -> None:
    """Un projet muet garde le comportement d'avant ce ticket."""
    politique = PolitiqueRun()

    assert (politique.base_branch or settings.github_base_branch) == "develop"
