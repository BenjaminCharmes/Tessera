"""Following the conflict resolver during a delivery — ticket-559.

Pure plumbing, no event type: `livraison.py` cannot import the event models
(they import `Livraison`, which would make a cycle). The announcer is a plain
callback, posed for the duration of a delivery by `livraison_evenements`.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Awaitable, Callable

#: Annonce une étape de la résolution d'un conflit : `(phase, fichiers, issue)`.
#: `phase` vaut « started » ou « ended » ; `issue` n'existe qu'à « ended »
#: (« resolved » ou « cancelled »).
SignalConflit = Callable[[str, tuple[str, ...], str | None], Awaitable[None]]
Resolveur = Callable[[tuple[str, ...]], Awaitable[None]]

#: `livrer` n'a qu'un argument (le résultat du run) : plutôt que d'en changer
#: la signature pour tous ses appelants, l'orchestrateur pose l'annonceur le
#: temps de l'appel.
_COURANT: ContextVar[SignalConflit | None] = ContextVar("signal_conflit", default=None)


@contextmanager
def poser_signal(signal: SignalConflit) -> Iterator[None]:
    """Make ``signal`` the announcer of the delivery launched inside the block."""
    jeton = _COURANT.set(signal)
    try:
        yield
    finally:
        _COURANT.reset(jeton)


def signal_courant() -> SignalConflit | None:
    """The announcer of the current delivery, or None outside a run."""
    return _COURANT.get()


def resolveur_suivi(
    resolus: list[str], resolveur: Resolveur | None, signal: SignalConflit | None
) -> Resolveur | None:
    """Wrap ``resolveur`` to note the files it receives and announce ``started``.

    Rend None sans résolveur : le conflit annule alors le rebase, rien n'est tenté.
    """
    if resolveur is None:
        return None

    async def suivi(fichiers: tuple[str, ...]) -> None:
        resolus.extend(fichiers)
        if signal is not None:
            await signal("started", fichiers, None)
        await resolveur(fichiers)

    return suivi


async def annoncer_fin_de_conflit(
    signal: SignalConflit | None, resolus: list[str], *, annule: bool
) -> None:
    """Announce ``ended`` once the rebase has ruled, if the resolver was called."""
    if signal is None or not resolus:
        return
    await signal("ended", tuple(resolus), "cancelled" if annule else "resolved")
