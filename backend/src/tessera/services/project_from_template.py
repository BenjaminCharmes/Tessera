"""Service de création de projet depuis le gabarit fastapi-react — ticket-373."""
import json
import re
import shutil
from pathlib import Path

from tessera.config import _REPO_ROOT
from tessera.models.project import ProjectCreate, ProjectFromTemplateResult
from tessera.services.git_link import init_repository
from tessera.services.project_loader import ProjectLoader
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

# Répertoire du gabarit, ancré sur la racine du dépôt.
_TEMPLATE_DIR = _REPO_ROOT / "templates" / "fastapi-react"

# Base des ports attribués aux projets créés depuis le gabarit.
_BACKEND_PORT_BASE = 8020
_FRONTEND_PORT_BASE = 5190

# Commande de tests complète, compatible WDAC (python -m), sans `cd` :
# reprise de la configuration éprouvée de vigie.
_TEST_COMMAND = (
    "npm --prefix frontend run typecheck && npm --prefix frontend run lint"
    " && npm --prefix frontend test && npm --prefix frontend run build"
    " && uv --directory backend run python -m mypy ."
    " && uv --directory backend run python -m pytest -q"
)

# Rôles des projets créés depuis le gabarit : production sur Sonnet, jugement
# et documentation sur Haiku via l'abonnement (configuration de vigie).
_MODELE_PRODUCTION = "claude-sonnet-5-5"
_MODELE_JUGEMENT = "claude-haiku-4-5"
_ROLES_PRODUCTION = ["codeur", "architect", "reviewer"]
_ROLES_JUGEMENT = ["securite", "validateur", "doc-technique", "doc-fonctionnelle"]
_ROLES_AVEC_SKILL_DESIGN = {"codeur", "architect"}


def _collect_used_ports(workspace: Path) -> set[int]:
    """Collecte les ports déjà utilisés dans les projets du workspace.

    Lit les commandes de services dans agents.json et les fichiers vite.config.ts.
    """
    used: set[int] = set()
    if not workspace.is_dir():
        return used

    for project_dir in workspace.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue

        # Ports déclarés dans les services de agents.json
        agents_json = project_dir / "agents.json"
        if agents_json.exists():
            try:
                data = json.loads(agents_json.read_text(encoding="utf-8"))
                for service in data.get("services", []):
                    commande = service.get("commande", "")
                    for m in re.finditer(r"--port[= ](\d+)", commande):
                        used.add(int(m.group(1)))
            except Exception:
                pass

        # Port déclaré dans frontend/vite.config.ts
        vite_config = project_dir / "frontend" / "vite.config.ts"
        if vite_config.exists():
            try:
                content = vite_config.read_text(encoding="utf-8")
                for m in re.finditer(r"\bport:\s*(\d+)", content):
                    used.add(int(m.group(1)))
            except Exception:
                pass

    return used


def _find_free_ports(workspace: Path) -> tuple[int, int]:
    """Retourne le premier couple (backend_port, frontend_port) libre."""
    used = _collect_used_ports(workspace)
    n = 0
    while True:
        backend_port = _BACKEND_PORT_BASE + n
        frontend_port = _FRONTEND_PORT_BASE + n
        if backend_port not in used and frontend_port not in used:
            return backend_port, frontend_port
        n += 1


def _substitute_markers(content: str, markers: dict[str, str]) -> str:
    """Remplace les marqueurs {{clef}} par leur valeur."""
    for key, value in markers.items():
        content = content.replace("{{" + key + "}}", value)
    return content


def _copy_template(template_dir: Path, dest_dir: Path, markers: dict[str, str]) -> None:
    """Copie le gabarit dans dest_dir en substituant les marqueurs."""
    for src_file in template_dir.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(template_dir)
        dest_file = dest_dir / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = src_file.read_text(encoding="utf-8")
            dest_file.write_text(_substitute_markers(content, markers), encoding="utf-8")
        except UnicodeDecodeError:
            # Fichier binaire : copie directe sans substitution
            shutil.copy2(src_file, dest_file)


