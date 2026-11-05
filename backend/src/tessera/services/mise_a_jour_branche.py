"""Merge a PR's base into its pushed head, outside any working tree — ticket-732.

Une PR devenue conflictuelle se met à jour en fusionnant `origin/<base>` dans
sa tête poussée, jamais en réécrivant son historique (ADR-069, ADR-022). Le
geste se fait dans un worktree détaché : le checkout du projet, son index et sa
branche ne sont ni lus ni déplacés (ADR-056). Seuls les journaux qui ne font
qu'ajouter des entrées se résolvent, en union, sans agent (ADR-033).

Le module ne lève jamais vers l'appelant : tout refus est un `MiseAJour` dont
`arret` dit pourquoi, et rien n'est poussé dans ce cas.
"""
from dataclasses import dataclass
from pathlib import Path

from tessera.services.git_workspace.git_runner import git
from tessera.services.git_workspace import GitCommandError
from tessera.services.git_workspace.chemins import (
    _JOURNAL_PIPELINE,
    _JOURNAL_UNION_SUFFIXES,
    _relatif_au_projet,
)
from tessera.services.git_workspace.textes import _union_json_lists, _union_lines
from tessera.services.retest_apres_rebase import RetestApresRebase
from tessera.services.worktrees.temporary_worktree import detached_worktree, run_git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class MiseAJour:
    """What a branch update did: the pushed head, or why nothing left."""

    #: Nouvelle tête poussée ; `None` si rien n'est parti.
    sha: str | None
    #: Cause du refus ; `None` quand `sha` est rempli.
    arret: str | None
    etapes: tuple[str, ...] = ()
    #: Base dont la mise à jour est partie (ticket-733) : le journal la nomme.
    base: str = ""


class _Refus(Exception):
    """A deliberate refusal; its message becomes `MiseAJour.arret`."""


async def mettre_a_jour_branche(
    depot: Path,
    branche: str,
    base: str,
    tete_attendue: str,
    retest: RetestApresRebase | None = None,
) -> MiseAJour:
    """Merge `origin/<base>` into `branche` and push it, without forcing.

    `tete_attendue` is the head the caller knows (`pushed_sha`): any other
    remote head refuses before a worktree exists. Never raises.
    """
    etapes: list[str] = []
    try:
        sha = await _derouler(depot, branche, base, tete_attendue, retest, etapes)
    except _Refus as refus:
        return MiseAJour(sha=None, arret=str(refus), etapes=tuple(etapes), base=base)
    except Exception as exc:  # noqa: BLE001 — le watcher ne doit jamais voir une exception
        _logger.warning("mise_a_jour_branche_echouee", extra={"erreur": str(exc)})
        return MiseAJour(sha=None, arret=_cause(exc), etapes=tuple(etapes), base=base)
    return MiseAJour(sha=sha, arret=None, etapes=tuple(etapes), base=base)


def _cause(exc: Exception) -> str:
    """The readable cause of an unexpected failure, git's stderr when it has one."""
    if isinstance(exc, GitCommandError):
        return f"git a échoué : {exc.stderr.strip() or ' '.join(exc.command)}"
    return f"mise à jour impossible : {type(exc).__name__}: {exc}"


async def _derouler(
    depot: Path,
    branche: str,
    base: str,
    tete_attendue: str,
    retest: RetestApresRebase | None,
    etapes: list[str],
) -> str:
    """Fetch, check the head, merge in a throwaway worktree, push; return the new head."""
    await run_git(depot, "fetch", "origin", base, branche)
    distante = (await run_git(depot, "rev-parse", f"origin/{branche}")).strip()
    if distante != tete_attendue:
        raise _Refus(
            f"La tête de {branche} a changé : {distante[:7]} au lieu de "
            f"{tete_attendue[:7]}. Rien n'est écrit."
        )
    prefixe = (await run_git(depot, "rev-parse", "--show-prefix")).strip()
    async with detached_worktree(depot, tete_attendue) as racine:
        await _fusionner(racine, prefixe, branche, base, etapes)
        await _retester(retest, base, etapes)
        await _pousser(racine, branche, etapes)
        return (await run_git(racine, "rev-parse", "HEAD")).strip()


