"""A project created from the template agrees with its own manifest — ticket-409.

Branch born on the declared base branch, build output ignored, and a CLAUDE.md
that names the real agents and ports instead of the generic placeholders.
"""
import json
import subprocess
from pathlib import Path

import pytest

from tessera.config import _REPO_ROOT
from tessera.services.project_from_template import create_project_from_template

_TEMPLATE_DIR = _REPO_ROOT / "templates" / "fastapi-react"

_GITIGNORE_ENTRIES = {
    "node_modules/",
    "frontend/dist/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    "*.db",
    ".env",
}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Isolated workspace: every test starts from an empty folder."""
    return tmp_path / "projects"


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


async def test_repository_is_born_on_main_even_if_default_branch_is_master(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """init.defaultBranch=master on the machine must not decide the base branch."""
    global_config = tmp_path / "gitconfig"
    global_config.write_text("[init]\n\tdefaultBranch = master\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    result = await create_project_from_template(
        workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
    )

    assert result.git_ready is True
    assert _git(workspace / "mon-projet", "symbolic-ref", "--short", "HEAD") == "main"


async def test_gitignore_is_copied_with_the_eight_entries(workspace: Path) -> None:
    """The dotfile of the template reaches the created project, entries intact."""
    await create_project_from_template(
        workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
    )

    gitignore = workspace / "mon-projet" / ".gitignore"
    assert gitignore.is_file()
    lines = set(gitignore.read_text(encoding="utf-8").split())
    assert _GITIGNORE_ENTRIES <= lines


async def test_claude_md_lists_every_active_role_and_no_placeholder(
    workspace: Path,
) -> None:
    """CLAUDE.md names each active role of agents.json; placeholders are gone."""
    await create_project_from_template(
        workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
    )

    projet = workspace / "mon-projet"
    data = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    roles = [a["role"] for a in data["agents"] if a["active"]]
    claude_md = (projet / "CLAUDE.md").read_text(encoding="utf-8")

    assert roles
    for role in roles:
        assert f"`{role}`" in claude_md
    assert "Aucun agent configuré" not in claude_md
    assert "À définir" not in claude_md
    assert "FastAPI" in claude_md
    assert "React 19" in claude_md


async def test_claude_md_cites_backend_and_frontend_ports(workspace: Path) -> None:
    """The ports allocated to the project appear in its CLAUDE.md."""
    result = await create_project_from_template(
        workspace, "mon-projet", "Mon Projet", _TEMPLATE_DIR
    )

    claude_md = (workspace / "mon-projet" / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"port {result.backend_port}" in claude_md
    assert f"port {result.frontend_port}" in claude_md
