import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import patch as mock_patch

import pytest

from tessera.models.project import ProjectCreate
from tessera.services.project_loader import (
    ProjectLoader,
    _default_agents_json,
    _load_category,
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
    # Pas de `auto_merge_on_approve` : il était écrit à `true` et ne faisait
    # rien. Qui merge est décidé par `autonomy` (ADR-029, ticket-091).
    assert "auto_merge_on_approve" not in data["pipeline"]


async def test_create_project_ecrit_un_manifeste_meme_sans_agents(
    tmp_path: Path,
) -> None:
    """Le manifeste est écrit même sans `active_agents` (ticket-105).

    Ce test verrouillait l'inverse. La modale de création n'envoie aucun rôle,
    si bien qu'un projet né de l'UI n'avait aucun `agents.json` : le pipeline
    retombait en silence sur `codeur → reviewer`, la sécurité et le validateur
    éteints alors que les deux services sont déjà câblés.
    """
    body = ProjectCreate(project_id="bare-proj", name="Sans agents")

    await ProjectLoader(tmp_path).create_project(body)

    manifeste = tmp_path / "bare-proj" / "agents.json"
    assert manifeste.exists()

    data = json.loads(manifeste.read_text(encoding="utf-8"))
    assert {a["role"] for a in data["agents"]} == {"codeur", "reviewer"}


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
    assert pipeline.testeur_enabled is False


def test_load_pipeline_config_reads_file(tmp_path: Path) -> None:
    _write_agents_json(tmp_path, [], pipeline={
        "max_review_rounds": 5,
        "testeur_enabled": True,
    })

    pipeline = load_pipeline_config(tmp_path)

    assert pipeline.max_review_rounds == 5
    assert pipeline.testeur_enabled is True


def test_un_reglage_disparu_ne_casse_pas_un_projet_existant(tmp_path: Path) -> None:
    # `default` et `auto_merge_on_approve` traînent encore dans les agents.json
    # déjà écrits. Les ignorer vaut mieux que refuser de charger le projet.
    _write_agents_json(tmp_path, [], pipeline={
        "default": ["codeur"],
        "auto_merge_on_approve": True,
        "max_review_rounds": 4,
    })

    pipeline = load_pipeline_config(tmp_path)

    assert pipeline.max_review_rounds == 4


# ------------------------------------------------------------------
# Le nom d'un projet n'est pas le nom d'un fichier — ticket-093
# ------------------------------------------------------------------


def test_le_nom_de_fichier_ne_devient_pas_le_nom_du_projet(tmp_path: Path) -> None:
    # Vu à l'écran : « Lyra — CLAUDE.md », « CLAUDE.md — projet ide-core ».
    # Le H1 était écrit comme un en-tête de fichier, puis relu comme le nom du
    # projet (ADR-007). Deux usages, une seule chaîne.
    (tmp_path / "CLAUDE.md").write_text("# Lyra — CLAUDE.md\n", encoding="utf-8")

    assert load_project(tmp_path).name == "Lyra"


def test_la_decoration_en_tete_est_retiree_aussi(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text(
        "# CLAUDE.md — projet ide-core\n", encoding="utf-8"
    )

    assert load_project(tmp_path).name == "ide-core"


def test_un_titre_propre_est_laisse_intact(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Orion Analytics\n", encoding="utf-8")

    assert load_project(tmp_path).name == "Orion Analytics"


def test_un_titre_qui_ne_serait_que_la_decoration_retombe_sur_le_dossier(
    tmp_path: Path,
) -> None:
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# CLAUDE.md\n", encoding="utf-8")

    assert load_project(projet).name == "mon-projet"


# ------------------------------------------------------------------
# _default_agents_json — skills tessera:design-ui (ticket-294)
# ------------------------------------------------------------------


def _agents_by_role(manifeste: str) -> dict[str, dict]:
    """Retourne un dict role → entrée agent depuis le JSON du manifeste."""
    data = json.loads(manifeste)
    return {a["role"]: a for a in data["agents"]}


def test_default_agents_json_adds_design_skill_to_codeur() -> None:
    """codeur reçoit tessera:design-ui dans le manifeste par défaut."""
    manifeste = _default_agents_json("mon-projet", ["codeur"], "local")
    agents = _agents_by_role(manifeste)

    assert "codeur" in agents
    assert agents["codeur"].get("skills") == ["tessera:design-ui"]


def test_default_agents_json_adds_design_skill_to_architect() -> None:
    """architect reçoit tessera:design-ui dans le manifeste par défaut."""
    manifeste = _default_agents_json("mon-projet", ["architect"], "local")
    agents = _agents_by_role(manifeste)

    assert "architect" in agents
    assert agents["architect"].get("skills") == ["tessera:design-ui"]


def test_default_agents_json_no_skill_for_reviewer() -> None:
    """reviewer ne reçoit aucun skill dans le manifeste par défaut."""
    manifeste = _default_agents_json("mon-projet", ["reviewer"], "local")
    agents = _agents_by_role(manifeste)

    assert "reviewer" in agents
    assert "skills" not in agents["reviewer"]


def test_default_agents_json_no_skill_for_securite() -> None:
    """securite ne reçoit aucun skill dans le manifeste par défaut."""
    manifeste = _default_agents_json("mon-projet", ["securite"], "local")
    agents = _agents_by_role(manifeste)

    assert "securite" in agents
    assert "skills" not in agents["securite"]


def test_default_agents_json_no_skill_for_validateur() -> None:
    """validateur ne reçoit aucun skill dans le manifeste par défaut."""
    manifeste = _default_agents_json("mon-projet", ["validateur"], "local")
    agents = _agents_by_role(manifeste)

    assert "validateur" in agents
    assert "skills" not in agents["validateur"]


def test_default_agents_json_mixed_roles_skills_only_for_ui_roles() -> None:
    """Sur un pipeline complet, seuls codeur et architect ont le skill de design."""
    roles = ["codeur", "reviewer", "architect", "securite", "validateur"]
    manifeste = _default_agents_json("mon-projet", roles, "local")
    agents = _agents_by_role(manifeste)

    for role in ("codeur", "architect"):
        assert agents[role].get("skills") == ["tessera:design-ui"], f"{role} doit avoir le skill"
    for role in ("reviewer", "securite", "validateur"):
        assert "skills" not in agents[role], f"{role} ne doit pas avoir de skills"


# ------------------------------------------------------------------
# Cache de projet — ticket-352
# ------------------------------------------------------------------


def _advance_mtime(path: Path, seconds: float = 1.0) -> None:
    """Force the mtime of a file ahead by `seconds` to guarantee a cache miss."""
    ts = time.time() + seconds
    os.utime(path, (ts, ts))


async def test_project_cache_reloads_on_agents_json_change(tmp_path: Path) -> None:
    """A modified agents.json is reloaded on the next list_projects call."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text("# My Project\n", encoding="utf-8")
    agents_json = project_dir / "agents.json"
    agents_json.write_text(
        '{"project_id": "my-project", "agents": [], "category": "first"}',
        encoding="utf-8",
    )

    loader = ProjectLoader(tmp_path)
    projects1 = await loader.list_projects()
    assert projects1[0].category == "first"

    agents_json.write_text(
        '{"project_id": "my-project", "agents": [], "category": "second"}',
        encoding="utf-8",
    )
    _advance_mtime(agents_json)

    projects2 = await loader.list_projects()
    assert projects2[0].category == "second"


async def test_project_cache_skips_reload_without_change(tmp_path: Path) -> None:
    """list_projects does not re-read project files when neither key file has changed."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "CLAUDE.md").write_text("# My Project\n", encoding="utf-8")

    loader = ProjectLoader(tmp_path)
    with mock_patch(
        "tessera.services.project_loader._load_category",
        wraps=_load_category,
    ) as mock_cat:
        await loader.list_projects()
        first_count = mock_cat.call_count
        await loader.list_projects()
        second_count = mock_cat.call_count

    # _load_category reads agents.json; it must not be called again on cache hit
    assert first_count == 1
    assert second_count == 1


async def test_project_loader_list_projects_uses_asyncio_to_thread(tmp_path: Path) -> None:
    """ProjectLoader.list_projects delegates its disk work to asyncio.to_thread."""
    loader = ProjectLoader(tmp_path)
    with mock_patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_thread:
        await loader.list_projects()
    assert mock_thread.called
