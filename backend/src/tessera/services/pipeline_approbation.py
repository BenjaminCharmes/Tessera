"""The commit an approval is bound to — ticket-492.

`finish_approved` records the head of the run's branch; the documentation step,
which the pipeline runs itself between the approval and the delivery, may move
it. Everything here fails soft: an unreadable SHA never undoes an approval, it
leaves the result without one, and the delivery then refuses to go further than
it can prove.
"""
from dataclasses import replace
from typing import TYPE_CHECKING

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.livraison import Livraison
from tessera.services.pipeline_capture import capturer_le_run
from tessera.services.pipeline_documentation import documenter_le_run
from tessera.services.pipeline_events import EventCallback, PipelineResult
from tessera.services.pipeline_run import PipelineRun
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def tete_de_branche(orch: "Orchestrator") -> str | None:
    """The full SHA of the branch head, None when it cannot be read."""
    # getattr : les doubles d'espace de travail des tests n'ont pas cette méthode.
    lire_tete = getattr(orch._git_workspace, "head_sha", None)
    if lire_tete is None:
        return None
    try:
        sha = await lire_tete()
    except GitWorkspaceError as exc:
        _logger.warning("tete_de_branche_illisible", extra={"error": str(exc)})
        return None
    return sha if isinstance(sha, str) else None


async def _noter(orch: "Orchestrator", run_id: str | None, sha: str) -> None:
    if run_id is None:
        return
    # getattr : les doubles d'orchestrateur des tests n'ont pas d'enregistreur.
    recorder = getattr(orch, "_run_recorder", None)
    if recorder is None:
        return
    try:
        await recorder.noter_approbation(run_id, sha)
    except Exception as exc:  # noqa: BLE001 — la base ne défait pas l'approbation
        _logger.warning("approved_sha_non_note", extra={"error": str(exc)})


async def noter_tete_approuvee(orch: "Orchestrator", run: PipelineRun) -> str | None:
    """Read the branch head at approval and record it on the run's row."""
    if run.branch is None:
        return None
    sha = await tete_de_branche(orch)
    if sha is not None:
        await _noter(orch, run.run_id, sha)
    return sha


async def suivre_documentation(
    orch: "Orchestrator", resultat: PipelineResult, avant_doc: str | None
) -> PipelineResult:
    """Carry the approved SHA over the pipeline's own documentation commit.

    The documentation step commits on the run's branch, in-process, while the
    run holds the project. Its commit was not read by the reviewer, but it is
    the pipeline's: the approved SHA follows it, **only** when the branch was
    still on the approved commit just before — a commit made by anyone else
    in the meantime stays visible to the delivery check.
    """
    if resultat.approved_sha is None or avant_doc != resultat.approved_sha:
        return resultat
    apres = await tete_de_branche(orch)
    if apres is None or apres == avant_doc:
        return resultat
    await _noter(orch, resultat.run_id, apres)
    return resultat.model_copy(update={"approved_sha": apres})


async def apres_approbation(
    orch: "Orchestrator",
    resultat: PipelineResult,
    project_id: str,
    on_event: EventCallback,
) -> PipelineResult:
    """Documentation, then captures, between the approval and the delivery."""
    # La documentation part sur la branche du run, avant sa livraison :
    # elle décrit ce que la PR livre, et se relit avec (ticket-198).
    # Exception : les tickets légers (ticket-292) ne déclenchent pas de
    # mise à jour immédiate — le marqueur ne bouge pas, et le prochain
    # ticket normal documente le lot entier, léger compris.
    ticket = await orch._ticket_svc.get_ticket(resultat.ticket_id)
    if ticket is None or not ticket.light:
        avant_doc = await tete_de_branche(orch)
        await documenter_le_run(orch, resultat, on_event)
        # Le commit de documentation est celui du pipeline : l'approbation
        # le suit, sans quoi la livraison le prendrait pour un intrus
        # (ticket-492).
        resultat = await suivre_documentation(orch, resultat, avant_doc)
    # Une fois par run, après l'approbation : jamais à chaque tour (ticket-618).
    relecture = await capturer_le_run(orch, resultat, project_id, on_event)
    if relecture is None:
        return resultat
    return resultat.model_copy(update={"relecture": relecture})


def retenir_pour_relecture(livraison: Livraison, relecture: str | None) -> Livraison:
    """Keep an opened PR from the watcher when a human must read the captures.

    Même mécanisme qu'un conflit résolu (ADR-033) : la PR reste ouverte, le
    ticket reste `done`, la cause est écrite dans `arret`. Sans PR ouverte, il
    n'y a rien à retenir.
    """
    if relecture is None or livraison.pr_number is None:
        return livraison
    motif = (
        f"Contrôle visuel en mode relire : {relecture} ; la PR #{livraison.pr_number} "
        "est ouverte, à relire. Elle ne se merge pas toute seule."
    )
    arret = f"{livraison.arret} ; {motif}" if livraison.arret else motif
    return replace(livraison, arret=arret, pr_orpheline=False)
