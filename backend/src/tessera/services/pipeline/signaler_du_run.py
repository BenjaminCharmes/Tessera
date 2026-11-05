"""The context of the `signaler` tool for one run — ticket-863, ADR-080.

Split from `pipeline_production`: the project, the ticket and the
confidentiality come from the run, never from an agent's arguments.
"""
from typing import TYPE_CHECKING

from tessera.models.agent import AgentRole
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.signalements_en_attente import mettre_en_attente
from tessera.services.projets.manifeste import lire_chaine
from tessera.services.providers.signaler import ContexteSignal

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator


def signaler_for(orch: "Orchestrator", run: PipelineRun) -> ContexteSignal | None:
    """Le contexte de l'outil `signaler` pour ce run, ou rien (ticket-863).

    La confidentialité est celle du `agents.json` du projet. Sans dossier de
    projet (test, appel programmatique), il n'y a rien à lire : pas d'outil.
    Le rôle est posé par `AgentRunner.run`, qui connaît celui de l'appel.
    """
    if orch._project_path is None:
        return None
    return ContexteSignal(
        projet=run.project_id,
        ticket=run.ticket_id,
        role=AgentRole.codeur.value,
        confidentialite=lire_chaine(orch._project_path, "confidentiality") or "personal",
        deposer=mettre_en_attente,
        compteur=run.compteur_signaux,
    )
