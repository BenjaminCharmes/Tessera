"""Stage — someone produces the work (ticket-688, split from `pipeline_stages`).

The coder (or the architect on a `design` ticket) writes to disk, then the
stage captures what was really written: the git diff and the artifact diff.
Also holds what every stage reads to build its context.
"""
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

from tessera.models.agent import AgentRole
from tessera.models.ticket import TicketStatus, TicketType
from tessera.services.artifact_snapshot import diff_artifacts, snapshot_artifacts
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun, set_status
from tessera.services.providers.refus_garde import refus_du_tour
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


def take_artifact_snapshot(orch: "Orchestrator", run: PipelineRun) -> None:
    """Take a snapshot of memory/ and tickets/ before any agent runs.

    Stored in ``run.artifact_snapshot`` and used at the end of each coder turn
    to produce the artifact diff — a textual view of what the agent wrote in
    Tessera's own directories, which are excluded from the git diff either
    because the project is in local-artifact mode (ADR-021) or because
    ``_ORCHESTRATOR_ARTIFACT_PATHS`` excludes them from the reviewed diff.

    Called once per run, before the first tour.  No-op when no project path is
    configured (tests, projects without a filesystem path).
    """
    if orch._project_path is None:
        return
    run.artifact_snapshot = snapshot_artifacts(orch._project_path)


def build_context(orch: "Orchestrator", run: PipelineRun) -> str:
    """Project context, reviewer feedback so far, and anything the user said.

    This is where the user's in-flight messages enter the run (ticket-066).
    Every stage builds its context here, so draining the mailbox at this one
    point is what makes an interjection reach *the next agent to speak*, no
    matter which one it is.

    The mailbox is drained, not read: a message injected twice would be
    repeated at every round, and the context would grow a little more each
    time.
    """
    parts = [orch._project_context]

    # Le plan précède les retours : le codeur le suit, le reviewer juge
    # l'écart (ticket-243). Il reste dans le contexte du tour, donc dans les
    # reprises : c'est court, et c'est ce qui dit où le travail doit aller.
    if run.plan:
        parts.append(f"\n\n## Plan retenu avant le code\n{run.plan}")

    if run.review_feedback:
        parts.append(
            "\n\n## Retours reviewer précédents\n"
            + "\n---\n".join(
                f"Tour {i + 1}: {fb}" for i, fb in enumerate(run.review_feedback)
            )
        )

    if messages := run.dialogue.drain():
        parts.append(
            "\n\n## Consignes de l'utilisateur, en cours de run\n"
            + "\n".join(f"- {m}" for m in messages)
        )

    # Gardé à part pour le codeur qui reprend sa session (ticket-187) : la
    # boîte aux lettres est vidée ici, une seconde construction ne retrouverait
    # plus les consignes.
    run.contexte_du_tour = "".join(parts[1:]).strip()
    return "".join(parts)


def asker_for(run: PipelineRun) -> Optional[Callable[[str], Awaitable[str]]]:
    """L'outil `ask_user` à donner à l'agent, ou rien (ticket-066).

    Un run non interactif — appel programmatique, test, run autonome — ne doit
    pas recevoir l'outil : l'agent y attendrait le délai complet d'ADR-025 à
    chaque question, sans que personne ne puisse jamais y répondre.
    """
    return run.dialogue.ask if run.dialogue.interactive else None


def journaliser_refus_cli(
    orch: "Orchestrator", ticket_id: str, role: AgentRole, outils: list[str]
) -> None:
    """Writes one journal line per tool the embedded CLI refused (ticket-515).

    Sans cette ligne le refus restait invisible : le tour finissait « normalement »
    alors que l'agent s'était arrêté sur un outil qu'on ne lui avait pas laissé.
    """
    for nom in outils:
        orch._log(f"[{ticket_id}] {role.value}: outil {nom} refusé par le CLI")


