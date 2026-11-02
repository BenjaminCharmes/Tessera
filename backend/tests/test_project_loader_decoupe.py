"""The three modules split out of `project_loader` — ticket-691."""

import json
from pathlib import Path

import pytest

from tessera.services import project_loader
from tessera.services.extraction_claude_md import (
    lire_readme,
    parse_active_agents,
    parse_description,
    parse_name,
    parse_stack,
)
from tessera.services.gabarits_projet import default_agents_json, default_claude_md
from tessera.services.manifeste_ecriture import (
    AgentAbsentDuProjet,
    set_agent_provider,
    set_pipeline_settings,
)

_CLAUDE_MD = """\
# CLAUDE.md — Mon projet

Une **description** avec un [lien](http://exemple.test).

## Agents actifs

- `codeur` — code
- `reviewer` — relit

## Stack

Python 3.11
FastAPI
"""


def test_parse_name_strips_the_file_name_decoration() -> None:
    assert parse_name(_CLAUDE_MD, fallback="dossier") == "Mon projet"
    assert parse_name("pas de titre", fallback="dossier") == "dossier"


def test_parse_description_falls_back_on_readme() -> None:
    assert parse_description(_CLAUDE_MD) == "Une description avec un lien."
    assert parse_description("# T\n\n> note aux agents\n", "# R\n\nDu readme.\n") == "Du readme."


def test_parse_active_agents_and_stack() -> None:
    assert parse_active_agents(_CLAUDE_MD) == ["codeur", "reviewer"]
    assert parse_stack(_CLAUDE_MD) == "Python 3.11\nFastAPI"
    assert parse_stack("# T\n") is None


def test_lire_readme_returns_empty_when_missing(tmp_path: Path) -> None:
    assert lire_readme(tmp_path) == ""
    (tmp_path / "README.md").write_text("bonjour", encoding="utf-8")
    assert lire_readme(tmp_path) == "bonjour"


def test_default_claude_md_lists_the_agents() -> None:
    texte = default_claude_md("p", "Mon projet", ["codeur"])
    assert texte.startswith("# Mon projet")
    assert "- `codeur`" in texte
    assert "_Aucun agent configuré._" in default_claude_md("p", "N", [])


def test_default_agents_json_falls_back_on_codeur_and_reviewer() -> None:
    data = json.loads(default_agents_json("p", [], "tracked"))
    assert [a["role"] for a in data["agents"]] == ["codeur", "reviewer"]
    assert data["autonomy"] == "commit"


def test_loader_keeps_its_old_names() -> None:
    assert project_loader._default_agents_json is default_agents_json
    assert project_loader.set_agent_provider is set_agent_provider
    assert project_loader.set_pipeline_settings is set_pipeline_settings


def test_set_pipeline_settings_preserves_the_rest_of_the_file(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "pr", "category": "x", "pipeline": {"a": 1}}),
        encoding="utf-8",
    )
    set_pipeline_settings(
        tmp_path, pipeline={"b": 2}, racine={"autonomy": "merge"}, retirer=("category",)
    )
    data = json.loads((tmp_path / "agents.json").read_text(encoding="utf-8"))
    assert data == {"autonomy": "merge", "pipeline": {"a": 1, "b": 2}}


def test_set_pipeline_settings_refuses_a_project_without_manifest(tmp_path: Path) -> None:
    with pytest.raises(AgentAbsentDuProjet):
        set_pipeline_settings(tmp_path, pipeline={}, racine={})
