"""Reprend la surveillance des PR confiées au CIWatcher avant un arrêt — ticket-510.

La phase 2 de livraison (attente de CI, merge) tourne en mémoire dans
`CIWatcher` (ADR-051) : un redémarrage du backend la coupe, et rien ne la
relance. Au démarrage, pour chaque projet en autonomie `merge`, ce module
retrouve les tickets `in-review` qui portent un `pr_number` et relit l'état
de leur PR :

- ouverte : confiée de nouveau à `CIWatcher.surveiller`, avec les mêmes règles
  qu'à la première livraison (CI verte, `merge_without_ci`, tête inchangée) ;
- mergée : le ticket passe en `done` ;
- fermée sans merge : rien, une ligne le dit dans `memory/pipeline-log.md`.

Depuis le ticket-516, les PR **ouvertes** du dépôt vers la base du projet, dont
la branche de tête suit `ticket-NNN-…`, sont reprises elles aussi : après la
phase 1, la fiche reste `todo` sur la base jusqu'au merge, et l'arbre local ne
la montre donc pas `in-review`. Une PR trouvée par les deux sources n'est
confiée qu'une fois. Une PR ouverte à la main sur une telle branche est mergée
à CI verte, comme les autres : c'est le comportement attendu en autonomie `merge`.

Une PR dont aucun commit poussé n'est noté n'est pas reprise : c'est celle
d'une résolution de conflit, qui ne se merge jamais seule (ADR-033), ou d'une
livraison interrompue. Toute erreur est journalisée et n'empêche jamais le
démarrage du backend.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.ci_watcher import EtatPr, decrire_exception
from tessera.services.github_service import PrOuverte
from tessera.services.pipeline_events import EventCallback
from tessera.services.politique_run import PolitiqueRun
from tessera.services.reprise_outils import ecrire_log as _ecrire_log
from tessera.services.reprise_outils import prs_a_reprendre
from tessera.services.sha_approbation import sha_pousse_du_ticket
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Confie une PR au watcher : (projet, ticket, numéro de PR, callback d'événements).
Surveiller = Callable[[str, str, int, EventCallback], Awaitable[None]]

#: Liste les PR ouvertes du dépôt vers la base du projet (ticket-516).
PrsOuvertes = Callable[[], Awaitable[list[PrOuverte]]]


@dataclass(frozen=True)
class SurveillanceProjet:
    """Ce dont la reprise a besoin pour un projet : lire une PR, la surveiller.

    `prs_ouvertes` et `base_branch` ouvrent la source GitHub (ticket-516) ;
    sans eux, seules les fiches `in-review` locales sont reprises.
    """

    etat_pr: EtatPr
    surveiller: Surveiller
    prs_ouvertes: PrsOuvertes | None = None
    base_branch: str | None = None


#: Construit la surveillance d'un projet à partir de sa politique de run.
FabriqueSurveillance = Callable[[str, PolitiqueRun], SurveillanceProjet]


async def _reprendre_ouverte(
    projet: Path,
    ticket_id: str,
    pr: int,
    surveillance: SurveillanceProjet,
    db_path: Path | str,
    on_event: EventCallback,
) -> None:
    """Hand an open PR back to the watcher, unless its pushed commit is unknown."""
    if await sha_pousse_du_ticket(db_path, projet.name, ticket_id) is None:
        _ecrire_log(
            projet,
            f"[{projet.name}] {ticket_id} PR #{pr} non reprise : "
            "aucun commit poussé noté (résolution de conflit ou livraison interrompue)",
        )
        return
    await surveillance.surveiller(projet.name, ticket_id, pr, on_event)
    _ecrire_log(
        projet,
        f"[{projet.name}] {ticket_id} PR #{pr} reprise par le CIWatcher après redémarrage",
    )


async def _reprendre_ticket(
    projet: Path,
    ticket: Ticket,
    pr: int,
    surveillance: SurveillanceProjet,
    tickets: TicketService,
    db_path: Path | str,
    on_event: EventCallback,
) -> None:
    """Re-read the PR of one ticket and act on its state."""
    etat = await surveillance.etat_pr(pr)
    if etat == "open":
        await _reprendre_ouverte(projet, ticket.id, pr, surveillance, db_path, on_event)
    elif etat == "merged":
        await tickets.update_status(ticket.id, TicketStatus.done)
        _ecrire_log(
            projet,
            f"[{projet.name}] {ticket.id} PR #{pr} mergée avant le redémarrage : "
            "ticket rangé en done",
        )
    elif etat == "closed":
        _ecrire_log(
            projet,
            f"[{projet.name}] {ticket.id} PR #{pr} fermée sans merge : non reprise",
        )
    else:
        _logger.warning(
            "reprise_ci_etat_inconnu",
            extra={"project": projet.name, "ticket": ticket.id, "pr": pr, "etat": etat},
        )


async def _reprendre_projet(
    projet: Path,
    db_path: Path | str,
    fabrique: FabriqueSurveillance,
    on_event: EventCallback,
) -> None:
    """Resume the watch of every in-review PR of one project in `merge` autonomy."""
    politique = PolitiqueRun.lire(projet)
    if politique.autonomy is not NiveauAutonomie.merge:
        return
    tickets = TicketService(projet, projet.name)
    surveillance = fabrique(projet.name, politique)
    vues: set[int] = set()
    for ticket in await tickets.list_tickets(TicketStatus.in_review):
        pr = ticket.pr_number
        if pr is None:
            continue
        vues.add(pr)
        await _proteger(projet, ticket.id, _reprendre_ticket(
            projet, ticket, pr, surveillance, tickets, db_path, on_event
        ))
    for ticket_id, pr in await _prs_de_github(projet, surveillance):
        if pr in vues:
            continue
        vues.add(pr)
        await _proteger(projet, ticket_id, _reprendre_ouverte(
            projet, ticket_id, pr, surveillance, db_path, on_event
        ))


async def _proteger(projet: Path, ticket_id: str, travail: Awaitable[None]) -> None:
    """Await one PR's resume; a failure is logged and never stops the others."""
    try:
        await travail
    except Exception as exc:  # noqa: BLE001 — une PR illisible n'arrête pas les autres
        _logger.warning(
            "reprise_ci_ticket_echec",
            extra={
                "project": projet.name,
                "ticket": ticket_id,
                "erreur": decrire_exception(exc),
            },
        )


