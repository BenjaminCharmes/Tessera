"""Conversational chat endpoints — ticket-048.

REST reads the history (so a reload restores the conversation), the WebSocket
carries one turn with its tokens and tool calls streamed as they arrive.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from tessera.config import settings
from tessera.services.adr import adr_pertinents
from tessera.services.chat_service import ChatBudgetExceeded, ChatService
from tessera.services.chat_suggestion import summarize_conversation
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import emetteur
from tessera.services.run_lock import RUN_LOCK
from tessera.services.run_registry import RUN_REGISTRY, RunActif, RunAlreadyInProgress
from tessera.services.database import (
    ChatMessageRow,
    ConversationSummary,
    conversation_cost_usd,
    list_chat_messages,
    list_conversations,
    save_chat_message,
)
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.project_loader import load_project
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

# Le chat lit et écrit des fichiers, et rien d'autre. Aucun outil shell : un
# agent conversationnel pilote par l'utilisateur, exécutant des commandes
# arbitraires dans son dépôt, est une surface d'attaque que ce ticket refuse
# d'ouvrir (ticket-048, hors périmètre explicite).
_CHAT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]

#: Le rôle sous lequel le chat lit les ADR : aucun ADR ne le nomme, il ne
#: reçoit donc que le tronc commun — toutes les contraintes, aucun choix passé.
_ROLE_CHAT = "chat"

# Un seul pipeline à la fois par projet : deux exécutions concurrentes
# se marcheraient dessus dans le même arbre de travail (ADR-018). L'instance
# est celle de l'orchestrateur : un run lancé depuis le tableau doit refuser
# celui du chat, et réciproquement (ticket-121).
_RUN_LOCK = RUN_LOCK


class ChatHistory(BaseModel):
    """A conversation as the UI needs it, with what it has cost so far."""

    project_id: str
    conversation_id: str
    messages: list[ChatMessageRow]
    spent_usd: float
    max_usd: float


def _project_path(project_id: str) -> Path:
    path = settings.ide_workspace_dir / project_id
    if not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet introuvable : {project_id}")
    return path


async def _build_context(project_id: str, project_path: Path) -> str:
    """Le même contexte que les agents du pipeline reçoivent."""
    project = load_project(project_path)
    tickets = await TicketService(project_path, project_id).list_tickets()
    open_tickets = [t for t in tickets if t.status.value in ("todo", "in-progress", "in-review")]
    tickets_summary = (
        "\n".join(f"- [{t.id}] {t.title} ({t.status.value})" for t in open_tickets)
        or "_Aucun ticket ouvert._"
    )
    decisions_path = project_path / "memory" / "decisions.md"
    decisions = (
        decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    )
    # Le même titre que le pipeline : c'est lui que `adr_pertinents` reconnaît.
    # Sous un autre titre, le chat recevait le fichier entier, choix de stack
    # compris, quand chaque agent du pipeline est filtré (ticket-126).
    contexte = (
        f"# {project_id}\n\n"
        f"## CLAUDE.md\n{project.raw_claude_md}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions récentes\n{decisions or '_Aucune décision._'}"
    )
    return adr_pertinents(contexte, _ROLE_CHAT)


async def _build_service(project_id: str) -> ChatService:
    project_path = _project_path(project_id)
    return ChatService(
        # Par la fabrique, comme tout le monde : le chat ignorait jusqu'ici
        # le provider réglé, et tournait toujours sur le SDK (ticket-188).
        provider=provider_pour_role(
            project_path, "chat", tools=_CHAT_TOOLS, project_id=project_id
        ),
        prompts_dir=settings.ide_prompts_dir,
        project_path=project_path,
        project_context=await _build_context(project_id, project_path),
        git_workspace=GitWorkspaceService(project_path),
        max_conversation_usd=settings.chat_max_conversation_usd,
    )


@router.get("/{project_id}/chat", response_model=list[ConversationSummary])
async def get_conversations(project_id: str) -> list[ConversationSummary]:
    """All conversations for a project, most recent first — ticket-224."""
    _project_path(project_id)
    return await list_conversations(settings.ide_db_path, project_id)


@router.get("/{project_id}/chat/{conversation_id}", response_model=ChatHistory)
async def get_chat_history(project_id: str, conversation_id: str) -> ChatHistory:
    _project_path(project_id)
    return ChatHistory(
        project_id=project_id,
        conversation_id=conversation_id,
        messages=await list_chat_messages(settings.ide_db_path, project_id, conversation_id),
        spent_usd=await conversation_cost_usd(settings.ide_db_path, project_id, conversation_id),
        max_usd=settings.chat_max_conversation_usd,
    )


@router.websocket("/{project_id}/chat")
async def chat_stream(websocket: WebSocket, project_id: str) -> None:
    """One connection, many turns. Each inbound message is one exchange."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_json()
            conversation_id = str(raw.get("conversation_id") or "default")
            message = str(raw.get("message") or "").strip()
            if not message:
                await websocket.send_json({"type": "error", "detail": "message vide"})
                continue

            # Le verrou, pour toute la durée du tour — ticket-139. Un tour
            # de chat n'est pas un « run », mais il écrit : `_commit_if_written`
            # crée une branche dès que l'arbre n'est pas propre (ADR-019), et
            # ce checkout déplacerait l'arbre sous le codeur d'un run en cours.
            # ADR-038 annonçait déjà couvrir le chat ; seul `/chat/run` l'était.
            tour: RunActif | None = None
            try:
                # `RUN_REGISTRY` directement plutôt que `_RUN_LOCK` : c'est le
                # même registre, mais il accepte un `mode`. Sans lui, le tour
                # s'affiche dans la supervision comme un run de ticket
                # « chat », avec un chrono, des tours et un verdict — pour
                # quelque chose qui n'en a aucun (ticket-130).
                async with RUN_REGISTRY.acquire(
                    project_id, _LIBELLE_DU_CHAT, mode="chat"
                ) as run:
                    tour = run
                    await _handle_turn(
                        websocket, project_id, conversation_id, message, run
                    )
            except RunAlreadyInProgress as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            finally:
                # Après la sortie du registre, jamais avant : `run_closed` dit
                # la fin **et** la libération du projet (ADR-041). Le publier
                # à l'intérieur ferait croire le projet encore occupé.
                if tour is not None:
                    await _clore_le_tour(tour, conversation_id)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001 — la socket ne doit jamais tuer le serveur
        _logger.warning("chat_stream_failed", extra={"error": str(exc)})
        try:
            await websocket.send_json({"type": "error", "detail": str(exc)})
        except Exception:
            pass


