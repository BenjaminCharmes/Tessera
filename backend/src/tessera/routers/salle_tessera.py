"""La salle des serveurs de Tessera, toujours allumée — ticket-726."""
from fastapi import APIRouter, Depends, Query

from tessera.config import settings
from tessera.models.salle_tessera import SalleTessera
from tessera.routers.services_running import get_sonde
from tessera.services.ci_watcher import CI_WATCHER
from tessera.services.providers.ollama import secondes_de_refroidissement
from tessera.services.run_registry import RUN_REGISTRY
from tessera.services.salle_tessera import ci_en_attente, salle_tessera
from tessera.services.sonde_systeme import SondeSysteme

router = APIRouter(prefix="/tessera", tags=["tessera"])


def _projets() -> list[str]:
    racine = settings.ide_workspace_dir
    return sorted(p.name for p in racine.iterdir() if p.is_dir()) if racine.is_dir() else []


@router.get("/salle", response_model=SalleTessera)
async def lire_la_salle(
    sonde: SondeSysteme = Depends(get_sonde),
    # Le journal déplié sous la salle en demande plus que l'écran du mur.
    journal: int = Query(default=6, ge=1, le=200),
) -> SalleTessera:
    return await salle_tessera(
        sonde,
        instantane=RUN_REGISTRY.instantane(),
        ci_en_attente=ci_en_attente(_projets(), CI_WATCHER.en_attente),
        ollama_url=settings.ollama_base_url,
        refroidissement_s=secondes_de_refroidissement(settings.ollama_base_url),
        journal=settings.ide_log_file,
        lignes_du_journal=journal,
        base=settings.ide_db_path,
        worktrees=settings.ide_worktrees_dir,
    )
