"""Conversational chat endpoints — ticket-048.

REST reads the history (so a reload restores the conversation), the WebSocket
carries one turn with its tokens and tool calls streamed as they arrive.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from tessera.config import settings
from tessera.services.chat_service import ChatBudgetExceeded, ChatService
from tessera.services.chat_suggestion import summarize_conversation
from tessera.services.run_lock import RUN_LOCK, RunAlreadyInProgress
from tessera.services.database import (
    ChatMessageRow,
    conversation_cost_usd,
    list_chat_messages,
    save_chat_message,
)
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.project_loader import load_project
from tessera.services.providers import get_provider
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

# Le chat lit et écrit des fichiers, et rien d'autre. Aucun outil shell : un
# agent conversationnel pilote par l'utilisateur, exécutant des commandes
# arbitraires dans son dépôt, est une surface d'attaque que ce ticket refuse
# d'ouvrir (ticket-048, hors périmètre explicite).
_CHAT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]

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
    return (
        f"# {project_id}\n\n"
        f"## CLAUDE.md\n{project.raw_claude_md}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions d'architecture\n{decisions or '_Aucune décision._'}"
    )


async def _build_service(project_id: str) -> ChatService:
    project_path = _project_path(project_id)
    return ChatService(
        provider=get_provider(tools=_CHAT_TOOLS),
        prompts_dir=settings.ide_prompts_dir,
        project_path=project_path,
        project_context=await _build_context(project_id, project_path),
        git_workspace=GitWorkspaceService(project_path),
        max_conversation_usd=settings.chat_max_conversation_usd,
    )


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

            await _handle_turn(websocket, project_id, conversation_id, message)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001 — la socket ne doit jamais tuer le serveur
        _logger.warning("chat_stream_failed", extra={"error": str(exc)})
        try:
            await websocket.send_json({"type": "error", "detail": str(exc)})
        except Exception:
            pass


async def _handle_turn(
    websocket: WebSocket, project_id: str, conversation_id: str, message: str
) -> None:
    db_path = settings.ide_db_path

    async def _on_token(token: str) -> None:
        await websocket.send_json({"type": "token", "token": token})

    async def _on_tool_use(name: str, payload: dict[str, object]) -> None:
        await websocket.send_json({"type": "tool_use", "tool": name, "input": payload})

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
            "run_in_progress": _RUN_LOCK.is_running(project_id),
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
