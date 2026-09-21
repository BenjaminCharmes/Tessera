"""Quand chaque agent parle — ticket-097."""
import json
from pathlib import Path

from tessera.services.agent_registry import AgentRegistryService, MomentAgent

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


def test_l_architecte_tient_l_etape_des_tickets_design() -> None:
    # Il était déclaré depuis le premier commit et n'était appelé nulle part ;
    # ticket-098 route les tickets `design` vers lui.
    moments = {a.role: a.moment for a in _registre().list_agents()}

    assert moments["architect"] is MomentAgent.pipeline


def test_les_prompts_que_rien_n_appelait_ont_disparu() -> None:
    # `testeur.md` décrivait une analyse de sortie de tests que le code fait
    # par expression régulière ; `orchestrateur.md` décrivait ce que
    # `pick_next_ticket()` fait en huit lignes. Les garder promettait des
    # agents qui ne parlaient jamais.
    roles = {a.role for a in _registre().list_agents()}

    assert "testeur" not in roles
    assert "orchestrateur" not in roles


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


def test_tout_prompt_charge_par_le_code_a_un_moment_declare() -> None:
    # La moitié « projet » du badge est recalculée à chaque lecture : brancher
    # un prompt dans un `agents.json` le fait basculer tout seul.
    #
    # La moitié « code » ne l'est pas : `ROLES_PIPELINE` et `ROLES_A_LA_DEMANDE`
    # sont des listes. Brancher `architect` dans le code demain sans les mettre
    # à jour laisserait le badge afficher « jamais appelé » sur un agent qui
    # parle — la dérive exacte qui avait supprimé `agent-creator` (ticket-079),
    # par une troisième porte.
    import re

    sources = Path(__file__).resolve().parents[1] / "src"
    charges: set[str] = set()
    for fichier in sources.rglob("*.py"):
        for nom in re.findall(
            r"[\"']([a-z][a-z0-9-]*)\.md[\"']", fichier.read_text(encoding="utf-8")
        ):
            charges.add(nom)
    charges &= {f.stem for f in _PROMPTS.glob("*.md")}

    classes = (
        AgentRegistryService.ROLES_PIPELINE | AgentRegistryService.ROLES_A_LA_DEMANDE
    )
    oublies = sorted(charges - classes)

    assert oublies == [], (
        "le code charge ces prompts, mais le badge les dira « jamais "
        f"appelé » : {oublies}"
    )
