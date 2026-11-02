"""CLAUDE.md d'un projet issu du gabarit fastapi-react — ticket-409.

`ProjectLoader.create_project` écrit un CLAUDE.md générique (« aucun agent »,
« stack à définir ») avant que le manifeste complet n'existe. Ce module le
réécrit une fois `agents.json` posé, pour que chaque agent lise un projet vrai.
"""
from pathlib import Path

from tessera.services.manifeste import lire_fichier


def active_roles(agents_json: Path) -> list[str]:
    """Return the roles declared active in a project's agents.json."""
    agents = lire_fichier(agents_json).get("agents")
    if not isinstance(agents, list):
        return []
    return [
        str(agent["role"])
        for agent in agents
        if isinstance(agent, dict) and "role" in agent and agent.get("active", True)
    ]


def render_claude_md(
    name: str, roles: list[str], backend_port: int, frontend_port: int
) -> str:
    """Render the CLAUDE.md of a template project from its real manifest data."""
    agents_block = "\n".join(f"- `{role}`" for role in roles)
    return f"""# {name}

Projet créé via Tessera depuis le gabarit fastapi-react.

---

## Agents actifs sur ce projet

{agents_block}

## Stack

- **Backend** : FastAPI + SQLite, dossier `backend/`, port {backend_port}
- **Frontend** : React 19 + Vite + Tailwind v4, dossier `frontend/`, port {frontend_port}
"""


def write_claude_md(
    project_path: Path, name: str, backend_port: int, frontend_port: int
) -> None:
    """Rewrite the project's CLAUDE.md from the agents.json already on disk."""
    roles = active_roles(project_path / "agents.json")
    (project_path / "CLAUDE.md").write_text(
        render_claude_md(name, roles, backend_port, frontend_port),
        encoding="utf-8",
    )
