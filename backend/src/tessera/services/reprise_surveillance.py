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

Une PR dont aucun commit poussé n'est noté n'est pas reprise : c'est celle
d'une résolution de conflit, qui ne se merge jamais seule (ADR-033), ou d'une
livraison interrompue. Toute erreur est journalisée et n'empêche jamais le
démarrage du backend.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.ci_watcher import EtatPr, decrire_exception
from tessera.services.pipeline_events import EventCallback
from tessera.services.politique_run import PolitiqueRun
from tessera.services.sha_approbation import sha_pousse_du_ticket
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Confie une PR au watcher : (projet, ticket, numéro de PR, callback d'événements).
Surveiller = Callable[[str, str, int, EventCallback], Awaitable[None]]


@dataclass(frozen=True)
class SurveillanceProjet:
    """Ce dont la reprise a besoin pour un projet : lire une PR, la surveiller."""

    etat_pr: EtatPr
    surveiller: Surveiller


#: Construit la surveillance d'un projet à partir de sa politique de run.
FabriqueSurveillance = Callable[[str, PolitiqueRun], SurveillanceProjet]


def _ecrire_log(projet: Path, texte: str) -> None:
    """Append one timestamped line to the project's pipeline log; never raises."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    chemin = projet / "memory" / "pipeline-log.md"
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("a", encoding="utf-8") as f:
            f.write(f"- {ts} — {texte}\n")
    except OSError as exc:
        _logger.warning("reprise_ci_log_echec", extra={"erreur": str(exc)})


async def _reprendre_ouverte(
    projet: Path,
    ticket: Ticket,
    pr: int,
    surveillance: SurveillanceProjet,
    db_path: Path | str,
    on_event: EventCallback,
) -> None:
    """Hand an open PR back to the watcher, unless its pushed commit is unknown."""
    if await sha_pousse_du_ticket(db_path, projet.name, ticket.id) is None:
        _ecrire_log(
            projet,
            f"[{projet.name}] {ticket.id} PR #{pr} non reprise : "
            "aucun commit poussé noté (résolution de conflit ou livraison interrompue)",
        )
        return
    await surveillance.surveiller(projet.name, ticket.id, pr, on_event)
    _ecrire_log(
        projet,
        f"[{projet.name}] {ticket.id} PR #{pr} reprise par le CIWatcher après redémarrage",
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
        await _reprendre_ouverte(projet, ticket, pr, surveillance, db_path, on_event)
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
    candidats = [
        t for t in await tickets.list_tickets(TicketStatus.in_review)
        if t.pr_number is not None
    ]
    if not candidats:
        return
    surveillance = fabrique(projet.name, politique)
    for ticket in candidats:
        pr = ticket.pr_number
        if pr is None:
            continue
        try:
            await _reprendre_ticket(
                projet, ticket, pr, surveillance, tickets, db_path, on_event
            )
        except Exception as exc:  # noqa: BLE001 — une PR illisible n'arrête pas les autres
            _logger.warning(
                "reprise_ci_ticket_echec",
                extra={
                    "project": projet.name,
                    "ticket": ticket.id,
                    "erreur": decrire_exception(exc),
                },
            )


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
