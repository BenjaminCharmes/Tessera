"""Les contrôles de la phase 1 qui ne touchent pas à l'enchaînement (ticket-700).

Sortis de `livraison.py` pour que le fichier rétrécisse : chaque fonction lit
un maillon (git, workflow) qu'on lui passe, et rend un arrêt ou une valeur.
"""
from typing import Protocol

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.livraison_resultat import Livraison
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


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


async def pr_ouverte_malgre(workflow: _WorkflowApres, branch: str) -> int | None:
    """Look for a PR already open on `branch` after a transport error.

    Never raises: a failing search keeps the original stop (ticket-455).
    """
    try:
        return await workflow.pr_ouverte_de(branch)
    except Exception as exc:  # noqa: BLE001 — la recherche ne masque pas l'erreur d'origine
        _logger.warning("recherche_pr_perdue_echouee", extra={"erreur": str(exc)})
        return None


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
