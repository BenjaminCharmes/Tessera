"""Builds the supervisor's triage and decision over the provider its role declares — tickets 855, 856, ADR-080."""
from pathlib import Path

from tessera.config import settings
from tessera.services.noyau.modeles_par_defaut import modele_par_defaut
from tessera.services.noyau.prompt_loader import load_system_prompt
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.supervision.superviseur_decision import SuperviseurDecision
from tessera.services.supervision.superviseur_tri import Intervenir, SuperviseurTri

ROLE = "superviseur"
#: Un blocage de règle ou de leçon engage tous les agents du projet : modèle fort par défaut.
MODELE_DECISION = "claude-opus-5-5"


def _fournisseur(project_id: str, project_path: Path) -> LLMProvider:
    """The role's provider, recorded like any other call; no tool and no shell (ADR-080)."""
    interne = provider_pour_role(project_path, ROLE, allow_tools=False, project_id=project_id)
    return ProviderEnregistrant(interne, role=ROLE, db_path=settings.ide_db_path)


def superviseur_tri_pour(project_id: str, project_path: Path, intervenir: Intervenir) -> SuperviseurTri:
    """The triage of `project_id`: the `superviseur` role, with no tool and no shell (ADR-080).

    The provider is the one `agents.json` declares for the role, recorded like
    any other call; `intervenir` is the only way the triage can write.
    """
    return SuperviseurTri(
        _fournisseur(project_id, project_path),
        intervenir,
        modele=modele_du_role(project_path, ROLE) or modele_par_defaut(ROLE),
        systeme=load_system_prompt(settings.ide_prompts_dir, f"{ROLE}.md"),
    )


def superviseur_decision_pour(project_id: str, project_path: Path, intervenir: Intervenir) -> SuperviseurDecision:
    """The decision of `project_id` on proposed lessons and rules: the `superviseur` role, Opus by default.

    The model the role declares in `agents.json` wins; `intervenir` is the only
    way the decision can write.
    """
    return SuperviseurDecision(
        _fournisseur(project_id, project_path),
        intervenir,
        modele=modele_du_role(project_path, ROLE) or MODELE_DECISION,
        systeme=load_system_prompt(settings.ide_prompts_dir, f"{ROLE}.md"),
    )
