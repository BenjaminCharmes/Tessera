import re
import shutil
from pathlib import Path
from typing import Literal

from vibe_ide.models.project import Project
from vibe_ide.services.project_loader import load_project

_COPY_EXCLUSIONS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".DS_Store",
}

_COPY_EXCLUSION_PATTERNS = (".pyc", ".env")

_VIBE_SUBDIRS = (
    "tickets/todo",
    "tickets/in-progress",
    "tickets/done",
    "tickets/cancelled",
    "memory",
    "workspace",
)


class ImportError(Exception):
    """Erreur métier lors de l'import d'un projet."""


class ProjectImporter:
    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

    async def import_project(
        self,
        source_path: Path,
        mode: Literal["copy", "symlink"],
        project_id: str | None = None,
    ) -> Project:
        resolved = source_path.resolve()
        self._validate_source(resolved)

        safe_id = project_id or _sanitize_id(resolved.name)
        dest = self._workspace / safe_id

        if dest.exists() or dest.is_symlink():
            raise ImportError(f"Un projet avec l'id '{safe_id}' existe déjà dans le workspace.")

        if mode == "symlink":
            dest.symlink_to(resolved, target_is_directory=True)
        else:
            _copy_project(resolved, dest)

        _scaffold_vibe_dirs(dest)
        return load_project(dest)

    def _validate_source(self, resolved: Path) -> None:
        if not resolved.exists():
            raise ImportError(f"Le dossier source n'existe pas : {resolved}")
        if not resolved.is_dir():
            raise ImportError(f"La source doit être un dossier : {resolved}")

        # Interdire d'importer le workspace lui-même ou un de ses parents
        try:
            resolved.relative_to(self._workspace)
            raise ImportError(
                "Impossible d'importer un dossier qui est déjà dans le workspace vibe-ide."
            )
        except ValueError:
            pass  # resolved n'est pas sous _workspace → ok

        # Interdire si le workspace est sous la source (path traversal)
        try:
            self._workspace.relative_to(resolved)
            raise ImportError(
                "Impossible d'importer un dossier parent du workspace vibe-ide."
            )
        except ValueError:
            pass  # _workspace n'est pas sous resolved → ok


def _sanitize_id(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower())[:50]


def _should_exclude(path: Path) -> bool:
    if path.name in _COPY_EXCLUSIONS:
        return True
    for suffix in _COPY_EXCLUSION_PATTERNS:
        if path.name.endswith(suffix) or path.name.startswith(".env"):
            return True
    return False


def _copy_project(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=False)
    for item in src.iterdir():
        if _should_exclude(item):
            continue
        if item.is_dir():
            shutil.copytree(
                item,
                dest / item.name,
                ignore=shutil.ignore_patterns(*_COPY_EXCLUSIONS, "*.pyc"),
                symlinks=False,
            )
        else:
            shutil.copy2(item, dest / item.name)


def _scaffold_vibe_dirs(project_root: Path) -> None:
    """Crée les sous-dossiers vibe-ide autour d'un projet existant, sans écraser."""
    for subdir in _VIBE_SUBDIRS:
        (project_root / subdir).mkdir(parents=True, exist_ok=True)

    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            f"# {project_root.name}\n\nProjet importé via vibe-ide.\n",
            encoding="utf-8",
        )
