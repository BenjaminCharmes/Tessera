"""Retry of transient GitHub 5xx answers — ticket-461.

A 502, 503 or 504 means GitHub is briefly unavailable, not that the request
was refused. Phase 2 of the delivery (CI read, merge) retries them instead of
giving up a merge whose CI is green. Any other status is returned untouched.
"""
import asyncio
from collections.abc import Awaitable, Callable

import httpx

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Statuts qui signalent une indisponibilité passagère de GitHub.
STATUTS_REESSAYABLES: frozenset[int] = frozenset({502, 503, 504})

#: Attentes avant chaque nouvel essai : trois réessais, donc quatre appels au plus.
ATTENTES_S: tuple[float, ...] = (1.0, 2.0, 4.0)

Dormir = Callable[[float], Awaitable[None]]


async def reessayer_5xx(
    appel: Callable[[], Awaitable[httpx.Response]],
    dormir: Dormir = asyncio.sleep,
    attentes_s: tuple[float, ...] = ATTENTES_S,
) -> httpx.Response:
    """Call `appel` again while GitHub answers 502, 503 or 504.

    Waits `attentes_s[i]` seconds before retry `i`. Once the retries are
    spent, the last response is returned as is, so the caller's own error
    handling (`raise_for_status`, status mapping) applies unchanged.
    """
    reponse = await appel()
    for attente in attentes_s:
        if reponse.status_code not in STATUTS_REESSAYABLES:
            break
        _logger.warning(
            "github_5xx_retry",
            extra={"status": reponse.status_code, "attente_s": attente},
        )
        await dormir(attente)
        reponse = await appel()
    return reponse
