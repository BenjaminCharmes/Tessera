"""A project created from the IDE is the root of its own git repository.

Without it, `GitWorkspaceService` raises `NotAGitRepository`: ADR-024 requires
`git rev-parse --show-toplevel` to return exactly the project folder, so that a
project sitting in `projects/` never makes git walk up to Tessera's own
repository. The run therefore stopped *before* creating its first branch, and
nothing was ever committed.

Every project created from the UI was born unusable for the pipeline, and the
user only found out at the first run.
"""
import asyncio
from pathlib import Path

import pytest

import tessera.routers.projects as projects_router
from tessera.config import settings
from tessera.models.project import ProjectCreate
from tessera.routers.projects import create_project


@pytest.fixture(autouse=True)
def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "ide_prompts_dir", tmp_path / "prompts")
    return tmp_path


async def _git(path: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode().strip()


async def test_le_projet_cree_est_la_racine_de_son_depot(tmp_path: Path) -> None:
    """ADR-024: the toplevel must be the project folder, not an ancestor."""
    await create_project(ProjectCreate(project_id="neuf", name="Neuf"))

    projet = tmp_path / "neuf"
    assert (projet / ".git").exists()

    code, toplevel = await _git(projet, "rev-parse", "--show-toplevel")
    assert code == 0
    assert Path(toplevel).resolve() == projet.resolve()


async def test_le_depot_cree_porte_un_commit_initial(tmp_path: Path) -> None:
    """Without the initial commit, everything already on disk would look like
    untracked changes to the pipeline and get swept into the first ticket's
    commit."""
    await create_project(ProjectCreate(project_id="neuf", name="Neuf"))
    projet = tmp_path / "neuf"

    _, sale = await _git(projet, "status", "--porcelain")
    assert sale == "", f"arbre sale à la création : {sale!r}"

    code, _ = await _git(projet, "rev-parse", "HEAD")
    assert code == 0, "aucun commit initial"


async def test_la_reponse_annonce_que_le_depot_est_pret(tmp_path: Path) -> None:
    """The user must know whether the repository is usable, the way
    `agents_created` already reports what was created."""
    result = await create_project(ProjectCreate(project_id="neuf", name="Neuf"))

    assert result.repository_ready is True


async def test_un_git_indisponible_ne_fait_pas_echouer_la_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The project already exists on disk: answering an error would leave the
    user with a created project and a failure message."""

    async def _casse(_: Path) -> None:
        raise RuntimeError("git introuvable")

    monkeypatch.setattr(projects_router, "init_repository", _casse)

    result = await create_project(ProjectCreate(project_id="neuf", name="Neuf"))

    assert result.project.id == "neuf"
    assert result.repository_ready is False
    assert (tmp_path / "neuf" / "CLAUDE.md").exists()


async def test_le_mode_des_artefacts_est_pose_avant_le_commit_initial(
    tmp_path: Path,
) -> None:
    """Order matters: initialising first would commit the very artifacts the
    mode was meant to keep out of the repository (ADR-021, ADR-023).

    `init_repository` stages with `git add -A`, so anything not excluded by
    then lands in the initial commit — and, on a client repository, in the
    first push.
    """
    await create_project(ProjectCreate(project_id="neuf", name="Neuf"))
    projet = tmp_path / "neuf"

    _, suivis = await _git(projet, "ls-files")
    fichiers = set(suivis.splitlines())

    exclude = projet / ".git" / "info" / "exclude"
    assert exclude.exists(), "aucun dépôt initialisé : le mode n'a rien pu exclure"

    if "tickets" in exclude.read_text(encoding="utf-8"):
        exclus = {f for f in fichiers if f.startswith(("tickets/", "memory/"))}
        assert not exclus, f"artefacts commités malgré l'exclusion : {exclus}"
