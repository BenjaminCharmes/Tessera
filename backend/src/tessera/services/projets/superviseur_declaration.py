"""Reads the `pipeline.superviseur` declaration of a project — ticket-852 (ADR-080)."""
from pathlib import Path

from pydantic import ValidationError

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.projets.manifeste import lire_valeur
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def load_config_superviseur(project_path: Path) -> ConfigSuperviseur:
    """Lit `pipeline.superviseur` de agents.json.

    Échec fermé : une déclaration absente, ou refusée (clé inconnue, budget
    hors bornes), ne délègue rien. Le refus est journalisé, et le reste du
    pipeline n'en souffre pas : `AgentPipelineConfig` ignore cette clé.
    """
    section = lire_valeur(project_path, "pipeline")
    brut = section.get("superviseur") if isinstance(section, dict) else None
    if brut is None:
        return ConfigSuperviseur()
    try:
        return ConfigSuperviseur.model_validate(brut)
    except ValidationError as exc:
        _logger.warning(
            "superviseur_config_refusee",
            extra={"project": project_path.name, "erreurs": exc.error_count()},
        )
        return ConfigSuperviseur()
