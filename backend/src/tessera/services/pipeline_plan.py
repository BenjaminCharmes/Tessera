"""A read-only planning round before the first coder round — ticket-243.

Sur un gros ticket, une erreur d'approche ne se voyait qu'au reviewer, après
un tour de code complet. Un ticket qui déclare `plan: true` passe d'abord par
un agent qui lit le dépôt sans rien écrire et rend un plan : les étapes, et
pour chaque critère d'acceptation, l'étape qui le couvre. Le plan part ensuite
au codeur, qui le suit, et au reviewer, qui juge l'écart.

Le plan est une aide, comme la carte du dépôt : s'il échoue, le run continue
sans lui.
"""
from typing import TYPE_CHECKING

from tessera.models.agent import AgentConfig, AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)

#: Le rôle sous lequel le plan s'appelle : son prompt, ses outils (lecture).
ROLE_PLAN = "plan"


async def run_plan(orch: "Orchestrator", run: PipelineRun) -> None:
    """Ask for a plan when the ticket declares one; never raises."""
    if not run.ticket.plan:
        return
    # Le fil du ticket montre le plan dans la colonne du codeur : c'est son
    # travail qui commence, et l'UI n'a pas à connaître un rôle de plus.
    await _emettre(run, EventType.AGENT_STARTED, {"round": 0, "phase": ROLE_PLAN})
    try:
        resultat = await orch._runner.run(
            role=ROLE_PLAN,
            ticket=run.ticket,
            project_context=_contexte(orch, run),
            agent_config=_config_du_plan(orch),
            run_id=run.run_id,
        )
    except Exception as exc:  # noqa: BLE001 — une aide ne coûte jamais le run
        _logger.warning("plan_failed", extra={"ticket_id": run.ticket_id, "error": str(exc)})
        orch._log(f"[{run.ticket_id}] plan : échec, le run continue sans ({exc})")
        return
    orch.record_spend(resultat.cost_usd)
    run.plan = resultat.content.strip()
    await _emettre(
        run,
        EventType.AGENT_DONE,
        {
            "round": 0,
            "phase": ROLE_PLAN,
            "content": run.plan,
            "cost_usd": resultat.cost_usd,
            "duration_ms": resultat.duration_ms,
        },
    )
    orch._log(f"[{run.ticket_id}] plan rendu ({resultat.duration_ms}ms)")


def _contexte(orch: "Orchestrator", run: PipelineRun) -> str:
    if not run.carte_du_depot:
        return orch._project_context
    return f"## Fichiers du projet\n\n{run.carte_du_depot}\n\n{orch._project_context}"


def _config_du_plan(orch: "Orchestrator") -> AgentConfig | None:
    """Le modèle du codeur, sous le prompt du plan.

    Le plan prépare le travail du codeur : il lit le même dépôt avec le même
    modèle. `prompt_file` est vidé, sinon celui du codeur serait chargé.
    """
    codeur = orch._config_for(AgentRole.codeur)
    if codeur is None:
        return None
    return codeur.model_copy(update={"role": ROLE_PLAN, "prompt_file": ""})


async def _emettre(run: PipelineRun, type_: EventType, data: dict[str, object]) -> None:
    await run.on_event(
        OrchestratorEvent(type=type_, agent=AgentRole.codeur, ticket_id=run.ticket_id, data=data)
    )
