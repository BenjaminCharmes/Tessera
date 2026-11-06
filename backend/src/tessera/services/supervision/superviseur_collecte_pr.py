"""The delivered runs a PR can be handed back for — ticket-867, ADR-080.

A candidate `reconfier_pr` exists only for a run that is approved, whose PR is
open, whose head on GitHub is still the `pushed_sha` it left with, and whose
delivery stopped on an infrastructure cut. A moved head offers nothing: it is no
longer the commit that was read (ADR-039), and the watcher must never merge it.
The action calls no model; `SuperviseurPr.reconfier` re-checks everything before
it gives the PR to `CIWatcher`, which stays the only one to merge.

The runs come from the usage base (one row per ticket, newest first); the open
PR numbers and their heads come from GitHub. A run with no `pushed_sha` — a
conflict resolution, ADR-033 — is never read here.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.noyau.pipeline_events import EventCallback
from tessera.services.supervision.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.supervision.superviseur_actions import Action, Decision
from tessera.services.supervision.superviseur_boucle_ports import Candidat
from tessera.services.supervision.superviseur_pr import RunLivre, SuperviseurPr, reperer
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class RunPousse:
    """The latest run of a ticket that pushed a commit: what its delivery left."""

    ticket_id: str
    approuve: bool
    arret: str | None
    pushed_sha: str


@dataclass(frozen=True)
class SourcesPr:
    """What the collector reads: the pushed runs, the open PRs by ticket, a PR's head."""

    runs: Callable[[], Awaitable[list[RunPousse]]]
    prs_ouvertes: Callable[[], Awaitable[dict[str, int]]]
    lire_tete: Callable[[int], Awaitable[str | None]]


async def runs_pousses(db_path: Path | str, project_id: str) -> list[RunPousse]:
    """The newest pushed run of each ticket of `project_id`, from the usage base."""
    requete = (
        "SELECT ticket_id, approved, arret, pushed_sha FROM pipeline_runs"
        " WHERE project_id = ? AND pushed_sha IS NOT NULL ORDER BY started_at DESC, rowid DESC"
    )
    async with ouvrir_en_lecture(db_path) as db, db.execute(requete, (project_id,)) as curseur:
        lignes = await curseur.fetchall()
    derniers: dict[str, RunPousse] = {}
    for ticket_id, approuve, arret, pousse in lignes:
        derniers.setdefault(
            str(ticket_id), RunPousse(str(ticket_id), bool(approuve), None if arret is None else str(arret), str(pousse))
        )
    return list(derniers.values())


def _livre(project_id: str, run: RunPousse, pr: int) -> RunLivre:
    livraison = Livraison(arret=run.arret, pr_number=pr, pushed_sha=run.pushed_sha, pr_orpheline=True)
    return RunLivre(project_id, run.ticket_id, run.approuve, livraison)


async def _tete_inchangee(sources: SourcesPr, run: RunPousse, pr: int) -> bool:
    """Whether the PR's head is still `pushed_sha`; an unreadable head reads as moved."""
    try:
        return await sources.lire_tete(pr) == run.pushed_sha
    except Exception as exc:  # noqa: BLE001 — une tête illisible n'offre rien
        _logger.warning("superviseur_pr_tete_illisible", extra={"pr": pr, "erreur": decrire_exception(exc)})
        return False


def _reconfier(superviseur: Callable[[], SuperviseurPr], livre: RunLivre, on_event: EventCallback) -> Callable[[], Awaitable[list[Decision]]]:
    """The execution of one hand-back, with its run bound to it."""

    async def executer() -> list[Decision]:
        return [await superviseur().reconfier(livre, on_event)]

    return executer


async def candidats_pr(
    project_id: str, sources: SourcesPr, superviseur: Callable[[], SuperviseurPr], on_event: EventCallback
) -> list[Candidat]:
    """One `reconfier_pr` candidate per approved run whose open PR still has its pushed head.

    `superviseur` is only called when a candidate is executed, so a project with
    nothing to hand back builds no GitHub client.
    """
    runs = await sources.runs()
    if not runs:
        return []
    prs = await sources.prs_ouvertes()
    candidats: list[Candidat] = []
    for run in runs:
        pr = prs.get(run.ticket_id)
        if pr is None:
            continue
        livre = _livre(project_id, run, pr)
        if not reperer([livre]) or not await _tete_inchangee(sources, run, pr):
            continue
        cible = f"{run.ticket_id} PR #{pr}"
        candidats.append(
            Candidat(project_id, Action.RECONFIER_PR, cible, run.pushed_sha, True, _reconfier(superviseur, livre, on_event))
        )
    return candidats