#: Ce que le tour de chat inscrit dans le verrou (ticket-139).
_LIBELLE_DU_CHAT = "chat"


def _un_run_occupe(project_id: str) -> bool:
    """Un *run* tourne — le tour de chat en cours ne compte pas.

    Depuis ticket-139 le tour de chat tient lui-même le verrou : interroger
    `is_running` depuis l'intérieur du tour répondrait toujours oui, et l'UI
    cacherait le bouton « lancer » pour une occupation qui est la sienne.
    Le champ dit « un pipeline tourne », et un tour de chat n'en est pas un.
    """
    if not _RUN_LOCK.is_running(project_id):
        return False
    return _RUN_LOCK.ticket_en_cours(project_id) != _LIBELLE_DU_CHAT


async def _clore_le_tour(run: RunActif, conversation_id: str) -> None:
    await emetteur(EVENT_HUB, run, None)(
        OrchestratorEvent(
            type=EventType.RUN_CLOSED,
            ticket_id=conversation_id,
            data={"mode": "chat"},
        )
    )


async def _handle_turn(
    websocket: WebSocket,
    project_id: str,
    conversation_id: str,
    message: str,
    run: RunActif,
) -> None:
    db_path = settings.ide_db_path
    # Publier sur le hub en plus de la socket du chat : le canal
    # d'observation porte « ce que l'IDE est en train de faire », et un chat
    # qui écrit dans un dépôt sans y apparaître serait le seul producteur de
    # travail invisible (ADR-019, ADR-041). `run_id_en_base=None` : un tour de
    # chat a déjà son historique de conversation, il n'ouvre pas de ligne de
    # run.
    publier = emetteur(EVENT_HUB, run, None)

    async def _evenement(type_: EventType, data: dict[str, object]) -> None:
        await publier(
            OrchestratorEvent(type=type_, ticket_id=conversation_id, data=data)
        )

    async def _on_token(token: str) -> None:
        await websocket.send_json({"type": "token", "token": token})
        await _evenement(EventType.AGENT_TOKEN, {"token": token})

    async def _on_tool_use(name: str, payload: dict[str, object]) -> None:
        await websocket.send_json({"type": "tool_use", "tool": name, "input": payload})
        await _evenement(EventType.AGENT_TOOL_USE, {"tool": name})

    await _evenement(EventType.AGENT_STARTED, {"mode": "chat"})

    history = await list_chat_messages(db_path, project_id, conversation_id)
    spent = await conversation_cost_usd(db_path, project_id, conversation_id)

    try:
        service = await _build_service(project_id)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "detail": str(exc.detail)})
        return

    # Le message de l'utilisateur est persisté avant l'appel : s'il échoue, la
    # question reste dans l'historique plutôt que de disparaître.
    await save_chat_message(db_path, project_id, conversation_id, "user", message, 0.0)
    await websocket.send_json({"type": "start", "conversation_id": conversation_id})

    try:
        reply = await service.send(
            history=history,
            message=message,
            spent_usd=spent,
            on_token=_on_token,
            on_tool_use=_on_tool_use,
        )
    except ChatBudgetExceeded as exc:
        await websocket.send_json({"type": "budget_exceeded", "detail": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001
        _logger.warning("chat_turn_failed", extra={"error": str(exc)})
        await websocket.send_json({"type": "error", "detail": str(exc)})
        return

    await save_chat_message(
        db_path, project_id, conversation_id, "assistant", reply.content, reply.cost_usd
    )
    await websocket.send_json(
        {
            "type": "done",
            "content": reply.content,
            "cost_usd": reply.cost_usd,
            "spent_usd": await conversation_cost_usd(db_path, project_id, conversation_id),
            "max_usd": settings.chat_max_conversation_usd,
            "branch": reply.branch,
            "commit_sha": reply.commit_sha,
            # L'agent suggère, l'utilisateur décide : l'UI en fait un bouton
            # (ticket-055).
            "suggested_ticket_id": reply.suggested_ticket_id,
            "run_in_progress": _un_run_occupe(project_id),
        }
    )


class RunFromChatRequest(BaseModel):
    """Le lancement accepté par l'utilisateur, pas déclenché par l'agent."""

    conversation_id: str = "default"
    ticket_id: str


class RunFromChatResponse(BaseModel):
    ticket_id: str
    approved: bool
    rounds: int
    final_status: str
    branch: str | None = None
    commit_sha: str | None = None


def _with_conversation(project_context: str, summary: str) -> str:
    """Append the discussion that led to the ticket, for the coder's prompt.

    Sans ce contexte, le codeur reçoit le ticket nu et tout ce qui a été
    décidé dans la conversation est perdu — c'est le manque que
    ticket-055 comble.
    """
    heading = "## Discussion ayant mené à ce ticket"
    return f"{project_context}\n\n{heading}\n{summary}"


@router.post("/{project_id}/chat/run", response_model=RunFromChatResponse)
async def run_pipeline_from_chat(
    project_id: str, body: RunFromChatRequest
) -> RunFromChatResponse:
    """Lance le pipeline en lui transmettant le raisonnement de la discussion.

    Sans ce contexte, le codeur reçoit le ticket nu et tout ce qui a été
    décidé dans la conversation est perdu — c'est le manque que ce ticket
    comble.
    """
    _project_path(project_id)

    async def _noop(event: object) -> None:
        return None

    # Le verrou est pris AVANT de construire l'orchestrateur : celui-ci charge
    # le projet et instancie les providers, travail entièrement perdu si un
    # run tourne déjà. Un refus doit être immédiat et bon marché.
    try:
        async with _RUN_LOCK.acquire(project_id, body.ticket_id):
            history = await list_chat_messages(
                settings.ide_db_path, project_id, body.conversation_id
            )
            summary = summarize_conversation(history)

            from tessera.routers.orchestrator import _build_orchestrator

            orchestrator = await _build_orchestrator(project_id)
            if summary:
                orchestrator._project_context = _with_conversation(
                    orchestrator._project_context, summary
                )

            result = await orchestrator.run_pipeline(project_id, body.ticket_id, _noop)
    except RunAlreadyInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RunFromChatResponse(
        ticket_id=result.ticket_id,
        approved=result.approved,
        rounds=result.rounds,
        final_status=result.final_status.value,
        branch=result.branch,
        commit_sha=result.commit_sha,
    )
