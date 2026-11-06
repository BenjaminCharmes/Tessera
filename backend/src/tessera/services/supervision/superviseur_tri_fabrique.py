"""Builds the supervisor's triage over the provider its role declares — ticket-855, ADR-080."""
from pathlib import Path

from tessera.config import settings
from tessera.services.noyau.modeles_par_defaut import modele_par_defaut
from tessera.services.noyau.prompt_loader import load_system_prompt
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.supervision.superviseur_tri import Intervenir, SuperviseurTri

ROLE = "superviseur"


def superviseur_tri_pour(project_id: str, project_path: Path, intervenir: Intervenir) -> SuperviseurTri:
    """The triage of `project_id`: the `superviseur` role, with no tool and no shell (ADR-080).

    The provider is the one `agents.json` declares for the role, recorded like
    any other call; `intervenir` is the only way the triage can write.
    """
    interne = provider_pour_role(project_path, ROLE, allow_tools=False, project_id=project_id)
    return SuperviseurTri(
        ProviderEnregistrant(interne, role=ROLE, db_path=settings.ide_db_path),
        intervenir,
        modele=modele_du_role(project_path, ROLE) or modele_par_defaut(ROLE),
        systeme=load_system_prompt(settings.ide_prompts_dir, f"{ROLE}.md"),
    )
