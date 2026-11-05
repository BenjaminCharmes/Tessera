"""Deliver an approved run and say what happened — ticket-792.

Extracted from `Orchestrator._mener_le_run` so the queue can run the very same
path a second time for a ticket whose first delivery stopped without a PR.
"""
from typing import TYPE_CHECKING

from tessera.services import pipeline_fin_de_file as fin_de_file
from tessera.services.livraison.livraison_evenements import evenements_de_livraison
from tessera.services.pipeline_approbation import retenir_pour_relecture
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator


async def livrer_le_resultat(
    orch: "Orchestrator",
    resultat: PipelineResult,
    project_id: str,
    on_event: EventCallback,
) -> PipelineResult:
    """Run delivery phase 1 for an approved result; return it with its Livraison."""
    ticket_id = resultat.ticket_id
    await on_event(
        OrchestratorEvent(type=EventType.LIVRAISON_STARTED, ticket_id=ticket_id)
    )
    # Phase 1 seulement : rebase, push, PR. La phase 2 (attente CI + merge)
    # est confiée à `CIWatcher` en tâche de fond (ADR-051). Le verrou
    # (ADR-038) se libère dès que `run_pipeline` rend la main, c'est-à-dire
    # dès la PR ouverte — pas après le merge.
    assert orch._livrer is not None
    with evenements_de_livraison(on_event, ticket_id):
        livraison = retenir_pour_relecture(await orch._livrer(resultat), resultat.relecture)
    for etape, duree_ms in zip(livraison.etapes, livraison.durees_ms):
        orch._log(f"[{ticket_id}] livraison: {etape} ({duree_ms:.0f}ms)")
    if livraison.arret:
        orch._log(f"[{ticket_id}] livraison: arrêt — {livraison.arret[:100]}")
    if livraison.bloque_le_ticket:
        resultat = await orch._bloquer_branche_modifiee(
            resultat, livraison, project_id, on_event
        )
    # Commit the delivery log lines just written, then return to the base
    # branch so the working tree is clean after a delivered run (ticket-378).
    await fin_de_file.finaliser_livraison(orch, livraison)
    await on_event(
        OrchestratorEvent(
            type=EventType.LIVRAISON_DONE,
            ticket_id=ticket_id,
            data=livraison.__dict__,
        )
    )
    # Si la phase 1 a ouvert une PR sans conflit, confier la phase 2 au
    # CIWatcher : il attend la CI et merge en arrière-plan. `surveiller`
    # retourne immédiatement (crée une tâche asyncio), ce qui permet à
    # `run_pipeline` de rendre la main et au verrou de se libérer avant
    # que `ci_merge_done` soit émis.
    # Une PR dont la phase 1 a levé après l'ouverture (`pr_orpheline`) est
    # surveillée malgré son `arret` ; un conflit résolu ne l'est jamais.
    if (
        livraison.pr_number is not None
        and (livraison.arret is None or livraison.pr_orpheline)
        and orch._surveiller is not None
    ):
        await orch._surveiller(project_id, ticket_id, livraison.pr_number, on_event)
    return resultat.model_copy(update={"livraison": livraison})