async def _prs_de_github(
    projet: Path, surveillance: SurveillanceProjet
) -> list[tuple[str, int]]:
    """The open pipeline PRs found on GitHub; empty, and logged, when it fails."""
    if surveillance.prs_ouvertes is None:
        return []
    try:
        prs = await surveillance.prs_ouvertes()
    except Exception as exc:  # noqa: BLE001 — la source locale a déjà été reprise
        _logger.warning(
            "reprise_ci_liste_github_echec",
            extra={"project": projet.name, "erreur": decrire_exception(exc)},
        )
        return []
    return prs_a_reprendre(prs, surveillance.base_branch)


async def reprendre_surveillances(
    workspace_dir: Path,
    db_path: Path | str,
    fabrique: FabriqueSurveillance,
    on_event: EventCallback,
) -> None:
    """Resume the CI watch of the PR handed over before the last stop.

    Called from the lifespan after the orphan runs are settled. Never raises:
    an error on one project is logged and the next project is still handled.
    """
    if not workspace_dir.is_dir():
        return
    for dossier in sorted(workspace_dir.iterdir()):
        if not dossier.is_dir() or dossier.name.startswith("."):
            continue
        try:
            await _reprendre_projet(dossier, db_path, fabrique, on_event)
        except Exception as exc:  # noqa: BLE001 — jamais d'échec de démarrage
            _logger.warning(
                "reprise_ci_projet_echec",
                extra={"project": dossier.name, "erreur": decrire_exception(exc)},
            )
