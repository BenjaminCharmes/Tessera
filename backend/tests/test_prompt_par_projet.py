"""Un projet choisit le prompt de chaque rôle — ticket-097."""
from pathlib import Path
from unittest.mock import MagicMock

from vibe_ide.models.agent import AgentConfig
from vibe_ide.services.agent_registry import AgentRegistryService
from vibe_ide.services.agent_runner import AgentRunner


def _runner(tmp_path: Path) -> AgentRunner:
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    (prompts / "codeur.md").write_text("prompt codeur générique", encoding="utf-8")
    (prompts / "analyste-carriere.md").write_text(
        "prompt analyste carrière", encoding="utf-8"
    )
    return AgentRunner(provider=MagicMock(), registry=AgentRegistryService(prompts))


def test_sans_declaration_le_role_charge_son_propre_prompt(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    assert "générique" in runner._load_system_prompt("codeur")


def test_un_projet_peut_pointer_un_role_vers_un_autre_prompt(tmp_path: Path) -> None:
    # Le pipeline appelle toujours le rôle `codeur` : c'est l'étape « quelqu'un
    # écrit ». Sur un projet qui n'est pas du code, ce quelqu'un doit être un
    # analyste, pas un développeur. `prompt_file` existait dans le modèle et
    # n'était lu nulle part : chaque agents.json en déclarait un pour rien.
    runner = _runner(tmp_path)
    config = AgentConfig(
        role="codeur",
        model="claude-sonnet-4-6",
        max_tokens=8192,
        prompt_file="agents/prompts/analyste-carriere.md",
    )

    assert "analyste" in runner._load_system_prompt("codeur", config)


def test_un_prompt_declare_mais_absent_echoue_bruyamment(tmp_path: Path) -> None:
    # Un projet qui pointe vers un prompt inexistant tournerait sinon avec le
    # prompt générique, en silence — et produirait du code là où on attendait
    # une analyse.
    from vibe_ide.services.agent_registry import AgentNotFoundError

    runner = _runner(tmp_path)
    config = AgentConfig(
        role="codeur",
        model="claude-sonnet-4-6",
        max_tokens=8192,
        prompt_file="agents/prompts/jamais-ecrit.md",
    )

    try:
        runner._load_system_prompt("codeur", config)
    except AgentNotFoundError as exc:
        assert "jamais-ecrit" in str(exc)
    else:
        raise AssertionError("un prompt déclaré mais absent doit échouer")


def test_le_chemin_declare_se_lit_depuis_le_dossier_des_prompts(tmp_path: Path) -> None:
    # `agents/prompts/x.md` et `x.md` désignent la même chose : le dossier des
    # prompts est déjà connu du runner, le préfixe est une commodité d'écriture.
    runner = _runner(tmp_path)
    config = AgentConfig(
        role="codeur",
        model="claude-sonnet-4-6",
        max_tokens=8192,
        prompt_file="analyste-carriere.md",
    )

    assert "analyste" in runner._load_system_prompt("codeur", config)
