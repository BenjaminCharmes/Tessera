"""The WebSocket side of a pipeline run — ticket-121.

`stream_pipeline` grew three near-identical closures — `send_event`,
`send_queue_event`, `send_event_autonomous` — and only the first tolerated a
dead socket. Closing the IDE tab during a queue run therefore raised inside
the pipeline, before its commit. One emitter, used by all three modes, is
what makes the tolerance a property of the endpoint rather than of whichever
closure a ticket happened to touch.

The run body lives here rather than in `routers/orchestrator.py` to keep that
module readable; it receives the router's builders as parameters so the two
modules do not import each other.
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from tessera.config import settings
from tessera.services.database import create_run, finish_run, save_event
from tessera.services.dialogue import DialogueChannel
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
)

Construire = Callable[[str], Awaitable[Orchestrator]]
TirerLesIssues = Callable[[str], Awaitable[int]]


def emetteur(websocket: WebSocket, run_id: str | None) -> EventCallback:
    """Build the callback that streams events to `websocket`.

    Émettre vers une socket morte ne doit pas tuer le run : le pipeline
    continue côté serveur, et l'utilisateur en est averti. Faire remonter
    l'erreur laissait le run ouvert en base, donc « en cours » à jamais dans
    l'historique (ticket-079). Avec un `run_id`, l'événement est aussi
    persisté — **après** l'envoi, pour qu'une socket morte ne l'empêche pas.
    """

    async def envoyer(event: OrchestratorEvent) -> None:
        try:
            await websocket.send_text(event.model_dump_json())
        except Exception:  # noqa: BLE001 — socket fermée, on continue
            pass
        if run_id is None:
            return
        await save_event(
            settings.ide_db_path,
            run_id,
            event.type.value,
            event.agent.value if event.agent else None,
            event.data,
            event.timestamp.isoformat(),
        )

    return envoyer


def libelle_du_run(raw: dict[str, Any]) -> str | None:
    """What the lock reports as running: the ticket, the queue, or the mode."""
    if raw.get("ticket_id"):
        return str(raw["ticket_id"])
    if raw.get("ticket_ids"):
        return ", ".join(str(t) for t in raw["ticket_ids"])
    mode = raw.get("mode")
    return str(mode) if mode else None


def _dialogue(envoyer: EventCallback, ticket_id: str) -> DialogueChannel:
    async def annoncer(question: str) -> None:
        await envoyer(
            OrchestratorEvent(
                type=EventType.AGENT_QUESTION,
                ticket_id=ticket_id,
                data={"question": question},
            )
        )

    return DialogueChannel(
        timeout_s=settings.dialogue_timeout_s, interactive=True, on_question=annoncer
    )


async def _lire_les_messages(websocket: WebSocket, dialogue: DialogueChannel) -> None:
    """Relay inbound messages to the dialogue, for the whole run.

    La socket ne lisait qu'un seul message entrant — la commande de
    démarrage — puis n'émettait plus : répondre à un agent bloqué était
    impossible. La lecture tourne en parallèle de l'émission (ticket-066).
    """
    while True:
        message = await websocket.receive_json()
        texte = str(message.get("text", ""))
        if message.get("type") == "answer":
            dialogue.answer(texte)
        elif message.get("type") == "interject":
            dialogue.interject(texte)
        elif message.get("type") == "stop":
            dialogue.request_stop()


async def stream_verrouille(
    websocket: WebSocket,
    project_id: str,
    raw: dict[str, Any],
    *,
    construire: Construire,
    tirer_les_issues: TirerLesIssues,
) -> None:
    """The body of `stream_pipeline`, run while the project lock is held."""
    orchestrator = await construire(project_id)

    ticket_id: str | None = raw.get("ticket_id")
    ticket_ids: list[str] = list(raw.get("ticket_ids") or [])
    mode: str = raw.get("mode", "single")

    if mode == "autonomous":
        if raw.get("depuis_github"):
            await tirer_les_issues(project_id)
        max_tickets = int(raw.get("max_tickets", 5))
        await orchestrator.run_autonomous(
            project_id, max_tickets, emetteur(websocket, run_id=None)
        )
    elif ticket_ids:
        await _stream_file(websocket, project_id, ticket_ids, orchestrator)
    elif ticket_id:
        await _stream_un_ticket(websocket, project_id, ticket_id, orchestrator)
    else:
        await websocket.send_json({"error": "ticket_id ou mode=autonomous requis"})


async def _stream_file(
    websocket: WebSocket,
    project_id: str,
    ticket_ids: list[str],
    orchestrator: Orchestrator,
) -> None:
    # Une file : l'utilisateur a désigné un lot et son ordre. Le canal de
    # dialogue est partagé par tous les runs, pour qu'un seul arrêt vide la
    # file entière (ticket-074).
    envoyer = emetteur(websocket, run_id=None)
    dialogue = _dialogue(envoyer, ticket_id="")
    lecteur = asyncio.create_task(_lire_les_messages(websocket, dialogue))
    try:
        await orchestrator.run_queue(project_id, ticket_ids, envoyer, dialogue)
    except ValueError as exc:
        await websocket.send_json({"error": str(exc)})
    finally:
        lecteur.cancel()


async def _stream_un_ticket(
    websocket: WebSocket, project_id: str, ticket_id: str, orchestrator: Orchestrator
) -> None:
    run_id = await create_run(settings.ide_db_path, project_id, ticket_id)
    envoyer = emetteur(websocket, run_id=run_id)
    dialogue = _dialogue(envoyer, ticket_id)
    lecteur = asyncio.create_task(_lire_les_messages(websocket, dialogue))
    result = None
    echec: str | None = None
    try:
        result = await orchestrator.run_pipeline(
            project_id, ticket_id, envoyer, run_id=run_id, dialogue=dialogue
        )
    except Exception as exc:  # noqa: BLE001 — toute panne clôt le run en base
        # `ValueError` seule laissait toute autre exception sauter
        # `finish_run` : l'historique restait « en cours » (ticket-121).
        echec = str(exc)
    finally:
        # Le lecteur attend indéfiniment un message : sans annulation, la
        # connexion ne se fermerait jamais après la fin du run.
        lecteur.cancel()

    # Clore le run **avant** toute écriture réseau. Placé après, cet appel
    # disparaissait dès que la socket mourait : la tâche était annulée et
    # l'`await` ne se terminait jamais, laissant la ligne ouverte et
    # l'historique bloqué sur « en cours » (ticket-079).
    await finish_run(
        settings.ide_db_path,
        run_id,
        result.rounds if result else 0,
        result.approved if result else False,
        result.final_status.value if result else "interrupted",
    )

    if echec is not None:
        await websocket.send_json({"error": echec})
