"""Regression tests — ticket-044 review, finding 4.

``plan_project`` and ``analyze_project`` build a ``PlannerService`` /
``ProjectAnalyzerService`` — both pure text-in/JSON-out agents with no use
for the Claude Agent SDK's file/shell tools. This pins that their router
call sites now request a tool-less provider via ``get_provider(...,
allow_tools=False)``.
"""
import json
from pathlib import Path

import pytest

import tessera.routers.projects as projects_router
from tessera.services.providers import par_role
from tessera.config import settings
from tessera.models.project import AnalyzeProjectRequest, PlanRequest, ProjectCreate
from tessera.routers.projects import analyze_project, create_project, plan_project


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    return tmp_path


def _make_project(workspace: Path, project_id: str) -> None:
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")


async def test_plan_project_utilise_un_provider_sans_outils(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path, "mon-projet")
    captured: dict[str, object] = {}
    real_get_provider = par_role.get_provider

    from unittest.mock import AsyncMock, MagicMock

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps({"tickets": [], "summary": "ok"}))]
    fake_response.usage = MagicMock(
        input_tokens=1, output_tokens=1,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )

    def spy(*args: object, **kwargs: object) -> object:
        captured["allow_tools"] = kwargs.get("allow_tools")
        provider = real_get_provider("anthropic_api", "sk-test")
        provider._client.messages.create = AsyncMock(return_value=fake_response)  # type: ignore[attr-defined]
        return provider

    monkeypatch.setattr(par_role, "get_provider", spy)

    await plan_project("mon-projet", PlanRequest(description="ajoute une feature"))

    assert captured["allow_tools"] is False


async def test_create_project_utilise_un_provider_sans_outils(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression — ticket-044 merge-gate finding 2 (critical):
    ProjectCreatorService (used here only for
    ``_auto_create_missing_agents``) is pure text-in/JSON-out and nothing
    wires it a resolved ``cwd``. It must get the tool-less provider like the
    other pure text-in/JSON-out call sites in this router."""
    captured: dict[str, object] = {}
    real_get_provider = par_role.get_provider

    from unittest.mock import AsyncMock, MagicMock

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="un system prompt d'agent bootstrap")]
    fake_response.usage = MagicMock(
        input_tokens=1, output_tokens=1,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )

    def spy(*args: object, **kwargs: object) -> object:
        captured["allow_tools"] = kwargs.get("allow_tools")
        provider = real_get_provider("anthropic_api", "sk-test")
        provider._client.messages.create = AsyncMock(return_value=fake_response)  # type: ignore[attr-defined]
        return provider

    monkeypatch.setattr(par_role, "get_provider", spy)
    # Sans ces deux lignes, `_auto_create_missing_agents` écrivait dans le
    # **vrai** dossier `agents/prompts/` du dépôt : la suite y recréait des
    # prompts livrés et en écrasait le contenu (ticket-098).
    monkeypatch.setattr(settings, "ide_prompts_dir", tmp_path / "prompts")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path / "workspace")

    await create_project(
        ProjectCreate(project_id="mon-projet", name="Mon Projet", active_agents=["redacteur"])
    )

    assert captured["allow_tools"] is False


async def test_analyze_project_utilise_un_provider_sans_outils(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path, "mon-projet")
    captured: dict[str, object] = {}
    real_get_provider = par_role.get_provider

    from unittest.mock import AsyncMock, MagicMock

    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(text=json.dumps({"claude_md": "# x", "detected_stack": [], "suggested_agents": []}))
    ]
    fake_response.usage = MagicMock(
        input_tokens=1, output_tokens=1,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )

    def spy(*args: object, **kwargs: object) -> object:
        captured["allow_tools"] = kwargs.get("allow_tools")
        provider = real_get_provider("anthropic_api", "sk-test")
        provider._client.messages.create = AsyncMock(return_value=fake_response)  # type: ignore[attr-defined]
        return provider

    monkeypatch.setattr(par_role, "get_provider", spy)

    await analyze_project("mon-projet", AnalyzeProjectRequest())

    assert captured["allow_tools"] is False
