"""Le merge de la livraison, et ce qu'on en conclut quand le réseau lâche — ticket-713.

Un merge qui expire n'est pas un merge qui a échoué : GitHub a pu le faire
avant que la réponse ne se perde. Arrêter la livraison sur ce doute laisse
une PR mergée que l'IDE croit ouverte. On relit donc la PR avant de conclure.
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from tessera.utils.logger import get_logger
from tessera.utils.statut_douteux import statut_douteux

_logger = get_logger(__name__)

FENETRE_RELECTURE_S = 120.0
INTERVALLE_RELECTURE_S = 15.0


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
    relu_pendant_s: float = 0.0
    refus_ci: str | None = None


async def relire_apres_erreur_reseau(
    relecture: _Relecture,
    pr_number: int,
    nom: str,
    fenetre_s: float | None = None,
    intervalle_s: float | None = None,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> IssueMerge:
    """Rereads the PR during a bounded window after a doubtful merge call.

    A merge GitHub is still performing reads `open`, so one reread is not
    enough. Fails closed (ADR-039): only `merged` counts as merged; `closed`,
    a PR still `open` at the end of the window, or a failed reread stop.
    """
    fenetre = FENETRE_RELECTURE_S if fenetre_s is None else fenetre_s
    intervalle = INTERVALLE_RELECTURE_S if intervalle_s is None else intervalle_s
    ecoule = 0.0
    while True:
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
                relu_pendant_s=ecoule,
            )
        if etat == "merged":
            _logger.info("merge_confirme_apres_erreur_reseau", extra={"pr": pr_number})
            return IssueMerge(merged=True, confirme_apres_reseau=True)
        if etat != "open" or ecoule + intervalle > fenetre:
            return IssueMerge(
                merged=False,
                erreur_reseau=f"{nom}, la PR est lue « {etat} »",
                relu_pendant_s=ecoule,
            )
        await dormir(intervalle)
        ecoule += intervalle


async def tenter_le_merge(
    workflow: _Fusion,
    pr_number: int,
    sha_attendu: str | None,
    fenetre_s: float | None = None,
    intervalle_s: float | None = None,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> IssueMerge:
    """Merges, and rereads the PR when the answer is a doubt (ticket-713).

    A network error, a 5xx or a 405 "Merge already in progress" is a doubt,
    reread over a window; any other refusal from GitHub is a verdict, never
    reread. The merge is never retried.
    """
    try:
        if sha_attendu is None:
            merged = await workflow.merge_si_la_ci_est_verte(pr_number)
        else:
            merged = await workflow.merge_si_la_ci_est_verte(
                pr_number, sha_attendu=sha_attendu
            )
    except httpx.TransportError as exc:
        nom = type(exc).__name__
    except httpx.HTTPStatusError as exc:
        if not statut_douteux(exc):
            return IssueMerge(merged=False)
        nom = f"HTTP {exc.response.status_code}"
    else:
        refus = getattr(workflow, "refus_ci", None)
        if not merged and isinstance(refus, str):
            return IssueMerge(merged=False, refus_ci=refus)
        return IssueMerge(merged=merged)
    return await relire_apres_erreur_reseau(
        workflow, pr_number, nom, fenetre_s, intervalle_s, dormir
    )


def arret_de_merge(pr_number: int, issue: IssueMerge) -> str:
    """The stop line of a merge that did not happen."""
    if issue.erreur_reseau is not None:
        duree = (
            f" La PR a été relue pendant {issue.relu_pendant_s:.0f} s."
            if issue.relu_pendant_s
            else ""
        )
        return (
            f"Le merge de la PR #{pr_number} a échoué sur une erreur réseau "
            f"({issue.erreur_reseau}).{duree} La PR reste ouverte."
        )
    if issue.refus_ci is not None:
        # Tessera n'a pas tenté le merge : GitHub n'a rien refusé.
        return (
            f"Merge de la PR #{pr_number} non tenté : la CI est « "
            f"{issue.refus_ci} ». La PR reste ouverte."
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


async def attendre_verdict_sans_ci(
    etat_ci: Callable[[int], Awaitable[str]],
    dormir: Callable[[float], Awaitable[None]],
    pr_number: int,
    attente_max_s: float,
    intervalle_s: float,
) -> str:
    """Under `merge_without_ci`, waits only while the CI is `pending`.

    `none` is returned at once (declared absence of CI holds); any other
    state is a verdict. Same wait bound as the regular CI wait (ticket-1004).
    """
    ecoule = 0.0
    while True:
        etat = await etat_ci(pr_number)
        if etat != "pending":
            return etat
        if ecoule >= attente_max_s:
            return "pending"
        await dormir(intervalle_s)
        ecoule += intervalle_s
