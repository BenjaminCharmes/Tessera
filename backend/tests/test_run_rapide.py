"""A run launched in fast mode takes each role's fallback straight away — ticket-578.

Ollama reste le premier choix ; le repli d'un rôle, déclaré dans `agents.json`,
est pris d'emblée quand l'appelant est pressé. Un rôle sans repli ne change pas.
"""
import json
from pathlib import Path
from typing import Any

import pytest

from tessera.config import settings
from tessera.routers.orchestrator import RunRequest
from tessera.services.assemblage_run import build_orchestrator
from tessera.services.journal_pipeline import journaliser_mode_rapide
from tessera.services.providers import par_role
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli
from tessera.services.providers.repli_direct import ProviderRepliDirect
from tests.test_provider_par_role import _agent, _manifeste
from tests.test_providers_base import FakeProvider

_REPLI = {"provider": "agent_sdk", "model": "claude-haiku-4-5"}


@pytest.fixture
def construits(monkeypatch: pytest.MonkeyPatch) -> list[FakeProvider]:
    """Every provider `get_provider` builds, in order, named after its provider."""
    fabriques: list[FakeProvider] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        p = FakeProvider()
        p.name = name or "agent_sdk"  # type: ignore[misc]
        fabriques.append(p)
        return p

    monkeypatch.setattr(par_role, "get_provider", fausse)
    return fabriques


def test_run_request_is_not_fast_by_default() -> None:
    assert RunRequest(project_id="projet").rapide is False


def test_run_request_accepts_rapide() -> None:
    assert RunRequest(project_id="projet", rapide=True).rapide is True


async def test_fast_run_builds_only_the_fallback_with_its_model(
    tmp_path: Path, construits: list[FakeProvider]
) -> None:
    projet = _manifeste(tmp_path, [
        _agent("validateur", provider="ollama", model="qwen3-coder:30b", fallback=_REPLI),
    ])

    provider = provider_pour_role(projet, "validateur", allow_tools=False, rapide=True)

    assert isinstance(provider, ProviderRepliDirect)
    assert [p.name for p in construits] == ["agent_sdk"]
    await provider.complete(system="s", user="u", model="qwen3-coder:30b", max_tokens=10)
    assert construits[0].calls[0]["model"] == "claude-haiku-4-5"


async def test_fast_run_streaming_also_carries_the_fallback_model(
    tmp_path: Path, construits: list[FakeProvider]
) -> None:
    projet = _manifeste(tmp_path, [
        _agent("validateur", provider="ollama", model="qwen3-coder:30b", fallback=_REPLI),
    ])
    provider = provider_pour_role(projet, "validateur", allow_tools=False, rapide=True)

    result = await provider.stream(system="s", user="u", model="qwen3-coder:30b", max_tokens=10)

    assert construits[0].calls[0]["model"] == "claude-haiku-4-5"
    assert result.model == "claude-haiku-4-5"


def test_normal_run_still_builds_the_primary(
    tmp_path: Path, construits: list[FakeProvider]
) -> None:
    projet = _manifeste(tmp_path, [
        _agent("validateur", provider="ollama", fallback=_REPLI),
    ])

    provider = provider_pour_role(projet, "validateur", allow_tools=False)

    assert isinstance(provider, ProviderAvecRepli)
    assert [p.name for p in construits] == ["ollama", "agent_sdk"]


def test_fast_run_keeps_the_provider_of_a_role_without_fallback(
    tmp_path: Path, construits: list[FakeProvider]
) -> None:
    projet = _manifeste(tmp_path, [_agent("codeur", provider="ollama")])

    provider = provider_pour_role(projet, "codeur", rapide=True)

    assert not isinstance(provider, (ProviderRepliDirect, ProviderAvecRepli))
    assert [p.name for p in construits] == ["ollama"]


def test_fast_journal_line_names_the_roles(tmp_path: Path) -> None:
    journal = tmp_path / "memory" / "pipeline-log.md"

    journaliser_mode_rapide(journal, "projet", ["validateur", "securite"])

    texte = journal.read_text(encoding="utf-8")
    assert "[projet] mode rapide : repli d'emblée pour validateur, securite" in texte
    assert texte.count("\n") == 1


def test_fast_journal_writes_nothing_without_a_fallback_role(tmp_path: Path) -> None:
    journal = tmp_path / "memory" / "pipeline-log.md"

    journaliser_mode_rapide(journal, "projet", [])

    assert not journal.exists()


def _projet_avec_validateur(workspace: Path) -> Path:
    projet = workspace / "mon-projet"
    (projet / "memory").mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")
    agent = _agent("validateur", provider="ollama", model="qwen3-coder:30b", fallback=_REPLI)
    (projet / "agents.json").write_text(json.dumps({
        "project_id": "mon-projet", "agents": [agent],
        "pipeline": {"validateur_enabled": True},
    }), encoding="utf-8")
    return projet


async def test_building_a_fast_orchestrator_logs_the_mode_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    projet = _projet_avec_validateur(tmp_path)

    orchestrator = await build_orchestrator("mon-projet", rapide=True)

    assert orchestrator._validator is not None
    assert isinstance(orchestrator._validator._provider._inner, ProviderRepliDirect)
    lignes = (projet / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert lignes.count("mode rapide : repli d'emblée pour validateur") == 1


async def test_building_a_normal_orchestrator_logs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    projet = _projet_avec_validateur(tmp_path)

    orchestrator = await build_orchestrator("mon-projet")

    assert isinstance(orchestrator._validator._provider._inner, ProviderAvecRepli)  # type: ignore[union-attr]
    assert not (projet / "memory" / "pipeline-log.md").exists()
