from pathlib import Path

import json

import pytest

from vibe_ide.models.project import ProjectCreate
from vibe_ide.services.project_loader import (
    ProjectLoader,
    list_projects,
    load_agents_config,
    load_pipeline_config,
    load_project,
)

_CLAUDE_MD = """\
# mon-projet

Description du projet.

## Agents actifs sur ce projet

- `codeur` — fait le code
- `reviewer` — valide

## Stack spécifique

Python + FastAPI
"""


# ------------------------------------------------------------------
# Module-level helpers (backward compat)
# ------------------------------------------------------------------


def test_load_project_with_claude_md(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text(_CLAUDE_MD, encoding="utf-8")

    project = load_project(project_dir)

    assert project.id == "my-project"
    assert project.name == "mon-projet"  # parsé depuis H1
    assert project.path == project_dir
    assert project.active_agents == ["codeur", "reviewer"]
    assert project.stack is not None and "Python" in project.stack
    assert "## Agents actifs" in project.raw_claude_md


def test_load_project_description_skips_heading(tmp_path: Path) -> None:
    project_dir = tmp_path / "p"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text("# Titre\n\nDescription ici.\n", encoding="utf-8")

    project = load_project(project_dir)

    assert project.description == "Description ici."


def test_load_project_without_claude_md(tmp_path: Path) -> None:
    project_dir = tmp_path / "bare-project"
    project_dir.mkdir()

    project = load_project(project_dir)

    assert project.id == "bare-project"
    assert project.name == "bare-project"  # fallback sur nom du dossier
    assert project.description == ""
    assert project.active_agents == []
    assert project.stack is None
    assert project.raw_claude_md == ""


def test_load_project_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Dossier introuvable"):
        load_project(tmp_path / "nonexistent")


def test_list_projects_empty_workspace(tmp_path: Path) -> None:
    assert list_projects(tmp_path) == []


def test_list_projects_nonexistent_workspace(tmp_path: Path) -> None:
    assert list_projects(tmp_path / "missing") == []


def test_list_projects_returns_all(tmp_path: Path) -> None:
    for name in ["project-a", "project-b", "project-c"]:
        (tmp_path / name).mkdir()

    projects = list_projects(tmp_path)

    assert len(projects) == 3
    assert [p.id for p in projects] == ["project-a", "project-b", "project-c"]


def test_list_projects_skips_hidden_dirs(tmp_path: Path) -> None:
    (tmp_path / "visible").mkdir()
    (tmp_path / ".hidden").mkdir()

    projects = list_projects(tmp_path)

    assert len(projects) == 1
    assert projects[0].id == "visible"


# ------------------------------------------------------------------
# ProjectLoader — async class
# ------------------------------------------------------------------


async def test_project_loader_list_filters_claude_md(tmp_path: Path) -> None:
    (tmp_path / "with-claude").mkdir()
    (tmp_path / "with-claude" / "CLAUDE.md").write_text("# avec\n", encoding="utf-8")
    (tmp_path / "without-claude").mkdir()

    projects = await ProjectLoader(tmp_path).list_projects()

    assert len(projects) == 1
    assert projects[0].id == "with-claude"


async def test_project_loader_list_empty_workspace(tmp_path: Path) -> None:
    assert await ProjectLoader(tmp_path).list_projects() == []


async def test_project_loader_list_missing_workspace(tmp_path: Path) -> None:
    assert await ProjectLoader(tmp_path / "missing").list_projects() == []


async def test_project_loader_load_project(tmp_path: Path) -> None:
    (tmp_path / "my-proj").mkdir()
    (tmp_path / "my-proj" / "CLAUDE.md").write_text("# My Project\n\nDesc.\n", encoding="utf-8")

    project = await ProjectLoader(tmp_path).load_project("my-proj")

    assert project.id == "my-proj"
    assert project.name == "My Project"


async def test_project_loader_load_project_not_found(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Dossier introuvable"):
        await ProjectLoader(tmp_path).load_project("ghost")


# ------------------------------------------------------------------
# ProjectLoader.create_project
# ------------------------------------------------------------------


async def test_create_project_creates_structure(tmp_path: Path) -> None:
    body = ProjectCreate(project_id="new-proj", name="Nouveau projet")

    project = await ProjectLoader(tmp_path).create_project(body)

    assert project.id == "new-proj"
    assert (tmp_path / "new-proj" / "CLAUDE.md").exists()
    assert (tmp_path / "new-proj" / "tickets" / "todo").is_dir()
    assert (tmp_path / "new-proj" / "tickets" / "done").is_dir()
    assert (tmp_path / "new-proj" / "memory").is_dir()
    assert (tmp_path / "new-proj" / "workspace").is_dir()


async def test_create_project_with_agents(tmp_path: Path) -> None:
    body = ProjectCreate(
        project_id="agent-proj",
        name="Projet avec agents",
        active_agents=["codeur", "reviewer"],
    )

    project = await ProjectLoader(tmp_path).create_project(body)

    assert project.active_agents == ["codeur", "reviewer"]
    assert "codeur" in project.raw_claude_md


async def test_create_project_custom_claude_md(tmp_path: Path) -> None:
    custom = "# Custom\n\n## Agents actifs sur ce projet\n\n- `architect` — design\n"
    body = ProjectCreate(
        project_id="custom-proj",
        name="Custom",
        claude_md_content=custom,
    )

    project = await ProjectLoader(tmp_path).create_project(body)

    assert project.raw_claude_md == custom
    assert project.active_agents == ["architect"]


async def test_create_project_conflict(tmp_path: Path) -> None:
    (tmp_path / "existing").mkdir()
    body = ProjectCreate(project_id="existing", name="Existant")

    with pytest.raises(ValueError, match="Projet déjà existant"):
        await ProjectLoader(tmp_path).create_project(body)


async def test_create_project_scaffolds_agents_json(tmp_path: Path) -> None:
    body = ProjectCreate(
        project_id="proj-with-agents",
        name="Proj",
        active_agents=["codeur", "reviewer"],
    )

    await ProjectLoader(tmp_path).create_project(body)

    agents_json = tmp_path / "proj-with-agents" / "agents.json"
    assert agents_json.exists()
    data = json.loads(agents_json.read_text(encoding="utf-8"))
    roles = [a["role"] for a in data["agents"]]
    assert roles == ["codeur", "reviewer"]
    assert data["agents"][0]["model"] == "claude-sonnet-4-6"
    assert data["pipeline"]["default"] == ["codeur", "reviewer"]


async def test_create_project_no_agents_json_when_no_agents(tmp_path: Path) -> None:
    body = ProjectCreate(project_id="bare-proj", name="Sans agents")

    await ProjectLoader(tmp_path).create_project(body)

    assert not (tmp_path / "bare-proj" / "agents.json").exists()


# ------------------------------------------------------------------
# load_agents_config / load_pipeline_config
# ------------------------------------------------------------------


def _write_agents_json(project_dir: Path, agents: list[dict], pipeline: dict | None = None) -> None:
    data: dict = {"project_id": project_dir.name, "agents": agents}
    if pipeline:
        data["pipeline"] = pipeline
    (project_dir / "agents.json").write_text(json.dumps(data), encoding="utf-8")


def test_load_agents_config_no_file(tmp_path: Path) -> None:
    assert load_agents_config(tmp_path) == []


def test_load_agents_config_returns_all(tmp_path: Path) -> None:
    _write_agents_json(tmp_path, [
        {"role": "codeur", "model": "claude-sonnet-4-6", "max_tokens": 8192,
         "prompt_file": "agents/prompts/codeur.md", "active": True},
        {"role": "reviewer", "model": "claude-sonnet-4-6", "max_tokens": 4096,
         "prompt_file": "agents/prompts/reviewer.md", "active": True},
    ])

    configs = load_agents_config(tmp_path)

    assert len(configs) == 2
    assert configs[0].role == "codeur"
    assert configs[0].model == "claude-sonnet-4-6"
    assert configs[0].max_tokens == 8192
    assert configs[1].role == "reviewer"


def test_load_agents_config_defaults(tmp_path: Path) -> None:
    _write_agents_json(tmp_path, [
        {"role": "architect", "model": "claude-sonnet-4-6", "max_tokens": 4096,
         "prompt_file": "agents/prompts/architect.md"},
    ])

    config = load_agents_config(tmp_path)[0]

    assert config.active is True
    assert config.max_instances == 1


def test_load_agents_config_malformed_json(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text("not valid json", encoding="utf-8")

    assert load_agents_config(tmp_path) == []


def test_load_pipeline_config_no_file(tmp_path: Path) -> None:
    pipeline = load_pipeline_config(tmp_path)
    assert pipeline.max_review_rounds == 3
    assert pipeline.auto_merge_on_approve is False
    assert pipeline.default == []


def test_load_pipeline_config_reads_file(tmp_path: Path) -> None:
    _write_agents_json(tmp_path, [], pipeline={
        "default": ["codeur", "reviewer"],
        "max_review_rounds": 5,
        "auto_merge_on_approve": True,
    })

    pipeline = load_pipeline_config(tmp_path)

    assert pipeline.default == ["codeur", "reviewer"]
    assert pipeline.max_review_rounds == 5
    assert pipeline.auto_merge_on_approve is True
