"""The watcher updates a conflicting PR, once, and follows its new head — ticket-733.

`mettre_a_jour_branche` (ticket-732) fait le geste ; ce module décide de ce qui
l'entoure : relire la tête juste avant, borner la durée, faire suivre
l'approbation (`pushed_sha`) et reconstruire le contrôle de tête. Il ne résout
rien lui-même : aucun agent n'intervient (ADR-069, ADR-033).

Tout refus se rend en ligne d'arrêt, jamais en exception : le watcher la
reporte telle quelle sur le ticket (ADR-039).
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from pathlib import Path

from tessera.config import settings
from tessera.services.controle_tete import ControleTete, decrire_exception, verifier_tete
from tessera.services.github_service import PrOuverte
from tessera.services.mise_a_jour_branche import MiseAJour, mettre_a_jour_branche
from tessera.services.sha_approbation import noter_poussee_du_ticket

#: Ce que le watcher appelle pour mettre à jour une PR : l'argument est la tête
#: attendue (`pushed_sha`).
MiseAJourPr = Callable[[str], Awaitable[MiseAJour]]

#: Borne propre de la mise à jour (fetch, merge, tests, push) : elle s'ajoute
#: à celle de la phase 2, qui s'applique à chaque passage.
DELAI_MISE_A_JOUR_S = 300.0

_PREFIXE_REFUS = "mise à jour refusée : "


@dataclass(frozen=True)
class SuiteMiseAJour:
    """What follows an update: the head to watch from now on, or why it stops."""

    arret: str | None = None
    controle: ControleTete | None = None


class TeteAttendue:
    """The head a PR's merge is bound to; it follows the updates of the watcher."""

    def __init__(self, sha: str | None) -> None:
        self.sha = sha


def mise_a_jour_de(
    *,
    depot: Path,
    base: str,
    pr_number: int,
    prs_ouvertes: Callable[[], Awaitable[list[PrOuverte]]],
    tete: TeteAttendue,
) -> MiseAJourPr:
    """The update of one PR: its branch is read on GitHub, the base comes from the policy.

    Quand la mise à jour pousse, `tete` prend la nouvelle tête : la phase 2 qui
    repart la lit pour lier le merge (ticket-492).
    """

    async def mise_a_jour(tete_attendue: str) -> MiseAJour:
        branche = await _branche_de(prs_ouvertes, pr_number)
        if branche is None:
            return MiseAJour(
                sha=None,
                arret=f"la branche de la PR #{pr_number} est introuvable chez GitHub.",
                base=base,
            )
        resultat = await mettre_a_jour_branche(depot, branche, base, tete_attendue)
        if resultat.sha is not None:
            tete.sha = resultat.sha
        return resultat

    return mise_a_jour


async def _branche_de(
    prs_ouvertes: Callable[[], Awaitable[list[PrOuverte]]], pr_number: int
) -> str | None:
    """The head branch of an open PR; None when it cannot be found."""
    try:
        for pr in await prs_ouvertes():
            if pr.number == pr_number and pr.branche:
                return pr.branche
    except Exception:  # noqa: BLE001 — pas de branche, pas de mise à jour
        return None
    return None


async def mettre_a_jour_la_pr(
    *,
    project_id: str,
    ticket_id: str,
    pr_number: int,
    controle: ControleTete,
    mise_a_jour: MiseAJourPr,
    journaliser: Callable[[str], None],
    delai_s: float = DELAI_MISE_A_JOUR_S,
) -> SuiteMiseAJour:
    """Update the PR, note the new head, and rebuild the head check around it.

    Dans l'ordre : la tête est relue, la mise à jour tourne sous sa borne, la
    tête poussée devient `pushed_sha` — avant toute attente de CI —, le contrôle
    est reconstruit sur elle. Chaque échec rend un arrêt ; rien n'est mergé.
    """
    # La tête a été contrôlée avant la phase 2 ; elle l'est de nouveau ici : un
    # push étranger pendant l'attente de la CI ne se fusionne pas.
    arret_tete = await verifier_tete(controle, pr_number)
    if arret_tete is not None or controle.pushed_sha is None:
        return SuiteMiseAJour(arret=arret_tete or "commit poussé inconnu")
    ancienne = controle.pushed_sha
    resultat = await _lancer(mise_a_jour, ancienne, delai_s)
    if resultat.sha is None:
        return SuiteMiseAJour(arret=_PREFIXE_REFUS + (resultat.arret or "aucune cause donnée"))
    try:
        await noter_poussee_du_ticket(settings.ide_db_path, project_id, ticket_id, resultat.sha)
    except Exception as exc:  # noqa: BLE001 — échoue fermé : une tête non notée ne se merge pas
        return SuiteMiseAJour(
            arret=(
                f"nouvelle tête {resultat.sha[:7]} non enregistrée "
                f"({decrire_exception(exc)}) : la PR #{pr_number} reste ouverte, "
                "rien n'est mergé."
            )
        )
    journaliser(
        f"PR #{pr_number} mise à jour avec {resultat.base or 'sa base'} : "
        f"{ancienne[:7]} → {resultat.sha[:7]}"
    )
    return SuiteMiseAJour(controle=replace(controle, pushed_sha=resultat.sha))


async def _lancer(mise_a_jour: MiseAJourPr, tete: str, delai_s: float) -> MiseAJour:
    """Run the update under its bound; a failure of any kind is a refusal, not a raise."""
    try:
        return await asyncio.wait_for(mise_a_jour(tete), timeout=delai_s)
    except asyncio.TimeoutError:
        return MiseAJour(sha=None, arret=f"délai dépassé ({delai_s:g} s)")
    except Exception as exc:  # noqa: BLE001 — le watcher ne doit pas voir une exception ici
        return MiseAJour(sha=None, arret=decrire_exception(exc))