def _build_agents_json(project_id: str, backend_port: int, frontend_port: int) -> str:
    """Construit le manifeste agents.json pour un projet gabarit."""
    agents: list[dict[str, object]] = [
        {
            "role": role,
            "model": _MODELE_PRODUCTION,
            "max_tokens": 8192 if role == "codeur" else 4096,
            "prompt_file": f"agents/prompts/{role}.md",
            "active": True,
            **({"skills": ["tessera:design-ui"]} if role in _ROLES_AVEC_SKILL_DESIGN else {}),
        }
        for role in _ROLES_PRODUCTION
    ]
    agents += [
        {
            "role": role,
            "model": _MODELE_JUGEMENT,
            "max_tokens": 4096,
            "prompt_file": f"agents/prompts/{role}.md",
            "active": True,
            "provider": "agent_sdk",
        }
        for role in _ROLES_JUGEMENT
    ]
    data: dict[str, object] = {
        "project_id": project_id,
        "artifacts": "tracked",
        "autonomy": "merge",
        "merge_without_ci": True,
        "base_branch": "main",
        "agents": agents,
        "services": [
            {
                "nom": "backend",
                "commande": (
                    "uv run python -m uvicorn app.main:app"
                    f" --host 127.0.0.1 --port {backend_port}"
                ),
                "cwd": "backend",
            },
            {
                "nom": "frontend",
                "commande": "npm run dev",
                "cwd": "frontend",
            },
        ],
        "pipeline": {
            "max_review_rounds": 3,
            "testeur_enabled": True,
            "test_command": _TEST_COMMAND,
            "securite_enabled": True,
            "validateur_enabled": True,
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


async def create_project_from_template(
    workspace: Path,
    project_id: str,
    name: str,
    template_dir: Path | None = None,
) -> ProjectFromTemplateResult:
    """Crée un projet depuis le gabarit fastapi-react.

    Steps:
    1. Allocates free (backend, frontend) port pair.
    2. Creates the Tessera folder structure via ProjectLoader.create_project.
    3. Copies the template files with marker substitution.
    4. Writes the definitive agents.json (overwrites the default).
    5. Initialises a git repository (reads artifacts mode from agents.json).

    Raises ValueError when project_id already exists (→ HTTP 409 in the router).
    No GitHub repository is created.
    """
    if template_dir is None:
        template_dir = _TEMPLATE_DIR

    # Attribution des ports libres avant toute écriture.
    backend_port, frontend_port = _find_free_ports(workspace)

    # Création de la structure Tessera (tickets/, memory/, CLAUDE.md, agents.json).
    # Lève ValueError si project_id existe déjà.
    loader = ProjectLoader(workspace)
    await loader.create_project(ProjectCreate(project_id=project_id, name=name))

    project_path = workspace / project_id

    # Copie du gabarit par-dessus la structure existante.
    markers: dict[str, str] = {
        "project_id": project_id,
        "project_name": name,
        "backend_port": str(backend_port),
        "frontend_port": str(frontend_port),
    }
    _copy_template(template_dir, project_path, markers)

    # Manifeste complet : remplace le manifeste par défaut écrit par create_project.
    (project_path / "agents.json").write_text(
        _build_agents_json(project_id, backend_port, frontend_port),
        encoding="utf-8",
    )

    # Initialisation du dépôt git (lit artifacts: tracked depuis agents.json).
    git_ready = False
    try:
        await init_repository(project_path)
        git_ready = True
    except Exception as exc:
        _logger.warning(
            "template_project_git_init_failed",
            extra={"project_id": project_id, "error": str(exc)},
        )

    # Rechargement du projet après écriture des fichiers (invalide le cache de mtime).
    project = await loader.load_project(project_id)

    return ProjectFromTemplateResult(
        project=project,
        backend_port=backend_port,
        frontend_port=frontend_port,
        git_ready=git_ready,
    )
