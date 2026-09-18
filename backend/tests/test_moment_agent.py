"""Quand chaque agent parle — ticket-097."""
import json
from pathlib import Path

from vibe_ide.services.agent_registry import AgentRegistryService, MomentAgent

_PROMPTS = Path(__file__).resolve().parents[2] / "agents" / "prompts"
_PROJETS = Path(__file__).resolve().parents[2] / "projects"


def _registre() -> AgentRegistryService:
    return AgentRegistryService(_PROMPTS, projects_dir=_PROJETS)


def test_le_codeur_parle_pendant_un_run() -> None:
    moments = {a.role: a.moment for a in _registre().list_agents()}

    assert moments["codeur"] is MomentAgent.pipeline
    assert moments["reviewer"] is MomentAgent.pipeline


def test_le_chat_parle_quand_on_le_demande() -> None:
    moments = {a.role: a.moment for a in _registre().list_agents()}

    assert moments["chat"] is MomentAgent.demande
    assert moments["planificateur"] is MomentAgent.demande


def test_un_prompt_que_rien_n_appelle_le_dit() -> None:
    # `testeur.md` existe et n'est chargé nulle part : l'étape de test lance un
    # sous-processus, elle n'appelle aucun agent. `architect.md` est déclaré
    # par `ide-core` et n'est lu par rien. Quatre prompts sur dix-sept ne
    # parlaient jamais, et le badge les annonçait comme « requis ».
    moments = {a.role: a.moment for a in _registre().list_agents()}

    assert moments["testeur"] is MomentAgent.jamais
    assert moments["architect"] is MomentAgent.jamais


def test_un_prompt_branche_par_un_projet_parle_dans_le_pipeline() -> None:
    # `analyste-carriere` n'est chargé par aucun code : c'est le `agents.json`
    # du projet carrière qui le substitue au prompt du codeur.
    moments = {a.role: a.moment for a in _registre().list_agents()}

    assert moments["analyste-carriere"] is MomentAgent.pipeline


def test_chaque_prompt_livre_a_un_moment_connu() -> None:
    # Le verrou anti-dérive : un prompt ajouté sans être classé apparaîtrait
    # comme « jamais appelé », ce qui serait faux et se verrait à l'écran.
    livres = {f.stem for f in _PROMPTS.glob("*.md")}
    classes = (
        AgentRegistryService.ROLES_PIPELINE | AgentRegistryService.ROLES_A_LA_DEMANDE
    )
    inconnus = sorted(classes - livres)

    assert inconnus == [], f"classés mais sans prompt livré : {inconnus}"


def test_un_agent_cree_par_l_utilisateur_n_est_pas_dit_appele(tmp_path: Path) -> None:
    (tmp_path / "expert-sql.md").write_text("prompt", encoding="utf-8")

    agents = AgentRegistryService(tmp_path, projects_dir=tmp_path / "vide").list_agents()
    moments = {a.role: a.moment for a in agents}

    assert moments["expert-sql"] is MomentAgent.jamais


def test_un_projet_qui_le_branche_change_son_moment(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "expert-sql.md").write_text("prompt", encoding="utf-8")
    projets = tmp_path / "projects" / "monprojet"
    projets.mkdir(parents=True)
    (projets / "agents.json").write_text(
        json.dumps(
            {"agents": [{"role": "codeur", "prompt_file": "agents/prompts/expert-sql.md",
                         "model": "m", "max_tokens": 1}]}
        ),
        encoding="utf-8",
    )

    agents = AgentRegistryService(prompts, projects_dir=tmp_path / "projects").list_agents()
    moments = {a.role: a.moment for a in agents}

    assert moments["expert-sql"] is MomentAgent.pipeline
