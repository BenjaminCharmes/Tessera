"""Open and close the database record of a pipeline run — ticket-121.

`run_queue`, `run_autonomous` and `/chat/run` called `run_pipeline` without a
`run_id`: no row in `pipeline_runs`, and `AgentRunner` computed each call's
cost without writing it anywhere. The cost breakdown ignored exactly the
modes that cost the most. The orchestrator stays ignorant of SQLite; it is
handed this recorder and asks it to open a run when the caller did not.
"""
from pathlib import Path

from tessera.services.database import create_run, finish_run
from tessera.services.pipeline_events import PipelineResult

#: Le statut écrit en base quand le run n'a pas rendu de résultat : la même
#: valeur que le stream single utilise depuis ticket-079.
_INTERROMPU = "interrupted"


class RunRecorder:
    """Create a `pipeline_runs` row when a run starts, close it when it ends."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = db_path

    async def ouvrir(
        self,
        project_id: str,
        ticket_id: str,
        parent_run_id: str | None = None,
    ) -> str:
        """Insert the run's row and return its id.

        Always ``single``: RunRecorder is called once per ticket inside a
        queue or autonomous run, never for the envelope itself.

        ``parent_run_id`` links this row to the envelope run created by
        ``executer``.  Events are stored on the envelope; this link lets
        ``get_run_events`` filter them by ticket (ticket-280).
        """
        return await create_run(
            self._db_path, project_id, ticket_id,
            mode="single", parent_run_id=parent_run_id,
        )

    async def clore(self, run_id: str, resultat: PipelineResult | None) -> None:
        """Close the row — with the result, or as interrupted when there is none."""
        await finish_run(
            self._db_path,
            run_id,
            resultat.rounds if resultat else 0,
            resultat.approved if resultat else False,
            resultat.final_status.value if resultat else _INTERROMPU,
            resultat.arret if resultat else None,
        )
