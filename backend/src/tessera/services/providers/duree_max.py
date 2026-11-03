"""A total time limit for one provider call — ticket-518.

Les bornes d'`ollama.py` (lecture) et d'`agent_sdk.py` (silence) sont
relatives : elles se remettent à zéro à chaque morceau reçu. Un flux qui
continue d'émettre, ou une file de créneaux, n'a donc pas de fin. Celle-ci
est absolue, et court sur tout l'appel.
"""
import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from tessera.services.providers.noms import ProviderIndisponible


@asynccontextmanager
async def borner(
    duree_s: float | None, *, a_l_expiration: Callable[[], None] | None = None
) -> AsyncIterator[None]:
    """Raises `ProviderIndisponible` when the body runs longer than `duree_s`.

    `None` ou une valeur ≤ 0 : pas de borne. `a_l_expiration` s'exécute
    seulement quand c'est cette borne qui a coupé — pas pour un délai d'une
    autre origine qui traverserait le bloc.
    """
    if duree_s is None or duree_s <= 0:
        yield
        return
    borne = asyncio.timeout(duree_s)
    try:
        async with borne:
            yield
    except TimeoutError as exc:
        if not borne.expired():
            raise
        if a_l_expiration is not None:
            a_l_expiration()
        raise ProviderIndisponible(
            f"durée maximale dépassée ({duree_s:.0f} s)"
        ) from exc
