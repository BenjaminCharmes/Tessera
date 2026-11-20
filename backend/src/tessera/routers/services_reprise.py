"""Relancer au démarrage les services que l'utilisateur avait demandés — ticket-890.

Vit dans les routeurs : elle réutilise `lancer_les_services`, l'inventaire du
domaine `supervision` et le registre de `verification` (ADR-076, ADR-082).
"""
from pathlib import Path

from tessera.routers.services import lancer_les_services
from tessera.services.noyau.services_demandes import lister, retirer
from tessera.services.supervision.sonde_systeme import SondeSysteme
from tessera.services.verification.process_registry import ProcessRegistry
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def reprendre_les_services(
    db_path: Path | str, sonde: SondeSysteme, registre: ProcessRegistry
) -> None:
    """Relaunch the services of each recorded project, one `try` per project.

    A failure (including the 409 of a service already running outside Tessera)
    is logged and the project is dropped from the table: no crash loop at each
    start, and the next projects are still resumed.
    """
    for project_id in await lister(db_path):
        try:
            await lancer_les_services(project_id, sonde, registre)
        except Exception as exc:  # noqa: BLE001 — un projet ne bloque pas les autres
            _logger.warning(
                "services_non_repris",
                extra={"projet": project_id, "erreur": str(exc)},
            )
            await retirer(db_path, project_id)
