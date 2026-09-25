"""The channel every client watches — ticket-128.

Un seul WebSocket, sans projet dans l'URL : il porte les runs de toute la
machine. ADR-038 autorise un run par projet et N projets en parallèle, et
c'est précisément ce parallélisme que l'UI ne montrait pas.

## Ce qui passe, et ce qui se demande

Les **transitions** partent à tous les observateurs : elles disent l'état, et
un état manquant se lit comme un run figé. Le **texte** — `agent_token`,
`agent_tool_use` — ne part qu'aux clients qui se sont abonnés à ce run précis.
Tout reste disponible ; on ne paie que ce qu'on regarde.

Le dialogue (ADR-025) passe par ici aussi : le canal du run vit dans
`RunRegistry`, donc n'importe quel observateur peut répondre. Avant, seule la
socket qui avait lancé le run le pouvait.
"""
import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tessera.services.event_hub import EVENT_HUB, JETABLES
from tessera.services.run_registry import RUN_REGISTRY
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


async def _lire_les_messages(websocket: WebSocket, abonnements: set[str]) -> None:
    """Relay inbound messages: subscriptions, and dialogue for any run.

    Tourne en parallèle de l'émission : une socket qui ne lit qu'entre deux
    envois ne permettrait de répondre à un agent que lorsqu'il parle, c'est-à-
    dire jamais — il est suspendu quand il attend (ticket-066).
    """
    while True:
        message: dict[str, Any] = await websocket.receive_json()

        cible = message.get("subscribe")
        if isinstance(cible, str):
            abonnements.add(cible)
            continue

        retire = message.get("unsubscribe")
        if isinstance(retire, str):
            abonnements.discard(retire)
            continue

        run = RUN_REGISTRY.get(str(message.get("run_id", "")))
        if run is None or run.dialogue is None:
            continue

        texte = str(message.get("text", ""))
        genre = message.get("type")
        if genre == "answer":
            run.dialogue.answer(texte)
        elif genre == "interject":
            run.dialogue.interject(texte)
        elif genre == "stop":
            run.dialogue.request_stop()


@router.websocket("/observe")
async def observe(websocket: WebSocket) -> None:
    await websocket.accept()
    abonnement = EVENT_HUB.subscribe()
    abonnements: set[str] = set()
    lecteur: asyncio.Task[None] | None = None

    try:
        # L'instantané d'abord : sans lui, un client qui arrive pendant un run
        # devrait attendre le prochain événement pour apprendre qu'il existe.
        await websocket.send_json(
            {"type": "snapshot", "runs": RUN_REGISTRY.instantane()}
        )
        lecteur = asyncio.create_task(_lire_les_messages(websocket, abonnements))

        while True:
            event = await abonnement.recevoir()
            if event.type in JETABLES and event.run_id not in abonnements:
                continue
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 — un observateur ne casse rien
        # Le run continue sans lui : c'est tout l'intérêt du découplage.
        _logger.warning("observateur_interrompu", extra={"erreur": str(exc)})
    finally:
        if lecteur is not None:
            lecteur.cancel()
        abonnement.fermer()
