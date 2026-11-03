"""Les apps de projet qui tournent sur la machine — ticket-416.

`GET /services/running` les liste, lancées par Tessera ou à la main ;
`POST /services/running/{pid}/stop` arrête celle dont le pid figure dans
l'inventaire **courant**. Jamais un pid arbitraire : l'inventaire est la
seule liste blanche, recalculée à chaque arrêt.
"""
from fastapi import APIRouter, Depends, HTTPException

from tessera.config import settings
from tessera.services.groupe_de_processus import tuer_l_arbre
from tessera.models.inventaire import AppEnCours, PortOccupe
from tessera.services.inventaire_apps import inventaire, inventaire_complet
from tessera.services.process_registry import PROCESS_REGISTRY
from tessera.services.sonde_systeme import SondeReelle, SondeSysteme

router = APIRouter(prefix="/services", tags=["services"])


def get_sonde() -> SondeSysteme:
    """La sonde de la machine ; les tests la remplacent par un faux."""
    return SondeReelle()


@router.get("/running", response_model=list[AppEnCours])
async def lister_les_apps(
    sonde: SondeSysteme = Depends(get_sonde),
) -> list[AppEnCours]:
    return await inventaire(sonde, settings.ide_workspace_dir)


@router.get("/running/avertissements", response_model=list[PortOccupe])
async def lister_les_ports_occupes(
    sonde: SondeSysteme = Depends(get_sonde),
) -> list[PortOccupe]:
    """Declared ports held by a foreign program: shown, never stoppable."""
    return (await inventaire_complet(sonde, settings.ide_workspace_dir)).ports_occupes


@router.post("/running/{pid}/stop")
async def arreter_une_app(
    pid: int, sonde: SondeSysteme = Depends(get_sonde)
) -> dict[str, object]:
    """Stop an app of the current inventory, 404 for any other pid.

    Un service `tessera` passe par le registre, qui arrête **tous** les
    services de son projet : le back et le front d'un même projet partent
    ensemble.
    """
    apps = await inventaire(sonde, settings.ide_workspace_dir)
    app = next((a for a in apps if a.pid == pid), None)
    if app is None:
        raise HTTPException(
            status_code=404,
            detail=f"Le pid {pid} ne figure pas dans l'inventaire des apps.",
        )
    if app.origine == "tessera":
        arretes = await PROCESS_REGISTRY.arreter(app.project_id)
        return {"pid": pid, "origine": app.origine, "arretes": arretes}
    arrete = await tuer_l_arbre(pid)
    return {"pid": pid, "origine": app.origine, "arretes": int(arrete)}
