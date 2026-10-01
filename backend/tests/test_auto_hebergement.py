"""Un projet peut travailler dans le depot qui le contient — ticket-081."""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService, NotAGitRepository


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()


@pytest.fixture
async def depot_parent(tmp_path: Path) -> Path:
    """Un depot, et dedans un dossier de projet sans depot propre."""
    parent = tmp_path / "Tessera"
    parent.mkdir()
    await _git(parent, "init", "-q", "-b", "main")
    await _git(parent, "config", "user.email", "t@t.local")
    await _git(parent, "config", "user.name", "t")
    (parent / "backend").mkdir()
    (parent / "backend" / "app.py").write_text("x = 1\n", encoding="utf-8")
    await _git(parent, "add", "-A")
    await _git(parent, "commit", "-qm", "init")
    (parent / "projects" / "ide-core").mkdir(parents=True)
    return parent


async def test_par_defaut_un_projet_sans_depot_est_refuse(depot_parent: Path) -> None:
    # ADR-024 : un dossier client pose dans `projects/` faisait remonter git
    # jusqu'au depot de Tessera, ou le run creait branche et commit.
    svc = GitWorkspaceService(depot_parent / "projects" / "ide-core")

    with pytest.raises(NotAGitRepository):
        await svc.create_branch("ticket-001", "essai")


async def test_un_projet_peut_declarer_qu_il_travaille_dans_le_parent(
    depot_parent: Path,
) -> None:
    # C'est le principe d'ADR-001 : le projet bootstrap construit l'IDE, donc
    # il travaille volontairement dans le depot qui le contient. Le refus
    # d'ADR-024 reste le defaut ; l'exception se declare.
    projet = depot_parent / "projects" / "ide-core"
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )

    svc = GitWorkspaceService(projet)
    branche = await svc.create_branch("ticket-001", "essai")

    assert branche == "ticket-001-essai"


async def test_le_travail_declare_est_bien_commite_dans_le_parent(
    depot_parent: Path,
) -> None:
    projet = depot_parent / "projects" / "ide-core"
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )

    svc = GitWorkspaceService(projet)
    await svc.create_branch("ticket-002", "essai")
    (depot_parent / "backend" / "app.py").write_text("x = 2\n", encoding="utf-8")

    sha = await svc.commit_all("feat: ticket-002 — essai")

    assert sha is not None


async def test_une_declaration_inconnue_ne_desarme_rien(depot_parent: Path) -> None:
    # Fail-closed : seule la valeur attendue ouvre l'exception.
    projet = depot_parent / "projects" / "ide-core"
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "n-importe-quoi"}), encoding="utf-8"
    )

    with pytest.raises(NotAGitRepository):
        await GitWorkspaceService(projet).create_branch("ticket-003", "essai")


async def test_le_journal_du_pipeline_ne_salit_pas_l_arbre_dans_le_parent(
    depot_parent: Path,
) -> None:
    # `git status --porcelain` rend les chemins depuis la racine du depot :
    # le journal d'un projet `ancestor` n'etait pas reconnu comme un artefact,
    # et la file refusait le ticket suivant (ticket-301).
    projet = depot_parent / "projects" / "ide-core"
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )
    (projet / "memory").mkdir()
    journal = projet / "memory" / "pipeline-log.md"
    journal.write_text("- debut\n", encoding="utf-8")
    await _git(depot_parent, "add", "-A")
    await _git(depot_parent, "commit", "-qm", "journal")

    journal.write_text("- debut\n- livraison : PR mergee\n", encoding="utf-8")

    assert await GitWorkspaceService(projet).is_clean() is True


async def test_un_fichier_de_code_modifie_salit_toujours_l_arbre_dans_le_parent(
    depot_parent: Path,
) -> None:
    projet = depot_parent / "projects" / "ide-core"
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )
    await _git(depot_parent, "add", "-A")
    await _git(depot_parent, "commit", "-qm", "manifeste")

    (depot_parent / "backend" / "app.py").write_text("x = 3\n", encoding="utf-8")

    assert await GitWorkspaceService(projet).is_clean() is False
