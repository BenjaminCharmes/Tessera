"""Service GitCloneService — ticket-030."""
import asyncio
import json
import re
import shutil
from pathlib import Path

from vibe_ide.models.project import CloneProjectResponse, Project
from vibe_ide.services.project_analyzer import ProjectAnalyzerService
from vibe_ide.services.project_importer import _scaffold_vibe_dirs
from vibe_ide.services.vibe_artifacts import (
    apply_artifact_mode,
    default_mode_for,
)
from vibe_ide.services.project_loader import load_project
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"
)


def _sanitize_id(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower())[:50]


def _repo_name(repo_url: str) -> str:
    return repo_url.rstrip("/").rsplit("/", 1)[-1]


def _build_clone_url(repo_url: str, github_token: str | None) -> str:
    if not github_token:
        return repo_url
    path = repo_url[len("https://github.com/"):]
    return f"https://{github_token}@github.com/{path}"


class CloneError(Exception):
    """Erreur métier lors du clonage."""


class GitCloneService:
    CLONE_TIMEOUT = 60

    def __init__(self, workspace: Path, analyzer: ProjectAnalyzerService) -> None:
        self._workspace = workspace.resolve()
        self._analyzer = analyzer

    async def clone(
        self,
        repo_url: str,
        project_id: str | None = None,
        github_token: str | None = None,
    ) -> CloneProjectResponse:
        if not _GITHUB_URL_RE.match(repo_url):
            raise CloneError(
                f"URL GitHub invalide : {repo_url!r}. "
                "Format attendu : https://github.com/owner/repo"
            )

        safe_id = project_id or _sanitize_id(_repo_name(repo_url))
        dest = self._workspace / safe_id

        if dest.exists() or dest.is_symlink():
            raise CloneError(
                f"Un projet avec l'id '{safe_id}' existe déjà dans le workspace."
            )

        clone_url = _build_clone_url(repo_url, github_token)
        try:
            await self._run_clone(clone_url, dest)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise

        _scaffold_vibe_dirs(dest)
        self._store_github_remote(dest, repo_url)
        # Le dépôt appartient déjà à quelqu'un d'autre : les artefacts
        # vibe-ide restent locaux par défaut (ticket-062). L'utilisateur
        # peut toujours choisir de les partager ensuite.
        await apply_artifact_mode(dest, default_mode_for("clone"))

        analysis = await self._analyzer.analyze(dest)

        project = load_project(dest)
        return CloneProjectResponse(
            project=project,
            claude_md_generated=analysis.claude_md_written,
            detected_stack=analysis.detected_stack,
        )

    async def _run_clone(self, url: str, dest: Path) -> None:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", url, str(dest),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.CLONE_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise CloneError(f"Le clone a dépassé {self.CLONE_TIMEOUT}s.")

        if proc.returncode != 0:
            _logger.warning(
                "git_clone_failed",
                extra={"returncode": proc.returncode},
            )
            raise CloneError(
                f"git clone a échoué (code {proc.returncode}). "
                "Vérifiez l'URL et vos droits d'accès."
            )

    def _store_github_remote(self, project_path: Path, repo_url: str) -> None:
        agents_json = project_path / "agents.json"
        if agents_json.exists():
            try:
                data = json.loads(agents_json.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        else:
            data = {}
        updated = {**data, "github_remote": repo_url}
        agents_json.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
