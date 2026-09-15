"""Artefacts vibe-ide versionnés ou locaux — ticket-062."""
import asyncio
import json
from pathlib import Path

import pytest

from vibe_ide.services.vibe_artifacts import (
    ArtifactMode,
    VIBE_ARTIFACT_PATHS,
    apply_artifact_mode,
    default_mode_for,
    read_artifact_mode,
    tracked_artifact_paths,
)


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    p = tmp_path / "mon-projet"
    (p / "tickets" / "todo").mkdir(parents=True)
    (p / "memory").mkdir()
    (p / "CLAUDE.md").write_text("# projet\n", encoding="utf-8")
    (p / "memory" / "decisions.md").write_text("## ADR-001\n", encoding="utf-8")
    await _git(p, "init", "-q")
    await _git(p, "config", "user.email", "t@t.local")
    await _git(p, "config", "user.name", "t")
    return p


# ------------------------------------------------------------------
# Défauts
# ------------------------------------------------------------------


def test_un_projet_cree_ou_importe_est_versionne_par_defaut() -> None:
    # Projets personnels : les ADR ont de la valeur, on les garde.
    assert default_mode_for("create") == "tracked"
    assert default_mode_for("import") == "tracked"


def test_un_projet_clone_est_local_par_defaut() -> None:
    # Le dépôt appartient déjà à quelqu'un d'autre. On peut toujours choisir
    # de partager ensuite ; on ne peut pas défaire un push.
    assert default_mode_for("clone") == "local"


def test_un_mode_inconnu_retombe_sur_le_choix_prudent() -> None:
    assert default_mode_for("inconnu") == "local"


# ------------------------------------------------------------------
# Lecture du mode
# ------------------------------------------------------------------


async def test_le_mode_se_lit_dans_agents_json(repo: Path) -> None:
    (repo / "agents.json").write_text(json.dumps({"vibe_artifacts": "local"}), encoding="utf-8")
    assert read_artifact_mode(repo) == "local"


async def test_sans_agents_json_le_mode_est_versionne(repo: Path) -> None:
    # Le comportement historique : les artefacts étaient commités.
    assert read_artifact_mode(repo) == "tracked"


# ------------------------------------------------------------------
# Application du mode
# ------------------------------------------------------------------


async def test_le_mode_local_exclut_les_artefacts_sans_toucher_au_gitignore(
    repo: Path,
) -> None:
    # `.gitignore` est lui-même versionné : le modifier produirait un diff qui
    # annonce exactement ce qu'on voulait taire sur un dépôt client.
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

    await apply_artifact_mode(repo, "local")

    exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "tickets/" in exclude
    assert "memory/" in exclude
    assert (repo / ".gitignore").read_text(encoding="utf-8") == "node_modules/\n"


async def test_le_mode_local_est_effectif_pour_git(repo: Path) -> None:
    await apply_artifact_mode(repo, "local")

    status = await _git(repo, "status", "--porcelain")

    assert "tickets/" not in status
    assert "memory/" not in status
    assert "CLAUDE.md" not in status


async def test_repasser_en_versionne_retire_l_exclusion(repo: Path) -> None:
    await apply_artifact_mode(repo, "local")
    await apply_artifact_mode(repo, "tracked")

    exclude_file = repo / ".git" / "info" / "exclude"
    content = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
    assert "tickets/" not in content

    status = await _git(repo, "status", "--porcelain")
    assert "CLAUDE.md" in status


async def test_l_exclusion_preserve_le_contenu_existant(repo: Path) -> None:
    exclude_file = repo / ".git" / "info" / "exclude"
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    exclude_file.write_text("# une règle de l'utilisateur\nscratch/\n", encoding="utf-8")

    await apply_artifact_mode(repo, "local")
    await apply_artifact_mode(repo, "tracked")

    content = exclude_file.read_text(encoding="utf-8")
    assert "scratch/" in content
    assert "une règle de l'utilisateur" in content


async def test_le_mode_est_consigne_dans_agents_json(repo: Path) -> None:
    (repo / "agents.json").write_text(
        json.dumps({"github_remote": "https://github.com/moi/r.git"}), encoding="utf-8"
    )

    await apply_artifact_mode(repo, "local")

    data = json.loads((repo / "agents.json").read_text(encoding="utf-8"))
    assert data["vibe_artifacts"] == "local"
    # Les autres clefs survivent.
    assert data["github_remote"] == "https://github.com/moi/r.git"


# ------------------------------------------------------------------
# Fichiers déjà suivis
# ------------------------------------------------------------------


async def test_les_artefacts_deja_suivis_sont_signales(repo: Path) -> None:
    # Passer en `local` ne suffit pas si les fichiers sont déjà dans l'index :
    # git continue de les suivre. Il faut le dire, pas le faire en silence.
    await _git(repo, "add", "CLAUDE.md", "memory/decisions.md")
    await _git(repo, "commit", "-q", "-m", "ajout")

    tracked = await tracked_artifact_paths(repo)

    assert "CLAUDE.md" in tracked
    assert any(p.startswith("memory/") for p in tracked)


async def test_aucun_artefact_suivi_sur_un_depot_neuf(repo: Path) -> None:
    assert await tracked_artifact_paths(repo) == []


def test_les_chemins_couverts_sont_explicites() -> None:
    assert set(VIBE_ARTIFACT_PATHS) == {"tickets/", "memory/", "CLAUDE.md", "agents.json"}
