"""A tool-bearing call cannot skip the agent account — ticket-1043, ADR-093."""
import json
from pathlib import Path
from typing import cast

import pytest

from tessera.config import settings
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider, _build_options
from tessera.services.providers.compte_exige import projet_exige_le_compte
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.providers.signaler import ContexteSignal


def _options(**extra: object) -> object:
    return _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=None, **extra  # type: ignore[arg-type]
    )


def _projet(tmp_path: Path, declaration: dict[str, object]) -> Path:
    (tmp_path / "agents.json").write_text(json.dumps({"agents": [], "worktree": declaration}))
    return tmp_path


def test_tools_without_account_are_refused() -> None:
    with pytest.raises(ProviderIndisponible):
        _options(compte_exige=True, allowed_tools=["Read"])
    with pytest.raises(ProviderIndisponible):
        _options(compte_exige=True)


def test_skill_without_account_is_refused() -> None:
    with pytest.raises(ProviderIndisponible):
        _options(compte_exige=True, allowed_tools=[], skills=["verifier-mon-travail"])


def test_signaler_without_account_is_refused() -> None:
    contexte = cast(ContexteSignal, object())
    with pytest.raises(ProviderIndisponible):
        _options(compte_exige=True, allowed_tools=[], signaler=contexte)


def test_call_without_tools_passes_without_account() -> None:
    assert _options(compte_exige=True, allowed_tools=[]) is not None


def test_nothing_changes_when_account_not_required() -> None:
    assert _options(compte_exige=False, allowed_tools=["Read"]) is not None


def test_project_requires_account_only_with_user_and_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, {"compte_agent": True})
    monkeypatch.setattr(settings, "agent_user", "")
    assert not projet_exige_le_compte(projet)
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    assert projet_exige_le_compte(projet)
    assert not projet_exige_le_compte(None)
    assert not projet_exige_le_compte(_projet(tmp_path, {"compte_agent": False}))


def test_provider_for_role_carries_the_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    projet = _projet(tmp_path, {"compte_agent": True})
    provider = cast(ClaudeAgentSDKProvider, provider_pour_role(projet, "codeur"))
    assert provider._compte_exige is True