async def _fusionner(
    racine: Path, prefixe: str, branche: str, base: str, etapes: list[str]
) -> None:
    """Merge `origin/<base>`; journals in conflict are unioned, anything else refuses."""
    cible = f"origin/{base}"
    deja = await git(racine, "merge-base", "--is-ancestor", cible, "HEAD")
    if deja.ok:
        raise _Refus(f"{branche} porte déjà {cible} : la cause du conflit est ailleurs.")
    message = f"chore: merge {base} into {branche}"
    fusion = await git(racine, "merge", "--no-ff", "--no-edit", "-m", message, cible)
    if fusion.ok:
        etapes.append(f"{cible} fusionné dans {branche}, sans conflit")
        return
    listing = (await git(racine, "diff", "--name-only", "--diff-filter=U")).out
    conflits = [ligne.strip() for ligne in listing.splitlines() if ligne.strip()]
    if not conflits:
        raise _Refus(f"Le merge de {cible} a échoué sans conflit : {fusion.err.strip()}")
    await _resoudre_en_union(racine, prefixe, conflits)
    await run_git(racine, "commit", "-m", message)
    etapes.append(f"{cible} fusionné dans {branche}, journaux résolus en union")


async def _resoudre_en_union(racine: Path, prefixe: str, conflits: list[str]) -> None:
    """Union of every conflicting journal; refuses at the first file that is not one."""
    relatifs = [_relatif_au_projet(c, prefixe) for c in conflits]
    autres = [c for c, r in zip(conflits, relatifs) if r not in _JOURNAL_UNION_SUFFIXES]
    if autres:
        raise _Refus(
            "Conflit hors des journaux, qui ne se résout pas sans relecture : "
            + ", ".join(autres)
        )
    # Tout se calcule avant la première écriture.
    resolus = {c: await _union_du_fichier(racine, c, r) for c, r in zip(conflits, relatifs)}
    for chemin, contenu in resolus.items():
        (racine / chemin).write_bytes(contenu.encode("utf-8"))
        await run_git(racine, "add", "--", chemin)


async def _union_du_fichier(racine: Path, chemin: str, relatif: str | None) -> str:
    """The union of one journal. Merge stage 2 is the PR branch, stage 3 the base.

    L'inverse du rebase : la base vient en premier dans l'union (ticket-391).
    """
    branche = await git(racine, "show", f":2:{chemin}")
    base = await git(racine, "show", f":3:{chemin}")
    if not (branche.ok and base.ok):
        raise _Refus(f"{chemin} est supprimé d'un côté : conflit hors union.")
    if relatif == _JOURNAL_PIPELINE:
        return _union_lines(base.out, branche.out)
    union = _union_json_lists(base.out, branche.out)
    if union is None:
        raise _Refus(f"{chemin} est illisible : l'union ne s'applique pas.")
    return union


async def _retester(retest: RetestApresRebase | None, base: str, etapes: list[str]) -> None:
    """Run the project's tests before the push; a red result refuses (ADR-039)."""
    if retest is None:
        return
    jugement = await retest.juger(base)
    if jugement is None:
        return
    etapes.append(jugement.etape)
    if jugement.arret is not None:
        raise _Refus(jugement.arret)


async def _pousser(racine: Path, branche: str, etapes: list[str]) -> None:
    """Push the merged head onto the PR branch; a refused push is a refusal, not retried."""
    envoi = await git(racine, "push", "origin", f"HEAD:refs/heads/{branche}")
    if not envoi.ok:
        raise _Refus(f"Push refusé, sans nouvelle tentative : {envoi.err.strip()}")
    etapes.append(f"{branche} poussée")
