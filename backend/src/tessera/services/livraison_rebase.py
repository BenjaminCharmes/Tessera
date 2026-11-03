"""What a delivery rebase did on its own, as steps of the delivery journal."""
from typing import Protocol

from tessera.services.retest_apres_rebase import RetestApresRebase
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class _TeteDeBranche(Protocol):
    async def head_sha(self) -> str: ...
    async def remettre_sur(self, sha: str) -> None: ...


def noter_ce_que_le_rebase_a_fait(
    git: object,
    etapes: list[str],
    durees_ms: list[float],
    resolus: list[str],
) -> None:
    """Appends one step per renumbered migration and per rule-settled conflict.

    Reads `migrations_renumerotees` and `regles_appliquees` off the workspace
    (absent on a double: nothing to note). A rule-settled file joins `resolus`
    like a resolver's: ADR-033 keeps its PR from merging alone, nobody having
    reread it either.
    """
    for ancien, nouveau in getattr(git, "migrations_renumerotees", ()):
        etapes.append(
            f"migration renumérotée : {ancien.rpartition('/')[2]}"
            f" → {nouveau.rpartition('/')[2]}"
        )
        durees_ms.append(0.0)
    for fichier, regle in getattr(git, "regles_appliquees", ()):
        etapes.append(f"conflit résolu par règle : {fichier} ({regle})")
        durees_ms.append(0.0)
        if fichier not in resolus:
            resolus.append(fichier)


async def tete_avant_rebase(git: _TeteDeBranche) -> str | None:
    """The branch head to come back to, or None when git cannot say (ticket-740)."""
    try:
        return await git.head_sha()
    except Exception as exc:  # noqa: BLE001 — sans tête notée, la remise dira qu'elle n'a pas eu lieu
        _logger.warning("tete_avant_rebase_illisible", extra={"erreur": str(exc)})
        return None


async def retester_apres_rebase(
    git: _TeteDeBranche,
    retest: RetestApresRebase | None,
    base: str,
    sha_avant: str | None,
    resolus: list[str],
    etapes: list[str],
    durees_ms: list[float],
) -> str | None:
    """Replay the tests when `retest` is given; the stop on red, else None.

    Un rouge ne pousse rien : le travail passait sur l'ancienne base
    (ticket-568). Ni reviewer ni validateur, le diff n'a pas changé. La branche
    ne reste pas rebasée sur un travail qui ne passe plus (ticket-740).
    """
    jugement = await retest.juger(base) if retest is not None else None
    if jugement is None:
        return None
    etapes.append(jugement.etape)
    durees_ms.append(jugement.duree_ms)
    if jugement.arret is None:
        return None
    return await remettre_la_branche(git, sha_avant, resolus, etapes, durees_ms, jugement.arret)


async def remettre_la_branche(
    git: _TeteDeBranche,
    sha_avant: str | None,
    resolus: list[str],
    etapes: list[str],
    durees_ms: list[float],
    arret: str,
) -> str:
    """Put the branch back on its pre-rebase head after a red retest; the stop to return.

    La tête d'avant porte les commits de rangement du pipeline : c'est l'état
    approuvé (ADR-039). Une remise impossible n'est jamais passée sous silence,
    et rien n'est poussé dans tous les cas.
    """
    if sha_avant is None:
        etapes.append("branche non remise : tête d'avant le rebase inconnue")
        durees_ms.append(0.0)
        return f"{arret}\nLa branche locale reste rebasée : sa tête d'avant le rebase est inconnue."
    court = sha_avant[:7]
    abandon = " ; résolution de conflit abandonnée" if resolus else ""
    try:
        await git.remettre_sur(sha_avant)
    except Exception as exc:  # noqa: BLE001 — l'arrêt dit que la remise a échoué
        _logger.warning("remise_de_branche_echouee", extra={"sha": court, "erreur": str(exc)})
        etapes.append(f"branche non remise sur {court} : {type(exc).__name__}")
        durees_ms.append(0.0)
        return f"{arret}\nLa branche n'a pas pu être remise sur {court} : elle reste rebasée ({exc})."
    etapes.append(f"branche remise sur {court}{abandon}")
    durees_ms.append(0.0)
    return f"{arret}\nBranche remise sur {court}{abandon}."
