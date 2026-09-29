"""Un rôle déclare les skills qu'il voit — ticket-242.

Sans filtre, le CLI montre au codeur d'ide-core les skills de la racine du
dépôt (dont `ticket-workflow`, qui dit de pousser) et une vingtaine de skills
intégrés. La liste déclarée est donc à la fois ce qui donne l'outil et ce qui
le borne.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider, _build_options
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli

_IDE_CORE = Path(__file__).resolve().parents[2] / "projects" / "ide-core"


def _options(**kwargs: object):  # type: ignore[no-untyped-def]
    return _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None, **kwargs,  # type: ignore[arg-type]
    )


def test_des_skills_declares_donnent_l_outil_et_le_bornent() -> None:
    options = _options(allowed_tools=["Read"], skills=["verifier-mon-travail"])

    assert "Skill" in options.tools
    assert "Skill" in options.allowed_tools
    assert options.skills == ["verifier-mon-travail"]


def test_sans_skills_rien_ne_change() -> None:
    options = _options(allowed_tools=["Read"])

    assert options.skills is None
    assert "Skill" not in options.tools


def _projet(tmp_path: Path) -> Path:
    projet = tmp_path / "p"
    projet.mkdir()
    (projet / "agents.json").write_text(
        json.dumps({
            "agents": [{
                "role": "codeur", "model": "m", "max_tokens": 1, "prompt_file": "x",
                "skills": ["verifier-mon-travail"],
                "fallback": {"provider": "agent_sdk", "model": "m2"},
            }]
        }),
        encoding="utf-8",
    )
    return projet


def test_provider_pour_role_transmet_les_skills_au_principal_et_au_repli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")

    provider = provider_pour_role(_projet(tmp_path), "codeur")

    assert isinstance(provider, ProviderAvecRepli)
    for interne in (provider._principal, provider._repli):
        assert isinstance(interne, ClaudeAgentSDKProvider)
        assert interne._skills == ["verifier-mon-travail"]


def test_un_role_qui_ne_declare_rien_n_a_pas_de_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")

    provider = provider_pour_role(_projet(tmp_path), "reviewer")

    assert isinstance(provider, ClaudeAgentSDKProvider)
    assert provider._skills == []


def test_les_skills_declares_par_ide_core_existent() -> None:
    # Un nom mal écrit lève au `connect()` du SDK : chaque run du rôle échouerait.
    manifeste = json.loads((_IDE_CORE / "agents.json").read_text(encoding="utf-8"))
    declares = [nom for agent in manifeste["agents"] for nom in agent.get("skills", [])]

    assert declares, "ide-core ne déclare aucun skill"
    for nom in declares:
        assert (_IDE_CORE / ".claude" / "skills" / nom / "SKILL.md").is_file(), nom
