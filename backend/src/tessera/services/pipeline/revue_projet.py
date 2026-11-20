"""Revue de projet : un run `design` qui n'écrit que `tickets/**` et `memory/**` — ticket-864, ADR-080.

Ce module tient ce qui se décide sans agent : la fiche de synthèse « Revue de
<projet> » et son brief, le plafond de dépense, et les deux bornes que le diff
du run doit respecter — aucun fichier hors `tickets/` et `memory/`, au plus dix
tickets créés. La route lance le run, le pipeline arrête le tour (`pipeline_revue`).
"""
import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.noyau import numerotation

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator

MODE_REVUE = "revue"
ROLE_REVUE = "architect"
MAX_TICKETS_CREES = 10
MAX_SIGNALEMENTS = 5
PLAFOND_REVUE_USD = 3.0
DOSSIERS_PERMIS: tuple[str, ...] = ("tickets/", "memory/")

CODE_HORS_PERIMETRE = "review_outside_scope"
CODE_TROP_DE_TICKETS = "review_too_many_tickets"

_ENTETE = re.compile(r"^diff --git a/(?P<ancien>.+?) b/(?P<nouveau>.+)$")
_NUMERO_TICKET = re.compile(r"^ticket-(\d+)")


def titre_de_revue(projet: str) -> str:
    """The title of the summary ticket of a review of `projet`."""
    return f"Revue de {projet}"


def corps_de_revue(projet: str) -> str:
    """The brief of the review: read the project, propose, implement nothing."""
    return (
        "## Objectif\n\n"
        f"Relire le projet `{projet}` et proposer des changements, sans rien implémenter.\n\n"
        "## Ce qu'il faut faire\n\n"
        "- Lire le `CLAUDE.md` du projet, ses ADR (`memory/decisions.md`), ses contraintes "
        "et ses tickets ouverts avant de proposer quoi que ce soit.\n"
        "- Lire le code là où un écart avec ces textes se soupçonne.\n"
        f"- Écrire au plus {MAX_TICKETS_CREES} tickets (`tickets/todo/`), chacun avec des "
        "critères d'acceptation vérifiables, sans doublon avec un ticket ouvert.\n"
        "- Un défaut de Tessera lui-même (garde trop stricte, outil cassé) se rapporte avec "
        f"l'outil `signaler`, {MAX_SIGNALEMENTS} fois au plus ; ce n'est pas un ticket du projet.\n\n"
        "## Ce que ça ne fait pas\n\n"
        "Aucun fichier n'est écrit hors de `tickets/` et de `memory/`. Aucun des tickets "
        "proposés n'est implémenté.\n\n"
        "## Critères d'acceptation\n\n"
        "- [ ] Les tickets proposés sont écrits sous `tickets/todo/`, dix au plus\n"
        "- [ ] Aucun fichier n'est modifié hors de `tickets/` et de `memory/`\n"
    )


def plafond_de_revue(run_max_budget_usd: float) -> float:
    """The spending cap of a review: the smaller of 3 $ and the run cap (ADR-075).

    Un plafond de run à zéro veut dire « sans plafond » (`.env` seulement) : la
    revue garde alors ses 3 $.
    """
    if run_max_budget_usd <= 0:
        return PLAFOND_REVUE_USD
    return min(PLAFOND_REVUE_USD, run_max_budget_usd)


def ticket_de_revue(projet: str, numero: int) -> Ticket:
    """The `design` summary ticket, entrusted to the architect."""
    return Ticket(
        id=f"ticket-{numero:03d}",
        title=titre_de_revue(projet),
        type=TicketType.design,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent=ROLE_REVUE,
        created=datetime.now(UTC).strftime("%Y-%m-%d"),
        body=corps_de_revue(projet),
        project_id=projet,
    )


async def reserver_numero(project_path: Path, base: str) -> int:
    """Reserve the number of the summary ticket: it is taken, used or not (ticket-848)."""
    return await asyncio.to_thread(
        numerotation.reserver, project_path, "ticket", base, settings.ide_state_dir
    )


