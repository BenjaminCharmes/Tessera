"""A role declares its reasoning effort — ticket-573.

Le champ est optionnel : un manifeste muet ne change rien. Déclaré, il doit
atteindre `ClaudeAgentOptions`, seul endroit où le SDK le lit.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tessera.models.agent import AgentConfig
from tessera.services.project_loader import load_agents_config
from tessera.services.providers import par_role
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider, _build_options
from tessera.services.providers.par_role import provider_pour_role

_NIVEAUX = ["low", "medium", "high", "xhigh", "max"]


def _config(**extra: Any) -> dict[str, Any]:
    return {"role": "codeur", "model": "m", "max_tokens": 1, "prompt_file": "x", **extra}


def _options(**kwargs: Any) -> Any:
    return _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None, **kwargs,
    )


def _ecrire_manifeste(projet: Path, **extra: Any) -> Path:
    projet.mkdir()
    (projet / "agents.json").write_text(
        json.dumps({"agents": [_config(**extra)]}), encoding="utf-8"
    )
    return projet


@pytest.mark.parametrize("niveau", _NIVEAUX)
def test_agent_config_accepts_each_sdk_effort_level(niveau: str) -> None:
    assert AgentConfig(**_config(effort=niveau)).effort == niveau


def test_agent_config_effort_is_absent_by_default() -> None:
    assert AgentConfig(**_config()).effort is None


def test_agent_config_rejects_an_unknown_effort() -> None:
    with pytest.raises(ValidationError):
        AgentConfig(**_config(effort="extreme"))


def test_an_unknown_effort_in_agents_json_is_refused_at_load(tmp_path: Path) -> None:
    projet = _ecrire_manifeste(tmp_path / "p", effort="extreme")

    # Le chargeur rejette tout le manifeste : le rôle n'est pas servi à demi.
    assert load_agents_config(projet) == []


@pytest.mark.parametrize("niveau", _NIVEAUX)
def test_build_options_passes_the_declared_effort(niveau: str) -> None:
    assert _options(effort=niveau).effort == niveau


def test_build_options_does_not_pass_effort_when_undeclared() -> None:
    assert _options().effort is None


def test_provider_hands_its_effort_to_the_sdk_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vus: list[Any] = []
    import tessera.services.providers.agent_sdk as module

    reel = module._build_options

    def espion(**kwargs: Any) -> Any:
        options = reel(**kwargs)
        vus.append(options)
        return options

    async def vide(prompt: str, options: Any) -> Any:
        return
        yield  # pragma: no cover — fait de la fonction un générateur

    monkeypatch.setattr(module, "_build_options", espion)
    monkeypatch.setattr(module, "_sdk_gen", vide)
    provider = ClaudeAgentSDKProvider(effort="low")

    # Le flux vide n'a pas de ResultMessage : l'appel échoue, mais les options
    # sont déjà construites, et c'est elles qu'on lit.
    with pytest.raises(RuntimeError):
        asyncio.run(provider.complete(system="s", user="u", model="m", max_tokens=10))

    assert vus[0].effort == "low"


def test_provider_pour_role_forwards_the_manifest_effort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> Any:
        appels.append(kwargs)
        return object()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    projet = _ecrire_manifeste(tmp_path / "p", effort="high")

    provider_pour_role(projet, "codeur")

    assert appels[0]["effort"] == "high"


def test_provider_pour_role_without_effort_passes_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> Any:
        appels.append(kwargs)
        return object()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    projet = _ecrire_manifeste(tmp_path / "p")

    provider_pour_role(projet, "codeur")

    assert appels[0]["effort"] is None
