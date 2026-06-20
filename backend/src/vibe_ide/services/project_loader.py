from pathlib import Path

from vibe_ide.models.project import Project


def load_project(project_path: Path) -> Project:
    """Charge un projet depuis son dossier en lisant son CLAUDE.md."""
    if not project_path.is_dir():
        raise ValueError(f"Dossier introuvable : {project_path}")

    claude_md = project_path / "CLAUDE.md"
    description = ""
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        # Première ligne non vide après les éventuels titres
        for line in content.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                description = stripped
                break

    return Project(
        id=project_path.name,
        name=project_path.name,
        path=project_path,
        description=description,
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
