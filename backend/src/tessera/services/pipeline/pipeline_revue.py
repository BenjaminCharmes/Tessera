"""Ce qui, à la fin du tour, dit qu'une revue de projet est sortie de son périmètre — ticket-864, ADR-080.

Une revue n'écrit que `tickets/**` et `memory/**`, dix tickets au plus. Ce module
ne fait que juger ; l'arrêt (`blocked`, commit non approuvé) est celui de
`pipeline_contraintes`, au même point que les autres gardes du tour. Un run non
approuvé ne se livre jamais (ADR-030).
"""
import asyncio
from typing import TYPE_CHECKING

from tessera.services.noyau.numerotation import GitIllisible, lire_git
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.revue_projet import MODE_REVUE, raison_de_revue
from tessera.services.pipeline.run_registry import RUN_REGISTRY

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator

RESUME = "project review went outside its scope"


def projet_en_revue(project_id: str) -> bool:
    """True when the run that holds `project_id` is a project review."""
    run = RUN_REGISTRY.run_du_projet(project_id)
    return run is not None and run.mode == MODE_REVUE


async def _prefixe_du_projet(orch: "Orchestrator") -> str:
    """The project folder inside its repository, '' when it is the root or unknown."""
    if orch._project_path is None:
        return ""
    try:
        sortie = await asyncio.to_thread(
            lire_git, orch._project_path, "rev-parse", "--show-prefix"
        )
    except GitIllisible:
        return ""
    return sortie.strip()


async def raison_revue_hors_perimetre(
    orch: "Orchestrator", run: PipelineRun
) -> tuple[str, str] | None:
    """(code, reason) when this review run's diff breaks a bound; None otherwise or off review."""
    if not projet_en_revue(run.project_id):
        return None
    return raison_de_revue(run.reviewed_code, run.ticket_id, await _prefixe_du_projet(orch))
