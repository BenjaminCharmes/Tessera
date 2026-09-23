"""Démarrer et arrêter les services d'un projet — ticket-137.

ADR-042 : le backend lance lui-même les commandes que le projet **déclare**,
sans shell et sans agent. Rien de déclaré, pas de lancement — le défaut
protège, et le refus dit quoi écrire plutôt que d'envoyer lire le code.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from tessera.config import settings
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.process_registry import (
    PROCESS_REGISTRY,
    CommandeInvalide,
    Service,
)
from tessera.services.project_loader import load_services_config
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["services"])


def _racine(project_id: str) -> Path:
    racine = settings.ide_workspace_dir / project_id
    if not racine.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet inconnu : {project_id}")
    return racine


async def _publier(service: Service, ligne: str) -> None:
    await EVENT_HUB.publish(
        OrchestratorEvent(
            type=EventType.SERVICE_OUTPUT,
            ticket_id=service.nom,
            data={"ligne": ligne, "service": service.nom},
            project_id=service.project_id,
        )
    )


@router.post("/{project_id}/services/start")
async def demarrer(project_id: str) -> dict[str, object]:
    racine = _racine(project_id)
    declares = load_services_config(racine)
    if not declares:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Le projet « {project_id} » ne déclare aucun service. "
                "Ajoute une liste `services` dans son `agents.json`, chaque "
                'entrée portant {"nom": "...", "commande": "..."}.'
            ),
        )

    demarres: list[dict[str, object]] = []
    try:
        for declare in declares:
            service = await PROCESS_REGISTRY.demarrer(
                project_id,
                declare["nom"],
                declare["commande"],
                racine,
                cwd=declare.get("cwd") or None,
                sur_ligne=_publier,
            )
            demarres.append(service.en_dict())
    except CommandeInvalide as exc:
        # Ce qui a déjà démarré s'arrête : un lancement à moitié fait laisse
        # un serveur seul, sans le reste dont il dépend.
        await PROCESS_REGISTRY.arreter(project_id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        await PROCESS_REGISTRY.arreter(project_id)
        raise HTTPException(
            status_code=422, detail=f"Lancement impossible : {exc}"
        ) from exc

    return {"services": demarres}


@router.post("/{project_id}/services/stop")
async def arreter(project_id: str) -> dict[str, int]:
    _racine(project_id)
    return {"arretes": await PROCESS_REGISTRY.arreter(project_id)}


@router.get("/{project_id}/services")
async def lister(project_id: str) -> list[dict[str, object]]:
    _racine(project_id)
    return [service.en_dict() for service in PROCESS_REGISTRY.services_de(project_id)]