async def ouvrir_revue(orch: "Orchestrator", fiche: Ticket, plafond_usd: float) -> None:
    """Make `orch` a review run: its summary ticket written, its own spending ceiling.

    La fiche s'écrit dans la racine d'écriture du run — le worktree s'il y en a un :
    elle n'existerait pas sur `origin/<base>`. Le plafond est celui du run entier.
    """
    await orch._ticket_svc.create_ticket(fiche)
    orch._run_max_budget_usd = plafond_usd


@dataclass(frozen=True)
class FichierDuDiff:
    """A file the diff touches: its paths and whether the run created it."""

    chemins: tuple[str, ...]
    cree: bool


def fichiers_du_diff(diff: str) -> list[FichierDuDiff]:
    """The files of a unified git diff, in order, with the ones it creates."""
    fichiers: list[FichierDuDiff] = []
    for ligne in diff.splitlines():
        entete = _ENTETE.match(ligne)
        if entete:
            chemins = tuple(dict.fromkeys((entete.group("ancien"), entete.group("nouveau"))))
            fichiers.append(FichierDuDiff(chemins, cree=False))
        elif ligne.startswith("new file mode") and fichiers:
            fichiers[-1] = FichierDuDiff(fichiers[-1].chemins, cree=True)
    return fichiers


def _relatif(chemin: str, prefixe: str) -> str:
    return chemin.removeprefix(prefixe) if prefixe else chemin


def _dans_le_perimetre(chemin: str, prefixe: str) -> bool:
    return _relatif(chemin, prefixe).startswith(DOSSIERS_PERMIS)


def fichiers_hors_perimetre(diff: str, prefixe: str = "") -> list[str]:
    """The paths the diff touches outside `tickets/` and `memory/`.

    `prefixe` est le dossier du projet dans le dépôt (`git rev-parse --show-prefix`),
    vide quand le projet est la racine du dépôt.
    """
    hors: list[str] = []
    for fichier in fichiers_du_diff(diff):
        hors += [c for c in fichier.chemins if not _dans_le_perimetre(c, prefixe) and c not in hors]
    return hors


def _numero(chemin: str) -> int | None:
    correspondance = _NUMERO_TICKET.match(chemin.rsplit("/", 1)[-1])
    return int(correspondance.group(1)) if correspondance else None


def tickets_crees(diff: str, ticket_de_synthese: str, prefixe: str = "") -> set[int]:
    """The numbers of the tickets the run created, its own summary ticket aside.

    La fiche de synthèse change de dossier au fil du run : elle apparaît comme un
    fichier créé de plus, qui n'est pas une proposition.
    """
    propre = _numero(ticket_de_synthese)
    crees: set[int] = set()
    for fichier in fichiers_du_diff(diff):
        chemin = _relatif(fichier.chemins[-1], prefixe)
        numero = _numero(chemin)
        if not fichier.cree or not chemin.startswith("tickets/"):
            continue
        if numero is not None and numero != propre:
            crees.add(numero)
    return crees


def raison_de_revue(
    diff: str, ticket_de_synthese: str, prefixe: str = ""
) -> tuple[str, str] | None:
    """(code, reason) when the diff breaks a bound of the review, else None."""
    hors = fichiers_hors_perimetre(diff, prefixe)
    if hors:
        return CODE_HORS_PERIMETRE, (
            "revue de projet : un fichier hors de tickets/ et de memory/ est modifié — "
            "la revue propose, elle n'écrit rien d'autre : " + " ; ".join(hors)
        )
    crees = tickets_crees(diff, ticket_de_synthese, prefixe)
    if len(crees) > MAX_TICKETS_CREES:
        return CODE_TROP_DE_TICKETS, (
            f"revue de projet : {len(crees)} tickets créés, {MAX_TICKETS_CREES} au plus — "
            "rien n'est livré"
        )
    return None