async def run_coder(orch: "Orchestrator", run: PipelineRun, context: str) -> None:
    """Run the coder, then capture what it actually wrote to disk."""
    # Un ticket `design` ne demande pas du code mais une décision, et
    # `ide-core/CLAUDE.md` promettait l'architecte dessus depuis le premier
    # commit sans que rien ne route par type (ticket-098). L'étape reste la
    # même — quelqu'un produit le travail — seul le rôle change. Les
    # événements portent ce rôle, pas `codeur` en dur : l'UI montrait un
    # codeur au travail quand l'architecte produisait (ticket-122).
    role = _role_qui_produit(run.ticket.type)
    codeur_cfg = orch._config_for(role)
    ticket_id = run.ticket_id

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=role,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — codeur démarré")

    async def _emit_token(token: str, tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOKEN,
                agent=role,
                ticket_id=tid,
                data={"token": token},
            )
        )

    async def _emit_tool(name: str, payload: dict[str, Any], tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOOL_USE,
                agent=role,
                ticket_id=tid,
                data={"tool": name, "input": payload},
            )
        )

    # Comme au niveau du provider : le paramètre n'est transmis que s'il y a
    # quelque chose à transmettre. Un run non interactif appelle donc le
    # runner exactement comme avant ce ticket.
    asker = asker_for(run)
    extra: dict[str, Any] = {"ask_user": asker} if asker is not None else {}

    # Au tour suivant, le codeur reprend sa conversation et ne reçoit que ce
    # que le tour ajoute : le ticket, les ADR et le dépôt, il les a déjà lus
    # (ticket-187). Sans session — premier tour, provider muet — l'appel
    # reste complet.
    if run.session_codeur is not None:
        extra["session"] = run.session_codeur
        context = run.contexte_du_tour
    elif run.carte_du_depot:
        # La carte précède le contexte : `adr_pertinents` découpe tout ce qui
        # suit « Décisions récentes » en ADR, et une carte placée après serait
        # avalée par le dernier d'entre eux (ticket-190). Le reviewer ne la
        # reçoit pas : il part du diff.
        context = (
            "## Fichiers du projet\n"
            "Lis ce dont tu as besoin ; ne relis pas cette carte.\n\n"
            f"{run.carte_du_depot}\n\n{context}"
        )

    # Ce qu'un rôle antérieur (le plan) aurait refusé n'est pas le tour du codeur.
    refus_du_tour(orch)
    codeur_result = await orch._runner.run(
        role=role,
        ticket=run.ticket,
        project_context=context,
        agent_config=codeur_cfg,
        stream_callback=_emit_token,
        tool_callback=_emit_tool,
        run_id=run.run_id,
        **extra,
    )
    if codeur_result.session_id is not None:
        run.session_codeur = codeur_result.session_id
    journaliser_refus_cli(orch, ticket_id, role, codeur_result.outils_refuses)
    orch.record_spend(codeur_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=role,
            ticket_id=ticket_id,
            # Le coût part avec la fin de l'appel : c'est pendant le run
            # qu'on décide de l'arrêter (ticket-197).
            data={
                "content": codeur_result.content,
                "cost_usd": codeur_result.cost_usd,
                "duration_ms": codeur_result.duration_ms,
            },
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — {role.value} terminé "
        f"({codeur_result.duration_ms}ms)"
    )

    run.refus_du_tour = refus_du_tour(orch)
    run.reviewed_code = await _capture_diff(orch, run, codeur_result.content)
    _capture_artifact_diff(orch, run)
    await set_status(orch, run, TicketStatus.in_review)


async def _capture_diff(orch: "Orchestrator", run: PipelineRun, prose: str) -> str:
    """The real diff if there is one, the coder's prose as a last resort.

    Le codeur écrit réellement sur disque : ce qui doit être relu, audité et
    validé, c'est le diff, pas la prose de l'agent.

    Sur une branche reprise (second run du même ticket), `diff_depuis_base`
    étend le diff jusqu'au point de divergence de la branche : l'audit
    sécurité, le reviewer et le validateur voient tout le travail accumulé,
    pas seulement ce que le dernier tour n'a pas encore commité (ticket-208).
    Une seule fonction calcule le diff — `reviewed_code` est posé ici et les
    trois portes le lisent, sans recalcul.
    """
    if orch._git_workspace is None:
        return prose
    try:
        diff = await orch._git_workspace.diff_depuis_base()
    except GitWorkspaceError as exc:
        _logger.warning("diff_failed", extra={"error": str(exc)})
        _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
        return prose
    if diff.strip():
        return diff
    _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
    return prose


def _capture_artifact_diff(orch: "Orchestrator", run: PipelineRun) -> None:
    """Compute and store the artifact diff since run start.

    Populates ``run.artifact_diff`` with the textual diff of memory/ and
    tickets/ since the snapshot taken by ``take_artifact_snapshot``.  No-op
    when no snapshot exists (no project path, or not yet taken).

    This diff is intentionally kept separate from ``run.reviewed_code`` (the
    git diff): it is passed to the reviewer and the validator but never
    committed, so it does not affect what ends up in the repository.
    """
    if orch._project_path is None or run.artifact_snapshot is None:
        return
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, orch._project_path)


def _role_qui_produit(type_de_ticket: "TicketType") -> AgentRole:
    """Qui tient l'étape « quelqu'un produit le travail », selon le ticket.

    Un ticket `design` appelle une décision d'architecture, pas du code. Le
    reste du pipeline est inchangé : le même reviewer relit, le même commit
    conclut.
    """
    if type_de_ticket is TicketType.design:
        return AgentRole.architect
    return AgentRole.codeur
