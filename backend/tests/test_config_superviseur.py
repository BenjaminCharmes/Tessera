"""The `pipeline.superviseur` declaration and the `superviseur` role — ticket-852 (ADR-080)."""
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tessera.config import settings
from tessera.models.superviseur_config import BUDGET_JOUR_PLAFOND_USD, ConfigSuperviseur
from tessera.services.projets.project_loader import load_pipeline_config
from tessera.services.projets.superviseur_declaration import load_config_superviseur
from tessera.services.providers import par_role
from tessera.services.providers.par_role import ROLES_TEXTE, provider_pour_role
from tests.test_providers_base import FakeProvider


def _manifeste(projet: Path, contenu: dict[str, Any]) -> Path:
    projet.mkdir(parents=True, exist_ok=True)
    (projet / "agents.json").write_text(json.dumps(contenu), encoding="utf-8")
    return projet


def test_defaults_delegate_nothing(tmp_path: Path) -> None:
    config = ConfigSuperviseur()

    assert config.delegation == []
    assert config.budget_jour_usd == 2.0
    assert config.relance_file is False
    # Ni manifeste, ni section pipeline, ni clé superviseur : même réponse.
    assert load_config_superviseur(tmp_path / "inexistant") == config
    assert load_config_superviseur(_manifeste(tmp_path / "a", {"pipeline": {}})) == config


def test_a_declared_delegation_is_read(tmp_path: Path) -> None:
    projet = _manifeste(tmp_path, {"pipeline": {"superviseur": {
        "delegation": ["lecons", "regles"], "budget_jour_usd": 5, "relance_file": True,
    }}})

    config = load_config_superviseur(projet)

    assert config.delegation == ["lecons", "regles"]
    assert config.budget_jour_usd == 5.0
    assert config.relance_file is True


def test_unknown_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ConfigSuperviseur.model_validate({"delegation": [], "autonomy": "merge"})
    with pytest.raises(ValidationError):
        ConfigSuperviseur.model_validate({"delegation": ["argent"]})

    # Déclaration refusée : rien n'est délégué, le reste du pipeline survit.
    projet = _manifeste(tmp_path, {"pipeline": {
        "lecons": True, "superviseur": {"delegation": ["lecons"], "autonomie": True},
    }})
    assert load_config_superviseur(projet) == ConfigSuperviseur()
    assert load_pipeline_config(projet).lecons is True


@pytest.mark.parametrize("budget", [BUDGET_JOUR_PLAFOND_USD + 0.01, 100, 0, -1])
def test_budget_above_hard_cap_is_refused(budget: float, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ConfigSuperviseur.model_validate({"budget_jour_usd": budget})

    projet = _manifeste(tmp_path, {"pipeline": {"superviseur": {
        "delegation": ["regles"], "budget_jour_usd": budget,
    }}})
    assert load_config_superviseur(projet).delegation == []


def test_budget_at_the_hard_cap_is_accepted() -> None:
    config = ConfigSuperviseur.model_validate({"budget_jour_usd": BUDGET_JOUR_PLAFOND_USD})

    assert config.budget_jour_usd == 20.0


def test_role_superviseur_gets_no_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        appels.append({"name": name, **kwargs})
        return FakeProvider()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    monkeypatch.setattr(settings, "llm_duree_max_role_texte_s", 99.0)
    # Même un manifeste qui lui donne le web ne lui rend ni outil ni shell.
    projet = _manifeste(tmp_path, {"agents": [{
        "role": "superviseur", "model": "m", "max_tokens": 1,
        "prompt_file": "agents/prompts/superviseur.md", "web": True,
    }]})

    provider_pour_role(projet, "superviseur", allow_tools=False)

    assert "superviseur" in ROLES_TEXTE
    assert appels[0]["allow_tools"] is False
    assert appels[0]["tools"] is None
    assert appels[0]["duree_max_s"] == 99.0
