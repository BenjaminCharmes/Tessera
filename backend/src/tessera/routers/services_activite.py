"""L'activité des agents des apps qui tournent — ticket-671, ADR-064.

`GET /services/running/activite` : une entrée par service qui déclare un
fichier d'activité **et** dont l'app figure dans l'inventaire courant. Un
service arrêté ne rend rien, même avec un fichier encore frais.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from tessera.config import settings
from tessera.models.activite import ActiviteDeService
from tessera.routers.services_running import get_sonde
from tessera.services.activite_produit import lire_activite
from tessera.services.declarations_activite import services_avec_activite
from tessera.services.inventaire_apps import inventaire
from tessera.services.sonde_systeme import SondeSysteme

router = APIRouter(prefix="/services", tags=["services"])


def _activites(apps: set[tuple[str, str]]) -> list[ActiviteDeService]:
    """Lit le fichier de chaque service déclaré dont l'app (projet, nom) tourne."""
    maintenant = datetime.now(timezone.utc)
    rendues: list[ActiviteDeService] = []
    for project_id in sorted({p for p, _ in apps}):
        racine = settings.ide_workspace_dir / project_id
        for declare in services_avec_activite(racine):
            if (project_id, declare.nom) not in apps or not declare.activite:
                continue
            rendues.append(
                ActiviteDeService(
                    project_id=project_id,
                    service=declare.nom,
                    agents=lire_activite(racine, declare.activite, maintenant),
                )
            )
    return rendues


@router.get("/running/activite", response_model=list[ActiviteDeService])
async def lister_l_activite(
    sonde: SondeSysteme = Depends(get_sonde),
) -> list[ActiviteDeService]:
    apps = await inventaire(sonde, settings.ide_workspace_dir)
    vivantes = {(a.project_id, a.nom) for a in apps}
    return await asyncio.to_thread(_activites, vivantes)
