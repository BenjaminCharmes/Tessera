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
from tessera.services.providers.agent_sdk import (
    ClaudeAgentSDKProvider,
    _TESSERA_PLUGIN_PATH,
    _build_options,
)
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.providers.repli import ProviderAvecRepli

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IDE_CORE = _REPO_ROOT / "projects" / "ide-core"


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
    # Les skills `tessera:` sont vérifiés séparément (test ci-dessous).
    manifeste = json.loads((_IDE_CORE / "agents.json").read_text(encoding="utf-8"))
    declares = [
        nom
        for agent in manifeste["agents"]
        for nom in agent.get("skills", [])
        if not nom.startswith("tessera:")
    ]

    assert declares, "ide-core ne déclare aucun skill local"
    for nom in declares:
        assert (_IDE_CORE / ".claude" / "skills" / nom / "SKILL.md").is_file(), nom


def test_skills_tessera_passent_un_plugin() -> None:
    """_build_options passe exactement un plugin local quand un skill porte le préfixe tessera:."""
    options = _options(skills=["tessera:x"])

    assert len(options.plugins) == 1
    plugin = options.plugins[0]
    assert plugin["type"] == "local"
    assert Path(plugin["path"]).is_absolute(), "le chemin du plugin doit être absolu"
    assert Path(plugin["path"]) == _TESSERA_PLUGIN_PATH


def test_skills_locaux_ne_passent_pas_de_plugin() -> None:
    """Un skill sans préfixe tessera: ne déclenche pas de plugin."""
    options = _options(skills=["verifier-mon-travail"])

    assert options.plugins == []


def test_sans_skills_pas_de_plugin() -> None:
    """Sans skills déclarés, aucun plugin n'est chargé."""
    options = _options(skills=None)

    assert options.plugins == []


def test_chaque_dossier_skill_plugin_a_un_skill_md() -> None:
    """Chaque dossier de agents/plugin/skills/ contient un SKILL.md valide.

    Le frontmatter doit porter `name` égal au nom du dossier et une
    `description` non vide. Un dossier vide de skills est acceptable
    (le premier skill arrive avec ticket-294).
    """
    skills_dir = _TESSERA_PLUGIN_PATH / "skills"
    if not skills_dir.is_dir():
        return  # aucun skill encore livré

    for dossier in sorted(skills_dir.iterdir()):
        if not dossier.is_dir():
            continue
        skill_md = dossier / "SKILL.md"
        assert skill_md.is_file(), f"SKILL.md manquant dans agents/plugin/skills/{dossier.name}/"
        content = skill_md.read_text(encoding="utf-8")
        # Extraire les valeurs du frontmatter YAML minimal (---\nname: …\n---)
        name_val: str | None = None
        desc_val: str | None = None
        for line in content.splitlines():
            if line.startswith("name:") and name_val is None:
                name_val = line.split(":", 1)[1].strip().strip("\"'")
            if line.startswith("description:") and desc_val is None:
                desc_val = line.split(":", 1)[1].strip().strip("\"'")
        assert name_val is not None, f"frontmatter 'name' manquant dans {dossier.name}/SKILL.md"
        assert name_val == dossier.name, (
            f"name '{name_val}' ≠ nom du dossier '{dossier.name}' dans agents/plugin/skills/"
        )
        assert desc_val, f"frontmatter 'description' vide dans {dossier.name}/SKILL.md"


def test_skills_tessera_declares_par_ide_core_existent() -> None:
    """Chaque skill tessera:<nom> déclaré dans ide-core/agents.json existe dans le plugin."""
    manifeste = json.loads((_IDE_CORE / "agents.json").read_text(encoding="utf-8"))
    declares = [
        nom
        for agent in manifeste["agents"]
        for nom in agent.get("skills", [])
        if nom.startswith("tessera:")
    ]

    for prefixed in declares:
        nom = prefixed[len("tessera:"):]
        skill_md = _TESSERA_PLUGIN_PATH / "skills" / nom / "SKILL.md"
        assert skill_md.is_file(), (
            f"agents/plugin/skills/{nom}/SKILL.md manquant "
            f"(déclaré dans ide-core/agents.json comme '{prefixed}')"
        )
