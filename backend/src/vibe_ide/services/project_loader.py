import re
from pathlib import Path

from vibe_ide.models.project import Project


def load_project(project_path: Path) -> Project:
    """Charge un projet depuis son dossier en lisant son CLAUDE.md."""
    if not project_path.is_dir():
        raise ValueError(f"Dossier introuvable : {project_path}")

    raw = ""
    if (claude_md := project_path / "CLAUDE.md").exists():
        raw = claude_md.read_text(encoding="utf-8")

    return Project(
        id=project_path.name,
        name=project_path.name,
        path=project_path,
        description=_parse_description(raw),
        active_agents=_parse_active_agents(raw),
        stack=_parse_stack(raw),
        raw_claude_md=raw,
    )


def list_projects(workspace: Path) -> list[Project]:
    """Liste tous les projets dans le workspace."""
    if not workspace.is_dir():
        return []
    return [
        load_project(p)
        for p in sorted(workspace.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


# ------------------------------------------------------------------
# Parsers internes
# ------------------------------------------------------------------


def _parse_description(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
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
