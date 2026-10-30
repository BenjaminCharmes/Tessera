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
