"""Le contrôle de tête d'une PR avant son merge, sorti de `ci_watcher.py` (ticket-733).

La tête de la PR doit être le commit que le pipeline a poussé (ticket-492) ;
GitHub peut montrer l'ancien quelques secondes après un push, d'où la fenêtre
de relecture (ticket-527). Ces fonctions ne décident de rien d'autre : elles
rendent la ligne d'arrêt, ou `None` quand la tête est la bonne.
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Relit le SHA de tête d'une PR ; `None` quand il ne peut pas être connu.
TetePr = Callable[[int], Awaitable[str | None]]

#: Dit si le premier SHA est un ancêtre du second : `True`, `False`, ou `None`
#: quand l'ascendance ne peut pas se vérifier (commit inconnu localement…).
EstAncetre = Callable[[str, str], Awaitable[bool | None]]

#: Fenêtre de relecture par défaut : 4 relectures espacées de 15 s, soit
#: 5 lectures sur 60 s en comptant la première (ticket-527).
_RELECTURES_TETE = 4
_INTERVALLE_RELECTURE_TETE_S = 15.0


@dataclass(frozen=True)
class ControleTete:
    """What the watcher checks before merging: the PR head is the pushed commit.

    `pushed_sha` is `None` when the delivery could not record it — the watcher
    then refuses to merge (ticket-492).

    GitHub may still show the previous commit a few seconds after a push. When
    the head read is an ancestor of `pushed_sha` — or when that cannot be
    checked — the head is read again up to `relectures` times, `intervalle_s`
    apart, before the merge is refused (ticket-527). A head that is not an
    ancestor refuses at once.
    """

    pushed_sha: str | None
    lire_tete: TetePr
    est_ancetre: EstAncetre | None = None
    relectures: int = _RELECTURES_TETE
    intervalle_s: float = _INTERVALLE_RELECTURE_TETE_S


def decrire_exception(exc: BaseException) -> str:
    """Name the exception type, then its text when it has one."""
    texte = str(exc)
    nom = type(exc).__name__
    return f"{nom}: {texte}" if texte else nom


async def verifier_tete(controle: ControleTete | None, pr_number: int) -> str | None:
    """The stop line when the PR head is not the pushed commit, else None.

    Fails closed (ADR-039): an unknown pushed commit, an unreadable head or
    a missing one all refuse the merge.
    """
    if controle is None:
        return None
    if controle.pushed_sha is None:
        return (
            f"commit poussé inconnu : la PR #{pr_number} n'est pas mergée, "
            "elle reste ouverte"
        )
    tete, arret = await _lire_tete(controle, pr_number)
    if tete is None:
        return arret
    if tete == controle.pushed_sha:
        return None
    if not await _tete_en_retard(controle, controle.pushed_sha, tete):
        return _arret_tete_changee(pr_number, tete, controle.pushed_sha)
    # Une tête en retard n'est pas une tête changée : GitHub rattrape le
    # push. On relit sur la fenêtre, sans jamais merger une autre tête.
    for _ in range(controle.relectures):
        await asyncio.sleep(controle.intervalle_s)
        tete, arret = await _lire_tete(controle, pr_number)
        if tete is None:
            return arret
        if tete == controle.pushed_sha:
            return None
    return _arret_tete_changee(pr_number, tete, controle.pushed_sha)


async def _lire_tete(
    controle: ControleTete, pr_number: int
) -> tuple[str | None, str | None]:
    """Read the PR head: `(sha, None)`, or `(None, stop line)` when unknown."""
    try:
        tete = await controle.lire_tete(pr_number)
    except Exception as exc:  # noqa: BLE001 — une tête illisible refuse le merge
        return None, (
            f"tête de la PR #{pr_number} illisible "
            f"({decrire_exception(exc)}) : elle reste ouverte"
        )
    if tete is None:
        return None, f"tête de la PR #{pr_number} inconnue : elle reste ouverte"
    return tete, None


async def _tete_en_retard(controle: ControleTete, pushed_sha: str, tete: str) -> bool:
    """True when `tete` may just be behind `pushed_sha` and is worth re-reading.

    Fails towards waiting, never towards merging: an ancestry that cannot be
    checked only delays the refusal (ADR-039).
    """
    if controle.est_ancetre is None:
        return True
    try:
        ancetre = await controle.est_ancetre(tete, pushed_sha)
    except Exception as exc:  # noqa: BLE001 — ascendance invérifiable : on relit
        _logger.warning(
            "ci_watcher_ascendance_illisible",
            extra={"erreur": decrire_exception(exc)},
        )
        return True
    return ancetre is None or ancetre


def _arret_tete_changee(pr_number: int, tete: str, pushed_sha: str) -> str:
    return (
        f"la tête de la PR #{pr_number} n'est plus le commit poussé : "
        f"{tete[:7]} au lieu de {pushed_sha[:7]}. "
        "La PR reste ouverte."
    )
