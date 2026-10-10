"""Creating a project from the fastapi-react template in one call — ticket-373.

The service allocates free ports, copies the template with marker substitution,
writes the definitive agents.json, and initialises a git repository.
No GitHub repository is created.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tessera.config import _REPO_ROOT
from tessera.services.git_link import GitStatus
from tessera.services.project_from_template import (
    _collect_used_ports,
    create_project_from_template,
)

_TEMPLATE_DIR = _REPO_ROOT / "templates" / "fastapi-react"

# Réponse git factice qui évite d'initialiser un vrai dépôt dans les tests.
_GIT_OK = GitStatus(is_own_repository=True, has_commits=True)

# Namespace où init_repository est importé dans le module du service.
_PATCH_GIT = "tessera.services.project_from_template.init_repository"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Workspace temporaire isolé : chaque test part d'un dossier vide."""
    return tmp_path / "projects"


async def test_template_files_created_without_markers(workspace: Path) -> None:
    """Les fichiers du gabarit existent dans le projet sans aucun marqueur {{."""
    with patch(_PATCH_GIT, new_callable=AsyncMock) as m:
        m.return_value = _GIT_OK
        await create_project_from_template(workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR)

    proj = workspace / "mon-projet"
    assert (proj / "backend" / "app" / "main.py").exists()
    assert (proj / "frontend" / "vite.config.ts").exists()
    assert (proj / "tickets" / "todo").is_dir()
    assert (proj / "memory").is_dir()

    for f in proj.rglob("*"):
        if f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                assert "{{" not in content, (
                    f"Marqueur non substitué dans {f.relative_to(proj)}"
                )
            except UnicodeDecodeError:
                pass  # Fichier binaire : pas de marqueur à vérifier


async def test_port_allocation_skips_used_ports(workspace: Path) -> None:
    """Avec 8020/5190 et 8021/5191 pris, le nouveau projet reçoit 8022 et 5192.

    Les ports sont lus depuis les services de agents.json et les vite.config.ts.
    """
    workspace.mkdir(parents=True, exist_ok=True)

    # Projet A : port backend dans la commande de service
    proj_a = workspace / "project-a"
    proj_a.mkdir()
    (proj_a / "agents.json").write_text(
        json.dumps({"services": [
            {"nom": "backend", "commande": "uvicorn app.main:app --port 8020"},
        ]}),
        encoding="utf-8",
    )
    vite_a = proj_a / "frontend" / "vite.config.ts"
    vite_a.parent.mkdir()
    vite_a.write_text(
        "export default defineConfig({ server: { port: 5190 } })",
        encoding="utf-8",
    )

    # Projet B : ports 8021/5191
    proj_b = workspace / "project-b"
    proj_b.mkdir()
    (proj_b / "agents.json").write_text(
        json.dumps({"services": [
            {"nom": "backend", "commande": "uvicorn app.main:app --port 8021"},
        ]}),
        encoding="utf-8",
    )
    vite_b = proj_b / "frontend" / "vite.config.ts"
    vite_b.parent.mkdir()
    vite_b.write_text(
        "export default defineConfig({ server: { port: 5191 } })",
        encoding="utf-8",
    )

    with patch(_PATCH_GIT, new_callable=AsyncMock) as m:
        m.return_value = _GIT_OK
        result = await create_project_from_template(
            workspace, "new-proj", "New Project", _TEMPLATE_DIR
        )

    assert result.backend_port == 8022
    assert result.frontend_port == 5192

    # Les ports apparaissent dans les fichiers générés
    vite_content = (workspace / "new-proj" / "frontend" / "vite.config.ts").read_text(
        encoding="utf-8"
    )
    assert "5192" in vite_content

    agents = json.loads((workspace / "new-proj" / "agents.json").read_text(encoding="utf-8"))
    backend_svc = next(s for s in agents["services"] if s["nom"] == "backend")
    assert "8022" in backend_svc["commande"]


async def test_agents_json_has_required_settings(workspace: Path) -> None:
    """agents.json : autonomy merge, merge_without_ci true, base_branch main.

    test_command contient python -m pytest et python -m mypy.
    """
    with patch(_PATCH_GIT, new_callable=AsyncMock) as m:
        m.return_value = _GIT_OK
        await create_project_from_template(
            workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
        )

    data = json.loads(
        (workspace / "mon-projet" / "agents.json").read_text(encoding="utf-8")
    )
    assert data["autonomy"] == "merge"
    assert data["merge_without_ci"] is True
    assert data["base_branch"] == "main"

    cmd: str = data["pipeline"]["test_command"]
    assert "python -m pytest" in cmd
    assert "python -m mypy" in cmd


async def test_duplicate_project_id_raises_value_error(workspace: Path) -> None:
    """Créer un project_id existant lève ValueError sans rien écrire.

    Le routeur convertit cette ValueError en HTTP 409.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    existing = workspace / "already-there"
    existing.mkdir()
    initial_children = sorted(str(f) for f in existing.rglob("*"))

    with pytest.raises(ValueError, match="déjà existant"):
        await create_project_from_template(
            workspace, "already-there", "Duplicate", _TEMPLATE_DIR
        )

    # Aucun fichier créé dans le dossier existant
    assert sorted(str(f) for f in existing.rglob("*")) == initial_children


async def test_no_github_api_calls(workspace: Path) -> None:
    """La création n'effectue aucun appel à l'API GitHub.

    Le service ne nécessite ni token ni paramètre GitHub. S'il en faisait,
    l'absence de token ferait échouer le test.
    """
    with patch(_PATCH_GIT, new_callable=AsyncMock) as m:
        m.return_value = _GIT_OK
        result = await create_project_from_template(
            workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
        )

    # Le projet est créé sans erreur, aucun token GitHub n'était requis.
    assert result.project.id == "mon-projet"


async def test_response_contains_ports_and_git_ready(workspace: Path) -> None:
    """La réponse porte backend_port, frontend_port et git_ready."""
    with patch(_PATCH_GIT, new_callable=AsyncMock) as m:
        m.return_value = _GIT_OK
        result = await create_project_from_template(
            workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
        )

    # Pas de projets existants → premier couple libre (8020, 5190)
    assert result.backend_port == 8020
    assert result.frontend_port == 5190
    assert result.git_ready is True
    assert result.project is not None
