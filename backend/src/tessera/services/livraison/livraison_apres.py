"""Les contrôles de la phase 1 qui ne touchent pas à l'enchaînement (ticket-700).

Sortis de `livraison.py` pour que le fichier rétrécisse : chaque fonction lit
un maillon (git, workflow) qu'on lui passe, et rend un arrêt ou une valeur.
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Attentes avant les deuxième et troisième recherches d'une PR perdue : GitHub
#: lent ne la liste pas encore à l'instant de l'erreur (ticket-788).
_DELAIS_RECHERCHE_S = (2.0, 5.0)
#: Attente avant l'unique nouvelle tentative d'ouverture sur une erreur 5xx.
_DELAI_NOUVELLE_TENTATIVE_S = 5.0


class _GitApres(Protocol):
    async def commits_hors_rangement(self, depuis: str) -> list[str]: ...
    async def sha_distant(self, branch: str) -> str | None: ...


class _WorkflowApres(Protocol):
    async def pr_ouverte_de(self, branch: str) -> int | None: ...


async def branche_modifiee(git: _GitApres, approved_sha: str) -> Livraison | None:
    """The stop when the branch moved since the approval, else None.

    Fails closed (ADR-039): a branch that cannot be compared is a branch
    that changed.
    """
    try:
        intrus = await git.commits_hors_rangement(approved_sha)
    except GitWorkspaceError as exc:
        _logger.warning("comparaison_approbation_echouee", extra={"erreur": str(exc)})
        return Livraison(
            branche_modifiee=True,
            arret=(
                "la branche n'a pas pu être comparée au commit approuvé "
                f"{approved_sha[:7]} : {type(exc).__name__}"
            ),
        )
    if not intrus:
        return None
    return Livraison(
        branche_modifiee=True,
        arret=f"la branche a changé depuis l'approbation : {intrus[0][:7]}",
    )


async def sha_pousse(git: _GitApres, branch: str) -> str | None:
    """The head of `branch` on the remote; None when it cannot be read."""
    try:
        sha = await git.sha_distant(branch)
    except Exception as exc:  # noqa: BLE001 — sans lui, le watcher refuse de merger
        _logger.warning("sha_pousse_illisible", extra={"erreur": str(exc)})
        return None
    return sha if isinstance(sha, str) else None


async def chercher_pr(
    workflow: _WorkflowApres,
    branch: str,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    delais: tuple[float, ...] = _DELAIS_RECHERCHE_S,
) -> tuple[int | None, bool]:
    """Search for an open PR on `branch`, once per attempt, until one is found.

    Returns the PR number (or None) and whether the search concluded: True when
    at least one attempt answered that no PR exists. Never raises; a failing
    attempt counts as an attempt (ticket-788).
    """
    conclue = False
    for essai, delai in enumerate((0.0, *delais)):
        if essai:
            await dormir(delai)
        try:
            pr = await workflow.pr_ouverte_de(branch)
        except Exception as exc:  # noqa: BLE001 — la recherche ne masque pas l'erreur d'origine
            _logger.warning("recherche_pr_perdue_echouee", extra={"erreur": str(exc)})
            continue
        if pr is not None:
            return pr, True
        conclue = True
    return None, conclue


async def pr_ouverte_malgre(
    workflow: _WorkflowApres,
    branch: str,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    delais: tuple[float, ...] = _DELAIS_RECHERCHE_S,
) -> int | None:
    """Look for a PR already open on `branch` after a lost response or a 5xx.

    Searches up to three times with a growing wait, stops at the first PR
    found, and never raises: a failing search keeps the original stop
    (ticket-455, ticket-788).
    """
    pr, _ = await chercher_pr(workflow, branch, dormir, delais)
    return pr


async def _tenter_l_ouverture(
    ouvrir: Callable[[], Awaitable[Any]],
    workflow: _WorkflowApres,
    branch: str,
    dormir: Callable[[float], Awaitable[None]],
) -> tuple[int, Exception | None]:
    """Open once; a lost response is searched for (ticket-455).

    Returns the PR number and, when the PR was only found afterwards, the
    transport error that hid it.
    """
    try:
        return int((await ouvrir()).pr_number), None
    except httpx.TransportError as exc:
        pr_perdue = await pr_ouverte_malgre(workflow, branch, dormir)
        if pr_perdue is None:
            raise
        return pr_perdue, exc


async def ouvrir_avec_recours(
    ouvrir: Callable[[], Awaitable[Any]],
    workflow: _WorkflowApres,
    branch: str,
    etapes: list[str],
    dormir: Callable[[float], Awaitable[None]],
) -> tuple[int, Exception | None]:
    """Open the PR, surviving one GitHub server error (ticket-781).

    A 5xx first looks for a PR opened despite the error, then retries the
    opening once. A 4xx, or a second error, is raised as is.
    """
    try:
        return await _tenter_l_ouverture(ouvrir, workflow, branch, dormir)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code < 500:
            raise
        premiere = exc
        statut = exc.response.status_code
    existante, conclue = await chercher_pr(workflow, branch, dormir)
    if existante is None and not conclue:
        # Jamais de second POST tant qu'aucune recherche n'a conclu (ticket-788).
        raise premiere
    if existante is not None:
        etapes.append(f"PR #{existante} reprise malgré l'erreur {statut}")
        return existante, None
    await dormir(_DELAI_NOUVELLE_TENTATIVE_S)
    etapes.append(f"nouvelle tentative d'ouverture de la PR après l'erreur {statut}")
    return await _tenter_l_ouverture(ouvrir, workflow, branch, dormir)


def pr_a_relire(
    pr_number: int,
    etapes: tuple[str, ...],
    durees_ms: tuple[float, ...],
    resolus: list[str],
) -> Livraison:
    """The stop of a PR whose conflicts the resolver settled: open, never merged alone."""
    # Un conflit est l'endroit où deux intentions divergent : le pire
    # endroit pour deviner. Le projet a beau déclarer `merge`, il n'a
    # pas déclaré ça — et personne n'a relu la résolution.
    return Livraison(
        etapes=etapes,
        durees_ms=durees_ms,
        pr_number=pr_number,
        conflits=tuple(resolus),
        arret=(
            f"Conflit résolu sur {', '.join(resolus)} : la PR "
            f"#{pr_number} est ouverte, à relire. Une résolution de "
            "conflit ne se merge jamais toute seule."
        ),
    )
