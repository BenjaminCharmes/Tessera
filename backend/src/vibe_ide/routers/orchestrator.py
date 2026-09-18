import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from vibe_ide.config import settings
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.agent_registry import AgentRegistryService
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.dialogue import DialogueChannel
from vibe_ide.services.pipeline_events import EventType
from vibe_ide.services.database import create_run, finish_run, save_event
from vibe_ide.services.doc_updater import DocUpdaterService
from vibe_ide.services.git_workspace import GitWorkspaceService
from vibe_ide.services.github_service import GitHubService
from vibe_ide.services.github_workflow import GitHubWorkflowService
from vibe_ide.services.livraison import Livraison, LivraisonService
from vibe_ide.services.providers import get_provider
from vibe_ide.services.security_auditor import SecurityAuditorService
from vibe_ide.services.test_runner import TestRunnerService
from vibe_ide.services.validator import ValidatorService
from vibe_ide.services.orchestrator import (
    Orchestrator,
    OrchestratorEvent,
    PipelineResult,
)
from vibe_ide.services.project_loader import (
    ProjectLoader,
    load_agents_config,
    load_pipeline_config,
    load_project,
)
from vibe_ide.services.ticket_service import TicketService
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


class RunRequest(BaseModel):
    project_id: str
    ticket_id: str


class RunAutonomousRequest(BaseModel):
    project_id: str
    max_tickets: int = 5


async def _build_project_context(project_id: str) -> str:
    """Assemble the textual context injected into every agent's prompt.

    Contains the project's ``CLAUDE.md`` (conditionally — see below), its
    active agents, its open tickets and its recent architecture decisions.
    """
    project_path = settings.ide_workspace_dir / project_id
    loader = ProjectLoader(settings.ide_workspace_dir)
    try:
        project = await loader.load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ticket_svc = TicketService(project_path, project_id)
    all_tickets = await ticket_svc.list_tickets()
    open_tickets = [t for t in all_tickets if t.status in _OPEN_STATUSES]

    decisions_path = project_path / "memory" / "decisions.md"
    recent_decisions = (
        decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    )

    tickets_summary = (
        "\n".join(f"- [{t.id}] {t.title} ({t.status.value})" for t in open_tickets)
        or "_Aucun ticket ouvert._"
    )

    # Le provider SDK exécute avec `cwd` pointé sur le dossier du projet et
    # charge donc déjà le CLAUDE.md nativement : le réinjecter ici ferait
    # payer le même contenu deux fois, à chaque appel, pour chacun des six
    # agents du pipeline sur jusqu'à trois rounds de revue. Seule l'API
    # Messages (`anthropic_api`), qui n'a pas de `cwd`, en a encore besoin.
    claude_md_section = (
        f"## CLAUDE.md\n{project.raw_claude_md}\n\n"
        if settings.llm_provider != "agent_sdk"
        else ""
    )

    return (
        f"# {project_id}\n\n"
        f"{claude_md_section}"
        f"## Agents actifs\n{', '.join(project.active_agents)}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions récentes\n{recent_decisions or '_Aucune décision._'}"
    )


async def _build_orchestrator(project_id: str) -> Orchestrator:
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
    )
    # Pure text-in/JSON-out services (security_auditor, validator,
    # doc_updater) have no use for file/shell tools — doc_updater writes
    # files itself via `_write_files`, never through an SDK tool, and no cwd
    # is threaded to it. Give them all a tool-less provider (ticket-044
    # review, finding 4; doc_updater moved here per merge-gate finding 2).
    tool_less_provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    registry = AgentRegistryService(settings.ide_prompts_dir)
    project_path = settings.ide_workspace_dir / project_id
    runner = AgentRunner(
        provider, registry, db_path=settings.ide_db_path, project_path=project_path
    )

    project_context = await _build_project_context(project_id)
    ticket_svc = TicketService(project_path, project_id)

    agent_configs = load_agents_config(project_path)
    pipeline_cfg = load_pipeline_config(project_path)

    doc_updater = (
        DocUpdaterService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.doc_updater_enabled
        else None
    )
    test_runner = TestRunnerService() if pipeline_cfg.testeur_enabled else None
    security_auditor = (
        SecurityAuditorService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.securite_enabled
        else None
    )
    validator = (
        ValidatorService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.validateur_enabled
        else None
    )

    git_workspace = GitWorkspaceService(project_path)

    return Orchestrator(
        runner=runner,
        ticket_service=ticket_svc,
        project_context=project_context,
        agent_configs=agent_configs,
        pipeline_log_path=project_path / "memory" / "pipeline-log.md",
        max_review_rounds=pipeline_cfg.max_review_rounds,
        doc_updater=doc_updater,
        test_runner=test_runner,
        test_command=pipeline_cfg.test_command,
        security_auditor=security_auditor,
        validator=validator,
        project_path=project_path,
        git_workspace=git_workspace,
        run_max_budget_usd=settings.run_max_budget_usd,
        # Le tracker vit sur le provider, qui est le seul à voir les
        # messages du SDK. `getattr` parce que le provider Messages API
        # n'a pas de quota d'abonnement à suivre (ticket-054).
        quota_tracker=getattr(provider, "quota", None),
    )


