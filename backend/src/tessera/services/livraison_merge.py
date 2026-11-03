"""Le merge de la livraison, et ce qu'on en conclut quand le réseau lâche — ticket-713.

Un merge qui expire n'est pas un merge qui a échoué : GitHub a pu le faire
avant que la réponse ne se perde. Arrêter la livraison sur ce doute laisse
une PR mergée que l'IDE croit ouverte. On relit donc la PR avant de conclure.
"""
from dataclasses import dataclass
from typing import Protocol

import httpx

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class _Relecture(Protocol):
    async def pr_state(self, pr_number: int) -> str: ...


class _Fusion(_Relecture, Protocol):
    async def tete_pr(self, pr_number: int) -> str | None: ...
    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool: ...


@dataclass(frozen=True)
class IssueMerge:
    """What the merge attempt came to.

    `merged` is the verdict; `confirme_apres_reseau` is True when it was
    established by rereading the PR after a network error; `erreur_reseau`
    names that error when the merge ended without a verdict.
    """

    merged: bool
    confirme_apres_reseau: bool = False
    erreur_reseau: str | None = None


async def relire_apres_erreur_reseau(
    relecture: _Relecture, pr_number: int, exc: httpx.TransportError
) -> IssueMerge:
    """Rereads the PR after a network error on the merge call.

    Fails closed (ADR-039): only a PR read as `merged` counts as merged. Any
    other state, or a reread that fails too, keeps the stop.
    """
    nom = type(exc).__name__
    try:
        etat = await relecture.pr_state(pr_number)
    except Exception as relecture_exc:  # noqa: BLE001 — une relecture muette garde l'arrêt
        _logger.warning(
            "merge_relecture_impossible",
            extra={"pr": pr_number, "erreur": type(relecture_exc).__name__},
        )
        return IssueMerge(
            merged=False,
            erreur_reseau=f"{nom}, puis la relecture de la PR a échoué aussi",
        )
    if etat == "merged":
        _logger.info("merge_confirme_apres_erreur_reseau", extra={"pr": pr_number})
        return IssueMerge(merged=True, confirme_apres_reseau=True)
    return IssueMerge(
        merged=False, erreur_reseau=f"{nom}, la PR est lue « {etat} »"
    )


async def tenter_le_merge(
    workflow: _Fusion, pr_number: int, sha_attendu: str | None
) -> IssueMerge:
    """Merges, and rereads the PR when the network gave out (ticket-713).

    A refusal from GitHub (HTTP status) is a verdict, not a doubt: it is
    never reread.
    """
    try:
        if sha_attendu is None:
            merged = await workflow.merge_si_la_ci_est_verte(pr_number)
        else:
            merged = await workflow.merge_si_la_ci_est_verte(
                pr_number, sha_attendu=sha_attendu
            )
    except httpx.TransportError as exc:
        return await relire_apres_erreur_reseau(workflow, pr_number, exc)
    except httpx.HTTPStatusError:
        return IssueMerge(merged=False)
    return IssueMerge(merged=merged)


def arret_de_merge(pr_number: int, issue: IssueMerge) -> str:
    """The stop line of a merge that did not happen."""
    if issue.erreur_reseau is not None:
        return (
            f"Le merge de la PR #{pr_number} a échoué sur une erreur réseau "
            f"({issue.erreur_reseau}). La PR reste ouverte."
        )
    return f"GitHub a refusé le merge de la PR #{pr_number}."


async def tete_a_change(
    workflow: _Fusion, pr_number: int, sha_attendu: str
) -> str | None:
    """The stop line when the PR head is not `sha_attendu`, else None.

    Fails closed (ADR-039): an unreadable head refuses the merge.
    """
    try:
        tete = await workflow.tete_pr(pr_number)
    except Exception as exc:  # noqa: BLE001 — une tête illisible refuse le merge
        _logger.warning("tete_pr_illisible", extra={"erreur": str(exc)})
        tete = None
    if tete == sha_attendu:
        return None
    lue = tete[:7] if tete else "inconnue"
    return (
        f"la tête de la PR #{pr_number} n'est plus le commit poussé : "
        f"{lue} au lieu de {sha_attendu[:7]}. La PR reste ouverte."
    )
