"""The documentation roles a project keeps active."""
from pathlib import Path

from tessera.services.documentation import ROLES_DOCUMENTATION
from tessera.services.providers.par_role import config_du_role


def roles_de_documentation(project_path: Path) -> tuple[str, ...]:
    """The documentation roles the project declares and keeps active (ticket-534).

    Un rôle absent d'`agents.json` ou marqué `"active": false` n'est pas appelé :
    c'est le réglage qui coupe la documentation, rôle par rôle.
    """
    retenus: list[str] = []
    for role in ROLES_DOCUMENTATION:
        config = config_du_role(project_path, role)
        if config is not None and config.active:
            retenus.append(role)
    return tuple(retenus)
