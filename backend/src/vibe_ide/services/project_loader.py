import re
from pathlib import Path

from vibe_ide.models.project import Project, ProjectCreate


# ------------------------------------------------------------------
# Module-level helpers (conservés pour les tests existants)
# ------------------------------------------------------------------


def load_project(project_path: Path) -> Project:
    """Charge un projet depuis son chemin absolu."""
    if not project_path.is_dir():
        raise ValueError(f"Dossier introuvable : {project_path}")

    raw = ""
    if (claude_md := project_path / "CLAUDE.md").exists():
        raw = claude_md.read_text(encoding="utf-8")

    return Project(
        id=project_path.name,
        name=_parse_name(raw, fallback=project_path.name),
        path=project_path,
        description=_parse_description(raw),
        active_agents=_parse_active_agents(raw),
        stack=_parse_stack(raw),
        raw_claude_md=raw,
    )


def list_projects(workspace: Path) -> list[Project]:
    """Liste tous les sous-dossiers d'un workspace (sans filtrer sur CLAUDE.md)."""
    if not workspace.is_dir():
        return []
    return [
        load_project(p)
        for p in sorted(workspace.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


# ------------------------------------------------------------------
# ProjectLoader — API async pour l'orchestrateur
# ------------------------------------------------------------------


class ProjectLoader:
    """Façade async autour du workspace. Filtre les projets sans CLAUDE.md."""

    def __init__(self, workspace_dir: Path) -> None:
        self._workspace = workspace_dir

    async def list_projects(self) -> list[Project]:
        if not self._workspace.is_dir():
            return []
        projects: list[Project] = []
        for p in sorted(self._workspace.iterdir()):
            if p.is_dir() and not p.name.startswith(".") and (p / "CLAUDE.md").exists():
                try:
                    projects.append(load_project(p))
                except Exception:
                    continue
        return projects

    async def load_project(self, project_id: str) -> Project:
        project_path = self._workspace / project_id
        return load_project(project_path)  # raises ValueError si absent

    async def create_project(self, body: ProjectCreate) -> Project:
        project_path = self._workspace / body.project_id
        if project_path.exists():
            raise ValueError(f"Projet déjà existant : {body.project_id}")

        for subdir in [
            "tickets/todo",
            "tickets/in-progress",
            "tickets/done",
            "tickets/cancelled",
            "memory",
            "workspace",
        ]:
            (project_path / subdir).mkdir(parents=True, exist_ok=True)

        content = body.claude_md_content or _default_claude_md(
            body.project_id, body.name, body.active_agents
        )
        (project_path / "CLAUDE.md").write_text(content, encoding="utf-8")
        return load_project(project_path)


# ------------------------------------------------------------------
# Parsers internes
# ------------------------------------------------------------------


def _parse_name(content: str, fallback: str) -> str:
    """Extrait le titre de la première ligne H1 du CLAUDE.md."""
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return fallback


def _parse_description(content: str) -> str:
    """Première ligne non vide non-titre."""
    skip_heading = True
    for line in content.splitlines():
        stripped = line.strip()
        if skip_heading and stripped.startswith("#"):
            skip_heading = False
            continue
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _parse_active_agents(content: str) -> list[str]:
    in_section = False
    agents: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Agents actifs", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section:
            m = re.match(r"^-\s+`(\w+)`", line)
            if m:
                agents.append(m.group(1))
    return agents


def _parse_stack(content: str) -> str | None:
    in_section = False
    lines: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Stack", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section and line.strip():
            lines.append(line.strip())
    return "\n".join(lines) if lines else None


def _default_claude_md(project_id: str, name: str, active_agents: list[str]) -> str:
    agents_block = (
        "\n".join(f"- `{a}` — à configurer" for a in active_agents)
        if active_agents
        else "_Aucun agent configuré._"
    )
    return f"""# {name}

Projet créé via vibe-ide.

---

## Agents actifs sur ce projet

{agents_block}

## Stack

À définir.
"""