async def _livrer(project_id: str, result: PipelineResult) -> PipelineResult:
    """Porte le travail du run aussi loin que le projet le déclare (ticket-083).

    Une livraison qui échoue ne fait **pas** échouer le run : le travail est
    commité, et perdre la réponse du pipeline parce que GitHub est injoignable
    ferait croire que c'est le pipeline qui a échoué. Le motif remonte dans
    `livraison.arret`, là où l'utilisateur le lira.
    """
    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path),
            github=github,
            base_branch=settings.github_base_branch,
            project_path=project_path,
        ),
        project_path=project_path,
        base_branch=settings.github_base_branch,
    )

    try:
        livraison = await service.livrer(
            ticket_id=result.ticket_id,
            ticket_title=result.ticket_id,
            ticket_body="",
            branch=result.branch,
            approuve=result.approved,
        )
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        _logger.warning("livraison_echouee", extra={"erreur": str(exc)})
        livraison = Livraison(arret=f"Livraison interrompue : {exc}")

    return result.model_copy(update={"livraison": livraison})


@router.post("/run", response_model=PipelineResult)
async def run_pipeline(request: RunRequest) -> PipelineResult:
    orchestrator = await _build_orchestrator(request.project_id)
    run_id = await create_run(settings.ide_db_path, request.project_id, request.ticket_id)

    async def on_event(event: OrchestratorEvent) -> None:
        await save_event(
            settings.ide_db_path,
            run_id,
            event.type.value,
            event.agent.value if event.agent else None,
            event.data,
            event.timestamp.isoformat(),
        )

    try:
        result = await orchestrator.run_pipeline(
            request.project_id, request.ticket_id, on_event, run_id=run_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await finish_run(
        settings.ide_db_path,
        run_id,
        result.rounds,
        result.approved,
        result.final_status.value,
    )
    return await _livrer(request.project_id, result)


@router.post("/run-autonomous", response_model=list[PipelineResult])
async def run_autonomous(request: RunAutonomousRequest) -> list[PipelineResult]:
    orchestrator = await _build_orchestrator(request.project_id)
    return await orchestrator.run_autonomous(request.project_id, request.max_tickets)


@router.websocket("/stream/{project_id}")
async def stream_pipeline(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        orchestrator = await _build_orchestrator(project_id)

        ticket_id: str | None = raw.get("ticket_id")
        ticket_ids: list[str] = list(raw.get("ticket_ids") or [])
        mode: str = raw.get("mode", "single")

        if mode == "autonomous":
            async def send_event_autonomous(event: OrchestratorEvent) -> None:
                await websocket.send_text(event.model_dump_json())

            max_tickets = int(raw.get("max_tickets", 5))
            await orchestrator.run_autonomous(project_id, max_tickets, send_event_autonomous)
        elif ticket_ids:
            # Une file : l'utilisateur a désigné un lot et son ordre. Le canal
            # de dialogue est partagé par tous les runs, pour qu'un seul arrêt
            # vide la file entière (ticket-074).
            async def send_queue_event(event: OrchestratorEvent) -> None:
                await websocket.send_text(event.model_dump_json())

            async def announce_queue_question(question: str) -> None:
                await send_queue_event(
                    OrchestratorEvent(
                        type=EventType.AGENT_QUESTION,
                        ticket_id="",
                        data={"question": question},
                    )
                )

            queue_dialogue = DialogueChannel(
                timeout_s=settings.dialogue_timeout_s,
                interactive=True,
                on_question=announce_queue_question,
            )

            async def read_queue_inbound() -> None:
                while True:
                    message = await websocket.receive_json()
                    texte = str(message.get("text", ""))
                    if message.get("type") == "answer":
                        queue_dialogue.answer(texte)
                    elif message.get("type") == "interject":
                        queue_dialogue.interject(texte)
                    elif message.get("type") == "stop":
                        queue_dialogue.request_stop()

            queue_reader = asyncio.create_task(read_queue_inbound())
            try:
                await orchestrator.run_queue(
                    project_id, ticket_ids, send_queue_event, queue_dialogue
                )
            except ValueError as exc:
                await websocket.send_json({"error": str(exc)})
            finally:
                queue_reader.cancel()
        elif ticket_id:
            run_id = await create_run(settings.ide_db_path, project_id, ticket_id)

            async def send_event(event: OrchestratorEvent) -> None:
                # Émettre vers une socket morte ne doit pas tuer le run : le
                # pipeline continue côté serveur, et l'utilisateur en est
                # averti. Faire remonter l'erreur ici laissait le run ouvert en
                # base, donc « en cours » à jamais dans l'historique
                # (ticket-079).
                try:
                    await websocket.send_text(event.model_dump_json())
                except Exception:  # noqa: BLE001 — socket fermée, on continue
                    pass
                await save_event(
                    settings.ide_db_path,
                    run_id,
                    event.type.value,
                    event.agent.value if event.agent else None,
                    event.data,
                    event.timestamp.isoformat(),
                )

            async def announce_question(question: str, tid: str = ticket_id) -> None:
                await send_event(
                    OrchestratorEvent(
                        type=EventType.AGENT_QUESTION,
                        ticket_id=tid,
                        data={"question": question},
                    )
                )

            dialogue = DialogueChannel(
                timeout_s=settings.dialogue_timeout_s,
                interactive=True,
                on_question=announce_question,
            )

            # La socket ne lisait qu'un seul message entrant — la commande de
            # démarrage — puis n'émettait plus : répondre à un agent bloqué
            # était impossible. La lecture tourne maintenant en parallèle de
            # l'émission, pour toute la durée du run.
            async def read_inbound() -> None:
                while True:
                    message = await websocket.receive_json()
                    texte = str(message.get("text", ""))
                    if message.get("type") == "answer":
                        dialogue.answer(texte)
                    elif message.get("type") == "interject":
                        dialogue.interject(texte)
                    elif message.get("type") == "stop":
                        dialogue.request_stop()

            reader = asyncio.create_task(read_inbound())
            result = None
            echec: str | None = None
            try:
                result = await orchestrator.run_pipeline(
                    project_id, ticket_id, send_event, run_id=run_id, dialogue=dialogue
                )
            except ValueError as exc:
                echec = str(exc)
            finally:
                # Le lecteur attend indéfiniment un message : sans annulation,
                # la connexion ne se fermerait jamais après la fin du run.
                reader.cancel()

            # Clore le run **avant** toute écriture réseau. Placé après, cet
            # appel disparaissait dès que la socket mourait : la tâche était
            # annulée et l'`await` ne se terminait jamais, laissant la ligne
            # ouverte et l'historique bloqué sur « en cours » (ticket-079).
            await finish_run(
                settings.ide_db_path,
                run_id,
                result.rounds if result else 0,
                result.approved if result else False,
                result.final_status.value if result else "interrupted",
            )

            if result is not None:
                result = await _livrer(project_id, result)
                if result.livraison is not None:
                    await send_event(
                        OrchestratorEvent(
                            type=EventType.LIVRAISON_DONE,
                            ticket_id=ticket_id,
                            data=result.livraison.__dict__,
                        )
                    )

            if echec is not None:
                await websocket.send_json({"error": echec})
        else:
            await websocket.send_json({"error": "ticket_id ou mode=autonomous requis"})

    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        try:
            await websocket.send_json({"error": exc.detail})
        except Exception:
            pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
