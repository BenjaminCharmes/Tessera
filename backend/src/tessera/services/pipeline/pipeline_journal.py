"""Le journal du superviseur, gardé au tour du codeur — ticket-853, ADR-080.

`memory/supervision.md` n'est écrit que par le service. Un diff de run qui le
touche met le run en `blocked` (l'arrêt est celui de `pipeline_contraintes`).
Seule exception : une intervention du superviseur, qui écrit une ligne par
action ; elle se reconnaît à son **type de run**, jamais au chemin du fichier.
"""
from tessera.services.gardes.journal_touche import lignes_du_journal
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.run_registry import RUN_REGISTRY

MODE_SUPERVISION = "supervision"
CODE_JOURNAL_MODIFIE = "supervision_journal_modified"
RESUME = "supervision journal changed by a run"


def projet_en_supervision(project_id: str) -> bool:
    """True when the run that holds `project_id` is a supervision intervention."""
    run = RUN_REGISTRY.run_du_projet(project_id)
    return run is not None and run.mode == MODE_SUPERVISION


def raison_journal_modifie(run: PipelineRun) -> str | None:
    """Why the run must stop, or None when it leaves the journal alone or is a supervision run."""
    if projet_en_supervision(run.project_id):
        return None
    touchees = lignes_du_journal(run.reviewed_code)
    if not touchees:
        return None
    return (
        "supervision.md modifié par un run — seul le service écrit ce journal : "
        + " ; ".join(touchees)
    )
