"""Arrêt à la fin du tour du codeur sur une règle écrite hors `## Proposées` — ticket-493.

Un run qui modifie `contraintes.md` ailleurs que sous `## Proposées` changerait
la consigne de tous les agents suivants sans relecture humaine. Il s'arrête en
`blocked` avec son commit, comme tout run non approuvé (ADR-018, ADR-037) ; la
raison part dans le journal et dans l'événement d'erreur.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.gardes.contraintes_touchees import lignes_hors_proposees
from tessera.services.gardes.lecons_touchees import lignes_de_lecons
from tessera.services.noyau.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline.pipeline_journal import CODE_JOURNAL_MODIFIE, raison_journal_modifie
from tessera.services.pipeline.pipeline_journal import RESUME as RESUME_JOURNAL
from tessera.services.pipeline.pipeline_outcomes import commit_ou_bloquer
from tessera.services.pipeline.pipeline_revue import RESUME as RESUME_REVUE
from tessera.services.pipeline.pipeline_revue import raison_revue_hors_perimetre
from tessera.services.pipeline.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline.pipeline_text import _unapproved_commit_message

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator


def raison_contraintes_hors_proposees(orch: "Orchestrator", run: PipelineRun) -> str | None:
    """Why the run must stop, or None when contraintes.md is untouched or only proposed to."""
    chemin = orch._project_path
    if chemin is None:
        return None
    racines = [chemin.resolve(), *chemin.resolve().parents]
    hors = lignes_hors_proposees(run.reviewed_code, racines)
    if not hors:
        return None
    return (
        "contraintes.md modifié hors de « ## Proposées » — une règle nouvelle "
        "s'y écrit, avec son ADR, et un humain la déplace : " + " ; ".join(hors)
    )


async def arret_contraintes_hors_proposees(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run after the coder's turn when it wrote a rule outside the proposals.

    Le même point d'arrêt garde `memory/lecons.md` (ticket-804) : le contrôle
    des leçons passe juste après, sur le même diff, puis celui du journal du
    superviseur (ticket-853), puis celui du périmètre d'une revue de projet
    (ticket-864).
    """
    raison = raison_contraintes_hors_proposees(orch, run)
    if raison is None:
        arret = await arret_lecons_modifiees(orch, run)
        if arret is None:
            arret = await arret_journal_modifie(orch, run)
        return arret if arret is not None else await arret_revue_hors_perimetre(orch, run)
    return await bloquer(
        orch, run, "constraints_outside_proposed", raison,
        "contraintes.md changed outside the Proposées section",
    )


def raison_lecons_modifiees(run: PipelineRun) -> str | None:
    """Why the run must stop, or None when the diff leaves lecons.md alone."""
    touchees = lignes_de_lecons(run.reviewed_code)
    if not touchees:
        return None
    return (
        "lecons.md modifié par un agent — seul le service écrit ce fichier ; "
        "un humain déplace une leçon sous « ## En vigueur » : " + " ; ".join(touchees)
    )


async def arret_lecons_modifiees(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run after the coder's turn when its diff touches lecons.md.

    La leçon que le service propose s'écrit **après** ce contrôle, à
    l'approbation (ticket-803) : elle n'est jamais dans le diff relu ici.
    """
    raison = raison_lecons_modifiees(run)
    if raison is None:
        return None
    return await bloquer(
        orch, run, "lessons_file_modified", raison, "lecons.md changed by an agent"
    )


async def arret_journal_modifie(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block the run when its diff touches the supervision journal, unless it is a supervision run."""
    raison = raison_journal_modifie(run)
    if raison is None:
        return None
    return await bloquer(orch, run, CODE_JOURNAL_MODIFIE, raison, RESUME_JOURNAL)


async def arret_revue_hors_perimetre(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult | None:
    """Block a review run whose diff leaves `tickets/` and `memory/`, or creates too many tickets."""
    raison = await raison_revue_hors_perimetre(orch, run)
    if raison is None:
        return None
    return await bloquer(orch, run, raison[0], raison[1], RESUME_REVUE)


async def bloquer(
    orch: "Orchestrator", run: PipelineRun, code: str, raison: str, resume: str
) -> PipelineResult:
    """End the run `blocked`, with its unapproved commit, naming `raison`."""
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason=code, detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, resume)
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason=code,
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret or raison,
    )
